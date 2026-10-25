#!/usr/bin/env python3
"""Cloud-only YOLO26 variant training; --help does not import model dependencies."""
from pathlib import Path
import argparse
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from uav_detection.training import train_detector


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument("--data", required=True, help="Local dataset YAML")
    parser.add_argument("--weights", required=True, help="Local official YOLO26n weights")
    parser.add_argument("--output", required=True)
    parser.add_argument("--deadline", required=True, help="Per-job budget safety deadline, ISO8601 with timezone")
    parser.add_argument("--max-hours", type=float, required=True)
    args = parser.parse_args()
    train_detector(args.config, args.data, args.weights, args.output,
                   args.deadline, args.max_hours)


if __name__ == "__main__":
    main()
