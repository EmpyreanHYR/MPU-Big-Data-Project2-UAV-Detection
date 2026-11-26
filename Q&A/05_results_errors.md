# 05 结果与误差分析 / Results and Error Analysis

## Q01. 主结果是什么？

**中文**：在 B0–B3 的受控消融里，PinP2（B3）取得最高的原生 AP50:95：**31.274%**，AP50 为 **69.606%**。基线 B0 是 27.952%，PConv-only B1 是 24.381%，P2-only B2 是 29.975%。所以组合相对基线提升 **+3.322 个百分点**；但 PConv 单独是下降的，说明收益不是“两个模块各自都有效”的简单相加。

**English**: In the controlled B0–B3 ablation, PinP2 (B3) has the highest native AP50:95 at **31.274%**, with **69.606%** AP50. Baseline B0 is 27.952%, PConv-only B1 is 24.381%, and P2-only B2 is 29.975%. The combination improves over the baseline by **+3.322 percentage points**, but PConv alone decreases accuracy, so the gain is not a simple sum of two individually positive modules.

## Q02. 为什么 PConv 单独用反而下降 3.571 个百分点？

**中文**：我们的解释是：PConv 把标准 3×3 卷积拆成四个方向分支，虽然参数只多 288，但空间覆盖和通道混合方式变了；在浅层、小目标、低对比度的红外图上，这种方向性增强可能损失了一部分各向同性的上下文，导致定位和置信度都变差。这个解释是**假设**，没有做消融去分离“方向分支”“共享权重”“融合层”各自的影响；单 seed 也不能排除训练噪声。

**English**: Our interpretation is that PConv splits a standard 3×3 convolution into four directional branches. Although it adds only 288 parameters, its spatial coverage and channel mixing change; on shallow, tiny, low-contrast infrared targets, the directional enhancement may lose some isotropic context, hurting both localization and confidence. This is a **hypothesis**: we did not ablate the directional branches, weight sharing, and fusion layer separately, and a single seed cannot rule out training noise.

**不要这样说 / Do not say**: “PConv 不适合红外”或“PConv 一定有害”。我们只观察到“在这个位置、这个数据、这个预算下，单独使用下降”。 / Do not say “PConv is unsuitable for infrared” or “PConv is harmful.” We only observed a drop when used alone at this location, on this data, with this budget.

## Q03. 为什么组合起来又比 P2 高 1.299 个百分点？

**中文**：一个合理的解释是：P2 提供了更细的 160×160 检测网格，PConv 在浅层提供方向性特征，两者形成了互补；PConv 单独时缺少细网格，P2 单独时浅层特征没有被方向性增强。但 1.299 个百分点并不大，单 seed、486 个验证框，不能把它说成稳固的交互效应。我们把它写成“观察到的增量”，不写“协同增益已被证明”。

**English**: A plausible explanation is that P2 provides a finer 160×160 detection grid while PConv provides directional shallow features, so the two are complementary: PConv alone lacks the fine grid, and P2 alone lacks the directional shallow enhancement. But 1.299 points is not large, and with one seed and 486 validation boxes it is not a robust interaction effect. We call it an observed increment, not a proven synergy.

## Q04. 和 YOLO11n、YOLOv8n 比怎么样？

**中文**：原生 AP50:95：PinP2 31.274，YOLO11n 27.04，YOLOv8n 26.63。但到 H10 上，YOLO11n 的 AP 是 26.066，反而比 PinP2 的 24.351 高 1.714 个百分点；YOLOv8n 的漏检率 30.45%，比 PinP2 的 33.539% 低 3.086 个百分点。PinP2 的优势是速度：22.72 FPS，对 YOLO11n 的 18.54、YOLOv8n 的 18.85；参数 2.516M，也更小。结论是**没有全面最优**，是精度、漏检、速度、体积的取舍。

**English**: Native AP50:95 is 31.274 for PinP2, 27.04 for YOLO11n, and 26.63 for YOLOv8n. On H10, however, YOLO11n reaches 26.066 AP, 1.714 points above PinP2's 24.351, and YOLOv8n has a 30.45% miss rate, 3.086 points below PinP2's 33.539%. PinP2's advantage is speed: 22.72 FPS versus 18.54 for YOLO11n and 18.85 for YOLOv8n, with fewer parameters (2.516M). The conclusion is that **no model is best on every axis**; it is a trade-off among accuracy, misses, speed, and size.

## Q05. PConv+SD 原生 AP 最高（32.93%），为什么最终不选它？

**中文**：三个原因。第一，它不是同一架构的消融：它是 YOLOv8n-P2 + PConv + SD Loss，和 YOLO26n 的 B0–B3 不是同一基线。第二，H10 上它的 AP 掉到 18.125%，只有 7.17 FPS，FP 331，说明这个组合对量化/部署路径很敏感。第三，最终选型不仅看原生 AP，还要看漏检、速度、内存和可部署性。PinP2 的 H10 AP 24.351、22.72 FPS、119 FP，是更平衡的选择。

