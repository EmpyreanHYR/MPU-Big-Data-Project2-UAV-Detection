# PinP2-YOLO NMS audit

This supplement audits frozen predictions and ONNX dataflow with NumPy and ONNX only. E0–E4 and cross-device results of the detector models stay as reported.

- `audit_nms.py`: no-NMS plus IoU 0.3–0.9 on both FP32 and H10, fixed confidence 0.25, AP floor 0.001, max 300, original coordinates after clipping, canonical annotation order, unchanged evaluator. Includes scalar reference, ties/boundaries and confidence-order checks. Output goes to a new directory.
- `audit_graph.py`: static ONNX head ancestry and convolution weight/bias comparison. Export-generated initializer identifiers are read as export-local names rather than stable parameter identities.
- `prepare_hardware_bundle.py`: creates a Pi5/H10-only worker and benchmark plan. The final hash-pinned private bundle covers 24 actual Pi5/H10 runs and its bounded serial queue, and runs on the Pi.
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

[Findings and evidence](../../docs/results/NMS_VLM_AUDIT_20261115.md). Hardware timing is complete: eight variants, three fresh processes each, 500 measured images and 20 warmups per run. The earlier 22.72 FPS is a historical measurement. Threshold exploration uses the 500-image internal validation split.

`summarize_hardware.py` verifies input/worker hashes, all 24 completion records and prediction arrays, recomputes metrics in canonical order, and reports run-level mean±sample SD. See [hardware summary](../../docs/results/NMS_HARDWARE_20261115.csv).
