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



if __name__ == "__main__":
    unittest.main()
