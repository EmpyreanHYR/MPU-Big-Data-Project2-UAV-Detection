# 02 数据与质量控制 / Data and Quality Control

## Q01. 数据来自哪里？为什么选 SIRST-UAVB？

**中文**：训练和内部验证使用 SIRST-UAVB 红外无人机数据集，原始 3000 张；外部评估使用 AUVD-Seg300。选 SIRST-UAVB 的原因是它专注 UAV 单类、提供边界框，规模和场景多样性适合课程项目；同时它带有明显的重复和标注冲突，正好能展示数据清洗对结果的影响。

**English**: Training and internal validation use SIRST-UAVB, an infrared UAV dataset with 3000 raw images; external evaluation uses AUVD-Seg300. We chose SIRST-UAVB because it focuses on a single UAV class, provides bounding boxes, and has enough scale and scene diversity for a course project. It also contains clear duplicates and annotation conflicts, which makes it a good case for showing why cleaning matters.

**来源说明 / Provenance**: 原始数据包保留在项目外部的数据目录；仓库只记录来源、清洗规则和清单，不重新分发原始图像。 / The original package stays in the external data directory; the repository records provenance, cleaning rules, and manifests without redistributing raw images.

## Q02. 3000 张是怎么变成 2499 张的？

**中文**：先对解码后的图像做像素级哈希，去掉 494 张完全重复图；再隔离 7 张标注冲突图；剩下 2499 张。之后按 seed42 和推断背景视图分组，划出 1999 张训练、500 张验证。清洗不是“删到好看”，而是先保证验证集里没有训练图的副本。

**English**: We hash decoded pixels to remove 494 exact duplicate images, isolate 7 images with annotation conflicts, and keep 2499. We then split by seed42 and inferred background view into 1999 training and 500 validation images. Cleaning is not cosmetic: the point is to keep copies of training images out of validation.

## Q03. 为什么要按像素哈希去重，而不是按文件名？

**中文**：文件名不能可靠地表示内容，同一场景可能被重命名、重新编码或复制成多个文件。我们比较解码后的像素内容，能抓到“文件名不同但图像相同”的重复。这里做的是精确重复检测，不是感知哈希，所以不会把“看起来相似”的图误删。

**English**: Filenames are not reliable content identifiers; the same scene can be renamed, re-encoded, or copied under several names. We compare decoded pixel content, which catches duplicates that have different filenames but identical pixels. This is exact-duplicate detection, not perceptual hashing, so visually similar but distinct images are not removed.

**边界 / Boundary**: 精确去重不能消除“同一背景、不同帧”的近重复；我们再用背景视图分组降低这种泄漏。 / Exact deduplication does not remove near-duplicates from the same background across frames; the background-view grouping is the second layer of defense.

## Q04. 7 张“标注冲突”具体是什么？为什么隔离而不是修正？

**中文**：这 7 张图存在不一致的标注，无法在不引入主观判断的情况下确定哪一份是对的。课程项目没有独立的第二标注员和仲裁流程，贸然选一个版本会把噪声带进训练和验证。把它们隔离，代价是少 7 张图，收益是标签口径干净、可复现。

**English**: These 7 images have inconsistent annotations, and there is no non-arbitrary way to decide which version is correct. The project has no independent second annotator or arbitration process, so choosing one version would inject noise into training and validation. Isolating them costs 7 images but keeps the label protocol clean and reproducible.

## Q05. 训练/验证怎么划分？怎么防止数据泄漏？

**中文**：固定 seed42，按“推断背景视图”分组，同一背景的前后帧只进一个 split；所有清洗在划分前完成，划分清单冻结，后续实验不再重划。这样做的目的是让验证集衡量“新场景”，而不是“同一场景的下一帧”。

**English**: We fix seed42 and group by inferred background view so frames from the same background go to only one split. Cleaning happens before splitting, the split manifest is frozen, and later experiments do not re-split. The goal is for validation to measure new scenes rather than the next frame of the same scene.

**边界 / Boundary**: 数据集没有官方 session/video ID，“背景视图”是推断出来的，不是元数据；因此仍可能有残余近重复。报告把这一点列为局限，没有声称完全无泄漏。 / The dataset has no official session or video IDs; the background view is inferred, not metadata. Residual near-duplicates are possible. The report lists this as a limitation and does not claim zero leakage.

## Q06. 为什么是 1999/500？500 张验证集够吗？

**中文**：2499 张按约 80/20 划分，得到 1999/500，没有为了凑整再动数据。验证集包含 486 个 UAV 框和 15 张负样本，能做模型间粗比较和固定阈值计数，但不足以支撑很窄的置信区间。我们的结论按“观察到的差异”表述，不宣称统计显著。

