#!/usr/bin/env python3
"""CPU-only random-weight inference smoke test; never starts a training loop."""
from pathlib import Path
import argparse
import json
import os
import platform
import sys
from importlib.metadata import version
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
os.environ.setdefault("YOLO_AUTOINSTALL","false")
os.environ.setdefault("YOLO_CONFIG_DIR",str(ROOT/".venv/yolo-settings"))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",required=True)
    args=parser.parse_args()
    import torch
    from uav_detection.modeling import build_detector
    torch.set_num_threads(2)
    report={"kind":"random-weight CPU inference, no training", "platform":platform.system(),
            "python":platform.python_version(),"torch":version("torch"),
            "ultralytics":version("ultralytics"),"input_shape":[1,3,640,640],"variants":{}}
    for name in ("baseline","pconv","p2"):
        torch.manual_seed(42)
        model=build_detector(name).model.cpu().eval()
        with torch.inference_mode():
            out,raw=model(torch.zeros(1,3,640,640))
        report["variants"][name]={"parameters_full_dual_head":sum(x.numel() for x in model.parameters()),
            "strides":model.stride.tolist(),"output_shape":list(out.shape),
            "finite":bool(torch.isfinite(out).all()),
            "one2one_feature_shapes":[list(x.shape) for x in raw["one2one"]["feats"]],
            "end2end":model.end2end}
    out=Path(args.output);out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2))


if __name__=="__main__":main()
