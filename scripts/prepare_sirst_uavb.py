#!/usr/bin/env python3
"""Prepare native YOLO/VOC boxes using an explicit manifest and class map."""
from pathlib import Path
import argparse
import json
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"src"))
from uav_detection.data.prepare import prepare_dataset, audit_prepared


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prep = commands.add_parser("prepare")
    for name in ("manifest", "source-root", "class-map", "output"):
        prep.add_argument("--"+name, required=True)
    prep.add_argument("--seed", type=int, default=42)
    prep.add_argument("--ratios", type=float, nargs=3, default=(0.7, 0.15, 0.15))
    prep.add_argument("--voc-mode", choices=["one-based-inclusive", "zero-based-half-open"])
    audit = commands.add_parser("audit")
    audit.add_argument("--output", required=True)
    args = parser.parse_args()
    if args.command == "audit":
        result = audit_prepared(args.output)
    else:
        result = prepare_dataset(args.manifest, args.source_root, args.class_map, args.output,
                                 args.seed, args.ratios, args.voc_mode)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
