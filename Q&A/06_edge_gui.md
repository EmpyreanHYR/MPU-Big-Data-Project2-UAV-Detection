# 06 边缘部署与 GUI / Edge Deployment and GUI

## Q01. 部署链路是什么？

**中文**：训练得到的 PyTorch 权重先导出为 ONNX，再用 Hailo 的编译器量化/编译成 HEF，部署到树莓派 5 的 Hailo-10H 上，由 HailoRT 运行；主机侧做图像读取、letterbox、UINT8 转换、同步调用、输出解码和 NMS。GUI 通过 SSH/Tailscale 把图像送到 Pi 上的服务，再把检测结果拉回来显示。Mac 不加载 Torch，也不做模型推理。

**English**: The trained PyTorch weights are exported to ONNX, quantized and compiled into a HEF with the Hailo toolchain, and run on the Hailo-10H attached to a Raspberry Pi 5 via HailoRT. The host handles image reading, letterboxing, UINT8 conversion, synchronous invocation, output decoding, and NMS. The GUI sends images to the Pi service over SSH/Tailscale and displays the returned detections. The Mac does not load Torch or run model inference.

## Q02. 为什么选树莓派 5 + Hailo-10H？为什么不用 Jetson 或纯 CPU？

**中文**：H10 是低功耗、小体积的 NPU，适合课程项目的边缘演示；Pi5 提供成熟的 Linux/USB/网络环境。实测 PinP2 在 H10 上 22.72 FPS，在 Pi CPU 上只有 4.13 FPS，H10 约快 5.5 倍；HEF 只有 4.02 MiB，H10 进程 RSS 86.3 MiB。我们没有测 Jetson，所以不能说“比 Jetson 更好”；选 H10 是因为手头有这块加速器，而且它的功耗/体积适合这个场景。

**English**: H10 is a low-power, small NPU suitable for an edge demo, and the Pi5 provides a mature Linux/USB/network environment. PinP2 runs at 22.72 FPS on H10 versus 4.13 FPS on the Pi CPU, about 5.5× faster; the HEF is only 4.02 MiB and the H10 process RSS is 86.3 MiB. We did not test Jetson, so we cannot say it is better than Jetson; H10 was chosen because it was available and its power/size fit the scenario.

## Q03. 量化怎么做的？精度损失多大？

**中文**：骨干用 INT8，检测输出用 a16_w16；校准只使用训练集图像（提供 1024 张，SDK 日志显示实际统计 64 张），没有用验证集/测试集，也没有做 QAT 或 Adaround。共同 FP32 路径的 AP50:95 是 25.186%，H10 无 NMS 是 24.351%，差 **0.835 个百分点**。这个 0.835 是纯量化差，不含“原生→共同路径”的 6.088 个百分点口径差。

**English**: The backbone uses INT8 and the detection output uses a16_w16. Calibration uses training images only (1024 were provided; the SDK log shows 64 were actually used for statistics), with no validation/test images and no QAT or Adaround. The common FP32 path gives 25.186% AP50:95; H10 without NMS gives 24.351%, a **0.835-point** gap. That 0.835 is the quantization-only gap and excludes the 6.088-point native-to-common-path difference.

**追问“为什么只统计 64 张”**: 我们提供的是 1024 张训练图，但 SDK 日志只记录 64 张的统计量；我们按日志如实报告，不声称“用了 1024 张”。 / We provided 1024 training images, but the SDK log records statistics for 64; we report the log faithfully and do not claim all 1024 were used.

## Q04. 22.89 FPS 到底测的是什么？

**中文**：500 张验证图、H10、解码后加 NMS 0.4 的端到端管线；三轮，均值 43.70 ms、22.89 FPS，NMS 本身 26.3 µs/图。它包含 JPEG 读取、PIL letterbox、UINT8 转换、同步 H10 调用、有限值检查、主机解码和 NMS；不包含初始化、预热、AP 计算、绘图、视频编码或网络传输。另一次 500 图验收是 22.56 FPS / 44.33 ms，不是矛盾，是不同运行。

**English**: It is the end-to-end pipeline on 500 validation images with H10 and NMS 0.4 after decoding: three runs, 43.70 ms mean, 22.89 FPS, with NMS itself at 26.3 µs/image. It includes JPEG read, PIL letterbox, UINT8 conversion, synchronous H10 invocation, finite-value checks, host decoding, and NMS; it excludes initialization, warm-up, AP computation, drawing, video encoding, and network transfer. A separate 500-image acceptance run gives 22.56 FPS / 44.33 ms; that is a different run, not a contradiction.

## Q05. 延迟主要花在哪里？为什么 NPU 调用 23.58 ms，管线却要 44 ms？

