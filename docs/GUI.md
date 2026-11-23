# PyQt6 红外无人机检测演示

新克隆仓库请从[GUI复现指南](GUI_REPRODUCIBILITY.md)开始：固定依赖、合成样例、配置模板和自动检查。下文是完整操作、素材格式与硬件实测。

界面采用英文为主、中文辅助的双语文案，包含输入设置、状态、操作按钮和错误提示。桌面入口为 [run_gui.py](../scripts/run_gui.py)，源代码在 [gui](../src/uav_detection/gui)。本机回放已有实验结果；实时检测支持 [H10 服务](../scripts/deployment/serve_gui.py) 和树莓派本机直接调用两条路径。界面不导入 Torch，也不读取 `.pt` 权重。普通回放入口不连接设备；H10 启动器连接配置的树莓派，在独立目录中创建有时限的服务。

## 启动

在仓库根目录使用 Python 3.10+：

```sh
python3 -m venv .venv-gui
.venv-gui/bin/python -m pip install -e '.[gui]' -c constraints/gui-desktop-20261116.txt
.venv-gui/bin/python scripts/run_gui.py
```

Mac 可双击仓库根目录的 [启动检测演示.command](../启动检测演示.command)。Windows 使用 `.venv-gui\Scripts\python.exe` 替代 `.venv-gui/bin/python`。Linux 桌面需要可用的 Qt 图形环境；本地只有回放和客户端，不要求 HailoRT。

Mac GUI 使用独立 `.venv-gui`，与训练环境分开。客户端优先使用 PyQt6；树莓派若只有现成的系统 PyQt5，则自动使用兼容层，不安装或替换系统 Qt。依赖是 PyQt6、NumPy、Pillow 和 OpenCV headless；OpenCV 负责媒体读写，Qt 负责显示。H10 服务使用树莓派已有的 HailoRT5.1.1、NumPy、Pillow，不需要在 Pi 上安装桌面依赖。应从完整源码仓库运行，以读取部署策略和实验表。

实测环境见[环境说明](ENVIRONMENT.md)；Mac依赖按上述验收组合由约束文件固定。

