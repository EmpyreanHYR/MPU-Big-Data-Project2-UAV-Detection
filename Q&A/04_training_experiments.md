# 04 训练与实验设计 / Training and Experiment Design

## Q01. 训练配置是什么？

**中文**：所有当前对比模型都用同一套主配置：输入 640、seed42、FP32、AdamW（lr0=0.001、lrf=0.01、weight_decay=0.0005、momentum=0.9）、名义 batch 32、nbs 32、100 轮。B0/B1 的物理 batch 是 32，B2/B3 因为 P2 的 160×160 特征图占显存，物理 batch 降到 8，但名义 batch 仍是 32。没有用 COCO 预训练权重。

**English**: All current comparison models use the same main recipe: 640 input, seed42, FP32, AdamW (lr0=0.001, lrf=0.01, weight_decay=0.0005, momentum=0.9), nominal batch 32, nbs 32, and 100 epochs. B0/B1 use a physical batch of 32; B2/B3 drop to 8 because the 160×160 P2 map consumes memory, while the nominal batch stays 32. No COCO-pretrained weights are used.

## Q02. 为什么从零训练 100 轮，而不是用 COCO 预训练或 150 轮？

**中文**：从零训练是为了把“架构差异”和“预训练域差异”分开。COCO 是可见光通用目标，和红外小目标差异很大；如果所有模型都从 COCO 初始化，比较会混入预训练带来的偏差。100 轮是当前 11 个模型的统一预算，不是“已经收敛”的证明。历史上有一组 COCO 预训练 150 轮的结果，但排序和当前 scratch100 不同（例如历史 combined 反而低于 baseline），所以两组必须分开报告，不能混用。

**English**: Training from scratch separates architecture effects from pretraining-domain effects. COCO is a visible-light general-object dataset and differs substantially from infrared tiny targets; initializing every model from COCO would mix pretraining bias into the comparison. The 100-epoch budget is shared by the current 11 models; it is not proof of convergence. We also have a historical COCO-pretrained 150-epoch group, but its ordering differs from the current scratch100 results (for example, the historical combined model is below the baseline), so the two groups must be reported separately and never mixed.

**追问 / Follow-up**: “为什么历史 150 轮的结论不一样？”——预训练权重、训练预算和数据协议都不同，不能拿来支持当前结论；它们只作为历史记录。 / The pretrained weights, budget, and data protocol all differ, so they cannot support the current conclusion; they are historical records only.

## Q03. 为什么只用一个 seed？有没有统计显著性？

**中文**：单 seed 是算力预算下的选择，也是报告明确写出的局限。我们没有跑多 seed，也没有做置信区间或显著性检验。500 张验证集、486 个 UAV 框，几个百分点的差异可能受初始化和数据顺序影响，所以我们只说“观察到的差异”，不说“显著提升”。硬件计时倒是做了三轮，报告的是均值和标准差。

**English**: A single seed is a compute-budget choice and an explicit limitation. We did not run multiple seeds, confidence intervals, or significance tests. With 500 validation images and 486 UAV boxes, a few percentage points can be affected by initialization and data order, so we report observed differences rather than “significant improvements.” Hardware timing, by contrast, was repeated three times and is reported with mean and standard deviation.

## Q04. B0/B1 用 batch 32，B2/B3 用 batch 8，这样公平吗？

**中文**：不完全是。名义 batch 都是 32，数据、epoch、seed、优化器都一样，但物理 batch 不同会影响 BN 统计和梯度噪声，所以这是一个混杂因素。我们选择降物理 batch 是为了在不爆显存的前提下把 P2 跑完；报告把它列为局限，没有声称“完全受控”。更严格的做法是全部用同一物理 batch，或做 batch 敏感性实验，当前没有做。

**English**: Not entirely. The nominal batch is 32 for all, and data, epochs, seed, and optimizer are the same, but physical batch size affects BN statistics and gradient noise, so it is a confounder. We reduced the physical batch to fit P2 without running out of memory; the report lists this as a limitation and does not claim a perfectly controlled comparison. A stricter design would use one physical batch for all models or run a batch-sensitivity study, which we did not do.