**中文**：H10 的 NPU 调用约 23.58 ms，但端到端还要加上图像读取/解码、letterbox、UINT8 转换、同步等待、输出拷贝、解码和 NMS。无 NMS 的管线均值 44.01 ms，p50 43.63 ms，p95 46.56 ms；NMS 只占 26.3 µs，所以瓶颈不在 NMS，而在主机侧预处理/数据搬运和同步调用。H10 不是“只算 23 ms 就能出图”，管线视角才是用户看到的延迟。

**English**: The H10 NPU call is about 23.58 ms, but end-to-end adds image read/decode, letterbox, UINT8 conversion, synchronous wait, output copy, decoding, and NMS. The pipeline without NMS has a 44.01 ms mean, 43.63 ms p50, and 46.56 ms p95; NMS takes only 26.3 µs, so the bottleneck is host-side preprocessing/data movement and the synchronous call, not NMS. H10 does not “produce a frame in 23 ms”; the pipeline is what the user experiences.

## Q06. 内存、温度和功耗怎么样？

**中文**：PinP2 的 HEF 是 4.02 MiB，H10 进程峰值 RSS 86.3 MiB；Pi CPU 路径峰值 RSS 250.4 MiB。温度在不同运行中约 48.5–53.45°C，没有记录到降频标志；Pi 本机 GUI 5 分钟循环最高 60.6°C，也没有降频。**功耗没有测**，所以不能报瓦数，也不能说“能效比某平台好”。温度低不等于功耗低，这是两件事。

**English**: PinP2's HEF is 4.02 MiB and the H10 process peak RSS is 86.3 MiB; the Pi CPU path peaks at 250.4 MiB. Temperatures across runs are about 48.5–53.45°C with no throttling flags recorded; the Pi-native GUI five-minute loop peaks at 60.6°C, also without throttling. **Power was not measured**, so we cannot report watts or claim better energy efficiency than another platform. Low temperature does not imply low power; they are different measurements.

## Q07. 为什么加 NMS？0.4 是怎么选的？

**中文**：YOLO26 的端到端头理论上 NMS-free，但 H10 输出里仍有同一目标附近的重复框。我们扫了 0.3–0.9 七档加无 NMS：0.3 的 AP 31.742、FP 62；0.4 的 AP 31.740、FP 62；0.5 的 AP 31.676、FP 63；无 NMS 是 24.351、FP 119。0.4 是“召回不变、FP 最低的阈值中较大的一档”，比 0.3 少一点误抑制风险，AP 只低 0.0026 个百分点；0.5 又多 1 个 FP。所以默认 0.4。

**English**: YOLO26's end-to-end head is nominally NMS-free, but H10 outputs still contain duplicate boxes around the same target. We swept seven thresholds from 0.3 to 0.9 plus no NMS: 0.3 gives AP 31.742 and 62 FPs; 0.4 gives 31.740 and 62; 0.5 gives 31.676 and 63; no NMS gives 24.351 and 119. 0.4 is the larger of the thresholds with unchanged recall and the lowest FP count, with slightly less suppression risk than 0.3 and only 0.0026 points lower AP; 0.5 adds one more FP. Hence 0.4 is the default.

## Q08. NMS 为什么能把 AP 从 24.351 拉到 31.740？会不会误删目标？

**中文**：NMS 去掉的是重复框，不是新增检测。固定阈值下 TP 仍是 323、FN 仍是 163，FP 从 119 降到 62；AP 的提升来自 precision–recall 排序变干净，不是找回了漏检。IoU 0.4 下有 17 个原 TP 框被抑制，但重匹配后每图 TP 数不变，说明它们有替代框；163 个漏检和 20 个鸟 FP 没有被“找回”。所以不能把 31.740 说成“模型精度提高了”，它只是部署后处理的收益。

**English**: NMS removes duplicate boxes; it does not create detections. At the fixed threshold, TP stays 323 and FN stays 163, while FP drops from 119 to 62; the AP gain comes from cleaner precision–recall ranking, not from recovering misses. At IoU 0.4, 17 original TP boxes are suppressed, but per-image TP counts are unchanged after rematching, meaning they had replacements; the 163 misses and 20 bird FPs are not recovered. So 31.740 is a post-processing gain, not a stronger model.

## Q09. GUI 是做什么的？它怎么连到 Pi？

**中文**：GUI 是 PyQt 写的桌面工作台，支持两种模式：回放已保存的预测结果，或通过 SSH/Tailscale 连接 Pi 上的 H10 服务做实时推理。界面显示检测框、置信度、原始/过滤后的计数，导出 JSON/CSV/标注图。Mac 端不导入 Torch、不读 `.pt`，只做传输、显示和 NumPy 层面的统计；模型加载和推理在 Pi/H10 上。GUI 还带一个可选的“时间文字过滤”，只对显式核验、hash 绑定的素材生效，且原始预测始终保留。

