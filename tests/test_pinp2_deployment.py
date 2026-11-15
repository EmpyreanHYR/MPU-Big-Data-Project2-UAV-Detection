"""NumPy-only deployment behavior tests: no Torch/model or Hailo inference."""
from pathlib import Path
import sys
import unittest
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts/deployment'))
from pinp2_postprocess import PinP2Postprocessor, load_policy
from raw_head_decode import decode as historical_decode


class PinP2DeploymentTests(unittest.TestCase):
    def test_default_suppresses_iou_between_four_and_five(self):
        boxes = np.array([[0,0,10,10,.9,0], [3.8,0,13.8,10,.8,0]], np.float32)
        decoder = PinP2Postprocessor()
        self.assertEqual(decoder.policy['nms_iou'], .4)
        np.testing.assert_array_equal(decoder.filter(boxes), boxes[:1])
        policy = load_policy(); policy['nms_iou'] = .5
        self.assertEqual(len(PinP2Postprocessor(policy).filter(boxes)), 2)
        self.assertEqual(decoder.receipt()['suppressed'], 1)

    def test_end_to_end_head_actually_flows_through_nms(self):
        boxes = np.array([[[[.5,1.5]], [[.5,.5]], [[1.,0.]], [[1.,1.]]]], np.float32)
        scores = np.array([[[[4.,3.]]]], np.float32)
        meta = {'family':'e2e','strides':[4],'reg_max':1}
        geometry = (1.,0,0,64,64)
        raw = historical_decode([boxes,scores], meta, geometry)
        self.assertEqual(len(raw), 2)
        actual = PinP2Postprocessor().decode([boxes,scores], meta, geometry)
        np.testing.assert_array_equal(actual, raw[:1])
        np.testing.assert_array_equal(actual[0,:4], [0,0,6,6])

    def test_tied_scores_keep_first_and_do_not_move_boxes(self):
        boxes = np.array([[0,0,5,5,.8,0],[0,0,5,5,.8,0],[10,10,14,14,.7,0]],np.float32)
        np.testing.assert_array_equal(PinP2Postprocessor().filter(boxes), boxes[[0,2]])

    def test_empty_and_disabled_policy(self):
        self.assertEqual(PinP2Postprocessor().filter(np.empty((0,6))).shape, (0,6))
        policy = load_policy(); policy['nms_enabled'] = False
        with self.assertRaises(ValueError): PinP2Postprocessor(policy)
        with self.assertRaises(ValueError): PinP2Postprocessor().filter(np.array([[0,0,1,1,.8,1]]))

if __name__ == '__main__': unittest.main()
