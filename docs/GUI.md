# PyQt6 红外无人机检测演示

首次克隆仓库请从[GUI复现指南](GUI_REPRODUCIBILITY.md)开始：包含固定依赖、无需私有素材的合成样例、配置模板和自动检查。下文记录完整操作、真实素材格式及已经完成的硬件验收。

界面采用英文为主、中文辅助的双语文案，包含输入设置、状态、操作按钮和错误提示。桌面入口为 [run_gui.py](../scripts/run_gui.py)，源代码在 [gui](../src/uav_detection/gui)。本机回放已有实验结果；实时检测支持 [H10 服务](../scripts/deployment/serve_gui.py) 和树莓派本机直接调用两条路径。界面不会导入 Torch、读取 `.pt` 权重或启动训练。普通回放入口不连接设备；专用 H10 启动器会连接配置的现有树莓派，创建有时限的独立服务，不修改系统服务或电源。

## 启动

在仓库根目录使用 Python 3.10+：

```sh
python3 -m venv .venv-gui
.venv-gui/bin/python -m pip install -e '.[gui]'
.venv-gui/bin/python scripts/run_gui.py
```

Mac 可双击仓库根目录的 [启动检测演示.command](../启动检测演示.command)。Windows 使用 `.venv-gui\Scripts\python.exe` 替代 `.venv-gui/bin/python`。Linux 桌面需要可用的 Qt 图形环境；本地只有回放和客户端，不要求 HailoRT。

Mac GUI 使用独立 `.venv-gui`，与历史训练环境分开。客户端优先使用 PyQt6；树莓派若只有现成的系统 PyQt5，则自动使用兼容层，不安装或替换系统 Qt。依赖是 PyQt6、NumPy、Pillow 和 OpenCV headless；OpenCV 负责媒体读写，Qt 负责显示。H10 服务使用树莓派已有的 HailoRT5.1.1、NumPy、Pillow，不需要在 Pi 上安装桌面依赖。应从完整源码仓库运行，以读取部署策略和实验表。

本次客户端实际验证环境：macOS ARM64、Python3.14.6、PyQt6 6.12.1／Qt6 6.12.0、NumPy2.5.4、Pillow13.0.0、opencv-python-headless4.14.0.94。树莓派另已验证现有 PyQt5 5.15.11／Qt5 5.15.15、NumPy2.2.4、Pillow11.1.0 和 HailoRT5.1.1。Windows 尚未验收。macOS系统辅助功能扫描Qt原生动态表格时会触发崩溃，降低Qt版本也未解决；现已改用富文本表格，保留表头排序、文本复制和点击目标放大，并通过原生窗口复测。Mac依赖固定为验收组合，未关闭辅助功能。

## 树莓派本机高速演示

视频演示优先使用 [启动树莓派本机演示.command](../启动树莓派本机演示.command)，在Pi显示器上打开GUI。素材按哈希缓存一次，随后本机解码和调用H10，无逐帧网络传输和PNG/JPEG编解码开销。保留原始像素、模型和NMS策略。操作、5分钟彩排和后续录制准备见 [演示准备](DEMO_REHEARSAL.md)。

## 无设备课堂演示

已经准备过真实样例时，启动会自动载入 `outputs/gui_demo/demo.json`；也可点击“载入项目真实演示样例”，再点击“开始检测 / 回放”。完整验证集以默认2帧/秒播放，约4分10秒；可在开始前调整速度。此模式只显示历史预测，界面和导出均标明 `replay`。

在另一台机器准备样例：

```sh
.venv-gui/bin/python scripts/prepare_gui_demo.py \
  --predictions /path/to/verified-deployment/detections.npz \
  --data-zip /path/to/validation_data.zip \
  --manifest /path/to/validation_manifest.json
```

该脚本校验完成记录中的预测哈希，以及清单中每张图片和标签的 SHA256，复制到新的私有输出目录；不覆盖已存在的目录，不改原始材料。默认包括全部清单，也可用 `--limit 20` 提取清单前20张作短演示。目录搬家后重新准备，或在界面重新选择素材、预测和标签路径。演示包、配置和导出均在 `.gitignore` 保护的 `outputs/` 内，不把数据和个人路径提交到 Git。

