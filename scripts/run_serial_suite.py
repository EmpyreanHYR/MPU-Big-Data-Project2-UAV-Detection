#!/usr/bin/env python3
"""Explicitly authorized, scratch-only serial jobs for the consolidated IR export.

Supervisor imports no model backend. Each GPU job is a separate bounded child;
errors stop the queue, without retries, checkpoint resume or parameter fallback.
"""
import argparse
import csv
import fcntl
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
JOBS = ("baseline", "pconv", "p2", "pconv_p2", "yolo11n", "yolov8n", "rtdetr_l")
PENDING = ("fasterrcnn_r50_fpn", "pconv_sdloss_yolov8n_p2", "msf_ghostnet_iii")


def digest(path):
    checksum = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            checksum.update(chunk)
    return checksum.hexdigest()


def write_json(path, value):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2))
    temporary.replace(path)


def validate_data(data):
    counts = {"train": 0, "val": 0, "test": 0}
    seen = set()
    with (data / "provenance/manifest_exported.csv").open(encoding="utf-8-sig") as stream:
        for row in csv.DictReader(stream):
            counts[row["split"]] += 1
            for kind in ("image", "label"):
                relative = Path(row[f"output_{kind}"])
                if relative.is_absolute() or ".." in relative.parts:
                    raise ValueError("Unsafe manifest path")
                path = data / relative
                if digest(path) != row[f"output_{kind}_sha256"]:
                    raise ValueError(f"Data hash mismatch: {relative}")
            if row["output_image"] in seen:
                raise ValueError("Duplicate export row")
            seen.add(row["output_image"])
    if counts != {"train": 5800, "val": 1450, "test": 2048}:
        raise ValueError(f"Unexpected split counts: {counts}")
    audit = json.loads((data / "provenance/audit.json").read_text())
    for key in ("cross_split_exact_pixel_duplicates", "cross_split_export_group_overlap",
                "retained_strong_near_identical_test_overlap"):
        if audit[key] != 0:
            raise ValueError(f"Unresolved overlap: {key}")
    return counts


def job_settings(name):
    spec = json.loads((ROOT / f"configs/experiments/four_source150/{name}.json").read_text())
    if name in JOBS[:4]:
        return {k: v for k, v in spec.items() if k not in {"model", "task", "variant"}}
    settings = {k: v for k, v in spec["training"].items()
                if k not in {"weights", "weights_backbone", "dataset_protocol"}}
    settings.update(device=0, save=True, save_period=10, plots=True, cache=False,
                    deterministic=True, momentum=0.9, warmup_bias_lr=0.0)
    return settings


def worker(args):
    from uav_detection.training import require_training_host
    require_training_host()
    from ultralytics.utils.torch_utils import init_seeds
    init_seeds(42, deterministic=True)
    settings = job_settings(args.job)
    settings.update(pretrained=False, resume=False, split="val")
    if settings["epochs"] != 150 or settings["seed"] != 42:
        raise ValueError("Wrong scratch protocol")
    if args.job in JOBS[:4]:
        from uav_detection.modeling import build_detector
        model = build_detector(args.job, weights=None)
    else:
        from uav_detection.comparison import build_comparison
        model = build_comparison(args.job)
    jobdir = args.output / args.job
    jobdir.mkdir(exist_ok=False)
    write_json(jobdir / "initialization.json", {
        "initialization": "random", "pretrained": False, "resume": False,
        "settings": settings, "manifest_sha256": digest(args.data / "provenance/manifest_exported.csv"),
        "test_used_for_selection": False, "script_sha256": digest(__file__)})
    model.train(data=str(args.data / "dataset.yaml"), project=str(jobdir),
                name="train", exist_ok=False, **settings)
    with (jobdir / "train/results.csv").open() as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != 150:
        raise RuntimeError(f"Expected 150 complete epochs; got {len(rows)}")
    write_json(jobdir / "completed.json", {"epochs": 150, "status": "completed", "finished": time.time()})


def supervisor(args):
    if not args.authorized:
        raise ValueError("Explicit training authorization is required")
    args.output.mkdir(exist_ok=False, parents=True)
    lock = (ROOT / ".serial-suite.lock").open("w")
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    write_json(args.output / "supervisor.json", {"pid": os.getpid(), "started": time.time()})
    counts = validate_data(args.data)
    plan = {"jobs": JOBS, "pending_adapters": PENDING, "counts": counts,
            "max_job_seconds": args.max_job_seconds, "retry": False, "fallback": False,
            "settings": {job: job_settings(job) for job in JOBS}, "script_sha256": digest(__file__)}
    write_json(args.output / "plan.json", plan)
    child = None
    def terminate(signum, frame):
        if child is not None and child.poll() is None:
            os.killpg(child.pid, signal.SIGTERM)
        raise SystemExit(128 + signum)
    signal.signal(signal.SIGTERM, terminate)
    signal.signal(signal.SIGINT, terminate)
    for index, job in enumerate(JOBS):
        if (args.output / "STOP").exists():
            write_json(args.output / "status.json", {"status": "stopped", "next": job})
            return
        status = {"status": "running", "job": job, "position": index + 1,
                  "total": len(JOBS), "started": time.time()}
        print(json.dumps(status), flush=True)
        with (args.output / f"{job}.log").open("wb", buffering=0) as log:
            child = subprocess.Popen([sys.executable, "-u", __file__, "--job", job,
                                      "--data", str(args.data), "--output", str(args.output)],
                                     cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
                                     start_new_session=True,
                                     env=os.environ | {"PYTHONUNBUFFERED": "1", "YOLO_AUTOINSTALL": "false"})
            status["child_pid"] = child.pid
            write_json(args.output / "status.json", status)
            try:
                result = child.wait(timeout=args.max_job_seconds)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGTERM)
                try:
                    child.wait(timeout=90)
                except subprocess.TimeoutExpired:
                    os.killpg(child.pid, signal.SIGKILL)
                    child.wait()
                result = 124
        if result != 0:
            status.update(status="failed", returncode=result, finished=time.time())
            write_json(args.output / "status.json", status)
            raise SystemExit(result)
        child = None
    write_json(args.output / "status.json", {"status": "completed_ready_jobs",
               "jobs": JOBS, "pending_adapters": PENDING, "finished": time.time()})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--authorized", action="store_true")
    parser.add_argument("--job", choices=JOBS)
    parser.add_argument("--max-job-seconds", type=int, default=86400)
    args = parser.parse_args()
    if not 600 <= args.max_job_seconds <= 172800:
        parser.error("Use a finite per-child guard between 600 and 172800 seconds")
    args.data = args.data.resolve()
    args.output = args.output.resolve()
    worker(args) if args.job else supervisor(args)
