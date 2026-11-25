# COMP6132 presentation script

HTML page 1 is the cover, pages 2–11 are the ten content slides, page 12 is the demonstration, and page 13 is the closing page. Timings are rehearsal targets that include brief pauses for figures.

## 01 · Background and Dataset · 50 s

**English**

Good morning. We are presenting PinP2-YOLO, our project on small UAV detection in infrared images. Managing unauthorized flights at night or in low visibility is one motivation for this work. Our detector estimates where a UAV is in an image. Whether a flight is authorized requires other information. Look at the two real infrared examples. The annotated objects are only a few pixels across, and birds or bright background details can look similar. We used the cleaned SIRST-UAVB dataset, with 1,999 training images and 500 validation images containing 486 UAV boxes.

**中文提示**：先指图里放大的小目标，再说明应用背景和目标检测的边界。

## 02 · Data Preparation and Quality Control · 50 s

**English**

We started with 3,000 source images. The preparation code reads image and label pairs, checks class mappings, and validates the box coordinates. It hashes decoded pixels so identical images can be found even if file names differ. We removed 494 duplicates and isolated seven annotation conflicts. We then grouped images by inferred background view before fixing the train and validation split with seed 42. Finally, we exported normalized YOLO labels, with UAV as the positive class. For this task, even a small annotation error can change whether a predicted box counts as a hit. A repeated image on both sides of the split would also inflate validation accuracy.

**中文提示**：讲清先去重再分组划分。背景分组来自推断。

## 03 · From YOLO26n to PinP2-YOLO · 65 s

**English**

Our starting point was YOLO26n, a compact baseline for comparing both accuracy and deployment cost. On the diagram, look first at the shallow stage on the left. We replaced one convolution with pinwheel convolution, or PConv. Its asymmetric padding lets different branches sample in different directions. Our motivation was to capture weak local structure around small objects. The next change is the P2 branch. Its prediction grid uses stride four, so it keeps finer spatial detail than the coarser prediction levels. That matters when a UAV covers only a few pixels and could fade as the feature map gets smaller. The combined model has about 2.516 million parameters. The experiments on the next two slides tell us how much each design choice helped.

**中文提示**：先指浅层 PConv，再指 P2 支路。把设计动机和实际效果分开。

## 04 · Comparison with Baseline Models · 65 s

**English**

This table shows selected models from the report, all trained from scratch for 100 epochs on the full training split. They share the same validation images and use native best-checkpoint metrics. The training settings for different model families can still differ. AP fifty measures ranking and detection at an overlap threshold of one half. AP fifty to ninety-five averages across stricter overlap levels and is our main accuracy metric. In the last row, PinP2 reaches 31.27 percent AP fifty to ninety-five. The YOLO26n baseline reaches 27.95 percent, and the parameter count changes only slightly. The strongest native AP in this table belongs to PConv plus SD. We selected PinP2 by also considering conversion, device accuracy and measured throughput.

**中文提示**：这是原生验证表。指出 PConv+SD 更高，最终选型还看部署。若想展示实际红外检测框，按左上角 Fig. 3 切换原图，再切回表 I。

## 05 · Ablation Study: PConv and P2 · 60 s

**English**

Read the bars from left to right. The first is YOLO26n at 27.952 percent. Adding PConv alone lowers native AP by 3.571 percentage points. Adding P2 alone raises it by 2.023 points. With both changes, we reach 31.274 percent, a gain of 3.322 points over the baseline. That is the strongest result among these four runs. It is useful evidence for our selected configuration, and it gives us a reason to keep testing the P2 branch. There are two limits to this comparison. We used one seed, and the models with P2 needed a smaller physical batch because of memory constraints. Matching batch sizes and repeating the runs would give a stronger test.

**中文提示**：突出 PConv 单独下降、P2 单独上升、组合最佳。说明单种子与 batch 差异。

## 06 · Edge Deployment: Raspberry Pi 5 + HAILO10H · 65 s

**English**

