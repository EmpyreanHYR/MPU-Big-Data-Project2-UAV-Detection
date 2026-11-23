# Pi desktop demonstration / 树莓派本机演示准备

在新机器上先完成[GUI复现指南](GUI_REPRODUCIBILITY.md)，再填写自己的配置并准备素材。下文的“已准备快捷方式”和“已缓存素材”对应原验收设备。

界面英文为主，中文辅助。演示采用 `H10 on this Pi / 本机加速`：视频先按 SHA256 缓存到树莓派，随后本机解码、H10推理、显示，逐帧网络上传量为0。首次传输时间与显示帧率分开计算。中继网络上传大文件较慢时，用Pi已有素材或在现场拷贝完整视频，再在界面选择；上传未完成的`.part`文件不计入有效缓存。同一素材再次启动只验证缓存哈希。

演示成片为[3分46秒英文配音版本](results/GUI_NARRATED_20261116.md)，含双语字幕、操作放大、图片检测、时间文字过滤和视频暂停恢复；可从[GitHub Release](https://github.com/EmpyreanHYR/MPU-Big-Data-Project2-UAV-Detection/releases/tag/gui-h10-v1.0.0)下载1080p原版、720p预览及字幕。[6分53秒完整录屏](results/GUI_RECORDING_20261116.md)记录首版流程。

两版视频均使用真实Pi/H10推理，视频素材是30张红外图片循环。[标注审计](results/TIMESTAMP_AUDIT_20261116.md)记录该30图在conf0.25、IoU0.5下TP为0，时间过滤使FP18→8、FN30不变；[定位诊断](results/LOCALIZATION_DIAGNOSIS_20261116.md)给出FP32/H10对照和标注尺度差异。讲述时把功能演示与检测精度分开。

未录屏5分钟真实窗口绘制为16.51 FPS；首版录屏活动显示约10.11 FPS，配音版约10.57 FPS。成片采样均为25 FPS，这些数值与22.89 FPS的固定图像硬件基准是不同口径。

## 日常启动

树莓派桌面已准备 `PinP2 H10 Demo / 本机演示` 快捷方式。也可在已配置连接的 Mac 双击 [启动树莓派本机演示.command](../启动树莓派本机演示.command)。窗口显示在**树莓派所连接的显示器**，默认已缓存短片段循环演示，在该窗口点击 `Start / 开始`。Mac上的旧入口用于需要在Mac选择图片或访问摄像头的远程客户端演示。

命令行可选其他视频：

```sh
.venv-gui/bin/python scripts/launch_pi_gui.py --video /path/to/demo.avi
```

每次创建独立版本目录，终端输出其位置。目录里的 `launch-on-pi.sh` 是下一次在Pi桌面本地启动的入口，使用同一份配置与缓存，无需Mac连接。GUI默认最多运行30分钟，外部进程守护最多31分钟，退出或超时释放两把既有硬件锁。

仅准备，不打开窗口：

```sh
.venv-gui/bin/python scripts/launch_pi_gui.py --prepare-only
```

## 录制前彩排

以下命令在真实桌面自动开始、循环素材、运行5分钟后停止并关闭，只记录数据，不录制视频也不导出逐帧图片：

```sh
.venv-gui/bin/python scripts/launch_pi_gui.py --rehearse-seconds 300
```

保存 `rehearsal.json`、逐帧预测、CSV、摘要和一张界面预览。记录Qt平台、已绘制帧数、帧间隔、RSS内存和温度。`Display FPS`统计检测视图实际 `paintEvent` 完成的不同帧；重绘同一帧不增加计数。它衡量应用绘制速率，显示器标称刷新率与扫描输出另行测量。彩排入口只在真实桌面平台运行。

## 再次录制流程

1. 准备最终视频，核对来源、使用范围、连续性、分辨率和时长。当前联调素材由真实图像排序构建，与连续摄像头录像的区别在视频说明中写明。
2. 启动Pi本机GUI，确认 `H10 local / 本机`、正确模型和素材，关闭历史回放；先运行一分钟预热与检查。
3. 展示原图/检测框、目标放大、显示FPS与H10耗时；依次演示开始、暂停、恢复、停止。展示约60–90秒即可，避免连续切换设置。
4. 屏幕录制选择Pi屏幕录制或HDMI采集，并测量录制开销。现有 `Record video` 导出标注画面，GUI窗口和音频由屏幕录制提供。
5. 先检查10秒样片：分辨率、文字大小、无隐私路径/令牌、帧率和音画同步，然后录制正式版本。录制开启后的性能单独测量。

录制脚本说明可用：“This is PinP2-YOLO running on Raspberry Pi with Hailo-10H. Frames stay on the Pi. The display rate and H10 processing time are measured separately.”（本机检测、分开报告显示与处理速度。）演示不包含实时准确率声明。
