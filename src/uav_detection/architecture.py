"""Version-pinned Ultralytics adapter without monkey-patching its YAML parser."""
from copy import deepcopy
from pathlib import Path
from importlib.metadata import version
import re

import torch
from ultralytics import YOLO
from ultralytics.nn.tasks import DetectionModel
from ultralytics.models.yolo.detect import DetectionTrainer
from ultralytics.utils import YAML, RANK
from .pconv import PConv

PINNED_VERSION = "8.4.184"


def check_backend_version():
    if version("ultralytics") != PINNED_VERSION:
        raise RuntimeError(f"Use ultralytics=={PINNED_VERSION} for the version-pinned adapter")


class UAVDetectionModel(DetectionModel):
    """Rebuild PConv from saved YAML metadata, including inside the trainer."""
    def __init__(self, cfg="yolo26n.yaml", ch=3, nc=None, verbose=False):
        check_backend_version()
        spec = deepcopy(cfg) if isinstance(cfg, dict) else YAML.load(str(cfg))
        replacements = spec.get("pconv_layers", [])
        if not isinstance(replacements, list) or len(replacements) > 1:
            raise ValueError("Specify at most one shallow PConv replacement")
        for replacement in replacements:
            if replacement != {"layer": 1, "kernel": 3}:
                raise ValueError("The PConv ablation requires layer 1 and kernel 3")
        if not spec.get("end2end") or spec.get("reg_max") != 1:
            raise ValueError("Expected a YOLO26 end-to-end, DFL-free configuration")
        super().__init__(spec, ch=ch, nc=nc, verbose=verbose)
        for replacement in replacements:
            layer = replacement["layer"]
            if layer != 1:
                raise ValueError("The current PConv ablation replaces exactly backbone layer 1")
            old = self.model[layer]
            conv = old.conv
            if conv.kernel_size != (3, 3) or conv.stride != (2, 2) or conv.groups != 1:
                raise ValueError("Unexpected shallow convolution geometry")
            module = PConv(conv.in_channels, conv.out_channels, replacement["kernel"], 2)
            module.to(device=conv.weight.device, dtype=conv.weight.dtype)
            for attr in ("i", "f"):
                setattr(module, attr, getattr(old, attr))
            module.type = "uav_detection.PConv"
            module.np = sum(p.numel() for p in module.parameters())
            self.model[layer] = module
        self.yaml = deepcopy(spec)
        self.yaml["nc"] = self.model[-1].nc
        self.yaml["channels"] = ch
        self.end2end = True


class UAVDetectionTrainer(DetectionTrainer):
    def get_model(self, cfg=None, weights=None, verbose=True):
        model = self.set_model_names_for_load(UAVDetectionModel(
            cfg, nc=self.data["nc"], ch=self.data.get("channels", 3),
            verbose=verbose and RANK == -1))
        if weights is not None:
            model.load(weights)
        return model


class UAVYOLO(YOLO):
    @property
    def task_map(self):
        mapping = super().task_map
        mapping["detect"] = {**mapping["detect"], "model": UAVDetectionModel,
                             "trainer": UAVDetectionTrainer}
        return mapping


def transfer_shared_prefix(target, source):
    """Copy only matching graph-prefix layers 0..16, before the P2 fork.

    Changed PConv layer 1 and all post-fork prediction layers stay initialized.
    This avoids loading unrelated equal-shape tensors after P2 shifts layer IDs.
    """
    src, dst = source.state_dict(), target.state_dict()
    excluded = {item["layer"] for item in target.yaml.get("pconv_layers", [])}
    selected = {}
    for key, value in src.items():
        match = re.match(r"model\.(\d+)\.", key)
        if match and int(match[1]) <= 16 and int(match[1]) not in excluded:
            if key in dst and dst[key].shape == value.shape:
                selected[key] = value
    if not selected:
        raise ValueError("No compatible YOLO26 graph-prefix tensors in source checkpoint")
    target.load_state_dict(selected, strict=False)
    return {"policy": "shared-prefix-0-through-16", "copied_keys": sorted(selected),
            "copied_tensors": len(selected), "excluded_layers": sorted(excluded),
            "post_fork_layers": "random initialization"}
