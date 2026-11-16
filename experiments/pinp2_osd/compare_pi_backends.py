"""Bounded Pi-only diagnostic inference with frozen FP32 ONNX or H10 weights.

Use a separate output directory and an external timeout guard. Never trains or
changes the deployed GUI. Saves raw outputs for independent coordinate review.
"""
import argparse
from contextlib import ExitStack
import json
from pathlib import Path
import platform
import subprocess
import sys
import time

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/evaluation"))
sys.path.insert(0, str(ROOT / "scripts/deployment"))
from detection_eval import prepare, postprocess, sha
from pinp2_postprocess import PinP2Postprocessor, load_policy


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--backend", choices=("fp32", "h10"), required=True)
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--model-dir", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--lock", type=Path, action="append", required=True)
    p.add_argument("--max-seconds", type=int, default=600)
    a = p.parse_args()
    assert platform.machine() == "aarch64"
    assert "Raspberry Pi 5" in Path("/proc/device-tree/model").read_text()
    assert len(set(x.resolve() for x in a.lock)) >= 2
    manifest = json.loads(a.manifest.read_text())
    rows = manifest["images"]
    assert 0 < len(rows) <= 400 and 0 < a.max_seconds <= 1200
    assert len({r["image"] for r in rows}) == len(rows)
    for r in rows:
        assert sha(a.manifest.parent / r["file"]) == r["sha256"]
    a.output.mkdir(parents=True, exist_ok=False)
    (a.output / "raw").mkdir()
    policy = load_policy()
    assert manifest["weights_sha256"] == policy["weights_sha256"]
    start = time.monotonic()
    predictions, original, image_receipts = [], [], []
    engine = None
    with ExitStack() as stack:
        if a.backend == "h10":
            from serve_gui import H10Engine
            engine = H10Engine(a.model_dir, a.lock)
            stack.callback(engine.close)
            meta = engine.meta
            identity = dict(engine.info)
            decoder = engine.decoder
        else:
            import fcntl
            for lock in sorted(set(x.resolve() for x in a.lock)):
                handle = stack.enter_context(lock.open("a"))
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            assert subprocess.run(["fuser", "/dev/hailo0"], capture_output=True).returncode == 1
            import onnxruntime as ort
            meta = json.loads((a.model_dir / "deployment_config.json").read_text())
            assert meta["weights_sha256"] == policy["weights_sha256"]
            assert sha(a.model_dir / "model.onnx") == meta["onnx_sha256"]
            options = ort.SessionOptions()
            options.intra_op_num_threads = 4
            options.inter_op_num_threads = 1
            session = ort.InferenceSession(str(a.model_dir / "model.onnx"), options,
                                           providers=["CPUExecutionProvider"])
            assert session.get_inputs()[0].shape == [1, 3, 640, 640]
            identity = {"backend": "FP32 ONNX CPU", "onnxruntime": ort.__version__,
                        "weights_sha256": meta["weights_sha256"], "onnx_sha256": meta["onnx_sha256"]}
            decoder = PinP2Postprocessor(policy)
        for i, row in enumerate(rows):
            assert time.monotonic() - start < a.max_seconds, "Diagnostic deadline exceeded"
            with Image.open(a.manifest.parent / row["file"]) as im:
                image = im.convert("RGB")
            x, geometry = prepare(image)
            pixels = np.ascontiguousarray(np.rint(x[0].transpose(1, 2, 0) * 255).astype(np.uint8))
            import hashlib
            pixel_hash = hashlib.sha256(pixels.tobytes()).hexdigest()
            assert pixel_hash == row["letterbox_uint8_sha256"]
            tick = time.perf_counter()
            if engine is not None:
                engine.bindings.input().set_buffer(pixels)
                engine.configured.run([engine.bindings], timeout=10000)
                raw = [np.asarray(engine.bindings.output(name).get_buffer()).transpose(2, 0, 1)[None].copy()
                       for name in engine.mapping]
                assert all(np.isfinite(v).all() for v in raw)
                from raw_head_decode import decode
                before_nms = decode(raw, meta, geometry, .001)
                net_boxes = decode(raw, meta, (1., 0, 0, 640, 640), .001)
            else:
                raw = session.run(None, {session.get_inputs()[0].name: x})
                assert len(raw) == 1 and raw[0].shape == (1, 300, 6)
                assert np.isfinite(raw[0]).all()
                before_nms = postprocess(raw[0], "e2e", geometry, .001)
                net_boxes = postprocess(raw[0], "e2e", (1., 0, 0, 640, 640), .001)
            det = decoder.filter(before_nms)
            elapsed = (time.perf_counter() - tick) * 1000
            np.savez_compressed(a.output / "raw" / f"{i:03}.npz",
                                **({f"head_{j}": v for j, v in enumerate(raw)}
                                   if a.backend == "fp32" or row.get("capture_raw", True) else {}),
                                network_coordinate_boxes=net_boxes,
                                restored_before_nms=before_nms, geometry=np.asarray(geometry))
            predictions.append(det.copy())
            original.append(before_nms.copy())
            image_receipts.append({"index": i, "image": row["image"], "geometry": list(geometry),
                                   "letterbox_uint8_sha256": pixel_hash, "decode_ms": elapsed,
                                   "lowfloor_detections": len(det), "fixed_detections": int((det[:, 4] >= .25).sum())})
            print("DIAGNOSTIC", a.backend, i + 1, "/", len(rows), round(elapsed, 1), "ms", flush=True)
    for name, values in [("predictions.npz", predictions), ("before_nms.npz", original)]:
        np.savez_compressed(a.output / name, images=np.asarray([r["image"] for r in rows]),
                            offsets=np.r_[0, np.cumsum([len(v) for v in values])],
                            detections=np.concatenate(values))
    receipt = {"status": "completed", "images": len(rows), "identity": identity,
               "confidence_floor": .001, "policy": policy, "runtime_numpy": np.__version__,
               "manifest_sha256": sha(a.manifest), "worker_sha256": sha(__file__),
               "source_sha256": {str(p.relative_to(ROOT)): sha(p) for p in [
                   ROOT / "scripts/evaluation/detection_eval.py", ROOT / "scripts/evaluation/raw_head_decode.py",
                   ROOT / "scripts/deployment/pinp2_postprocess.py", ROOT / "scripts/deployment/serve_gui.py"]},
               "per_image": image_receipts, "elapsed_seconds": time.monotonic() - start,
               "predictions_sha256": sha(a.output / "predictions.npz")}
    (a.output / "completed.json").write_text(json.dumps(receipt, indent=2) + "\n")


if __name__ == "__main__":
    main()