**English**: The GUI is a PyQt desktop workbench with two modes: replay saved predictions, or connect to the H10 service on the Pi over SSH/Tailscale for live inference. It shows boxes, confidence, raw/filtered counts, and exports JSON/CSV/annotated images. The Mac does not import Torch or read `.pt` files; it only transfers, displays, and computes NumPy-level statistics. Model loading and inference happen on the Pi/H10. The GUI also has an optional timestamp-text filter that only applies to explicitly verified, hash-bound media, and raw predictions are always preserved.

## Q10. 演示视频里 30 帧零检出，是不是说明模型失败了？

**中文**：不是模型在验证集上失效，而是演示素材和训练分布不匹配。那 30 帧是外部红外素材，FP32 路径同样是 0 TP、25 FP、30 FN，H10 是 0 TP、18 FP、30 FN；说明问题不在 H10 或 GUI 坐标。复核发现坐标/步长/单位都正确，但预测框偏矮，外部标注的尺度和形状与模型输出不匹配，置信度也低；把 conf 降到 0.001 也只找回 1–2 个 TP。视频里还有时间文字造成的误报，时间文字过滤把 FP 从 18 降到 8。这个演示用于展示工作流，不作为精度证据。

**English**: This is not a validation-set failure; the demo material does not match the training distribution. On those 30 external infrared frames, the FP32 path also gives 0 TP, 25 FP, 30 FN, and H10 gives 0 TP, 18 FP, 30 FN, so the problem is not H10 or GUI coordinates. The review found correct coordinates, stride, and units, but predicted boxes are too short, the external annotation scale/shape does not match the model output, and confidence is low; lowering conf to 0.001 recovers only 1–2 TPs. Timestamp text also causes false positives, and the timestamp filter reduces FP from 18 to 8. The demo demonstrates the workflow, not accuracy.

## Q11. 为什么 GUI 只有 10–16 FPS，而 H10 基准是 22.89 FPS？

**中文**：因为它们测的不是同一段。22.89 FPS 是“500 张图、无绘图、无网络”的 H10 管线；GUI 还要做 Qt 绘制、PNG 编码、SSH/Tailscale 传输、显示刷新，录屏还会增加开销。录屏窗口里的活动显示约 10.11 FPS；Pi 本机 5 分钟循环平均 16.51 FPS（4941 帧绘制），不走网络。Mac 经 Tailscale 请求 64 张图时平均 1459 ms/帧，网络是主要瓶颈；H10 本身处理约 46 ms。所以三个数字各有各的口径，不能互相替代。

**English**: They measure different segments. The 22.89 FPS is the H10 pipeline on 500 images with no drawing and no network; the GUI also does Qt drawing, PNG encoding, SSH/Tailscale transfer, and display refresh, and screen recording adds overhead. The active display in the recorded window is about 10.11 FPS; the Pi-native five-minute loop averages 16.51 FPS (4941 frames drawn) without network. A Mac request over Tailscale for 64 images averages 1459 ms/frame, with the network as the main bottleneck; H10 itself takes about 46 ms. The three numbers have different scopes and cannot replace one another.

## Q12. 模型和 GUI 怎么复现？公开了什么？

**中文**：代码、配置、测试和文档在 GitHub；最终模型在 `pinp2-final-model-v1.1.0` Release，GUI/HEF 在 `gui-h10-v1.0.0` Release，包含 HEF、元数据、校验和与演示视频。原始数据集、训练权重、私有预测和连接配置不公开。GUI 有 33 个测试、12 帧窗口/导出冒烟检查；模型侧有导出保真检查（133 个卷积权重逐位一致、8 张图框集合一致）。复现需要 Pi5 + H10 和对应的 HailoRT 环境；没有 H10 时可以用回放模式看已保存结果。

**English**: The code, configs, tests, and docs are on GitHub. The final model is in the `pinp2-final-model-v1.1.0` release, and the GUI/HEF is in the `gui-h10-v1.0.0` release with the HEF, metadata, checksums, and demo video. Raw datasets, training weights, private predictions, and connection profiles are not public. The GUI has 33 tests and a 12-frame window/export smoke check; the model side has export-fidelity checks (133 convolution weights bit-identical, identical box sets on 8 images). Reproduction needs a Pi5 + H10 and the matching HailoRT environment; without H10, replay mode can show saved results.

## Q13. 为什么不在 Mac 上直接跑模型？

**中文**：项目约定 Mac 只做数据传输、NumPy 统计和文档编辑，不导入 Torch、不反序列化 checkpoint、不做模型推理。这样避免“在 Mac 上跑出一个和云端/边缘不一致的结果”，也避免把大权重和运行时环境带到本地。模型加载、ONNX 导出和 H10 编译都在授权云上完成；Pi 只做 H10 推理。

**English**: The project rule is that the Mac only transfers data, computes NumPy statistics, and edits documents; it does not import Torch, deserialize checkpoints, or run model inference. This avoids “a Mac result that disagrees with cloud/edge” and keeps large weights and runtimes off the local machine. Model loading, ONNX export, and H10 compilation happen on the authorized cloud; the Pi only runs H10 inference.
