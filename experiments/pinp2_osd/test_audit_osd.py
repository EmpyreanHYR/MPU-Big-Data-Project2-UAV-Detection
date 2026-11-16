"""Metric safety checks; no detector or remote device is involved."""
import unittest
import numpy as np
from audit_osd import audit, overlap_fraction


class AuditTests(unittest.TestCase):
    def run_case(self, boxes, regions):
        return audit({"sample": np.asarray(boxes, np.float32).reshape(-1, 6)},
                     [{"image": "sample", "UAV_boxes": [[0, 0, 10, 10]]}],
                     {"sample": regions}, ap_available=False)[0]

    def test_partial_overlap_is_prediction_area(self):
        np.testing.assert_allclose(overlap_fraction([[0, 0, 10, 10]], [[0, 0, 100, 5]]), [.5])

    def test_filtering_a_true_detection_retains_gt_and_adds_miss(self):
        r = self.run_case([[0, 0, 10, 10, .9, 0]], [[0, 0, 10, 10]])
        self.assertEqual((r["before"]["TP"], r["after"]["TP"], r["after"]["FN"]), (1, 0, 1))
        self.assertEqual(r["removed_original_TP"], 1)
        self.assertIsNone(r["after"]["mAP50_95_deployment"])

    def test_surviving_duplicate_is_rematched(self):
        r = self.run_case([[0, 0, 10, 10, .9, 0], [2, 0, 12, 10, .8, 0]], [[0, 0, 5, 10]])
        self.assertEqual(r["removed_original_TP"], 1)
        self.assertEqual((r["after"]["TP"], r["after"]["FP"], r["after"]["FN"]), (1, 0, 0))

    def test_no_timestamp_does_not_filter_corner_detections(self):
        r = self.run_case([[0, 0, 10, 10, .9, 0]], [])
        self.assertEqual(r["before"], r["after"])

    def test_missing_region_review_fails_closed(self):
        with self.assertRaises(AssertionError):
            audit({"sample": np.empty((0, 6))}, [{"image": "sample", "UAV_boxes": [[0, 0, 1, 1]]}], {})


if __name__ == "__main__":
    unittest.main()
