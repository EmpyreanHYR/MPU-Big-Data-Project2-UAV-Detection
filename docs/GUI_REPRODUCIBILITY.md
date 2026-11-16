# Reproduce the GUI / 从仓库复现界面

[![GUI reproduction](https://github.com/EmpyreanHYR/MPU-Big-Data-Project2-UAV-Detection/actions/workflows/gui.yml/badge.svg)](https://github.com/EmpyreanHYR/MPU-Big-Data-Project2-UAV-Detection/actions/workflows/gui.yml)

The complete GUI, H10 adapters, configuration templates and checks are in this
repository. A fresh checkout can run the interface without private files using
an explicitly **synthetic replay fixture**. Real detection additionally requires
the verified model package and a Raspberry Pi 5 with HAILO10H.

仓库即可复现界面与合成样例；真机检测还需匹配的模型包和硬件，合成样例不代表模型效果。

## 1. Clone and install / 安装

Use Python **3.12 or later** for the recorded desktop dependency set (the local
acceptance used Python 3.14.6 on macOS ARM64). From a terminal:

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

The constraint file pins all six GUI runtime packages. An unconstrained
`pip install -e '.[gui]'` supports the project's broader Python 3.10+ range, but
may select different dependency versions. Do not install the `model` extra for
GUI replay; Torch and detector checkpoints are unnecessary.

On Windows PowerShell, use `py -3.12 -m venv .venv-gui` (or an installed newer
Python) and replace `.venv-gui/bin/python` with `.venv-gui\Scripts\python.exe`.
Windows has not had native acceptance testing. Linux needs a desktop Qt platform
and its OpenGL/EGL runtime libraries; `QT_QPA_PLATFORM=offscreen` is for tests,
not an interactive demonstration. Keep the **whole checkout** and use editable
installation: the GUI also reads the repository's evaluation scripts and policy.
Run the commands from the repository root. The generated default configuration
uses relative paths, so moving the whole checkout preserves those paths.

## 2. Run the checks / 检查

```sh
.venv-gui/bin/python scripts/check_gui.py
.venv-gui/bin/python scripts/check_repository.py
.venv-gui/bin/python scripts/check_references.py
```

`check_gui.py` requires the GUI dependencies, runs the GUI contract/lifecycle
tests, generates a fresh fixture in a temporary directory, opens a Qt window,
processes 12 images, verifies exports and confirms no Torch/Hailo runtime was
loaded. Its offscreen painted frames are a software check, not a monitor FPS
measurement. The [GUI workflow](../.github/workflows/gui.yml) runs this check on
GitHub Actions; it does not connect to hardware or train a model.

## 3. Check timestamp filtering / 时间文字过滤

```sh
.venv-gui/bin/python scripts/run_gui.py --config outputs/gui_smoke/timestamp_demo.json
```

Click **Start**: the generated timestamp prediction is removed while the generated
target remains. Switch the filter off and run again to compare. Both runs retain
`raw_detections.jsonl`; filtered JSONL/CSV and the original GT remain separately
auditable. This demonstrates the application rule, not improved model accuracy.

Real media require an independently reviewed timestamp rectangle and the SHA256
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

The rectangle above describes the previously reviewed thermal demonstration,
not a default for other videos. Unknown files, wrong image dimensions, folders
and cameras are not filtered. A genuine target entering an excluded region can
also be removed. Keep the filter off until the new source has been reviewed.

## 4. Prepare real H10 detection / 准备真机

| Requirement | How it is supplied |
|---|---|
| Raspberry Pi 5, HAILO10H, working desktop | Existing device; physical display for native GUI |
| HailoRT 5.1.1 and matching driver | Existing working device stack; launchers do not install drivers |
| Python, NumPy, Pillow, OpenCV, PyQt5 or PyQt6 | The verified Pi used system PyQt5 5.15.11 / Qt 5.15.15, NumPy 2.2.4, Pillow 11.1.0 |
| `model/model.hef`, `model/h10_metadata.json` | Obtain the frozen PinP2 H10 deployment package from the project maintainer |
| Input images or video | Your own media, or the authorized project dataset/result package |
| Two shared hardware locks | The actual lock files used by the device's other workloads |

模型、原始数据、SSH凭据和本机录像不随Git发布。没有模型包时，可复现界面和测试，
不能运行真实H10检测或重现原模型精度。

The [deployment policy](../configs/deployment/pinp2_h10.json) defines the exact
model identity, HEF/weight SHA256, confidence 0.25 and NMS IoU 0.4. The expected
HEF hash is `ad2d561f768bb31262ddad49b1a5b55a0d05fba8a339bc4860df8fcd9d730c15`.
The metadata must come with that same package; it includes `model_id`, `family`,
`weights_sha256`, `hef_sha256`, `output_shapes`, `strides` and `reg_max` for the
eight raw output heads. A general YOLO HEF or an arbitrarily edited hash is not
an equivalent model. Startup checks the hashes, output mapping and device type,
and refuses busy hardware or incompatible models without CPU fallback.

### Native Pi GUI / 树莓派本机界面

Clone the complete repository **on the Pi**, then in its graphical desktop terminal:

```sh
mkdir -p outputs
cp configs/gui/pi-local.example.json outputs/gui_pi_local.json
# Edit media, model and the two existing shared lock paths in the private copy.
python3 -c "import numpy, PIL, cv2, PyQt5, hailo_platform; print('Pi dependencies available')"
timeout --signal=TERM --kill-after=20s 1860s \
  python3 scripts/run_pi_gui.py --config outputs/gui_pi_local.json --fullscreen
```

If the Pi uses PyQt6, replace `PyQt5` in the dependency check. Use the interpreter
that can import the installed HailoRT stack; do not replace it with the desktop
pip environment. The native GUI decodes local frames and calls H10 in memory,
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
must exist. The profile's source file is on the client. For a GUI shown on the
**Pi's monitor**, use `scripts/launch_pi_gui.py --video /path/to/local/video.avi`;
it caches that file on the Pi and creates a separate release and local launcher.
Alternatively use the native configuration above with media already on the Pi.

## 5. Real replay, outputs and limitations / 真实结果回放

To replay the original model results without hardware, obtain the corresponding
prediction file, validation ZIP and manifest. Then follow
[the real replay preparation steps](GUI.md#无设备课堂演示).
Prediction files alone cannot reconstruct the source images.

The [GUI guide](GUI.md) covers formats, controls, result exports, HTTP transport
and error messages. The [native demonstration guide](DEMO_REHEARSAL.md) covers
recording; the GUI's silent annotated AVI export is different from a full desktop
recording with narration. Dated [acceptance results](results/GUI_NARRATED_20261116.md)
describe the previously measured device, not measurements made by fresh-clone CI.

Publication check on 2026-11-16: a clean export of the Git candidate was installed
into a new desktop environment using the constraint file, with no private assets.
All 33 GUI tests, the 12-image window/export smoke check and the synthetic timestamp
example passed. The public project suite ran 98 tests with 8 optional model tests
skipped; the 5 timestamp audit tests also passed. The CLI entry point and dependency
consistency were checked. See the workflow badge for subsequent Linux CI results.

| Symptom | Check |
|---|---|
| Blank initial window / no demo bundle | Run the synthetic generator and pass its `demo.json`, or supply real replay assets |
| GUI dependencies missing | Use the same Python interpreter for install, check and launch |
| Qt platform plugin failure | Use a graphical desktop and its Qt/EGL libraries; offscreen only for automated checks |
| `No module named detection_eval` after installing a wheel | Use the full checkout and `pip install -e`, as above |
| Model hash mismatch | Obtain the matching HEF **and** metadata package; keep the frozen policy |
| H10 is busy | Wait for the other workload to release its actual shared locks |
| Timestamp filter inactive | Check source SHA256, source kind and exact image dimensions |
| Missing labels | Clear the optional label path for unlabeled media, or provide the mirrored YOLO labels |