**English**: Three reasons. First, it is not an ablation on the same architecture: it is YOLOv8n-P2 + PConv + SD Loss, not the same YOLO26n baseline as B0–B3. Second, on H10 its AP falls to 18.125% at only 7.17 FPS with 331 FPs, showing high sensitivity to the quantization/deployment path. Third, final selection considers misses, speed, memory, and deployability, not native AP alone. PinP2's H10 result of 24.351 AP, 22.72 FPS, and 119 FPs is the more balanced choice.

## Q06. 训练数据量对结果影响多大？

**中文**：很大。500/1000/1999 张训练图（25%/50%/100%）的原生 AP50:95 分别是 16.353、24.543、31.274；共同 GPU 部署口径是 7.077、13.792、25.186；固定阈值漏检率是 57.613%、43.004%、32.510%。从 500 到 1000 提升约 8.19 个百分点，从 1000 到 1999 再提升约 6.73 个百分点。曲线还没有明显饱和，说明这个任务对数据量仍然敏感。

**English**: Large. With 500/1000/1999 training images (25%/50%/100%), native AP50:95 is 16.353, 24.543, and 31.274; the common GPU deployment path gives 7.077, 13.792, and 25.186; fixed-threshold miss rates are 57.613%, 43.004%, and 32.510%. The gain from 500 to 1000 is about 8.19 points, and from 1000 to 1999 about 6.73 points. The curve has not clearly saturated, so the task remains data-sensitive.

## Q07. 错误主要集中在哪里？小目标有多严重？

**中文**：非常集中。验证集 486 个 UAV 框里有 441 个的等效直径小于 8 px；163 个漏检里有 153 个来自这一组，占 93.87%，组内漏检率 34.69%。8–16 px 组是 40 个里漏 10 个（25%）；16 px 以上的 5 个全部检出。也就是说，模型的主要失败模式不是“完全看不见目标”，而是“极小目标定位/置信度不够”。

**English**: Highly concentrated. Of the 486 validation UAV boxes, 441 have an equivalent diameter below 8 px; 153 of the 163 misses come from this group, i.e., 93.87%, with a within-group miss rate of 34.69%. The 8–16 px group misses 10 of 40 (25%), and all 5 boxes at 16 px or above are detected. The main failure mode is therefore not “the target is completely invisible,” but “localization/confidence is insufficient for extremely small targets.”

## Q08. 背景纹理和鸟的误报各是什么情况？

**中文**：低纹理的 16 张图漏检率 56.25%（9/16），说明弱对比度下目标容易丢；中纹理组的 FP 最高，平均 0.441 个/图，说明杂波会带来误报；高纹理组漏检 31.56%。鸟的方面，119 个 FP 里有 20 个匹配鸟标注，占 FP 的 16.81%、鸟标注的 8.55%。有鸟的图 FP/图更高，但 UAV 漏检反而更低（20.93% 对 38.10%），所以鸟是一个可解释的来源，但不是最大来源，也不能说“鸟图更容易漏 UAV”。

**English**: The 16 low-texture images have a 56.25% miss rate (9/16), so weak contrast causes missed targets. The mid-texture group has the highest FP rate, 0.441 per image, so clutter produces false positives; the high-texture group has a 31.56% miss rate. For birds, 20 of 119 FPs match bird annotations, i.e., 16.81% of FPs and 8.55% of bird labels. Images with birds have more FPs per image but a lower UAV miss rate (20.93% vs 38.10%), so birds are an explainable source but not the largest one; it would be wrong to say bird images are more likely to miss UAVs.

## Q09. 外部 AUVD-Seg300 的结果为什么低这么多？

**中文**：外部 AP50 是 33.008%，AP50:95 是 11.494%，而内部原生 AP50 是 69.606%、AP50:95 是 31.274%。差距来自域差：AUVD 的成像条件、目标尺度、框的形状/长宽比和标注风格都与 SIRST-UAVB 不同；而且它的框是从分割掩码转出来的，和检测框的标注口径不完全一致。我们冻结权重、不微调、不选阈值，所以这个数字只是一个“跨源直接迁移”的参考值，既不是调优后的上限，也不能当成所有外部场景的下限。

**English**: External AP50 is 33.008% and AP50:95 is 11.494%, versus internal native AP50 of 69.606% and AP50:95 of 31.274%. The gap comes from domain shift: AUVD's imaging conditions, target scale, box shape/aspect ratio, and annotation style differ from SIRST-UAVB, and its boxes are derived from segmentation masks, so the box protocol is not identical. We freeze the weights, do not fine-tune, and do not tune thresholds, so this is a reference point for direct cross-source transfer: neither a tuned upper bound nor a universal lower bound for all external scenes.