## Q05. 11 个模型是怎么保证可比的？

**中文**：它们共享同一份冻结数据清单、同一 1999/500 划分、同一评价脚本和同一套指标；训练预算统一为 100 轮、640、seed42、FP32。但“可比”不等于“同代码库”：YOLO11n、YOLOv8n、RT-DETR-L、PConv+SD、MSF-GhostNet-III 各自有适配器，结构差异是比较对象本身。我们保证的是数据和评价口径一致，不是网络结构一致。

**English**: They share the same frozen data manifest, the same 1999/500 split, the same evaluation script, and the same metrics; the training budget is uniformly 100 epochs, 640, seed42, FP32. “Comparable” does not mean “same codebase”: YOLO11n, YOLOv8n, RT-DETR-L, PConv+SD, and MSF-GhostNet-III each have their own adapter, and architectural differences are the object of comparison. We hold data and evaluation constant, not network structure.

## Q06. 消融实验怎么设计？

**中文**：四个模型：B0 是 YOLO26n 基线；B1 只换 PConv；B2 只加 P2；B3 同时加 PConv 和 P2，也就是 PinP2。四者同一数据、同一 100 轮预算、同一评价。这样可以直接读四个读数：B1−B0 是 PConv 单独效应，B2−B0 是 P2 单独效应，B3−B2 是在 P2 之上再加 PConv 的增量，B3−B1 是在 PConv 之上再加 P2 的增量。

**English**: Four models: B0 is the YOLO26n baseline; B1 adds only PConv; B2 adds only P2; B3 adds both, i.e., PinP2. All four use the same data, the same 100-epoch budget, and the same evaluation. This gives four direct readings: B1−B0 is the PConv-only effect, B2−B0 is the P2-only effect, B3−B2 is the increment from adding PConv on top of P2, and B3−B1 is the increment from adding P2 on top of PConv.

**结果 / Results**: B1−B0 = −3.571 pp；B2−B0 = +2.023 pp；B3−B2 = +1.299 pp；B3−B0 = +3.322 pp。 / B1−B0 = −3.571 pp; B2−B0 = +2.023 pp; B3−B2 = +1.299 pp; B3−B0 = +3.322 pp.

## Q07. 训练比例实验怎么设计？为什么固定 100 轮？

**中文**：用 500、1000、1999 张训练图，分别对应 25%、50%、100%；验证集固定为同一 500 张，不随训练比例变化。25% 和 50% 是新训的 100 轮模型，100% 复用已验证的全量 PinP2 权重。固定 100 轮是为了比较“同等训练预算下，数据量带来的收益”，不是让每个比例都训练到收敛。结果是原生 AP50:95 16.353 / 24.543 / 31.274，说明这个任务对数据量仍然敏感。

**English**: We use 500, 1000, and 1999 training images, i.e., 25%, 50%, and 100%, with the same fixed 500-image validation set. The 25% and 50% models are newly trained for 100 epochs; the 100% result reuses the verified full-data PinP2 weights. The fixed 100 epochs compare the gain from data at an equal training budget, not convergence at every fraction. Native AP50:95 is 16.353 / 24.543 / 31.274, showing that the task remains data-sensitive.

**注意 / Caution**: 25%/50% 的权重只在 GPU 上测过，没有 Pi/H10 结果；不要把它们写成“边缘可用”。 / The 25%/50% weights were measured on GPU only, not on Pi/H10; do not describe them as edge-ready.

## Q08. AP、P、R、F1、漏检率分别怎么定义？

**中文**：AP 用 0.001 的置信度下限和 101 点插值；AP50:95 是 IoU 0.50、0.55、…、0.95 十档 AP 的平均。固定阈值指标先把 conf<0.25 的框去掉，再按 IoU≥0.5 做一对一匹配；TP+FN 固定为 486 个 UAV 框。Precision=TP/(TP+FP)，Recall=TP/(TP+FN)，F1 是两者的调和平均，漏检率=FN/(TP+FN)。这样既有排序指标 AP，也有部署时能解释的计数。