公开模型下载、自动配置和新设备复现步骤见[GUI复现指南](GUI_REPRODUCIBILITY.md#4-prepare-real-h10-detection--准备真机)；[README内嵌演示](../README.md#gui-demonstration--操作演示)可直接观看。

## 树莓派本机高速演示

视频演示使用 [启动树莓派本机演示.command](../启动树莓派本机演示.command)，在Pi显示器上打开GUI。素材按哈希缓存一次，随后本机解码并调用H10，无逐帧网络传输，保留原始像素、模型和NMS策略。操作、5分钟彩排和后续录制准备见 [演示准备](DEMO_REHEARSAL.md)。

## 无设备课堂演示

准备好项目素材后，启动自动载入 `outputs/gui_demo/demo.json`；也可点击“载入项目演示样例”，再点击“开始检测 / 回放”。完整验证集以默认2帧/秒播放，约4分10秒；可在开始前调整速度。此模式只显示历史预测，界面和导出均标明 `replay`。

在另一台机器准备样例：

```sh
.venv-gui/bin/python scripts/prepare_gui_demo.py \
  --predictions /path/to/verified-deployment/detections.npz \
  --data-zip /path/to/validation_data.zip \
  --manifest /path/to/validation_manifest.json
```

该脚本校验预测哈希及清单中每张图片和标签的 SHA256，复制到新的私有输出目录，保留原始材料。默认包括全部清单，也可用 `--limit 20` 提取清单前20张作短演示。目录搬家后重新准备，或在界面重新选择路径。演示包、配置和导出均在 `.gitignore` 保护的 `outputs/` 内。

已有结果可以直接选择：

- NPZ：`images` 为相对路径字符串数组，`offsets` 为长度 N+1 的整数数组，`detections` 为 M×6 数组；禁止 pickle。
- JSONL：每行包含 `image` 和 `boxes_xyxy_score_class`，格式为 `[x1,y1,x2,y2,score,class]`。UAV 类别为0，坐标为原图像素。
- 同名 `.meta.json` 可提供 `model_id`、`confidence_floor`、`policy`、`weights_sha256`、`hef_sha256`、`image_hashes`、`label_hashes`；没有时尝试同目录 `completed.json`，否则明确显示来源未提供，保存阈值按0.25处理。
- 素材根目录拼接 `image` 后必须找到原图；例如记录是 `images/val/a.jpg`，应选择包含 `images` 的目录。单图模式按唯一 basename 匹配，重名会拒绝。
- 可选标注目录须镜像图片相对路径，将后缀换成 `.txt`。例如 `labels_root/images/val/a.txt`。格式为 YOLO 单类归一化 `0 cx cy w h`，负样本要有空文件。缺失标签会报错，不视为负样本。

回放沿用保存时的 NMS 输出。显示置信度默认0.25，可提高；来源中的 NMS 口径保留在摘要中。

## 一键连接现有树莓派

本机连接配置准备好后，双击 [启动H10实时检测.command](../启动H10实时检测.command)，自动创建独立服务目录、建立 SSH 隧道，并打开已配置令牌的 GUI。默认选择红外视频与无损 PNG 帧传输；可在界面选择 JPEG95 有损加速。首次视频开始前选择 `Start / 开始`。

[run_live_gui.py](../scripts/run_live_gui.py) 每次生成新令牌，通过加密 SSH 标准输入传递，不写入配置、远端文件或命令行参数。关闭 GUI 后，按 PID、进程启动时间和完整命令结束本次服务及自有隧道，释放共享锁。远端服务另有 GNU timeout 时限。

连接配置为本机私有的 `outputs/gui_h10_profile.json`，已在 `.gitignore` 中排除。迁移到另一台电脑时填写实际信息，例如：

```json
{
  "host": "your-pi-ssh-alias",
  "identity_file": "~/.ssh/your_existing_key",
  "remote_root": "/home/USER/Desktop/mpu-class",
  "model_dir": "/path/to/verified-release/model",
  "shared_lock": "/path/to/existing_hardware.lock",
  "additional_lock": "/path/to/other_project_hardware.lock",
  "max_seconds": 1800,
  "gui_config": {
    "kind": "video",
    "source": "/path/to/infrared-video.avi",
    "labels": "",
    "transport": "png",
    "display_fps": 30,
    "save_video": true
  }
}
```

`remote_root` 必须已存在，两个锁是设备使用者共享的实际锁。测试连接并立即释放资源：

```sh
.venv-gui/bin/python scripts/run_live_gui.py --check-only
```

连接记录放在 `outputs/gui_connections/`。SSH 需已配置密钥登录及可信主机记录。远端设备忙时直接失败。

## H10 实时检测

使用当前已验证 PinP2 发布包的 `model/`，必须包含匹配部署策略的 `model.hef` 和 `h10_metadata.json`。服务核对模型、HEF 哈希和 HAILO10H 身份，持有两个共享设备锁；设备忙或模型不符即报错。默认 conf0.25、原图裁剪坐标后 NMS IoU0.4、max300；不在 GUI 中更改这套已验证策略。

在已授权、可用的树莓派上手动运行（先将仓库放到独立目录，替换现有模型和锁路径）：

```sh
# 在 Pi 的终端输入令牌，不把令牌保存到仓库或命令行参数。
read -r -s -p 'Service token (at least 32 characters): ' PINP2_GUI_TOKEN
export PINP2_GUI_TOKEN

timeout --signal=TERM --kill-after=20s 1900s \
  python3 scripts/deployment/serve_gui.py \
  --model-dir /path/to/release/model \
  --shared-lock /path/to/existing_hardware.lock \
  --additional-lock /path/to/other_project_hardware.lock \
  --max-seconds 1800
```

服务只监听 Pi 的 `127.0.0.1:8765`。最长配置7200秒，默认1800秒；请求和设备调用有超时，外层 `timeout` 限定本次服务及其子进程的结束。该服务与设备上其他任务共用同一组锁路径。

在客户端另开终端建立隧道：

```sh
ssh -N -L 8765:127.0.0.1:8765 your-pi-ssh-alias
```

GUI 选择 `H10 live detection / 实时检测`，保持地址 `http://127.0.0.1:8765`，输入同一令牌。令牌只保存在当前内存。客户端对本机地址使用明文 HTTP（经 SSH 隧道），远端直连须 HTTPS。标准部署使用隧道。

选择单图、文件夹、视频或摄像头后开始。切换素材或输入类型会清空旧标注路径；选择视频／摄像头切换到 H10 引擎。摄像头编号指**运行 GUI 的电脑**连接的摄像头，画面经隧道发给 Pi，首次使用需操作系统授权。视频逐帧顺序处理，不跳帧，实际帧率取决于素材与网络。

服务 API：带 Bearer 令牌的 `GET /health` 返回模型、设备、代码哈希、策略及累计解码次数；`POST /detect` 接受 `image/png` 或 `image/jpeg`，上限16MB、2400万像素，返回原图坐标、分数和服务处理耗时。协议标识 `pinp2-demo-v1`。HTTP/1.1 长连接减少重复建立连接；最多4个连接，H10 调用由互斥锁保护，设备正在推理时另一个推理请求返回409。服务连接等待窗口为30秒，客户端请求超时为45秒。客户端在请求超过8秒未响应时重新连接；失败推理请求不自动重发。

图片模式直接上传原始 PNG/JPEG 字节，避免解码再编码增大上传量，也不改原始像素。其他图片格式仍编码为 PNG。视频／摄像头可选择无损 PNG 或 JPEG95；JPEG95 会改变像素，仅供网络带宽受限的演示；同一段前30帧 PNG 得到18个框、JPEG95得到17个框，因此默认保留无损路径。逐帧输出记录实际编码和上传字节数。

## 在 Pi 本机运行界面

Pi 的系统 `python3` 已带 PyQt5 和 OpenCV，兼容层可直接使用。将客户端 `src/`、`scripts/`、`configs/` 以及可选 `docs/results/` 放到一个独立源码目录，按上一节启动 H10 服务，在同一终端环境中运行 GUI（配置里的 URL 指向本机服务）：

```sh
PINP2_GUI_TOKEN="${PINP2_GUI_TOKEN}" python3 scripts/run_gui.py --config /path/to/local_gui_config.json
```

GUI 进程从 `PINP2_GUI_TOKEN` 环境变量读取令牌。使用时需要 Pi 的桌面显示会话。Pi 本机路径没有 Mac—Pi 中继的逐帧上传开销。

## 演示操作与输出

| 操作 | 行为 |
|---|---|
| 开始／暂停／继续／停止 | 后台线程处理；停止会完成当前有界请求并保留已完成输出；关闭窗口等待线程释放 |
| 空格／Esc／F11 | 暂停继续／停止／全屏切换 |
| 滚轮／拖动／双击图片 | 缩放／平移／适应窗口 |
| 点击目标明细行 | 高亮目标并显示局部放大，放大图隐藏文字以便观察微小目标 |
| 黄色／绿色／红色框 | 参考标注／检测框／当前选中目标 |
| 保存当前截图 | 导出当前帧检测叠加 PNG |
| 保存标注图片 | 每个处理帧写入 `annotated/`，文件名是原始处理序号 |
| 保存演示视频 | 写入 MJPG/AVI，无音频；所有帧同尺寸，帧率为素材帧率与播放上限较小值 |
| 保存／加载配置 | 保存界面设置（不含令牌）；加载配置后手动运行 |
| 实验结果对比 | 读取仓库中的结果CSV，保留原列名，可按表头排序；与本次会话分开 |

每次创建新的带时间和随机后缀目录：

- `detections.jsonl`：含无目标帧的逐帧记录、检测框、客户端／服务耗时和 TP/FP/FN。
- `raw_detections.jsonl`：时间区域过滤之前的原始预测框，保留已有置信度阈值和 NMS 输出。
- `detections.csv`：逐检测框数据，适合表格分析；无目标帧见 JSONL。
- `detections.meta.json`：模型身份、已有策略、显示阈值和来源信息，可用于再次回放。
- `summary.json`：状态 `running/completed/stopped/failed/time_limit`，已保存帧数、检测框数、固定阈值的 TP/FP/FN、Precision/Recall/F1，以及耗时范围。异常时保留已完成部分；未定义的指标为 `null`；进程被强制结束时状态为 `running`。

逐图回放的 `Request / replay latency` 只计查询已有预测；实时模式计客户端上传请求与响应解析。服务耗时含预处理、H10、解码和NMS，不含传输、GUI显示和导出。`Display FPS` 是检测视图最近最多30个不同帧的绘制完成速率（paintEvent），包含网络、解码和绘制，暂停恢复时重置；`Speed cap` 是上限值。保存的视频为等间隔演示视频，不含原始音频。精度指标（AP/mAP）以原实验记录为准。

## 测试与实测结果

```sh
QT_QPA_PLATFORM=offscreen .venv-gui/bin/python -m unittest discover -s tests -p 'test_gui.py' -v
.venv-gui/bin/python scripts/check_repository.py
.venv-gui/bin/python scripts/check_references.py
```

Mac 本机31项测试通过，覆盖格式与路径校验、空预测、标注缺失、哈希不符、混合尺寸导出失败计数、取消／暂停／重启、窗口关闭，以及测试服务的鉴权、长连接、并发拒绝、图片和视频请求。发布的500张验证集预测经完整 GUI 回放得到385个框、TP323／FP62／FN163／GT486，与2026-11-15部署验收一致。Pi/H10 实测：64张图片逐值一致，30帧PNG无损视频、300帧JPEG95视频及12秒暂停恢复通过，导出AVI逐帧可解码；Pi 本机完成30帧实际Qt窗口离屏测试，Pi GUI测试31项中30项通过（1项为Mac专属约束）。详情见 [H10联调记录](results/GUI_H10_20261116.md)。

线程控制采用 Qt 的信号与协作停止方式，GUI只在主线程绘制：[Qt QThread 官方说明](https://doc.qt.io/qt-6/qthread.html)。

本机优化版在Wayland桌面完成5分钟循环，平均绘制16.51FPS、最高60.6°C，无降频，每帧网络上传为0；详见 [本机显示稳定性](results/GUI_NATIVE_20261116.md)。

## Timestamp filter / 时间区域过滤

`Timestamp filter` 是 GUI 的可选后处理规则。仅当输入文件 SHA256 命中私有 `timestamp_profiles` 配置，且画面尺寸一致时，才过滤已核验时间文字区域内的预测。未知素材、摄像头和图片文件夹不套用这项规则。通用配置默认关闭；本机演示配置可针对已核验素材开启。

配置记录 `size: [width, height]`、`region: [x1, y1, x2, y2]`（原图像素）和 `coverage`。预测框与文字区域交集占预测框面积至少50%时移除；区域很小，并且与具体素材绑定。更换视频或文件后需重新核验区域。进入被排除区域的真实目标同样会被过滤。

原图、模型权重和标注保持不变。`raw_detections.jsonl` 保留过滤前预测，`detections.jsonl`、CSV及界面使用过滤后结果；每帧记录规则状态和移除数量，摘要记录 `raw_detections` 与 `timestamp_removed`。有标注时，匹配仍使用原始GT。

2026-11-16：33项GUI测试通过；Pi/H10 对同一张含时间文字图片过滤前1框、过滤后0框；30帧演示素材18框→8框，移除10个时间文字误检，无文字的控制图片保留原框。
