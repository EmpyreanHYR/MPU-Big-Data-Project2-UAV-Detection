#!/usr/bin/env python3
"""One-epoch cloud CPU fixture run, distinct from all formal 150-epoch jobs."""
import argparse
import csv
import json
from pathlib import Path
import platform
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", choices=["faster", "sd", "msf"], required=True)
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--msf-source", type=Path)
    args = parser.parse_args()
    if platform.system() != "Linux" or platform.machine().lower() not in {"x86_64", "amd64"}:
        raise RuntimeError("Cloud only")
    import torch
    import yaml
    torch.set_num_threads(2)
    torch.manual_seed(42)
    data = args.fixture / "dataset.yaml"
    if args.model == "faster":
        from uav_detection.faster_adapter import train_faster, match_predictions
        import numpy as np
        toy = torch.tensor([[0., 0., 10., 10.], [0., 0., 10., 10.], [30., 30., 40., 40.]])
        truth = torch.tensor([[0., 0., 10., 10.]])
        matched = match_predictions(toy, truth, np.array([.5, .95]))
        assert (matched.sum(axis=0) == [1, 1]).all() and not matched[2].any()
        assert not match_predictions(toy, truth[:0], np.array([.5, .95])).any()
        train_faster(args.fixture, args.output, epochs=1, device="cpu", workers=0,
                     size=128, expected_counts=(2, 2))
    elif args.model == "sd":
        from uav_detection.pconv_sd import SDYOLO
        import ultralytics.utils.torch_utils as tu
        tu.NUM_THREADS = 2
        model = SDYOLO("yolov8n-p2.yaml", task="detect")
        model.train(data=str(data), epochs=1, imgsz=128, batch=2, device="cpu", workers=0,
                    pretrained=False, resume=False, amp=False, optimizer="AdamW", lr0=.001,
                    nbs=32, patience=0, seed=42, plots=False, project=str(args.output.parent),
                    name=args.output.name, exist_ok=False)
    else:
        sys.path.insert(0, str(args.msf_source))
        import train
        settings = yaml.safe_load((args.msf_source / "data/hyps/hyp.scratch-high.yaml").read_text())
        settings.update(lr0=.001, lrf=.01, momentum=.9, weight_decay=.0005,
                        warmup_bias_lr=0., mixup=0., copy_paste=0., scale=.5)
        hyp = args.output.parent / "integration-hyp.yaml"
        hyp.write_text(yaml.safe_dump(settings))
        train.run(data=str(data), cfg=str(ROOT / "configs/models/msf-ghostnet-iii.yaml"),
                  weights="", resume=False, epochs=1, batch_size=2, imgsz=128, workers=0,
                  device="cpu", optimizer="AdamW", hyp=str(hyp), seed=42, patience=0,
                  noautoanchor=True, noplots=True, project=str(args.output.parent),
                  name=args.output.name, exist_ok=False)
    with (args.output / "results.csv").open() as stream:
        assert len(list(csv.DictReader(stream))) == 1
    assert (args.output / "weights/best.pt").is_file()
    assert (args.output / "weights/last.pt").is_file()
    (args.output.parent / f"{args.model}-integration.json").write_text(json.dumps({
        "model": args.model, "status": "passed", "device": "cloud_cpu", "epochs": 1,
        "fixture_train": 2, "fixture_val": 2, "formal_experiment": False,
        "checks": ["actual_entry_one_epoch", "validation", "results_csv", "best_and_last_saved"],
        "msf_autoanchor": "disabled_only_for_two_image_fixture" if args.model == "msf" else None}, indent=2))
    print(f"PASS {args.model}: one-epoch CPU integration fixture")


if __name__ == "__main__":
    main()
