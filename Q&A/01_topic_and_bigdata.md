# 01 选题与大数据背景 / Topic and Big-Data Framing

## Q01. 用一句话介绍这个项目。

**中文**：我们在清洗后的 SIRST-UAVB 红外数据集上，把浅层 PConv 和 stride-4 P2 融合分支接入 YOLO26n，从零训练 100 轮，得到 31.274% 的原生 AP50:95，并把最终模型部署到树莓派 5 + Hailo-10H，以 22.89 FPS 运行。

**English**: On the cleaned SIRST-UAVB infrared dataset, we added a shallow PConv and a stride-4 P2 fusion branch to YOLO26n, trained from scratch for 100 epochs, reached 31.274% native AP50:95, and deployed the final model on a Raspberry Pi 5 with Hailo-10H at 22.89 FPS.

**如果只要一个数字 / If only one number**: 原生 AP50:95 = **31.274%**；部署默认路径 = **31.740%**（H10 + NMS 0.4）。两个数不能混着说。 / Native AP50:95 = **31.274%**; default deployment path = **31.740%** (H10 + NMS 0.4). Do not mix them.

## Q02. 为什么选“红外无人机检测”这个题目？

**中文**：无人机体积小、背景复杂，可见光在夜间和低照度下容易失效；红外成像不依赖可见光照明，适合夜间、雾天和边境/机场等场景的被动监测。我们把问题限定为单类 UAV 的边界框检测，目标是做一个能在边缘设备上跑起来的基线，而不是做完整的反无人机系统。

**English**: UAVs are small and often appear against cluttered backgrounds, while visible-light cameras degrade at night and in low illumination. Infrared imaging does not rely on visible illumination and is useful for passive monitoring at night, in haze, and around borders or airports. We limit the task to single-class UAV bounding-box detection and aim for a baseline that runs on an edge device, not a complete counter-UAV system.

**边界 / Boundary**: 红外也有低对比度、热交叉、雨雾衰减等问题；它不是“任何条件下都看得见”。 / Infrared also suffers from low contrast, thermal crossover, and rain/haze attenuation; it is not “visible under all conditions.”

## Q03. 这和“大数据”课程有什么关系？你们的数据有多大？

**中文**：我们不去声称有互联网级的数据量。这个项目对应的是大数据处理链路里的三个问题：**真实性（veracity）**——3000 张原始图里有 494 张像素重复、7 张标注冲突，必须先清洗；**体量（volume）**——在 2499 张清洗图上做 500/1000/1999 三档训练比例，以及 125/250/500 张的推理负载实验；**速度（velocity）**——在 H10 上测吞吐、延迟和内存，回答“能不能实时跑”。

**English**: We do not claim internet-scale data volume. The project maps to three concerns in a big-data pipeline: **veracity**—among 3000 raw images, 494 were pixel duplicates and 7 had annotation conflicts, so cleaning came first; **volume**—three training fractions (500/1000/1999 images) on the 2499 cleaned images, plus inference workloads of 125/250/500 images; and **velocity**—throughput, latency, and memory on H10, to answer whether it runs in real time.

**追问 / Follow-up**: “这不就是小数据集吗？”——是的，规模不大；我们把重点放在数据质量、可复现实验和边缘吞吐，而不是堆数据量。 / “Isn't this a small dataset?” Yes. We focus on data quality, reproducible experiments, and edge throughput rather than scale alone.

## Q04. 为什么做目标检测，不做分类或分割？

**中文**：应用需要知道“在哪里”，不只是“有没有”。分类只能回答图像里有没有无人机；分割需要像素级标注，而 SIRST-UAVB 主要提供边界框。检测在标注成本、推理速度和部署复杂度之间更平衡。AUVD-Seg300 有分割标注，但我们只把掩码转成框做外部评估，不改变主任务。

**English**: The application needs to know *where*, not only *whether*. Classification answers only whether a UAV is present; segmentation needs pixel-level labels, while SIRST-UAVB mainly provides bounding boxes. Detection balances labeling cost, inference speed, and deployment complexity. AUVD-Seg300 has segmentation labels, but we convert its masks to boxes only for external evaluation and keep the main task as detection.