## Q10. 31.274% 和 31.740% 到底哪个是“最终结果”？

**中文**：两个都是真实结果，但口径不同。**31.274%** 是原生验证器、最佳检查点的 AP50:95，用于模型间比较；**31.740%** 是 H10 部署路径、加 NMS 0.4 后的 AP50:95，用于部署验收。后者比前者高 0.466 个百分点，但不是“模型变强了”：权重冻结，NMS 只是去掉重复框，TP/FN 仍然是 323/163，没有找回新的目标。汇报时要说清“原生”还是“部署”。

**English**: Both are real, but under different protocols. **31.274%** is the native validator's AP50:95 on the best checkpoint, used for model comparison; **31.740%** is the H10 deployment path with NMS 0.4, used for deployment acceptance. The latter is 0.466 points higher, but the model did not become stronger: the weights are frozen, NMS only removes duplicate boxes, and TP/FN remain 323/163 with no new targets recovered. Always say “native” or “deployment.”

## Q11. 从原生 31.274% 到 H10 24.351%，中间发生了什么？

**中文**：中间有两段，不能混成“量化掉了 6.9 个点”。第一段是**评价路径差**：原生 31.274% → 共同 FP32 部署路径 25.186%，差 6.088 个百分点；冻结导出、统一预处理/解码、置信度下限和匹配脚本都可能贡献这部分差异，但我们没有逐项分解。第二段才是**量化差**：共同 FP32 25.186% → H10 无 NMS 24.351%，差 0.835 个百分点，来自骨干 INT8、输出 a16_w16。把两段分开，才能说清“量化损失只有 0.835”。

**English**: There are two stages, and they must not be merged into “quantization cost 6.9 points.” The first is an **evaluation-path difference**: native 31.274% → common FP32 deployment 25.186%, a 6.088-point gap to which frozen export, unified preprocessing/decoding, the confidence floor, and the matching script may all contribute; we did not decompose it item by item. The second is the **quantization difference**: common FP32 25.186% → H10 without NMS 24.351%, a 0.835-point gap from the INT8 backbone and a16_w16 output. Separating the two is the only way to say “quantization costs 0.835.”

## Q12. 这些差异有统计显著性吗？

**中文**：没有做正式的显著性检验，也没有置信区间。单 seed、500 张验证图、486 个框，几个百分点的差异可能是初始化或数据顺序造成的。我们的表述是“观察到 +3.322”“观察到 −3.571”，不是“显著优于”。硬件计时是另一回事：三轮均值和标准差很小（例如 22.89±0.01 FPS），那只能说明计时稳定，不能说明模型差异显著。

**English**: We did not run formal significance tests or confidence intervals. With one seed, 500 validation images, and 486 boxes, a few percentage points may come from initialization or data order. We say “observed +3.322” and “observed −3.571,” not “significantly better.” Hardware timing is different: the three-run mean and standard deviation are small (e.g., 22.89±0.01 FPS), which shows stable timing, not statistically significant model differences.

## Q13. PinP2 是“全面最好”的模型吗？

**中文**：不是。它在 B0–B3 里原生 AP 最高，也是我们最终选的边缘平衡点；但原生 AP 的最高值是 PConv+SD 的 32.93%，H10 AP 的最高值是 YOLO11n 的 26.066%，H10 漏检最低的是 PConv+SD 的 26.75%（但只有 7.17 FPS、331 FP），YOLOv8n 的漏检也比 PinP2 低。PinP2 的定位是“在 22.72 FPS、2.516M 参数下，精度/漏检/速度比较均衡”，不是“所有指标第一”。

**English**: No. It has the highest native AP within B0–B3 and is our final edge-balanced choice, but the highest native AP belongs to PConv+SD at 32.93%, the highest H10 AP belongs to YOLO11n at 26.066%, the lowest H10 miss rate belongs to PConv+SD at 26.75% (but at only 7.17 FPS with 331 FPs), and YOLOv8n also has a lower miss rate than PinP2. PinP2 is positioned as a balance of accuracy, misses, and speed at 22.72 FPS and 2.516M parameters, not as the best on every metric.

## Q14. 密集目标、多目标场景测了吗？

**中文**：没有充分测。验证集里只有 1 张图包含 2 个不重叠的 UAV，绝大多数图是单目标；所以“密集目标”不是当前数据的强项。NMS 也主要在候选框少于 1 个/图的条件下测的，密集场景下的抑制行为没有验证。这是报告的明确局限，不能说“已经支持密集场景”。

**English**: Not adequately. Only one validation image contains two non-overlapping UAVs; almost all images are single-target, so dense scenes are not a strength of the current data. NMS was also tested mainly with fewer than one candidate per image; its behavior in dense scenes is unverified. This is an explicit limitation, and we cannot say dense scenes are supported.
