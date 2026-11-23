# PinP2 H10 default deployment

For the PyQt6 demonstration client and the bounded, authenticated H10 HTTP service, see [GUI guide](../../docs/GUI.md) and [serve_gui.py](serve_gui.py). Video/camera frames are captured by the client. The HTTP path passed real H10 image and video acceptance; see [GUI integration results](../../docs/results/GUI_H10_20261116.md) for scope and measured transport latency. Physical camera capture is the next validation step. The image/folder CLI evidence below is a separate measurement.

The frozen scratch100 PinP2 model uses **NMS IoU=0.4**, confidence0.25 and max300. [Policy](../../configs/deployment/pinp2_h10.json) pins the exact weights and HEF hashes. [Postprocessor](pinp2_postprocess.py) calls greedy NMS after raw decoding, original-coordinate restoration and clipping, using the policy rather than the historical metadata field. Stable score ordering and coordinates/scores identical to the H10 output are retained.

[pinp2_h10.py](pinp2_h10.py) is the current image/folder deployment entry point. Run on Raspberry Pi5 with HailoRT5.1.1, HAILO10H, NumPy and Pillow (replace paths with the existing device paths):

```sh
timeout --signal=TERM --kill-after=20s 900s python3 scripts/deployment/pinp2_h10.py \
  --model-dir /path/to/pinp2_model --input /path/to/images \
  --output /path/to/new_output \
  --shared-lock /path/to/existing_hardware.lock \
  --additional-lock /path/to/other_project_hardware.lock
```

Use the release's matching `model/` directory. The output directory is new, and both existing hardware locks are required; a busy device stops the run before inference. The default config is resolved relative to the code, independent of working directory, so no `--policy` override is needed. `--validation-data` replaces `--input` for a frozen validation root. Optional `--save-ap-predictions` records a separate0.001-floor pass outside the timed pipeline.

`completed.json` records effective IoU, actual NMS calls, candidate and suppression counts, code/model hashes and timing scope. `detections.npz` and `detections.jsonl` contain the filtered boxes. For application integration, call `PinP2Postprocessor.decode(outputs, metadata, geometry)` after each H10 result; the raw decoder alone returns unfused e2e candidates. This release covers image/folder inference; camera streaming is served by the GUI service.

Release20261115-nms04 passed a fresh500-image default-policy acceptance without overrides:500 NMS calls,442→385 candidates,57 suppressed, all boxes/scores/order identical to frozen NMS replay. TP323/FP62/FN163; AP50:95=31.740%. Four NumPy tests cover actual raw-head invocation, a0.4-versus0.5 boundary example, ties and invalid policies. [Acceptance aggregate](../../docs/results/NMS_DEPLOYMENT_ACCEPTANCE_20261115.json).

The acceptance pass measured22.56 FPS (44.33ms/image), separate from the three-repeat threshold benchmark22.89±0.01 FPS. The 500-image split is the internal validation set used for threshold selection; crowded targets, independent video, long-running camera throughput and power are the remaining measurement scope. Historical evaluation scripts and raw decoder reproduce the earlier results. [Choice and full comparisons](../../docs/results/NMS_VLM_AUDIT_20261115.md).
