"""Validated training settings and an explicit Linux/CUDA training entry."""
from datetime import datetime, timezone
from pathlib import Path
import json
import platform


def read_experiment(path: str | Path) -> dict:
    settings = json.loads(Path(path).read_text(encoding="utf-8"))
    if settings.get("model") != "yolo26n.yaml" or settings.get("task") != "detect":
        raise ValueError("This entry accepts the YOLO26n detection baseline.")
    for name in ("epochs", "imgsz", "batch"):
        value = settings.get(name)
        if type(value) is not int or value <= 0:
            raise ValueError(f"{name} must be a positive integer")
    if settings.get("device") != 0:
        raise ValueError("Use the single authorized CUDA device 0.")
    allowed = {"model", "task", "epochs", "imgsz", "batch", "device", "seed",
               "workers", "patience", "cache", "plots", "save", "save_period",
               "deterministic"}
    if set(settings) - allowed:
        raise ValueError(f"Unknown settings: {sorted(set(settings) - allowed)}")
    return settings


def training_window(deadline: str, max_hours: float, now: datetime | None = None) -> float:
    """Return a bounded number of hours; reject expired/ambiguous deadlines."""
    end = datetime.fromisoformat(deadline.replace("Z", "+00:00"))
    if end.tzinfo is None:
        raise ValueError("The deadline must include a timezone.")
    if not 0 < max_hours <= 8:
        raise ValueError("max_hours must be in (0, 8].")
    remaining = (end - (now or datetime.now(timezone.utc))).total_seconds() / 3600
    if remaining <= 0:
        raise ValueError("The training deadline has passed.")
    return min(max_hours, remaining)


def require_training_host():
    """Reject Mac/Pi/CPU training before building or loading any model."""
    if platform.system() != "Linux" or platform.machine().lower() not in {"x86_64", "amd64"}:
        raise RuntimeError("Training requires the authorized Linux x86_64 CUDA host.")
    import torch
    if not torch.cuda.is_available() or torch.cuda.device_count() != 1:
        raise RuntimeError("Training requires exactly one visible CUDA GPU.")
    if "2080 Ti" not in torch.cuda.get_device_name(0):
        raise RuntimeError("The current training authorization specifies an RTX 2080 Ti.")


def train_baseline(config, data, weights, output, deadline, max_hours):
    settings = read_experiment(config)
    data_path, weight_path = Path(data).resolve(), Path(weights).resolve()
    for path in (data_path, weight_path):
        if not path.is_file():
            raise FileNotFoundError(path)
    hours = training_window(deadline, max_hours)
    require_training_host()
    from .modeling import build_baseline
    detector = build_baseline(weight_path)
    kwargs = {k: v for k, v in settings.items() if k not in {"model", "task"}}
    return detector.train(data=str(data_path), project=str(Path(output).resolve()),
                          name="yolo26n-baseline", exist_ok=False, time=hours, **kwargs)
