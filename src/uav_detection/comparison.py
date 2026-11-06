"""Lazy model constructors for scratch-only comparisons; no training on import."""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "configs/experiments/four_source150/comparison_registry.json"


def comparison_spec(model_id):
    registry = json.loads(REGISTRY.read_text())
    spec = next((m for m in registry["models"] if m["id"] == model_id), None)
    if spec is None:
        raise ValueError(f"Unknown comparison model: {model_id}")
    return spec, registry["common"]


def build_comparison(model_id):
    """Return a native model, with both detector and backbone randomly initialized.

    External author implementations have explicit pending adapters; they cannot
    accidentally fall back to a stock YOLO or download a checkpoint.
    """
    spec, _ = comparison_spec(model_id)
    if spec["backend"] not in {"uav_adapter", "ultralytics", "torchvision"} and model_id != "pconv_sdloss_yolov8n_p2":
        raise NotImplementedError(f"{model_id}: {spec['status']}; no substitute model is allowed")
    from .training import require_training_host
    require_training_host()  # Reject Mac/Pi before importing a model backend.
    if model_id == "pconv_sdloss_yolov8n_p2":
        from .pconv_sd import SDYOLO
        return SDYOLO("yolov8n-p2.yaml", task="detect")
    if spec["backend"] == "uav_adapter":
        from .modeling import build_detector
        return build_detector(spec["variant"], weights=None)
    if spec["backend"] == "torchvision":
        from torchvision.models.detection import fasterrcnn_resnet50_fpn
        return fasterrcnn_resnet50_fpn(**spec["constructor_kwargs"])
    from .architecture import check_backend_version
    check_backend_version()
    from ultralytics import YOLO, RTDETR
    constructor = {"YOLO": YOLO, "RTDETR": RTDETR}[spec["constructor"]]
    model = constructor(spec["model"])
    model.overrides.update(pretrained=False, resume=False)
    return model