已有结果可以直接选择：

- NPZ：`images` 为相对路径字符串数组，`offsets` 为长度 N+1 的整数数组，`detections` 为 M×6 数组；禁止 pickle。
- JSONL：每行包含 `image` 和 `boxes_xyxy_score_class`，格式为 `[x1,y1,x2,y2,score,class]`。UAV 类别为0，坐标为原图像素。
- 同名 `.meta.json` 可提供 `model_id`、`confidence_floor`、`policy`、`weights_sha256`、`hef_sha256`、`image_hashes`、`label_hashes`；没有时尝试同目录 `completed.json`，否则明确显示来源未提供，保存阈值按0.25处理。
- 素材根目录拼接 `image` 后必须找到原图；例如记录是 `images/val/a.jpg`，应选择包含 `images` 的目录。单图模式按唯一 basename 匹配，重名会拒绝。
- 可选标注目录须镜像图片相对路径，将后缀换成 `.txt`。例如 `labels_root/images/val/a.txt`。格式为 YOLO 单类归一化 `0 cx cy w h`，负样本要有空文件。缺失标签会报错，不视为负样本。

回放不会重新做 NMS，也不能恢复保存阈值以下的预测。显示置信度默认0.25，可提高；来源中的 NMS 口径保留在摘要中。新增的演示包会逐帧复核素材和标注哈希。

## 一键连接现有树莓派

本机连接配置准备好后，双击 [启动H10实时检测.command](../启动H10实时检测.command)，会自动创建独立服务目录、核验代码、建立 SSH 隧道，并打开已配置令牌的 GUI。默认选择真实红外视频与无损 PNG 帧传输；可在界面选择 JPEG95 有损加速。首次视频开始前选择 `Start / 开始`。

[run_live_gui.py](../scripts/run_live_gui.py) 每次生成新令牌，通过加密 SSH 标准输入传递；不会把令牌写入配置、远端文件或命令行参数。关闭 GUI 后，仅按 PID、进程启动时间和完整命令核验并结束本次服务及自有隧道，释放共享锁。远端服务另有 GNU timeout 时限保护；不修改常驻服务，不关闭树莓派。

连接配置为本机私有的 `outputs/gui_h10_profile.json`，不可提交 Git。迁移到另一台电脑时填写实际信息，例如：

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

`remote_root` 必须已存在，两个锁必须是设备使用者共享的实际锁。测试连接并立即释放资源可执行：

```sh
.venv-gui/bin/python scripts/run_live_gui.py --check-only
```

所有连接记录放在 `outputs/gui_connections/`。SSH 必须已配置密钥登录及可信主机记录；程序不关闭主机密钥检查、不安装驱动、不启动离线设备。远端忙时直接失败，不抢占其他任务。

## H10 实时检测

使用当前已验证 PinP2 发布包的 `model/`，必须包含匹配部署策略的 `model.hef` 和 `h10_metadata.json`。服务会核对模型、HEF 哈希和 HAILO10H 身份，持有两个已有共享设备锁；设备忙或模型不符即报错，不回退到 CPU。默认 conf0.25、原图裁剪坐标后 NMS IoU0.4、max300；不在 GUI 中更改这套已验证策略。

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

服务只监听 Pi 的 `127.0.0.1:8765`，不创建系统服务、不改防火墙。最长配置7200秒，默认1800秒；请求和设备调用有超时。外层 `timeout` 为本次服务及其子进程提供有限结束保护。使用实际已有锁路径，不能另造锁名绕过设备占用。

在客户端另开终端建立隧道：

```sh
ssh -N -L 8765:127.0.0.1:8765 your-pi-ssh-alias
```

