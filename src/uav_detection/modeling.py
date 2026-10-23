"""Build the baseline. Model dependencies load only when explicitly requested."""
from pathlib import Path


def build_baseline(weights: str | Path | None = None):
    """Build YOLO26n Detect and optionally load a local checkpoint."""
    checkpoint = None
    if weights is not None:
        checkpoint = Path(weights).expanduser().resolve()
        if not checkpoint.is_file():
            raise FileNotFoundError(checkpoint)
    from ultralytics import YOLO
    detector = YOLO("yolo26n.yaml", task="detect")
    if checkpoint is not None:
        detector.load(str(checkpoint))
    return detector
