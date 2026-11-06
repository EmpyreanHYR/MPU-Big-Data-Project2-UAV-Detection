#!/usr/bin/env python3
"""Append three validated comparisons after the original seven jobs finish.

Runs as an independent waiter, never edits or restarts the existing supervisor.
"""
import argparse
import fcntl
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from run_serial_suite import validate_data, digest, write_json

JOBS = ("fasterrcnn_r50_fpn", "pconv_sdloss_yolov8n_p2", "msf_ghostnet_iii")


def previous_ready(previous):
    status = json.loads((previous / "status.json").read_text())
    if status["status"] in {"failed", "stopped"}:
        raise RuntimeError("Existing queue stopped; do not bypass it")
    if status["status"] != "completed_ready_jobs":
        return False
    jobs = json.loads((previous / "plan.json").read_text())["jobs"]
    return len(jobs) == 7 and all((previous / job / "completed.json").is_file() and
        json.loads((previous / job / "completed.json").read_text()).get("epochs") == 150 for job in jobs)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--previous", type=Path, required=True)
    parser.add_argument("--previous-config", type=Path, required=True)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--msf-python", type=Path, required=True)
    parser.add_argument("--msf-source", type=Path, required=True)
    parser.add_argument("--authorized", action="store_true")
    parser.add_argument("--max-job-seconds", type=int, default=604800)
    args = parser.parse_args()
    if not args.authorized or not 600 <= args.max_job_seconds <= 604800:
        parser.error("Explicit authorization and a finite child guard are required")
    try:
        run(args)
    except Exception as error:
        status_path = args.output / "status.json"
        if status_path.exists():
            status = json.loads(status_path.read_text())
            status.update(status="failed", error=type(error).__name__, message=str(error))
            write_json(status_path, status)
        raise


def run(args):
    root = Path(__file__).resolve().parents[1]
    ready = json.loads((root / "ADAPTERS_READY.json").read_text())
    for relative, sha in ready["checked_files"].items():
        if digest(root / relative) != sha:
            raise RuntimeError(f"Adapter changed after validation: {relative}")
    args.output.mkdir(parents=True, exist_ok=False)
    own_lock = (root / ".pending-serial.lock").open("w")
    fcntl.flock(own_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    write_json(args.output / "plan.json", {"jobs": JOBS, "previous": str(args.previous),
               "epochs": 150, "scratch": True, "batch_fallback": False,
               "max_job_seconds": args.max_job_seconds, "ready": ready})
    write_json(args.output / "status.json", {"status": "waiting_existing_queue", "jobs": JOBS, "pid": os.getpid()})
    while not previous_ready(args.previous):
        if (args.output / "STOP").exists():
            write_json(args.output / "status.json", {"status": "stopped_while_waiting"})
            return
        time.sleep(30)
    # Original worker lock is retained until the original supervisor exits.
    with (args.previous_config / ".serial-suite.lock").open("a") as previous_lock:
        fcntl.flock(previous_lock, fcntl.LOCK_EX)
        validate_data(args.data)
        child = None
        def stop(signum, frame):
            if child is not None and child.poll() is None:
                os.killpg(child.pid, signal.SIGTERM)
            raise SystemExit(128 + signum)
        signal.signal(signal.SIGTERM, stop)
        signal.signal(signal.SIGINT, stop)
        for index, job in enumerate(JOBS):
            if (args.output / "STOP").exists():
                write_json(args.output / "status.json", {"status": "stopped", "next": job})
                return
            executable = str(args.msf_python) if job == "msf_ghostnet_iii" else sys.executable
            command = [executable, "-u", str(root / "scripts/train_pending_adapter.py"),
                       "--model", job, "--data", str(args.data), "--output", str(args.output / job),
                       "--msf-source", str(args.msf_source)]
            status = {"status": "running", "job": job, "position": index + 1, "total": 3, "started": time.time()}
            with (args.output / f"{job}.log").open("wb", buffering=0) as log:
                child = subprocess.Popen(command, cwd=root, stdout=log, stderr=subprocess.STDOUT,
                         start_new_session=True, env=os.environ | {"YOLO_AUTOINSTALL": "false", "PYTHONUNBUFFERED": "1"})
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
                status.update(status="failed", returncode=result)
                write_json(args.output / "status.json", status)
                raise SystemExit(result)
            if not (args.output / job / "completed.json").is_file():
                raise RuntimeError("Missing full-schedule completion marker")
            child = None
        write_json(args.output / "status.json", {"status": "completed", "jobs": JOBS, "finished": time.time()})


if __name__ == "__main__":
    main()
