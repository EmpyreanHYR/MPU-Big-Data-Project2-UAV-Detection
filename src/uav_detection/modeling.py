"""Build all three YOLO26 variants; loading never downloads a checkpoint."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODEL_FILES = {"baseline": "yolo26n-baseline.yaml", "pconv": "yolo26n-pconv.yaml",
               "p2": "yolo26n-p2.yaml"}


def model_path(variant: str) -> Path:
    if variant not in MODEL_FILES:
        raise ValueError(f"Unknown variant: {variant}")
    path = ROOT / "configs" / "models" / MODEL_FILES[variant]
    if not path.is_file():
        raise FileNotFoundError(path)
    return path


def build_detector(variant="baseline", weights: str | Path | None = None):
    checkpoint = None
    if weights is not None:
        checkpoint = Path(weights).expanduser().resolve()
        if not checkpoint.is_file():
            raise FileNotFoundError(checkpoint)
    from .architecture import UAVYOLO, transfer_shared_prefix
    detector = UAVYOLO(str(model_path(variant)), task="detect")
    detector.overrides["nms"] = False
    if checkpoint is not None:
        # The existing local official checkpoint is the only pretrained source.
        source = UAVYOLO(str(checkpoint), task="detect")
        if not source.model.yaml.get("end2end") or source.model.yaml.get("reg_max") != 1:
            raise ValueError("The checkpoint must be a YOLO26 detection model")
        detector.transfer_report = transfer_shared_prefix(detector.model, source.model)
        # YOLO.train rebuilds from model.yaml with this adapter's trainer.
        detector.ckpt = source.ckpt
        detector.ckpt_path = str(checkpoint)
        detector.overrides["pretrained"] = True
    else:
        detector.transfer_report = {"policy": "random initialization", "copied_tensors": 0}
    return detector


def build_baseline(weights: str | Path | None = None):
    return build_detector("baseline", weights)
