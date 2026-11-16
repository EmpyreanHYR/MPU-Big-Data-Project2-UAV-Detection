# PinP2 H10 GUI model / 真机模型

The GUI's frozen HAILO10H model is available in [GitHub Release](https://github.com/EmpyreanHYR/MPU-Big-Data-Project2-UAV-Detection/releases/tag/gui-h10-v1.0.0).
From the repository root, run:

```sh
python3 scripts/download_gui_model.py
python3 scripts/download_gui_model.py --verify-only
```

Files are installed in `models/pinp2_h10/` (ignored by Git). The downloader checks
the ZIP and every file against the [release manifest](../configs/deployment/pinp2_h10_release.json)
and verifies identity against the [deployment policy](../configs/deployment/pinp2_h10.json).
See [real-media setup](../docs/GUI_REPRODUCIBILITY.md#4-prepare-real-h10-detection--准备真机).

Only `model.hef` and its matching `h10_metadata.json` are needed at inference;
the package also includes policy, checksums and a README. No Torch/PT/ONNX is
needed by this GUI. HailoRT 5.1.1 and HAILO10H hardware are required.

Local archive links `trained/`, `deployment/` and `pretrained/` are maintainer
artifacts and are not needed to reproduce GUI inference from this public release.
