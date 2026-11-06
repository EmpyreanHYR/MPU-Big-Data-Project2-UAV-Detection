import importlib.util
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location("serial_suite", Path(__file__).resolve().parents[1] / "scripts/run_serial_suite.py")
suite = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(suite)


class SerialSuiteTests(unittest.TestCase):
    def test_failure_stops_before_second_model_without_retry(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            args = SimpleNamespace(authorized=True, output=root / "out", data=root / "data", max_job_seconds=86400)
            with patch.object(suite, "ROOT", root), patch.object(suite, "validate_data", return_value={}), \
                 patch.object(suite, "job_settings", return_value={}), \
                 patch.object(suite.subprocess, "Popen") as launch, \
                 patch.object(suite.signal, "signal"):
                launch.return_value.wait.return_value = 7
                launch.return_value.pid = 12345
                with self.assertRaises(SystemExit) as failure:
                    suite.supervisor(args)
                self.assertEqual(failure.exception.code, 7)
                self.assertEqual(launch.call_count, 1)
                self.assertTrue(launch.call_args.kwargs["start_new_session"])
                self.assertEqual(json.loads((args.output / "status.json").read_text())["status"], "failed")

    def test_manifest_hash_tampering_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "provenance").mkdir()
            (root / "sample.jpg").write_bytes(b"changed")
            (root / "provenance/manifest_exported.csv").write_text(
                "split,output_image,output_image_sha256\ntrain,sample.jpg,wrong\n")
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                suite.validate_data(root)

    def test_queued_models_are_scratch_full_schedule(self):
        for job in suite.JOBS:
            settings = suite.job_settings(job)
            self.assertEqual(settings["epochs"], 150)
            self.assertEqual(settings["seed"], 42)
            self.assertIs(settings["pretrained"], False)
            self.assertIs(settings["amp"], False)
            self.assertEqual(settings["patience"], 0)
        self.assertFalse(set(suite.PENDING) & set(suite.JOBS))


if __name__ == "__main__":
    unittest.main()
