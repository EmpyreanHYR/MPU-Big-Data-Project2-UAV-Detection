#!/usr/bin/env python3
"""Cloud-only training entry for the three adapted comparisons."""
import argparse
import csv
import json
import os
import shutil
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def train_msf(data, output, source):
    import yaml
    from run_serial_suite import digest
    sys.path.insert(0, str(source))
    import train
    settings = yaml.safe_load((source / "data/hyps/hyp.scratch-high.yaml").read_text())
    settings.update(lr0=0.001, lrf=0.01, momentum=0.9, weight_decay=0.0005,
                    warmup_bias_lr=0.0, scale=0.5, mixup=0.0, copy_paste=0.0)
    # Old YOLOv5 resolves relative paths against its checkout, so supply an
    # explicit derived runtime YAML without modifying the frozen data export.
    output.mkdir(parents=True, exist_ok=False)
    # Keep the old YOLOv5 cache/verification writes away from the immutable
    # prepared export and from the currently running Ultralytics queue.
    view = output / "native-data-view"
    with (data / "provenance/manifest_exported.csv").open(encoding="utf-8-sig") as stream:
        rows = [row for row in csv.DictReader(stream) if row["split"] in {"train", "val"}]
    for row in rows:
        for key in ("output_image", "output_label"):
            target = view / row[key]
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(data / row[key], target)
            if digest(target) != row[key + "_sha256"]:
                raise ValueError(f"Runtime view hash mismatch: {row[key]}")
    runtime = {"path": str(view), "train": str(view / "images/train"),
               "val": str(view / "images/val"), "nc": 1, "names": ["uav"]}
    (output / "source-manifest.json").write_text(json.dumps(rows, ensure_ascii=False))
    data_yaml = output / "runtime-dataset.yaml"
    data_yaml.write_text(yaml.safe_dump(runtime))
    hyp_yaml = output / "runtime-hyp.yaml"
    hyp_yaml.write_text(yaml.safe_dump(settings))
    os.environ.update(WANDB_MODE="disabled", WANDB_DISABLED="true", YOLOv5_AUTOINSTALL="false")
    train.run(data=str(data_yaml), cfg=str(ROOT / "configs/models/msf-ghostnet-iii.yaml"),
              weights="", resume=False, epochs=150, batch_size=16, imgsz=640,
              workers=8, device="0", optimizer="AdamW", hyp=str(hyp_yaml),
              seed=42, patience=0, project=str(output), name="train", exist_ok=False,
              save_period=10, noplots=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, choices=["fasterrcnn_r50_fpn", "pconv_sdloss_yolov8n_p2", "msf_ghostnet_iii"])
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--msf-source", type=Path)
    args = parser.parse_args()
    from uav_detection.training import require_training_host
    require_training_host()
    from run_serial_suite import validate_data, digest, write_json
    validate_data(args.data)
    if args.output.exists():
        raise FileExistsError("Scratch-only entry requires a new output")
    import torch
    torch.manual_seed(42)
    if args.model == "fasterrcnn_r50_fpn":
        from uav_detection.faster_adapter import train_faster
        train_faster(args.data, args.output / "train")
    elif args.model == "pconv_sdloss_yolov8n_p2":
        from uav_detection.pconv_sd import SDYOLO
        from ultralytics.utils.torch_utils import init_seeds
        init_seeds(42, deterministic=True)
        model = SDYOLO("yolov8n-p2.yaml", task="detect")
        model.train(data=str(args.data / "dataset.yaml"), project=str(args.output), name="train",
                    epochs=150, imgsz=640, batch=8, nbs=32, seed=42, device=0,
                    pretrained=False, resume=False, amp=False, optimizer="AdamW",
                    lr0=0.001, lrf=0.01, momentum=0.9, weight_decay=0.0005,
                    warmup_bias_lr=0.0, workers=8, patience=0, save_period=10,
                    deterministic=True, split="val", exist_ok=False)
    else:
        if args.msf_source is None:
            parser.error("MSF requires the separately patched pinned source")
        train_msf(args.data, args.output, args.msf_source)
    with (args.output / "train/results.csv").open() as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != 150:
        raise RuntimeError(f"Incomplete schedule: {len(rows)} epochs")
    write_json(args.output / "completed.json", {"model": args.model, "epochs": 150,
               "initialization": "random", "resume": False, "test_used": False,
               "manifest_sha256": digest(args.data / "provenance/manifest_exported.csv")})


if __name__ == "__main__":
    main()