## Q05. 你们的创新点是什么？和原 PConv / P2 论文有什么区别？

**中文**：我们没有发明 PConv 或 P2。我们的工作是把两者**组合进 YOLO26n 的一个具体位置**：第 1 个下采样卷积换成四方向 PConv，同时增加 stride-4 的 P2 检测支路，形成四尺度融合；然后在同一数据划分、同一 100 轮预算下做 B0–B3 消融，并把最终模型真正部署到 Pi5 + H10，测出精度、漏检、帧率、内存和量化损失。另一个贡献是**诚实的负结果**：VLM 候选复核没有带来收益，我们如实记录；NMS 阈值扫描则是有效的部署后处理，把 H10 路径的 AP 从 24.351% 提到 31.740%，但 TP/FN 不变，不能算模型精度提升。

**English**: We did not invent PConv or P2. We integrated both at a specific location in YOLO26n: the first downsampling convolution becomes a four-direction PConv, and a stride-4 P2 detection branch is added for four-scale fusion. We then run a B0–B3 ablation on the same split and the same 100-epoch budget, and deploy the final model on Pi5 + H10 to measure accuracy, misses, frame rate, memory, and quantization loss. A second contribution is **honest negative evidence**: the VLM candidate check did not produce a gain, and we report that. The NMS threshold sweep, by contrast, is an effective deployment post-process: it raises the H10-path AP from 24.351% to 31.740%, but TP/FN are unchanged, so it is not a model-accuracy gain.

**一句话 / One line**: 不是“新算子”，而是“受控集成 + 边缘实测 + 诚实的负结果”。 / Not a new operator, but controlled integration, edge measurement, and honest negative evidence.

## Q06. 为什么选 YOLO26n 作为基线？

**中文**：YOLO26n 只有 2.504M 参数，单阶段、部署链路简单，而且带端到端检测头，适合边缘场景。它的原生 AP50:95 是 27.952%，给我们留出了可测量的改进空间。我们没有说它全面优于 YOLO11n 或 YOLOv8n；实际上在 H10 上 YOLO11n 的 AP 更高，但更慢、参数更多，最后是综合取舍。

**English**: YOLO26n has only 2.504M parameters, is single-stage, has a simple deployment path, and includes an end-to-end detection head, which suits edge use. Its native AP50:95 is 27.952%, leaving measurable room for improvement. We do not claim it dominates YOLO11n or YOLOv8n; on H10, YOLO11n actually has higher AP but is slower and larger, so the final choice was a trade-off.

## Q07. 检测到无人机，是否等于判断“黑飞”？系统会做什么？

**中文**：不等同。我们只做“图像里有没有 UAV、在哪里”的感知，不判断空域授权、身份、意图或合法性，也不做自动拦截。真实系统还需要雷达/射频、飞行许可、人工复核和法律流程。我们把输出限定为检测框和置信度，避免把感知结果当成执法结论。

**English**: No. We only perceive whether a UAV is present and where; we do not decide airspace authorization, identity, intent, or legality, and we do not perform autonomous interception. A real system would also need radar/RF sensing, flight authorization, human review, and legal procedures. We limit the output to boxes and confidence scores and avoid treating perception as an enforcement decision.

## Q08. 为什么做到边缘部署，而不只停在 GPU 实验？

**中文**：课程项目如果只在 GPU 上报告 AP，无法回答“实际能不能用”。我们把最终权重导出为 ONNX，再编译成 H10 的 HEF，在 Pi5 上测端到端延迟、帧率、内存和漏检。结果是：H10 比 Pi CPU 快约 5.5 倍，但量化会让 AP 掉 0.835 个百分点（共同路径 25.186→24.351，无 NMS）；这些代价必须被测出来，而不是假设“量化没有影响”。

**English**: A GPU-only AP number cannot answer whether the system is usable. We export the final weights to ONNX, compile them into an H10 HEF, and measure end-to-end latency, frame rate, memory, and misses on a Pi5. H10 is about 5.5× faster than the Pi CPU, but quantization costs 0.835 AP points on the common path (25.186→24.351 without NMS). That cost has to be measured, not assumed away.
