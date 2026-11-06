import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('pretrained_queue', ROOT / 'scripts/run_pretrained_baseline.py')
queue = importlib.util.module_from_spec(spec)
spec.loader.exec_module(queue)


class PretrainedQueueTests(unittest.TestCase):
    def test_only_initialization_changes(self):
        scratch = json.loads((ROOT / 'configs/experiments/four_source150/baseline.json').read_text())
        actual = queue.settings(ROOT)
        for key, value in scratch.items():
            if key not in {'model', 'task', 'variant', 'pretrained'}:
                self.assertEqual(actual[key], value)
        self.assertTrue(actual['pretrained'])
        self.assertFalse(actual['resume'])

    def test_wait_and_failure_do_not_start(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'status.json').write_text('{"status":"waiting_existing_queue"}')
            self.assertFalse(queue.previous_ready(root))
            (root / 'status.json').write_text('{"status":"failed"}')
            with self.assertRaises(RuntimeError):
                queue.previous_ready(root)

    def test_all_adapter_completions_required(self):
        jobs = ['fasterrcnn_r50_fpn', 'pconv_sdloss_yolov8n_p2', 'msf_ghostnet_iii']
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'status.json').write_text('{"status":"completed"}')
            (root / 'plan.json').write_text(json.dumps({'jobs': jobs}))
            for job in jobs[:2]:
                (root / job).mkdir()
                (root / job / 'completed.json').write_text('{"epochs":150}')
            self.assertFalse(queue.previous_ready(root))
            (root / jobs[2]).mkdir()
            (root / jobs[2] / 'completed.json').write_text('{"epochs":149}')
            self.assertFalse(queue.previous_ready(root))
            (root / jobs[2] / 'completed.json').write_text('{"epochs":150}')
            self.assertTrue(queue.previous_ready(root))


if __name__ == '__main__':
    unittest.main()
