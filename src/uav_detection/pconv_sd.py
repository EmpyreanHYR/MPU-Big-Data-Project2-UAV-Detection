"""YOLOv8n-P2 adaptation with author PConv and complete SDB regression loss.

Positions 0/1 are an explicit project integration choice, not an exact claim of
the paper's training recipe. DFL, assignment and classification stay native.
"""
from copy import deepcopy
import torch
from ultralytics import YOLO
from ultralytics.nn.tasks import DetectionModel, yaml_model_load
from ultralytics.models.yolo.detect import DetectionTrainer
from ultralytics.utils import RANK
from ultralytics.utils.loss import BboxLoss, v8DetectionLoss
from .architecture import check_backend_version
from .pconv import PConv
from .sd_reference import bbox_iou


class SDBboxLoss(BboxLoss):
    def forward(self, pred_dist, pred_bboxes, anchor_points, target_bboxes,
                target_scores, target_scores_sum, fg_mask, imgsz, stride):
        _, dfl = super().forward(pred_dist, pred_bboxes, anchor_points, target_bboxes,
                                target_scores, target_scores_sum, fg_mask, imgsz, stride)
        weight = target_scores[fg_mask].sum(-1, keepdim=True)
        sd = bbox_iou(pred_bboxes[fg_mask], target_bboxes[fg_mask],
                      xywh=False, SDIoU=True, delta=0.5)
        return ((1 - sd) * weight).sum() / target_scores_sum, dfl


class SDDetectionModel(DetectionModel):
    def __init__(self, cfg=None, ch=3, nc=None, verbose=False):
        check_backend_version()
        spec = deepcopy(cfg) if isinstance(cfg, dict) else yaml_model_load(cfg or "yolov8n-p2.yaml")
        spec.setdefault("pconv_layers", [0, 1])
        spec["sd_loss"] = "author-sdb-delta0.5-feature-grid"
        if spec["pconv_layers"] != [0, 1]:
            raise ValueError("This reference fixes PConv at shallow layers 0 and 1")
        super().__init__(spec, ch=ch, nc=nc, verbose=verbose)
        for layer in spec["pconv_layers"]:
            old = self.model[layer]
            replacement = PConv(old.conv.in_channels, old.conv.out_channels, 3, 2)
            replacement.to(device=old.conv.weight.device, dtype=old.conv.weight.dtype)
            for key in ("i", "f"):
                setattr(replacement, key, getattr(old, key))
            replacement.type = "uav_detection.PConv"
            replacement.np = sum(p.numel() for p in replacement.parameters())
            self.model[layer] = replacement
        self.yaml = deepcopy(spec)
        self.yaml["nc"] = self.model[-1].nc
        self.yaml["channels"] = ch

    def init_criterion(self):
        loss = v8DetectionLoss(self)
        loss.bbox_loss = SDBboxLoss(self.model[-1].reg_max).to(next(self.parameters()).device)
        return loss


class SDTrainer(DetectionTrainer):
    def get_model(self, cfg=None, weights=None, verbose=True):
        model = self.set_model_names_for_load(SDDetectionModel(
            cfg, ch=self.data.get("channels", 3), nc=self.data["nc"],
            verbose=verbose and RANK == -1))
        if weights is not None:
            model.load(weights)
        return model


class SDYOLO(YOLO):
    @property
    def task_map(self):
        mapping = super().task_map
        mapping["detect"] = {**mapping["detect"], "model": SDDetectionModel, "trainer": SDTrainer}
        return mapping
