"""Protocol and initialization guards; never imports a model backend."""
from pathlib import Path
import json
import sys
import tempfile
import unittest
from unittest.mock import patch, Mock
from types import SimpleNamespace
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from uav_detection.training import read_experiment, train_detector
from uav_detection.comparison import comparison_spec


class ScratchProtocol(unittest.TestCase):
    def test_four_variants_share_scratch_protocol(self):
        for variant in ('baseline','pconv','p2','pconv_p2'):
            s=read_experiment(ROOT/f'configs/experiments/four_source150/{variant}.json')
            self.assertEqual(s['variant'],variant)
            self.assertEqual((s['epochs'],s['seed']),(150,42))
            self.assertIs(s['pretrained'],False)
            self.assertIs(s['amp'],False)

    def test_detector_and_backbone_weights_disabled(self):
        s,common=comparison_spec('fasterrcnn_r50_fpn')
        self.assertIsNone(s['constructor_kwargs']['weights'])
        self.assertIsNone(s['constructor_kwargs']['weights_backbone'])
        self.assertIs(common['resume'],False)

    def test_scratch_rejects_weights_before_data_or_model_loading(self):
        with patch('uav_detection.training.require_training_host'), \
             patch('uav_detection.training._utc_now',return_value=datetime(2026,10,30,tzinfo=timezone.utc)), \
             patch('uav_detection.modeling.build_detector') as build:
            with self.assertRaisesRegex(ValueError,'Scratch initialization forbids'):
                train_detector(ROOT/'configs/experiments/four_source150/baseline.json',
                               'missing/dataset.yaml','old.pt','unused','2026-10-30T02:00:00Z',1)
            build.assert_not_called()

    def test_train_sources_and_demo_never_include_external_test(self):
        p=json.loads((ROOT/'configs/protocols/four_source_uav_scratch150.json').read_text())
        self.assertEqual(p['train_validation']['ratio'],[8,2])
        self.assertEqual(set(p['train_validation']['datasets']),
                         {'SIRST-UAVB','UAV-CB','Tri-Modal Anti-UAV','AUVD-Seg300'})
        self.assertEqual(p['test']['requested_dataset'],'Anti-UAV-detection')
        self.assertIs(p['test']['use_entire_selected_dataset_as_test'],True)
        self.assertIs(p['test']['require_source_sequence_disjoint_from_train_validation'],True)
        self.assertIs(p['test']['keep_empty_labels_as_negatives'],True)
        self.assertIs(p['test']['in_training'],False)
        self.assertIs(p['test']['used_for_checkpoint_selection'],False)
        self.assertEqual(p['videos']['required'],3)
        self.assertIs(p['authorization']['start_training'],True)

    def test_scratch_entry_passes_no_checkpoint_and_150_epochs(self):
        fake=SimpleNamespace(overrides={}, transfer_report={'policy':'random'},
                             trainer=SimpleNamespace(epoch=149,stop=False),
                             add_callback=Mock(),train=Mock(return_value='synthetic'))
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp); data=folder/'dataset.yaml';data.write_text('names: {0: uav}\n')
            (folder/'manifest.json').write_text('{}')
            with patch('uav_detection.training.require_training_host'), \
                 patch('uav_detection.training._utc_now',return_value=datetime(2026,10,30,tzinfo=timezone.utc)), \
                 patch('uav_detection.data.prepare.audit_prepared'), \
                 patch('uav_detection.modeling.build_detector',return_value=fake) as build, \
                 patch.dict(sys.modules, {'ultralytics.utils.torch_utils':SimpleNamespace(init_seeds=Mock())}):
                train_detector(ROOT/'configs/experiments/four_source150/pconv_p2.json',
                               data,None,folder/'run','2026-10-30T02:00:00Z',1)
            build.assert_called_once_with('pconv_p2',None)
            self.assertEqual(fake.train.call_args.kwargs['epochs'],150)
            self.assertIs(fake.train.call_args.kwargs['pretrained'],False)
            provenance=json.loads((folder/'run/initialization.json').read_text())
            self.assertIsNone(provenance['weights_sha256'])
            self.assertEqual(provenance['initialization_mode'],'random')


if __name__=='__main__':unittest.main()
