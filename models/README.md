# Model weights / 模型权重

The final model (YOLO26n + PConv + P2, scratch 100 epochs) is published in two
GitHub Releases; weights are not stored in the Git history.

| Package | Contents |
|---|---|
| [pinp2-final-model-v1.1.0](https://github.com/EmpyreanHYR/MPU-Big-Data-Project2-UAV-Detection/releases/download/pinp2-final-model-v1.1.0/pinp2-final-model-v1.1.0.zip) | `best.pt` (epoch 85, FP32), `model.onnx` (opset 17), `model.hef`, architecture, deployment config/policy, export-verification and selection records, `SHA256SUMS` |
| [gui-h10-v1.0.0](https://github.com/EmpyreanHYR/MPU-Big-Data-Project2-UAV-Detection/releases/tag/gui-h10-v1.0.0) | GUI inference package (`model.hef` + matching `h10_metadata.json`, identical HEF bytes) and the narrated demonstration video |

The GUI downloads and verifies its package automatically:

```sh
python3 scripts/download_gui_model.py
python3 scripts/download_gui_model.py --verify-only
```

Files are installed in `models/pinp2_h10/` (ignored by Git). The downloader checks
the ZIP and every file against the [release manifest](../configs/deployment/pinp2_h10_release.json)
and matches identity against the [deployment policy](../configs/deployment/pinp2_h10.json).
See [real-media setup](../docs/GUI_REPRODUCIBILITY.md#4-prepare-real-h10-detection--准备真机).

The GUI runs `model.hef` on HAILO10H with HailoRT 5.1.1 and needs no Torch/PT/ONNX
or the full-model ZIP's `best.pt`.

Weights of the other 18 comparison and ablation runs (COCO-initialized 150-epoch
models, YOLO11n/YOLOv8n/RT-DETR-L/PF-SIA/MSF-GhostNet comparisons, training-fraction
runs) are in the private result package; this repository publishes the final model.
