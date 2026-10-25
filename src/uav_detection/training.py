"""Validated training settings and an explicit Linux/CUDA training entry."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import json
import math
import platform
import time


def read_experiment(path: str | Path) -> dict:
    settings = json.loads(Path(path).read_text(encoding="utf-8"))
    from .modeling import MODEL_FILES
    variant = settings.get("variant", "baseline")
    expected = MODEL_FILES.get(variant)
    valid_models = {expected} if expected else set()
    if variant == "baseline":
        valid_models.add("yolo26n.yaml")
    if settings.get("model") not in valid_models or settings.get("task") != "detect":
        raise ValueError("Variant/model must match a configured YOLO26n detector")
    for name in ("epochs", "imgsz", "batch"):
        value = settings.get(name)
        if type(value) is not int or value <= 0:
            raise ValueError(f"{name} must be a positive integer")
    if settings["epochs"] > 300:
        raise ValueError("The baseline/ablation epoch cap is 300; a time window must not extend it")
    if type(settings.get("device")) is not int or settings["device"] != 0:
        raise ValueError("Use the single authorized CUDA device 0.")
    allowed = {"variant", "model", "task", "epochs", "imgsz", "batch", "device", "seed",
               "workers", "patience", "cache", "plots", "save", "save_period",
               "deterministic", "stop_after_epochs", "optimizer", "lr0",
               "momentum", "weight_decay", "lrf", "nbs", "warmup_bias_lr"}
    if set(settings) - allowed:
        raise ValueError(f"Unknown settings: {sorted(set(settings) - allowed)}")
    if "stop_after_epochs" in settings:
        stop = settings["stop_after_epochs"]
        if type(stop) is not int or not 1 <= stop <= settings["epochs"]:
            raise ValueError("stop_after_epochs must be an integer within the configured epoch schedule")
        if not {"optimizer", "lr0", "momentum", "weight_decay", "lrf", "nbs", "warmup_bias_lr"} <= set(settings):
            raise ValueError("A matched epoch comparison requires the explicit optimizer schedule")
    if "optimizer" in settings and settings["optimizer"] != "AdamW":
        raise ValueError("Only the explicit AdamW comparison optimizer is supported")
    for name, include_zero in (("lr0", False), ("momentum", True),
                               ("weight_decay", True), ("lrf", False), ("warmup_bias_lr", True)):
        if name not in settings:
            continue
        value = settings[name]
        if (type(value) not in (int, float) or not math.isfinite(value) or
            not (0 <= value <= 1 if include_zero else 0 < value <= 1) or
            (name == "momentum" and value >= 1)):
            raise ValueError(f"Invalid finite optimizer parameter: {name}")
    if "nbs" in settings and (type(settings["nbs"]) is not int or settings["nbs"] <= 0):
        raise ValueError("nbs must be a positive integer")
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



def _utc_now():
    return datetime.now(timezone.utc)


class BudgetStopCallback:
    """Stop between batches/epochs without Ultralytics' epoch-reestimating time option.

    The monotonic window starts at function entry; UTC independently enforces the
    authorized wall-clock deadline. The outer cloud timeout remains authoritative.
    """
    def __init__(self, deadline, max_hours, epoch_limit, *, utc_now=None,
                 monotonic=None, save_buffer_seconds=90, stop_after_epochs=None):
        self.utc_now = utc_now or _utc_now
        self.monotonic = monotonic or time.monotonic
        self.started_utc = self.utc_now()
        self.started_monotonic = self.monotonic()
        self.allowed_seconds = training_window(deadline, max_hours, self.started_utc)*3600
        self.deadline = datetime.fromisoformat(deadline.replace("Z", "+00:00"))
        self.max_hours = max_hours
        self.epoch_limit = epoch_limit
        self.stop_after_epochs = stop_after_epochs
        self.save_buffer_seconds = save_buffer_seconds
        if not 60 <= save_buffer_seconds <= 120 or self.allowed_seconds <= save_buffer_seconds:
            raise ValueError("Insufficient training window after the 60–120 second save buffer")
        self.stop_after_seconds = self.allowed_seconds - save_buffer_seconds
        self.stop_at_utc = self.started_utc + timedelta(seconds=self.stop_after_seconds)
        self.path = None
        self.reason = None
        self.stopped_utc = None
        self.status = "prepared"
        self.epochs_observed = None
        self.error = None

    def policy(self):
        return {"deadline_utc": self.deadline.astimezone(timezone.utc).isoformat(),
                "requested_max_hours": self.max_hours, "epoch_limit": self.epoch_limit,
                "stop_after_complete_epochs": self.stop_after_epochs,
                "started_utc": self.started_utc.isoformat(),
                "allowed_seconds": self.allowed_seconds,
                "save_buffer_seconds": self.save_buffer_seconds,
                "stop_after_monotonic_seconds": self.stop_after_seconds,
                "soft_stop_at_utc": self.stop_at_utc.isoformat(),
                "ultralytics_time_argument": "omitted to preserve the epoch limit"}

    def _persist(self):
        if self.path is None:
            return
        record = self.policy() | {"status": self.status, "stop_reason": self.reason,
                                  "stop_requested_utc": self.stopped_utc,
                                  "elapsed_monotonic_seconds": max(0, self.monotonic()-self.started_monotonic),
                                  "epochs_observed": self.epochs_observed, "error": self.error}
        temporary = self.path.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(record, indent=2)+"\n")
        temporary.replace(self.path)

    def attach(self, path):
        self.path = Path(path)
        self.status = "running"
        self._persist()

    def _expired_reason(self):
        if self.utc_now() >= self.stop_at_utc:
            return "utc_window_save_buffer"
        if self.monotonic()-self.started_monotonic >= self.stop_after_seconds:
            return "monotonic_window_save_buffer"
        return None

    def require_remaining_window(self):
        reason = self._expired_reason()
        if reason:
            self.reason = reason
            self.stopped_utc = self.utc_now().isoformat()
            self.status = "stopped_before_training"
            self._persist()
            raise TimeoutError("The authorized training window elapsed during preparation")

    def __call__(self, trainer):
        if self.reason is not None:
            trainer.stop = True
            return
        reason = self._expired_reason()
        if reason:
            trainer.stop = True
            self.reason = reason
            self.stopped_utc = self.utc_now().isoformat()
            self.status = "stop_requested"
            epoch = getattr(trainer, "epoch", None)
            self.epochs_observed = epoch+1 if type(epoch) is int else None
            self._persist()

    def finalize(self, outcome, trainer=None, error=None):
        epoch = getattr(trainer, "epoch", None)
        self.epochs_observed = epoch+1 if type(epoch) is int else self.epochs_observed
        self.status = outcome
        if self.reason is None:
            if outcome == "returned":
                self.reason = ("epoch_limit" if self.epochs_observed is not None and
                               self.epochs_observed >= self.epoch_limit else "trainer_returned_before_epoch_limit")
            else:
                self.reason = "exception"
        self.error = type(error).__name__ if error is not None else None
        self._persist()



class CompleteEpochStopCallback:
    """Stop only after a complete epoch while retaining the full LR/mosaic schedule.

    Register after the budget callback on on_train_epoch_end only. Budget stops
    take priority, so an interrupted epoch is never labeled a matched full epoch.
    """
    def __init__(self, stop_after_epochs, budget):
        self.stop_after_epochs = stop_after_epochs
        self.budget = budget

    def __call__(self, trainer):
        self.budget(trainer)  # Independently preserve budget priority at this boundary.
        if self.budget.reason is not None or getattr(trainer, "stop", False):
            return
        epoch = getattr(trainer, "epoch", None)
        if type(epoch) is int and epoch+1 >= self.stop_after_epochs:
            trainer.stop = True
            self.budget.reason = "matched_complete_epoch_limit"
            self.budget.stopped_utc = self.budget.utc_now().isoformat()
            self.budget.status = "stop_requested"
            self.budget.epochs_observed = epoch+1
            self.budget._persist()


def require_training_host():
    """Reject Mac/Pi/CPU training before building or loading any model."""
    if platform.system() != "Linux" or platform.machine().lower() not in {"x86_64", "amd64"}:
        raise RuntimeError("Training requires the authorized Linux x86_64 CUDA host.")
    import torch
    if not torch.cuda.is_available() or torch.cuda.device_count() != 1:
        raise RuntimeError("Training requires exactly one visible CUDA GPU.")
    if "2080 Ti" not in torch.cuda.get_device_name(0):
        raise RuntimeError("The current training authorization specifies an RTX 2080 Ti.")


def train_detector(config, data, weights, output, deadline, max_hours):
    settings = read_experiment(config)
    budget = BudgetStopCallback(deadline, max_hours, settings["epochs"],
                                stop_after_epochs=settings.get("stop_after_epochs"))
    require_training_host()
    data_path, weight_path = Path(data).resolve(), Path(weights).resolve()
    if data_path.name != "dataset.yaml":
        raise ValueError("Use the dataset.yaml generated by prepare_sirst_uavb.py")
    for path in (data_path, weight_path):
        if not path.is_file():
            raise FileNotFoundError(path)
    from .data.prepare import audit_prepared, sha256
    audit_prepared(data_path.parent)
    from .modeling import build_detector, model_path
    from ultralytics.utils.torch_utils import init_seeds
    init_seeds(settings.get("seed", 0), deterministic=settings.get("deterministic", False))
    variant = settings.get("variant", "baseline")
    detector = build_detector(variant, weight_path)
    # Any inherited time override could trigger epoch reestimation in Ultralytics.
    detector.overrides.pop("time", None)
    root = Path(output).resolve()
    root.mkdir(parents=True, exist_ok=False)
    budget.attach(root/"training_budget.json")
    provenance = {"variant": variant, "experiment": settings,
                  "model_yaml_sha256": sha256(model_path(variant)),
                  "weights_sha256": sha256(weight_path),
                  "prepared_manifest_sha256": sha256(data_path.parent/"manifest.json"),
                  "initialization": detector.transfer_report,
                  "training_budget": budget.policy()}
    (root/"initialization.json").write_text(json.dumps(provenance, indent=2)+"\n")
    kwargs = {k: v for k, v in settings.items() if k not in {"model", "task", "variant", "stop_after_epochs"}}
    detector.add_callback("on_train_batch_end", budget)
    detector.add_callback("on_train_epoch_end", budget)
    if "stop_after_epochs" in settings:
        detector.add_callback("on_train_epoch_end",
                              CompleteEpochStopCallback(settings["stop_after_epochs"], budget))
    try:
        budget.require_remaining_window()
        result = detector.train(data=str(data_path), project=str(root),
                                name=f"yolo26n-{variant}", exist_ok=False, **kwargs)
    except BaseException as error:
        budget.finalize("failed", getattr(detector, "trainer", None), error)
        raise
    budget.finalize("returned", getattr(detector, "trainer", None))
    return result


# Compatibility with the original baseline-only script entry.
train_baseline = train_detector
