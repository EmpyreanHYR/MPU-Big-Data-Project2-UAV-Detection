#!/usr/bin/env python3
"""Build a YOLO26n graph, optionally loading a local checkpoint."""
from pathlib import Path
import argparse
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--weights", help="Optional local YOLO26n checkpoint")
    args = parser.parse_args()
    from uav_detection.modeling import build_baseline
    build_baseline(args.weights).info()


if __name__ == "__main__":
    main()
