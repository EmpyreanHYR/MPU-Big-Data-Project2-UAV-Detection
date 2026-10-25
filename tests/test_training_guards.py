from datetime import datetime, timedelta, timezone
from pathlib import Path
import json
import sys
import tempfile
import unittest
from unittest.mock import patch, Mock
from types import SimpleNamespace
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from uav_detection.training import read_experiment, require_training_host, training_window


class TrainingGuards(unittest.TestCase):
    def test_three_variant_configs_and_mismatch(self):
        root = Path(__file__).resolve().parents[1]
        for variant in ("baseline", "pconv", "p2"):
            settings = read_experiment(root / f"configs/experiments/yolo26n_{variant}.json")
            self.assertEqual(settings["variant"], variant)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "bad.json"
            path.write_text(json.dumps(settings | {"model": "yolo26n-pconv.yaml"}))
            with self.assertRaises(ValueError):
                read_experiment(path)

    def test_mac_train_entry_stops_before_model_build(self):
        from uav_detection.training import train_detector
        root = Path(__file__).resolve().parents[1]
        with patch("platform.system", return_value="Darwin"), patch("uav_detection.modeling.build_detector") as build:
            with self.assertRaises(RuntimeError):
                train_detector(root/"configs/experiments/yolo26n_baseline.json", "missing.yaml", "missing.pt", "unused", "2999-01-01T00:00:00Z", 1)
            build.assert_not_called()

    def test_mac_and_pi_rejected_before_torch_import(self):
        for system, machine in [("Darwin", "arm64"), ("Linux", "aarch64")]:
            with self.subTest(system=system), patch("platform.system", return_value=system), patch("platform.machine", return_value=machine):
                with self.assertRaises(RuntimeError):
                    require_training_host()

    def test_expired_or_naive_deadline_rejected(self):
        now = datetime(2026, 10, 23, tzinfo=timezone.utc)
        for value in ["2026-10-22T00:00:00Z", "2026-10-24T00:00:00"]:
            with self.assertRaises(ValueError):
                training_window(value, 8, now)

    def test_window_is_bounded_by_deadline_and_eight_hours(self):
        now = datetime(2026, 10, 23, tzinfo=timezone.utc)
        self.assertEqual(training_window("2026-10-23T02:00:00Z", 8, now), 2)
        with self.assertRaises(ValueError):
            training_window("2026-10-24T00:00:00Z", 9, now)

    def test_wrong_model_or_cpu_config_rejected(self):
        base = {"model": "yolo26n.yaml", "task": "detect", "epochs": 300,
                "imgsz": 640, "batch": 4, "device": 0}
        with tempfile.TemporaryDirectory() as folder:
            file = Path(folder) / "experiment.json"
            for changes in [{"model": "yolov8n.yaml"}, {"task": "segment"}, {"device": "cpu"}, {"epochs": 301}]:
                file.write_text(json.dumps(base | changes))
                with self.assertRaises(ValueError):
                    read_experiment(file)


    def budget(self, max_hours=1, deadline="2026-10-24T14:00:00Z"):
        from uav_detection.training import BudgetStopCallback
        clock={"utc":datetime(2026,10,24,12,tzinfo=timezone.utc),"mono":100.0}
        callback=BudgetStopCallback(deadline,max_hours,300,
                                    utc_now=lambda:clock["utc"],monotonic=lambda:clock["mono"])
        return callback,clock

    def test_budget_callback_normal_path_does_not_stop_or_change_epochs(self):
        callback,clock=self.budget()
        trainer=SimpleNamespace(stop=False,epoch=4,epochs=300)
        clock['mono']+=60;clock['utc']+=timedelta(seconds=60)
        callback(trainer)
        self.assertFalse(trainer.stop)
        self.assertEqual(trainer.epochs,300)
        self.assertIsNone(callback.reason)
        self.assertEqual(callback.policy()['save_buffer_seconds'],90)

    def test_monotonic_budget_stops_even_if_utc_does_not_advance(self):
        callback,clock=self.budget();trainer=SimpleNamespace(stop=False,epoch=10,epochs=300)
        clock['mono']+=callback.stop_after_seconds
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'training_budget.json';callback.attach(path);callback(trainer)
            self.assertTrue(trainer.stop)
            self.assertEqual(trainer.epochs,300)
            record=json.loads(path.read_text())
            self.assertEqual(record['stop_reason'],'monotonic_window_save_buffer')
            self.assertEqual(record['status'],'stop_requested')
            self.assertEqual(record['epochs_observed'],11)
            self.assertEqual(record['deadline_utc'],'2026-10-24T14:00:00+00:00')

    def test_utc_deadline_stops_even_when_monotonic_does_not_advance(self):
        callback,clock=self.budget(max_hours=8,deadline='2026-10-24T12:10:00Z')
        trainer=SimpleNamespace(stop=False,epoch=0,epochs=300)
        self.assertEqual(callback.stop_after_seconds,510)
        clock['utc']+=timedelta(seconds=510);callback(trainer)
        self.assertTrue(trainer.stop)
        self.assertEqual(callback.reason,'utc_window_save_buffer')
        trainer.stop=False;callback(trainer)
        self.assertTrue(trainer.stop)

    def test_too_short_or_preparation_consumed_window_rejects_before_training(self):
        from uav_detection.training import BudgetStopCallback
        now=datetime(2026,10,24,12,tzinfo=timezone.utc)
        with self.assertRaises(ValueError):
            BudgetStopCallback('2026-10-24T12:01:00Z',1,300,utc_now=lambda:now,monotonic=lambda:1)
        callback,clock=self.budget();clock['mono']+=3600
        with self.assertRaises(TimeoutError):callback.require_remaining_window()

    def test_mock_training_preserves_300_epochs_without_ultralytics_time(self):
        from uav_detection.training import train_detector
        root=Path(__file__).resolve().parents[1]
        events={};fake=SimpleNamespace(overrides={'time':8},transfer_report={'policy':'mock'},
                                      trainer=SimpleNamespace(epoch=299,stop=False))
        fake.add_callback=lambda event,handler:events.setdefault(event,handler)
        fake.train=Mock(return_value='mock-result')
        now=datetime(2026,10,24,12,tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp);data=folder/'dataset.yaml';data.write_text('names: {0: uav}\n')
            (folder/'manifest.json').write_text('{}');weights=folder/'official.pt';weights.write_bytes(b'mock')
            output=folder/'run'
            with patch('uav_detection.training.require_training_host'), \
                 patch('uav_detection.data.prepare.audit_prepared'), \
                 patch('uav_detection.modeling.build_detector',return_value=fake), \
                 patch.dict(sys.modules, {'ultralytics.utils.torch_utils':SimpleNamespace(init_seeds=Mock())}), \
                 patch('uav_detection.training._utc_now',return_value=now), \
                 patch('uav_detection.training.time.monotonic',return_value=100):
                value=train_detector(root/'configs/experiments/yolo26n_baseline.json',data,weights,
                                     output,'2026-10-24T14:00:00Z',1)
            self.assertEqual(value,'mock-result')
            kwargs=fake.train.call_args.kwargs
            self.assertEqual(kwargs['epochs'],300)
            self.assertNotIn('time',kwargs)
            self.assertNotIn('time',fake.overrides)
            self.assertEqual(set(events),{'on_train_batch_end','on_train_epoch_end'})
            self.assertIs(events['on_train_batch_end'],events['on_train_epoch_end'])
            initial=json.loads((output/'initialization.json').read_text())
            self.assertEqual(initial['training_budget']['epoch_limit'],300)
            final=json.loads((output/'training_budget.json').read_text())
            self.assertEqual(final['stop_reason'],'epoch_limit')
            self.assertEqual(final['status'],'returned')



    def test_matched92_configs_retain_original_schedule_and_explicit_adamw(self):
        root=Path(__file__).resolve().parents[1]
        expected={'optimizer':'AdamW','lr0':.002,'momentum':.9,
                  'weight_decay':.0005,'lrf':.01,'nbs':64,'stop_after_epochs':92,'warmup_bias_lr':0.0}
        for variant in ('pconv','p2'):
            original=read_experiment(root/f'configs/experiments/yolo26n_{variant}.json')
            matched=read_experiment(root/f'configs/experiments/yolo26n_{variant}_matched92.json')
            self.assertEqual(matched,original|expected)
            self.assertEqual(matched['epochs'],300)
            self.assertEqual((matched['batch'],matched['seed'],matched['imgsz']),(4,42,640))

    def test_matched92_policy_rejects_bad_optimizer_and_numeric_settings(self):
        root=Path(__file__).resolve().parents[1]
        base=read_experiment(root/'configs/experiments/yolo26n_pconv_matched92.json')
        changes=[{'stop_after_epochs':92.0},{'stop_after_epochs':True},{'stop_after_epochs':0},
                 {'stop_after_epochs':301},{'optimizer':'SGD'},{'lr0':float('nan')},
                 {'lr0':0},{'lr0':True},{'lr0':'.002'},{'momentum':1},
                 {'momentum':float('inf')},{'weight_decay':-.001},{'lrf':0},
                 {'nbs':64.0},{'nbs':True},{'nbs':0},{'warmup_bias_lr':-0.1},
                 {'warmup_bias_lr':float('nan')},{'warmup_bias_lr':True},{'unexpected_optimizer_option':1}]
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'experiment.json'
            for change in changes:
                path.write_text(json.dumps(base|change))
                with self.subTest(change=change),self.assertRaises(ValueError):read_experiment(path)
            missing=dict(base);missing.pop('lr0');path.write_text(json.dumps(missing))
            with self.assertRaises(ValueError):read_experiment(path)

    def test_complete_epoch_callback_keeps_budget_priority(self):
        from uav_detection.training import CompleteEpochStopCallback
        budget,clock=self.budget();stop=CompleteEpochStopCallback(92,budget)
        trainer=SimpleNamespace(stop=False,epoch=90,epochs=300)
        stop(trainer);self.assertFalse(trainer.stop)
        trainer.epoch=91
        budget(trainer)  # A batch at epoch 92 does not meet the complete-epoch policy.
        self.assertFalse(trainer.stop)
        stop(trainer)
        self.assertTrue(trainer.stop)
        self.assertEqual(budget.reason,'matched_complete_epoch_limit')
        self.assertEqual(trainer.epochs,300)
        self.assertEqual(budget.epochs_observed,92)
        budget,clock=self.budget();stop=CompleteEpochStopCallback(92,budget)
        trainer=SimpleNamespace(stop=False,epoch=91,epochs=300)
        clock['mono']+=3600;stop(trainer)
        self.assertTrue(trainer.stop)
        self.assertEqual(budget.reason,'monotonic_window_save_buffer')

    def test_mock_matched92_train_kwargs_and_complete_epoch_stop(self):
        from uav_detection.training import train_detector
        root=Path(__file__).resolve().parents[1]
        now=datetime(2026,10,24,12,tzinfo=timezone.utc)
        for variant in ('pconv','p2'):
            with self.subTest(variant=variant),tempfile.TemporaryDirectory() as tmp:
                events={};fake=SimpleNamespace(overrides={'time':8},transfer_report={'policy':'mock'},
                                              trainer=SimpleNamespace(epoch=90,stop=False,epochs=300))
                fake.add_callback=lambda event,handler:events.setdefault(event,[]).append(handler)
                captured={}
                def mocked_train(**kwargs):
                    captured.update(kwargs)
                    for event in ('on_train_batch_end','on_train_epoch_end'):
                        for handler in events[event]:handler(fake.trainer)
                    self.assertFalse(fake.trainer.stop)
                    fake.trainer.epoch=91
                    for handler in events['on_train_batch_end']:handler(fake.trainer)
                    self.assertFalse(fake.trainer.stop)
                    for handler in events['on_train_epoch_end']:handler(fake.trainer)
                    self.assertTrue(fake.trainer.stop)
                    return 'mock-matched-result'
                fake.train=Mock(side_effect=mocked_train)
                folder=Path(tmp);data=folder/'dataset.yaml';data.write_text('names: {0: uav}\n')
                (folder/'manifest.json').write_text('{}');weights=folder/'official.pt';weights.write_bytes(b'mock')
                output=folder/'run'
                with patch('uav_detection.training.require_training_host'), \
                     patch('uav_detection.data.prepare.audit_prepared'), \
                     patch('uav_detection.modeling.build_detector',return_value=fake), \
                     patch.dict(sys.modules, {'ultralytics.utils.torch_utils':SimpleNamespace(init_seeds=Mock())}), \
                     patch('uav_detection.training._utc_now',return_value=now), \
                     patch('uav_detection.training.time.monotonic',return_value=100):
                    result=train_detector(root/f'configs/experiments/yolo26n_{variant}_matched92.json',
                                          data,weights,output,'2026-10-24T14:00:00Z',1)
                self.assertEqual(result,'mock-matched-result')
                self.assertEqual(captured['epochs'],300)
                self.assertNotIn('time',captured)
                self.assertNotIn('stop_after_epochs',captured)
                self.assertEqual({k:captured[k] for k in ('optimizer','lr0','momentum','weight_decay','lrf','nbs','warmup_bias_lr')},
                                 {'optimizer':'AdamW','lr0':.002,'momentum':.9,'weight_decay':.0005,'lrf':.01,'nbs':64,'warmup_bias_lr':0.0})
                self.assertEqual(len(events['on_train_batch_end']),1)
                self.assertEqual(len(events['on_train_epoch_end']),2)
                self.assertIs(events['on_train_batch_end'][0],events['on_train_epoch_end'][0])
                record=json.loads((output/'training_budget.json').read_text())
                self.assertEqual(record['stop_reason'],'matched_complete_epoch_limit')
                self.assertEqual(record['stop_after_complete_epochs'],92)
                self.assertEqual(record['epochs_observed'],92)
                self.assertEqual(record['epoch_limit'],300)



if __name__ == "__main__":
    unittest.main()
