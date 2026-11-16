"""Analytic input/decoder coordinate checks; NumPy/Pillow only, no inference."""
import json
from pathlib import Path
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts/evaluation"))
from detection_eval import prepare
from raw_head_decode import decode


def check():
    meta = {"family": "e2e", "strides": [4, 8, 16, 32], "reg_max": 1}
    records = []
    # Include the actual demo geometry, a half-size image, a double-size image,
    # portrait orientation, and asymmetric rounding/padding cases.
    for width, height in [(640, 512), (320, 256), (1280, 1024), (512, 640), (641, 479), (901, 500)]:
        _, geo = prepare(Image.new("RGB", (width, height)))
        scale, left, top, _, _ = geo
        for stride_index, stride in enumerate(meta["strides"]):
            for relative in [[.2, .25, .55, .6], [.57, .345, .595, .377], [0, 0, .1, .1]]:
                target = np.asarray(relative) * [width, height, width, height]
                network = target * scale + [left, top, left, top]
                cx, cy = (network[:2] + network[2:]) / 2
                col, row = int(cx // stride), int(cy // stride)
                anchor = (np.asarray([col, row]) + .5) * stride
                distances = np.r_[anchor - network[:2], network[2:] - anchor] / stride
                raw = []
                for s in meta["strides"]:
                    h = w = 640 // s
                    raw.extend([np.ones((1, 4, h, w), np.float32),
                                np.full((1, 1, h, w), -30, np.float32)])
                raw[2 * stride_index][0, :, row, col] = distances
                raw[2 * stride_index + 1][0, 0, row, col] = 5.
                actual = decode(raw, meta, geo, .25)
                assert len(actual) == 1
                error = float(np.abs(actual[0, :4] - target).max())
                assert error < 1e-3, (width, height, stride, error)
                records.append({"size": [width, height], "stride": stride,
                                "geometry": list(geo), "target_xyxy": target.tolist(),
                                "decoded_xyxy": actual[0, :4].tolist(), "max_abs_error_px": error})
    # At the actual demo size there must be no resampling or width/height scaling.
    rgb = np.random.default_rng(42).integers(0, 256, (512, 640, 3), dtype=np.uint8)
    x, geo = prepare(Image.fromarray(rgb))
    restored = np.rint(x[0].transpose(1, 2, 0) * 255).astype(np.uint8)
    assert tuple(geo) == (1., 0, 64, 640, 512)
    np.testing.assert_array_equal(restored[64:576], rgb)
    assert (restored[:64] == 114).all() and (restored[576:] == 114).all()
    return {"status": "passed", "analytic_cases": len(records),
            "demo_no_resampling_pixel_exact": True,
            "demo_geometry": list(geo), "max_abs_error_px": max(r["max_abs_error_px"] for r in records),
            "records": records}


if __name__ == "__main__":
    print(json.dumps(check(), indent=2))