GUI 选择 `H10 live detection / 实时检测`，保持地址 `http://127.0.0.1:8765`，输入同一令牌。令牌只保存在当前内存，不写配置、摘要或日志。客户端仅允许本机明文 HTTP（供 SSH 隧道使用）；远端直连须 HTTPS，不跟随重定向。服务端没有 HTTPS 终止功能，标准部署应使用隧道。

选择单图、文件夹、视频或摄像头后开始。切换素材或输入类型会清空旧标注路径，避免把图片标注误用到视频；选择视频／摄像头会切换到 H10 引擎。摄像头编号指**运行 GUI 的电脑**所连接摄像头，画面经过隧道发给 Pi；本程序没有实现远程 Pi 摄像头采集。首次使用摄像头需操作系统授权。视频逐帧顺序处理，不跳帧、不保证原始实时帧率；摄像头读取依赖操作系统驱动，驱动卡住时不能承诺立即停止。独立长时间摄像头运行尚未验收。

服务 API：带 Bearer 令牌的 `GET /health` 返回模型、设备、代码哈希、策略及累计真实解码次数；`POST /detect` 接受 `image/png` 或 `image/jpeg`，上限16MB、2400万像素，返回原图坐标、分数和服务处理耗时。协议标识 `pinp2-demo-v1`。HTTP/1.1 长连接减少重复建立连接；最多4个连接，H10 调用由互斥锁保护，设备正在推理时另一个推理请求返回409。服务连接等待窗口为30秒，客户端请求超时为45秒。客户端根据上次请求起点及响应到达时间，在超过8秒后于发请求前保守地重新连接；失败推理请求不会自动重发。

图片模式直接上传原始 PNG/JPEG 字节，避免解码再编码增大上传量，也不改原始像素。其他图片格式仍编码为 PNG。视频／摄像头可选择无损 PNG 或 JPEG95；**JPEG95 会改变像素**，它是网络演示选项，不能把该路径检测结果视为与无损基准逐值等价。逐帧输出记录实际编码和上传字节数。本次同一段前30帧 PNG 得到18个框、JPEG95得到17个框，不能据此判断哪一个正确，但足以说明两者输出不等价，因此默认保留无损路径。

## 在 Pi 本机运行界面

当前 Pi 已有 PyQt5 和 OpenCV，兼容层可直接使用系统 `python3`，不需要重建训练环境。将客户端 `src/`、`scripts/`、`configs/` 以及可选 `docs/results/` 放到一个独立源码目录，按上一节启动 H10 服务，在同一终端环境中运行 GUI（配置里的 URL 指向本机服务）：

```sh
PINP2_GUI_TOKEN="${PINP2_GUI_TOKEN}" python3 scripts/run_gui.py --config /path/to/local_gui_config.json
```

GUI 进程会从 `PINP2_GUI_TOKEN` 环境变量读取令牌，仍不写入配置。正常使用需要 Pi 的桌面显示会话；本次硬件联调用 `QT_QPA_PLATFORM=offscreen` 验证实际 Qt 窗口、绘制、推理、导出和生命周期，未把离屏吞吐率当作物理显示器刷新率。Pi 本机路径没有 Mac—Pi 中继网络逐帧上传开销。

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
| 保存／加载配置 | 保存界面设置，不保存令牌；加载配置不自动运行 |
| 实验结果对比 | 读取仓库真实 CSV，保留原列名，可按表头排序；与本次会话分开 |

每次创建新的带时间和随机后缀目录，绝不覆盖旧结果：

- `detections.jsonl`：含无目标帧的逐帧记录、检测框、客户端／服务耗时和 TP/FP/FN。
- `raw_detections.jsonl`：时间区域过滤之前的原始预测框，保留已有置信度阈值和 NMS 输出。
- `detections.csv`：逐检测框数据，适合表格分析；无目标帧见 JSONL。
- `detections.meta.json`：模型身份、已有策略、显示阈值和来源信息，可用于再次回放。
- `summary.json`：状态 `running/completed/stopped/failed/time_limit`，已保存帧数、检测框数、固定阈值的 TP/FP/FN、Precision/Recall/F1，以及耗时范围。异常仍保存已完成部分；未定义的指标为 `null`。进程被强制结束时保留 `running`，不会伪称完成。