We exported the model to ONNX and compiled it to a Hailo HEF file of about 4.02 mebibytes. The Raspberry Pi reads and preprocesses images, sends them to Hailo, and decodes the output boxes. The deployed host code then restores image coordinates and applies NMS. On the final H10 evaluation path, we measured 31.740 percent AP fifty to ninety-five. The three-run threshold benchmark averaged 22.89 images per second. These numbers refer to the device pipeline, so neither native AP nor the GUI display rate is directly comparable. We also measured historical workloads of 125, 250 and 500 images. Mean processing time rose from 5.570 to 22.261 seconds while throughput stayed close to 22.5 images per second. The timing loop includes preprocessing and NMS, so it describes the deployed pipeline rather than raw model inference.

**中文提示**：区分原生 AP、设备 AP、三轮测速与 GUI 帧率。左表是另一组历史工作量实验。

## 07 · Effect of Training Data Scale · 55 s

**English**

For the training-size experiment, we trained PinP2 on nested subsets of 500, 1,000, and 1,999 images. Each run used 100 epochs, physical batch eight, and seed 42. The smallest subset reached 16.353 percent native AP. The middle subset reached 24.543 percent, and the full set reached 31.274 percent on the same 500 validation images. The graph shows a clear increase across these three runs. More examples may offer more background and target variation, but the larger subsets also receive more optimizer steps at fixed epochs. One split and one seed limit what we can conclude. A repeat with matched steps and more seeds would help separate those effects.

**中文提示**：这是训练规模实验，和后面的推理负载实验分开。固定轮次不等于固定更新步数。

## 08 · Post-processing Optimization: NMS IoU = 0.4 · 60 s

**English**

Intersection over union, or IoU, measures overlap between two boxes. NMS keeps the higher scoring box and suppresses a lower scoring one if the overlap is above the threshold. In report Figure Four, the two example boxes overlap by about 0.468, so a threshold of 0.4 suppresses the duplicate while 0.5 retains it. In the validation sweep, turning on NMS at 0.4 reduced false positives from 119 to 62. True positives stayed at 323 and false negatives stayed at 163. A threshold of 0.3 also gave 62 false positives, and 0.4 was the largest tested value that achieved this count at unchanged recall. We selected the threshold on internal validation, so crowded independent video is a useful next test.

**中文提示**：先指图 4 的 (d) 和 (e)，说明同一张图上 0.4 去掉重复框、0.5 保留。再点 Threshold sweep，指出全验证集 FP 从 119 降到 62、FN 不变。

## 09 · Offline VLM-assisted Candidate Verification · 60 s

**English**

We wanted to see whether semantic cues could help distinguish UAVs from birds or background. We took saved H10 candidates and sent selected crops to Qwen two point five VL on a separate GPU. We compared it against raising the detector confidence threshold. The unfiltered candidates gave 66.46 percent recall. Selective VLM review dropped recall to 37.86 percent, with 184 true positives and 12 false positives. Confidence filtering kept the same 184 true positives with only 11 false positives. So this VLM policy offered no advantage in our comparison. A crop with only a few useful pixels may not carry enough information for reliable verification. That is a possible explanation. We kept this experiment offline and left it out of the deployed H10 pipeline.

**中文提示**：同召回基线只有 11 个 FP，VLM 为 12 个。可能原因和实测结论要分开。

## 10 · Conclusion and Future Work · 70 s

**English**

Our work starts with a compact baseline and adds directional sampling and a finer prediction branch. The final model reached 31.274 percent AP fifty to ninety-five in native validation. It also performed better on this split as the training subset grew. On the separate H10 path, the chosen NMS threshold reduced duplicate detections, and the image pipeline ran at about 22.89 frames per second in the benchmark. The offline vision-language experiment gave us a useful negative result, since confidence filtering performed better at matched recall. The smallest targets still account for 153 of the 163 misses, and performance dropped on the external AUVD case. We would improve the annotations and tiny-target localization, repeat the runs with multiple seeds, and validate the system on new sensors and independent continuous infrared video. Thank you. We are happy to take questions.

**中文提示**：依次收束模型、数据规模、部署、NMS、VLM 局限。在此结束 10 分钟正文。

**Optional demo handoff**: Next, we will demonstrate our detection workbench.

## Optional demo

**If time allows**: Advance from the conclusion to the GUI Demonstration slide, then click Play full video. It opens fullscreen and returns to the demonstration slide when it ends.

**If time is tight**: Use the preview shown on the demonstration slide. Point out the input on the left, detection view on the right and the results table below. Advance to the closing page.