**English**: AP uses a 0.001 confidence floor and 101-point interpolation; AP50:95 averages AP over ten IoU thresholds from 0.50 to 0.95 in steps of 0.05. Fixed-threshold metrics first drop boxes with conf<0.25, then perform one-to-one matching at IoU≥0.5; TP+FN is fixed at 486 UAV boxes. Precision=TP/(TP+FP), Recall=TP/(TP+FN), F1 is their harmonic mean, and miss rate=FN/(TP+FN). This gives both a ranking metric (AP) and deployable counts.

## Q09. 你们是不是在验证集上调参？有没有独立测试集？

**中文**：是，模型选择和 NMS 阈值都在同一个 500 张验证集上做；没有独立的内部测试集。这是报告明确写出的局限，会让结果偏乐观。我们用一个外部源 AUVD-Seg300 做冻结权重的跨源检查，但它不是内部测试集，也不能替代独立测试。更严格的做法是划出 test split，或做 nested cross-validation，当前没有做。

**English**: Yes, both model selection and the NMS threshold use the same 500-image validation set; there is no separate internal test set. This is an explicit limitation and can make the results optimistic. We use one external source, AUVD-Seg300, for a frozen-weight cross-source check, but it is not an internal test set and cannot replace one. A stricter design would hold out a test split or use nested cross-validation, which we did not do.

## Q10. 为什么输入是 640？为什么用 AdamW？

**中文**：640 是 YOLO 系列的常用输入，也是 H10 编译时使用的固定尺寸；再大对小目标可能有利，但延迟和显存都会上升，我们没有做 512/800 的消融。AdamW 是当前 YOLO 训练的常用优化器，学习率和权重衰减沿用固定配置，没有针对每个模型单独调参。这样比较的是结构，不是调参运气。

**English**: 640 is a common YOLO input size and the fixed size used for H10 compilation. A larger input might help tiny targets but would increase latency and memory; we did not ablate 512 or 800. AdamW is a common optimizer for current YOLO training, and the learning rate and weight decay follow a fixed recipe rather than per-model tuning. The comparison is about architecture, not tuning luck.

## Q11. 一共做了多少实验？为什么有些模型没有 H10 结果？

**中文**：累计 19 个有效权重：当前 11 个 scratch100 主比较、2 个训练比例模型、6 个历史 150 轮模型。GPU 测了 19 组，Pi CPU 17 组，H10 兼容 7 组。没有 H10 的原因分两类：SIA、SIA+CSP、MSF-GhostNet-III 的本权重原始头导出或数值/解码验证没有通过，标为 E1；RT-DETR-L 没有 H10 适配，标为 E2。E1/E2 是“没有测”，不是“0 分”。

**English**: There are 19 valid weights in total: 11 current scratch100 models, 2 training-fraction models, and 6 historical 150-epoch models. GPU has 19 runs, Pi CPU 17, and H10-compatible 7. Missing H10 results fall into two groups: SIA, SIA+CSP, and MSF-GhostNet-III did not pass raw-head export or numerical/decoding validation for their own weights (E1); RT-DETR-L has no H10 adapter (E2). E1/E2 mean “not measured,” not “zero.”

## Q12. 为什么没有做多 seed 或交叉验证？

**中文**：算力和时间不够。11 个模型 × 100 轮已经占满当前预算；再加多 seed 或 5-fold 会让实验量翻几倍。我们选择先把数据清洗、受控消融和边缘测量做完整，再把“单 seed”作为公开局限，而不是用多 seed 的数字来包装置信度。后续如果有算力，优先补 3 个 seed 和独立测试集。

**English**: Compute and time were insufficient. Eleven models × 100 epochs already consumed the available budget; multiple seeds or 5-fold cross-validation would multiply the work. We prioritized complete data cleaning, a controlled ablation, and edge measurements, and disclose the single-seed limitation instead of wrapping the numbers in false confidence. With more compute, the first additions would be three seeds and an independent test set.
