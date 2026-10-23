from datetime import datetime, timezone
from pathlib import Path
import json
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from uav_detection.training import read_experiment, require_training_host, training_window


class TrainingGuards(unittest.TestCase):
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
            for changes in [{"model": "yolov8n.yaml"}, {"task": "segment"}, {"device": "cpu"}]:
                file.write_text(json.dumps(base | changes))
                with self.assertRaises(ValueError):
                    read_experiment(file)


if __name__ == "__main__":
    unittest.main()
