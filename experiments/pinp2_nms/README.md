# PinP2-YOLO NMS audit

This supplement audits frozen predictions and ONNX dataflow. It does not retrain or run a model on the Mac. Original E0–E4 and cross-device results remain unchanged.

- `audit_nms.py`: no-NMS plus IoU 0.3–0.9 on both FP32 and H10, fixed confidence 0.25, AP floor 0.001, max 300, original coordinates after clipping, canonical annotation order, unchanged evaluator. Scalar reference, ties/boundaries, and confidence-order checks are included. New output directory required.
- `audit_graph.py`: static ONNX head ancestry and convolution weight/bias comparison. Export-generated initializer identifiers must not be treated as stable parameter identities.
- `prepare_hardware_bundle.py`: creates a Pi5/H10-only worker and benchmark plan. The final hash-pinned private bundle completed 24 actual Pi5/H10 runs. The private bundle also contains its bounded serial queue. Never run this on a Mac or substitute CPU model inference.
- `outputs/`: private source hashes, per-image paired TP changes, sweep, ONNX audit, and the measured hardware bundle; ignored by Git.

Example replay (paths refer to private local artifacts):

```sh
python experiments/pinp2_nms/audit_nms.py \
  --h10 H10_FROZEN.npz --fp32 FP32_FROZEN.npz \
  --annotations ANNOTATIONS.json --output NEW_OUTPUT_DIRECTORY
python experiments/pinp2_nms/audit_graph.py \
  --full FULL.onnx --raw RAW_HEADS.onnx --output NEW_GRAPH_AUDIT.json
```

Dependencies: NumPy/Pillow for metrics; ONNX for static graph audit. No Torch import or checkpoint loading. Raw data/models remain private.

[Findings and evidence limits](../../docs/results/NMS_VLM_AUDIT_20261115.md). Hardware timing is complete: eight variants, three fresh processes each, 500 measured images and20 warmups per run. Original22.72FPS remains historical. Threshold exploration reuses the 500-image internal validation split and is not independent test-set selection.

`summarize_hardware.py` verifies input/worker hashes, all24 completion receipts and prediction arrays, recomputes metrics in canonical order, and reports run-level mean±sample SD. See [hardware summary](../../docs/results/NMS_HARDWARE_20261115.csv).
