# Timestamp false-positive audit

NumPy-only replay of saved predictions. This does not load a detector, change images,
modify labels, or enable a GUI filter. The dated findings are in
[the audit report](../../docs/results/TIMESTAMP_AUDIT_20261116.md).

Provide the existing prediction NPZ (`images`, `offsets`, `detections`, with xyxy,
score, class columns), annotation JSON records (`image`, `UAV_boxes`), and a JSON
mapping from every image name to its reviewed timestamp rectangles. Explicit empty
lists mean no timestamp. Unknown images fail rather than receiving a generic corner mask.

```sh
python experiments/pinp2_osd/audit_osd.py \
  --predictions /path/to/original.npz \
  --annotations /path/to/annotations.json \
  --regions /path/to/timestamp_regions.json \
  --output /path/to/new-audit-directory
```

Use `--fixed-only` for GUI outputs saved only at conf0.25: their missing low-score
predictions prevent AP recomputation. Use original low-floor predictions for AP;
the default evaluator assumes the project's 0.001 floor. The script refuses to
reuse an output directory and verifies source hashes before/after.

The rule removes a prediction when at least half its area overlaps a reviewed
timestamp rectangle. All GT boxes remain in the evaluation, and surviving boxes
are matched again. The outputs include per-box decisions, per-image TP/FP/FN,
filtered prediction copies, aggregate metrics, removed original TPs, and new misses.
Original results remain separate. Region choices made after observing errors are
descriptive analysis, not independent validation of a deployable filtering policy.

Run the safety checks with:

```sh
python -m unittest discover -s experiments/pinp2_osd -p 'test_*.py' -v
```

The follow-up [localization diagnosis](../../docs/results/LOCALIZATION_DIAGNOSIS_20261116.md)
adds three separate tools:

- `check_geometry.py`: 72 analytic decode/restore checks and exact demo input-pixel checks; safe for offline NumPy analysis.
- `compare_pi_backends.py`: explicitly authorized, Pi-only FP32/H10 diagnostic inference. Requires a hash-checked image manifest, frozen model directory, two existing shared locks, a fresh output directory and an external timeout guard. It does not launch itself or install a runtime.
- `analyze_paired.py --returned /path/to/returned --output /path/to/new-analysis`: offline metrics, confidence diagnostics, actual network-to-image coordinate checks and a scalar reconstruction of the saved H10 head for frame4. No model loading.

The native ONNX graph and H10 host decoder are compared on identical image pixels.
The same original labels remain in both evaluations. Counterfactual box resizing
is diagnostic only and must not silently replace the deployed policy or original GT.
