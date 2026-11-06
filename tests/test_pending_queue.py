import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
from run_pending_suite import previous_ready


class PendingQueueTests(unittest.TestCase):
    def make(self, root, status, complete=7):
        (root / "status.json").write_text(json.dumps({"status": status}))
        jobs = [f"job{i}" for i in range(7)]
        (root / "plan.json").write_text(json.dumps({"jobs": jobs}))
        for job in jobs[:complete]:
            (root / job).mkdir()
            (root / job / "completed.json").write_text('{"epochs":150}')

    def test_running_queue_never_overlaps(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.make(root, "running")
            self.assertFalse(previous_ready(root))

    def test_failed_queue_is_not_bypassed(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.make(root, "failed")
            with self.assertRaisesRegex(RuntimeError, "do not bypass"):
                previous_ready(root)

    def test_all_seven_completion_markers_required(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.make(root, "completed_ready_jobs", complete=6)
            self.assertFalse(previous_ready(root))
            (root / "job6").mkdir()
            (root / "job6/completed.json").write_text('{"epochs":150}')
            self.assertTrue(previous_ready(root))


if __name__ == "__main__":
    unittest.main()
