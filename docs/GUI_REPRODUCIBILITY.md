# Reproduce the GUI / 从仓库复现界面

[![GUI reproduction](https://github.com/EmpyreanHYR/MPU-Big-Data-Project2-UAV-Detection/actions/workflows/gui.yml/badge.svg)](https://github.com/EmpyreanHYR/MPU-Big-Data-Project2-UAV-Detection/actions/workflows/gui.yml)

The complete GUI, H10 adapters, configuration templates and checks are in this
repository. A fresh checkout can run the interface without private files using
the **synthetic replay fixture**. Device detection additionally requires
the [public, verified model package](https://github.com/EmpyreanHYR/MPU-Big-Data-Project2-UAV-Detection/releases/tag/gui-h10-v1.0.0) and a Raspberry Pi 5 with HAILO10H.

模型包和完整演示视频已公开；有匹配硬件即可用自己的素材检测。下面的合成样例用于无设备界面检查。

## 1. Clone and install / 安装

Use Python 3.12 or later with the pinned desktop dependency set. From a terminal:

```sh
git clone https://github.com/EmpyreanHYR/MPU-Big-Data-Project2-UAV-Detection.git
cd MPU-Big-Data-Project2-UAV-Detection
python3 -m venv .venv-gui
.venv-gui/bin/python -m pip install -e '.[gui]' -c constraints/gui-desktop-20261116.txt
.venv-gui/bin/python scripts/prepare_gui_smoke_demo.py
.venv-gui/bin/python scripts/run_gui.py --config outputs/gui_smoke/demo.json
```

Click **Start**, **Pause**, **Resume**, then **Stop**. Generated shapes appear in
the input and detection panes; select a table row to inspect the enlarged target.
The preview image and model identifier explicitly say that this is a fixture.
Exports go to `outputs/gui_smoke/results/` with a new directory for each session.
The generator refuses to overwrite an existing bundle; reuse the existing one or
pass `--output outputs/gui_smoke_2` and open that directory's `demo.json`.

The constraint file pins all six GUI runtime packages. The `gui` extra is
sufficient for replay; the `model` extra is not needed.

On Windows PowerShell, use `py -3.12 -m venv .venv-gui` and replace
`.venv-gui/bin/python` with `.venv-gui\Scripts\python.exe`. Linux needs a desktop
Qt platform and its OpenGL/EGL runtime libraries; `QT_QPA_PLATFORM=offscreen` is for
tests. Keep the whole checkout and editable installation, since the GUI also
reads the repository's evaluation scripts and policy. Run the commands from the
repository root; the default configuration uses relative paths, so moving the
whole checkout preserves them.

## 2. Run the checks / 检查

```sh
.venv-gui/bin/python scripts/check_gui.py
.venv-gui/bin/python scripts/check_repository.py
.venv-gui/bin/python scripts/check_references.py
```

`check_gui.py` needs the GUI dependencies; it runs the GUI contract/lifecycle
tests, generates a fixture in a temporary directory, opens a Qt window, processes
12 images, checks exports and confirms that no Torch/Hailo runtime was loaded. The
[GUI workflow](../.github/workflows/gui.yml) runs this check on GitHub Actions.

## 3. Check timestamp filtering / 时间文字过滤

```sh
.venv-gui/bin/python scripts/run_gui.py --config outputs/gui_smoke/timestamp_demo.json
```

Click **Start**: the generated timestamp prediction is removed while the generated
target remains. Switch the filter off and run again to compare. Both runs retain
`raw_detections.jsonl`, and filtered JSONL/CSV keeps the original GT.

Media files require an independently reviewed timestamp rectangle and the SHA256
of the exact input file. The configuration map is keyed by that hash:

```json
{
  "timestamp_filter": true,
  "timestamp_profiles": {
    "REPLACE_WITH_REVIEWED_SOURCE_SHA256": {
      "name": "Reviewed timestamp region",
      "size": [640, 512],
      "region": [14, 16, 171, 32],
      "coverage": 0.5
    }
  }
}
```

The rectangle above belongs to the previously reviewed thermal demonstration.
Unknown files, wrong image dimensions, folders and cameras are not filtered, and a
target entering an excluded region is removed as well. Keep the filter off until
the new source has been reviewed.

## 4. Prepare real H10 detection / 准备真机

| Requirement | How it is supplied |
|---|---|
| Raspberry Pi 5, HAILO10H, working desktop | Existing device; physical display for native GUI |
| HailoRT 5.1.1 and matching driver | Existing device stack; launchers do not install drivers |
| Python, NumPy, Pillow, OpenCV, PyQt5 or PyQt6 | The verified Pi used system PyQt5 5.15.11 / Qt 5.15.15, NumPy 2.2.4, Pillow 11.1.0 |
| `models/pinp2_h10/model.hef`, `h10_metadata.json` | Download the pinned public release with the command below |
| Input images or video | Your own media, or the authorized project dataset/result package |
| Two shared hardware locks | Lock files shared with other workloads on the device |

### Download the model / 下载模型

Run this **on the Pi**, from the complete repository checkout:

```sh
python3 scripts/download_gui_model.py
python3 scripts/download_gui_model.py --verify-only
```

The standard-library downloader installs the [frozen release](https://github.com/EmpyreanHYR/MPU-Big-Data-Project2-UAV-Detection/releases/tag/gui-h10-v1.0.0)
into `models/pinp2_h10/`. It checks the ZIP size/SHA256, every extracted file,
metadata identity and the repository deployment policy, and leaves existing files
untouched. The [release manifest](../configs/deployment/pinp2_h10_release.json)
pins the checksums. For an offline Pi, download
[`pinp2-h10-model-v1.0.0.zip`](https://github.com/EmpyreanHYR/MPU-Big-Data-Project2-UAV-Detection/releases/download/gui-h10-v1.0.0/pinp2-h10-model-v1.0.0.zip)
on another computer, copy it to the Pi, then run:

```sh
python3 scripts/download_gui_model.py --archive /path/to/pinp2-h10-model-v1.0.0.zip
```

The package contains `model.hef`, `h10_metadata.json`, `deployment_policy.json`,
`README.md` and `SHA256SUMS`. GUI inference needs no `.pt`, ONNX, Torch or training
environment and targets **HAILO10H**. The metadata is kept byte-for-byte; its
historical `H10_used: false` field records export provenance.

模型和[带配音演示视频](https://github.com/EmpyreanHYR/MPU-Big-Data-Project2-UAV-Detection/releases/download/gui-h10-v1.0.0/PinP2_H10_GUI_narrated_demo.mp4)
公开下载。使用自己的图片／视频即可检测，无需标签；重算论文精度需对应的验证集、标注和划分。

The [deployment policy](../configs/deployment/pinp2_h10.json) defines model
identity, HEF/weight SHA256, confidence 0.25 and NMS IoU 0.4. The expected
HEF hash is `ad2d561f768bb31262ddad49b1a5b55a0d05fba8a339bc4860df8fcd9d730c15`.
The metadata shipped with that package includes `model_id`, `family`,
`weights_sha256`, `hef_sha256`, `output_shapes`, `strides` and `reg_max` for the
eight raw output heads. Startup checks the hashes, output mapping and device type,
and rejects busy hardware or incompatible models.

### Native Pi GUI / 树莓派本机界面

Clone the complete repository **on the Pi**, then in its graphical desktop terminal:

```sh
python3 -c "import numpy, PIL, cv2, PyQt5, hailo_platform; print('Pi dependencies available')"
python3 scripts/configure_pi_gui.py \
  --source /absolute/path/to/your-image.png \
  --shared-lock /absolute/path/to/shared-hardware.lock \
  --additional-lock /absolute/path/to/shared-device.lock
timeout --signal=TERM --kill-after=20s 1860s \
  python3 scripts/run_pi_gui.py --config outputs/gui_pi_local.json --fullscreen
```

Replace the three paths with your own image/video and the two locks shared by all
H10 users on that device. Lock parent directories must exist and be writable. On a
new dedicated Pi, create a stable directory (e.g. `mkdir -p "$HOME/.local/state/pinp2"`)
and use `hardware.lock` and `device.lock` inside it; every later H10 workflow reuses
these paths. On a shared Pi, reuse the existing locks.

The helper creates `outputs/gui_pi_local.json` with absolute paths and does not
overwrite an existing file. For a video, supply an `.mp4`/`.avi` to `--source`, optionally
add `--loop`, and use `--output outputs/gui_pi_video.json`; launch with that config.
Choose **Start**, then **Pause**, **Resume**, and **Stop** in the GUI. Detections and
session summaries are saved under `outputs/gui/`. Labels are optional and empty
by default; without GT labels the counts are detections only.
The timestamp filter starts off; configure a reviewed source as in section 3.

If the Pi uses PyQt6, replace `PyQt5` in the dependency check. Use the interpreter
that imports the installed HailoRT stack. The native GUI decodes local frames and calls H10 in memory,
with zero per-frame network upload. Select **Start** to begin inference. A bounded
unrecorded desktop rehearsal can add `--rehearse-seconds 60` to the command.

### SSH launch from another computer / 从电脑连接

```sh
mkdir -p outputs
cp configs/gui/h10-profile.example.json outputs/gui_h10_profile.json
# Edit the private profile with your existing SSH alias, paths and shared locks.
.venv-gui/bin/python scripts/run_live_gui.py --check-only
.venv-gui/bin/python scripts/run_live_gui.py
```

The SSH host key must already be trusted and key login must work. `remote_root`
must exist. Set `model_dir` to the Pi's absolute `models/pinp2_h10` directory
after downloading the model there; a client-side download does not install it on
the Pi. The profile's source file is on the client. For a GUI shown on the
Pi's monitor, use `scripts/launch_pi_gui.py --video /path/to/local/video.avi`;
it caches that file on the Pi and creates a separate release and local launcher.
Alternatively use the native configuration above with media already on the Pi.

## 5. Replay and outputs / 结果回放

To replay the original model results without hardware, obtain the corresponding
prediction file, validation ZIP and manifest. Then follow
[the real replay preparation steps](GUI.md#无设备课堂演示).

The [GUI guide](GUI.md) covers formats, controls, result exports, HTTP transport
and error messages. The [native demonstration guide](DEMO_REHEARSAL.md) covers
recording; the GUI's silent annotated AVI export differs from a full desktop
recording with narration. Dated [acceptance results](results/GUI_NARRATED_20261116.md)
describe the measured Raspberry Pi 5 / HAILO10H device.

A clean export of the repository installed into a fresh desktop environment with
the constraint file passes all 33 GUI tests, the 12-image window/export smoke check,
the synthetic timestamp example, 98 project tests (8 optional model tests skipped)
and 5 timestamp audit tests. The model package adds 3 integrity tests (36 GUI tests
total), including installation of the release ZIP without loading it and public
downloads checked against the pinned hashes. The workflow badge reports the Linux
CI status.

| Symptom | Check |
|---|---|
| Blank initial window / no demo bundle | Run the synthetic generator and pass its `demo.json`, or supply real replay assets |
| GUI dependencies missing | Use the same Python interpreter for install, check and launch |
| Qt platform plugin failure | Use a graphical desktop and its Qt/EGL libraries; offscreen only for automated checks |
| `No module named detection_eval` after installing a wheel | Use the full checkout and `pip install -e`, as above |
| Model hash mismatch | Obtain the matching HEF and metadata package; keep the pinned policy |
| H10 is busy | Wait for the other workload to release the shared locks |
| Timestamp filter inactive | Check source SHA256, source kind and exact image dimensions |
| Missing labels | Clear the optional label path for unlabeled media, or provide the mirrored YOLO labels |
