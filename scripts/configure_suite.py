#!/usr/bin/env python3
"""Validate and display the requested suite without importing Torch or running jobs."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    protocol = json.loads((ROOT / "configs/protocols/four_source_uav_scratch150.json").read_text())
    registry = json.loads((ROOT / "configs/experiments/four_source150/comparison_registry.json").read_text())
    assert protocol["train_validation"]["ratio"] == [8, 2]
    assert len(protocol["train_validation"]["datasets"]) == 4
    assert protocol["training"]["epochs"] == 150
    assert protocol["training"]["pretrained"] is False
    assert protocol["training"]["backbone_pretrained"] is False
    assert protocol["training"]["resume"] is False
    assert registry["automatic_run"] is False
    assert protocol["test"]["requested_dataset"] == "Anti-UAV-detection"
    assert protocol["test"]["in_training"] is False
    assert protocol["test"]["used_for_checkpoint_selection"] is False
    assert protocol["test"]["require_source_sequence_disjoint_from_train_validation"] is True
    from uav_detection.training import read_experiment
    for name in ("baseline", "pconv", "p2", "pconv_p2"):
        settings = read_experiment(ROOT / f"configs/experiments/four_source150/{name}.json")
        assert settings["epochs"] == 150 and settings["pretrained"] is False
        assert settings["seed"] == 42
    for spec in registry["models"]:
        if "constructor_kwargs" in spec:
            assert spec["constructor_kwargs"]["weights"] is None
            assert spec["constructor_kwargs"]["weights_backbone"] is None
    if args.json:
        print(json.dumps({"protocol": protocol, "registry": registry}, ensure_ascii=False, indent=2))
    else:
        print("PASS: four UAV sources, 8:2, seed42, 150 epochs, scratch detector/backbone, no auto-run")
        for spec in registry["models"]:
            print(f"{spec['id']}: {spec['status']}")
        print("Anti-UAV-detection: external UAV test only; native YOLO labels, negatives retained, cross-source audit required")


if __name__ == "__main__":
    main()