逐图回放的 `Request / replay latency`只计查询已有预测；实时模式计客户端上传请求与响应解析，不计编码。服务耗时计预处理、H10、解码和NMS，不含传输、GUI显示和导出，且首帧无预热；它们都不是正式报告中的硬件基准 FPS。`Display FPS` 是检测视图最近最多30次不同帧的实际绘制完成速率（paintEvent，重复重绘不计数），包含网络、解码和绘制等影响，暂停恢复时重置；`Speed cap` 仅是上限，不代表可达到该帧率。保存的视频是等间隔演示视频，不保留原始音频或每帧网络等待时间。没有标注不计算 P/R/F1；这里不计算 AP/mAP，正式指标仍以原实验记录为准。

## 验证与范围

```sh
QT_QPA_PLATFORM=offscreen .venv-gui/bin/python -m unittest discover -s tests -p 'test_gui.py' -v
.venv-gui/bin/python scripts/check_repository.py
.venv-gui/bin/python scripts/check_references.py
```

2026-11-16 Mac 本地验证：31项测试通过，覆盖格式与路径校验、空预测、标注缺失、哈希不符、混合尺寸导出失败计数、取消／暂停／重启、窗口关闭，以及测试服务的鉴权、长连接、并发拒绝、图片和视频请求。测试服务使用明确命名的固定夹具，不是实际模型检测。

当前发布的500张真实预测还通过完整 GUI 回放，得到385个框、TP323／FP62／FN163／GT486，与2026-11-15部署验收一致；Mac不执行模型推理。本次已连接真实Pi/H10验证新HTTP服务：64张图片逐值一致，30帧PNG无损视频、300帧JPEG95视频及12秒暂停恢复通过，导出AVI逐帧可解码；Pi本机另完成30帧实际Qt窗口离屏测试。Pi GUI测试31项中30项通过、1项Mac专属约束测试跳过。详情与口径见 [H10联调记录](results/GUI_H10_20261116.md)。实际摄像头及长期现场运行尚未验收。

线程控制采用 Qt 的信号与协作停止方式，GUI只在主线程绘制：[Qt QThread 官方说明](https://doc.qt.io/qt-6/qthread.html)。

本机优化版已在真实Wayland桌面完成5分钟循环，平均绘制16.51FPS、最高60.6°C，无降频且每帧网络上传为0；详见 [本机显示稳定性](results/GUI_NATIVE_20261116.md)。后续原始录屏与配音版本分别保存，见结果导航。

## Timestamp filter / 时间区域过滤

`Timestamp filter` 是 GUI 的可选后处理规则。仅当输入文件 SHA256 命中私有 `timestamp_profiles` 配置，且画面尺寸一致时，才过滤已核验时间文字区域内的预测。未知素材、摄像头和图片文件夹不会套用这项规则。通用配置默认关闭；已准备的本机演示配置可针对核验素材开启。

配置记录 `size: [width, height]`、`region: [x1, y1, x2, y2]`（原图像素）和 `coverage`。预测框与文字区域交集占预测框面积至少50%时移除；区域很小，并且与具体素材绑定。更换视频或改变文件后需要重新核验，不能直接套用旧区域。真实目标若进入被排除区域，也可能被过滤；此功能不代表模型学会了区分文字。

原图、模型权重和标注不变。`raw_detections.jsonl` 保留过滤前预测，`detections.jsonl`、CSV及界面使用过滤后结果；每帧记录规则状态和移除数量，摘要记录 `raw_detections` 与 `timestamp_removed`。有标注时，匹配仍使用原始GT，不能因过滤而删除GT或漏检。

2026年11月16日：33项GUI测试通过；Pi/H10对同一张时间图片实测过滤前1框、过滤后0框；30帧演示素材18框→8框，移除10个时间文字误检。原始30帧预测与此前录像逐值一致，无文字的控制图片保留原框。模型精度的结论仍见原审计与定位诊断。