**English**: The 2499 images split roughly 80/20 into 1999/500 without adjusting the data to a round number. Validation contains 486 UAV boxes and 15 negatives, enough for coarse model comparison and fixed-threshold counts, but not for narrow confidence intervals. We report observed differences and do not claim statistical significance.

## Q07. 鸟的标注为什么保留？会不会干扰训练？

**中文**：主任务是 UAV 单类，鸟不是正类，所以鸟框不参与正样本监督。保留鸟框是为了做误差分析：119 个 FP 里有 20 个与 234 个鸟标注匹配，占 FP 的 16.81%、鸟标注的 8.55%。这说明鸟是一个可解释的误报来源，但不是最大来源；我们没有把它加进训练，也没有声称“鸟类分支”已经完成。

**English**: The main task is single-class UAV, so bird boxes are not positive supervision. We keep them for error analysis: 20 of 119 FPs match the 234 bird annotations, i.e., 16.81% of FPs and 8.55% of bird labels. Birds are an explainable false-positive source, but not the largest one. We did not add a bird class to training and do not claim a completed bird branch.

**如果追问“为什么不加鸟类”**: 那会改变任务定义和评价口径；更合理的做法是把鸟当 hard negative 或加一个辅助类，但这需要重新训练和重新评估，当前没有做。 / That would change the task and metric definition. A cleaner follow-up is to treat birds as hard negatives or add an auxiliary class, but that needs retraining and re-evaluation, which we did not do.

## Q08. AUVD-Seg300 怎么用？为什么不做微调？

**中文**：AUVD-Seg300 有 300 张图，原始是分割掩码；我们只把掩码转成边界框，用冻结的最终权重做外部评估，不微调、不选阈值。结果是 AP50 33.008%、AP50:95 11.494%；其中 AP50:95 明显低于内部的 31.274%（AP50 不能直接和 AP50:95 比）。这个差距主要反映域差：红外成像条件、目标尺度、框的形状和标注风格都不同。

**English**: AUVD-Seg300 has 300 images with segmentation masks. We convert the masks to boxes and evaluate the frozen final weights externally, without fine-tuning or threshold tuning. It reaches 33.008% AP50 and 11.494% AP50:95; the AP50:95 is well below the internal 31.274% (AP50 is not directly comparable to AP50:95). The gap mainly reflects domain shift: infrared conditions, target scale, box shape, and annotation style all differ.

**为什么不能拿它当“独立测试集”**: 它只有一个外部源，而且是从分割转框；它能说明跨源泛化有限，但不能代表所有真实场景。 / It is a single external source and boxes are derived from masks. It shows limited cross-source generalization but cannot represent all real scenes.

## Q09. 负样本和类别不平衡怎么处理？

**中文**：训练集有 20 张无 UAV 的负样本，验证集 15 张；数量不大，但能让模型见到“纯背景”。主任务是单类，所以不存在多类不平衡；真正的失衡在**尺度**：验证集 486 个 UAV 框里 441 个的等效直径小于 8 px。我们没有用重采样或类别权重，因为问题不是类频率，而是小目标定位。

**English**: Training has 20 UAV-free negatives and validation has 15; the number is small, but it exposes the model to pure background. The task is single-class, so there is no multi-class imbalance. The real imbalance is **scale**: 441 of the 486 validation UAV boxes have an equivalent diameter below 8 px. We did not use resampling or class weights because the issue is tiny-object localization, not class frequency.

## Q10. 标注质量怎么保证？有没有做一致性检查？

**中文**：我们做了三类检查：像素重复、标注冲突隔离、固定划分；没有做多标注员一致性统计，也没有重新标注全部图像。这是项目的实际边界。外部 30 帧零检出也提醒我们：标注的尺度/形状和模型输出可能不匹配，不能把“没检出”全归因于模型。

**English**: We performed three checks: pixel duplicates, annotation-conflict isolation, and a frozen split. We did not compute inter-annotator agreement or re-annotate every image; that is the actual boundary of the project. The zero detections on 30 external frames also remind us that annotation scale and shape may not match model outputs, so “no detection” cannot be blamed on the model alone.

## Q11. 数据隐私和伦理怎么处理？

**中文**：使用的是公开研究数据集，不包含个人身份信息；仓库不重新分发原始图像，只保留来源、清洗规则和清单。红外成像仍然可能涉及敏感区域，所以项目定位为检测研究，不做身份识别、不做自动拦截，也不把数据用于未授权监控。

**English**: We use public research datasets that contain no personal identity information. The repository does not redistribute raw images; it keeps provenance, cleaning rules, and manifests. Infrared imagery can still be sensitive, so the project is positioned as detection research: no identity recognition, no autonomous interception, and no use for unauthorized surveillance.
