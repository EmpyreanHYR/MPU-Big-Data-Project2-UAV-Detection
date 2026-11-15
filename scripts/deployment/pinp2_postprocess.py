"""Explicit PinP2 deployment NMS; the historical evaluator stays unchanged."""
import json
from pathlib import Path
import sys
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts/evaluation'))
from detection_eval import nms
from raw_head_decode import decode as decode_raw_heads

DEFAULT_CONFIG = ROOT / 'configs/deployment/pinp2_h10.json'


def load_policy(path=DEFAULT_CONFIG):
    return validate_policy(json.loads(Path(path).read_text()))


def validate_policy(policy):
    policy = dict(policy)
    if policy.get('nms_enabled') is not True:
        raise ValueError('PinP2 deployment requires explicit NMS enabled')
    if policy.get('family') != 'e2e' or policy.get('model_id') != 'scratch100__pconv_p2':
        raise ValueError('This deployment policy is only for the frozen PinP2 model')
    if not 0 < policy['nms_iou'] < 1 or policy['max_detections'] != 300:
        raise ValueError('Invalid NMS threshold or unsupported candidate cap')
    if policy['confidence'] != .25 or policy['input_size'] != 640:
        raise ValueError('This deployment requires the validated confidence/input protocol')
    if policy['nms_coordinate_space'] != 'original_image_after_clipping':
        raise ValueError('NMS must run after original-coordinate restoration and clipping')
    return policy


class PinP2Postprocessor:
    """Call the raw decoder, then real greedy NMS at the selected threshold."""

    def __init__(self, policy=None):
        self.policy = load_policy() if policy is None else validate_policy(policy)
        self.calls = 0
        self.candidates_before = 0
        self.candidates_after = 0

    def filter(self, detections):
        detections = np.asarray(detections)
        if detections.ndim != 2 or detections.shape[1] != 6:
            raise ValueError('Expected Nx6 original-coordinate detections')
        if not np.isfinite(detections).all() or np.any(detections[:, 5] != 0):
            raise ValueError('Expected finite, single-class detections')
        if len(detections) and np.any(detections[:, 2:4] <= detections[:, :2]):
            raise ValueError('Boxes must have positive area')
        keep = nms(detections[:, :4], detections[:, 4],
                   threshold=self.policy['nms_iou'],
                   max_det=self.policy['max_detections'])
        result = detections[keep]
        self.calls += 1
        self.candidates_before += len(detections)
        self.candidates_after += len(result)
        return result

    def decode(self, outputs, metadata, geometry, confidence=None):
        if metadata['family'] != self.policy['family']:
            raise ValueError('Model family differs from the deployment policy')
        confidence = self.policy['confidence'] if confidence is None else confidence
        restored = decode_raw_heads(outputs, metadata, geometry, confidence)
        return self.filter(restored)

    def receipt(self):
        return {'nms_applied': True, 'nms_iou_effective': self.policy['nms_iou'],
                'coordinate_space': self.policy['nms_coordinate_space'],
                'max_detections': self.policy['max_detections'],
                'calls': self.calls, 'candidates_before': self.candidates_before,
                'candidates_after': self.candidates_after,
                'suppressed': self.candidates_before - self.candidates_after}
