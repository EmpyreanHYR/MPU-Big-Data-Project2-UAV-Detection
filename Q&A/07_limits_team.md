# 07 局限、展望与团队 / Limitations, Future Work, and Team

## Q01. 这个项目最大的局限是什么？

**中文**：我认为有三个，按重要性排序：第一，**没有独立测试集**，模型选择和 NMS 阈值都在同一个 500 张验证集上做，结果会偏乐观；第二，**单 seed**，没有置信区间或显著性检验，几个百分点的差异不能当成稳固结论；第三，**没有独立连续视频测试**，演示是 30 张外部静图循环，不能代表真实视频流。它们不是“以后再说”的客套，而是直接影响结论强度的限制。

**English**: Three, in order of importance. First, **no independent test set**: both model selection and the NMS threshold use the same 500-image validation set, so results are optimistic. Second, **a single seed**, with no confidence intervals or significance tests, so a few percentage points are not a robust conclusion. Third, **no independent continuous-video test**: the demo loops 30 external still images and does not represent a real video stream. These are not polite caveats; they directly limit how strong the conclusions can be.

## Q02. 为什么没有做独立连续视频测试？

**中文**：没有一份带逐帧标注、且与训练来源独立的连续红外视频。公开数据里，SIRST-UAVB 是图像集，AUVD 是另一个外部图像/分割源；把它们拼成“视频”会制造伪连续序列。我们选择诚实地说“没有”，而不是用 30 张静图循环冒充视频测试。要补这项，需要一段有授权、有逐帧框标注、且场景独立于训练集的视频。

**English**: We do not have a continuous infrared video with per-frame annotations from a source independent of training. In the public data, SIRST-UAVB is an image set and AUVD is a separate external image/segmentation source; stitching them into a “video” would create a fake continuous sequence. We chose to say “not available” rather than pass a 30-still loop off as a video test. Closing this gap needs an authorized continuous video with per-frame boxes and scenes independent of training.

## Q03. 密集目标、多目标场景为什么没测？

**中文**：验证集里只有 1 张图包含 2 个不重叠 UAV，绝大多数是单目标；NMS 也主要在候选框少于 1 个/图的条件下测。这个数据分布不支持“密集场景”的结论。我们把这个缺口写进报告，而不是用单目标结果外推。要测密集场景，需要额外收集/标注多目标视频或合成排列，并单独评估 NMS 的误抑制。

**English**: Only one validation image contains two non-overlapping UAVs; almost all are single-target, and NMS was tested mainly with fewer than one candidate per image. This distribution cannot support conclusions about dense scenes. We document the gap instead of extrapolating from single-target results. Testing dense scenes would require additional multi-target video or synthetic arrangements and a separate evaluation of NMS over-suppression.

## Q04. 如果还有时间，下一步做什么？

**中文**：优先级从高到低：第一，划出独立 test split，或做 3 个 seed 的重复实验，补置信区间；第二，录一段有逐帧标注的独立红外视频，做真正的连续评估；第三，测 P1、SAHI/切片和跟踪，看能否改善极小目标；第四，做 QAT/Adaround，比较量化感知训练能否把 0.835 的量化差再压小；第五，把鸟当 hard negative 或加辅助类；第六，测板端功耗和更长时热稳定性。

**English**: In priority order: first, hold out an independent test split or run three seeds with confidence intervals; second, record an independent infrared video with per-frame annotations for a true continuous evaluation; third, test P1, SAHI/tiling, and tracking for tiny targets; fourth, try QAT/Adaround to see whether quantization-aware training can reduce the 0.835-point gap; fifth, treat birds as hard negatives or add an auxiliary class; sixth, measure board power and longer thermal stability.

## Q05. 如果重新做一次，你会改什么？

**中文**：我会在模型选择之前就把 test split 锁死，所有阈值只在 validation 上选，最后只碰一次 test；把 B0–B3 的物理 batch 统一，或者至少做 batch 敏感性检查；先做 3 个 seed 再决定要不要加模块；数据侧先做完整的近重复审计，而不只是精确像素哈希。这样结论不一定更好看，但会更可信。

**English**: I would lock a test split before model selection, choose all thresholds on validation only, and touch test once; unify the physical batch for B0–B3, or at least run a batch-sensitivity check; run three seeds before deciding whether a module is worth adding; and on the data side, audit near-duplicates, not only exact pixel hashes. The results might look less impressive, but they would be more credible.

## Q06. 四位成员各自做了什么？

**中文**：按报告附录的公开分工：**Yaorong Huang** 负责模型、实验与边缘部署，包括 PConv/P2 结构、对照与消融训练、ONNX/H10/Pi 测试、NMS 审计、VLM 负结果和报告/复现材料；**Chunshen Yu** 负责 13 页汇报、图表、讲稿与问答备份，以及 README 链接的自动部署；**Yifan Zhai** 负责应用测试与错误分析，按背景复杂度、目标尺寸和阈值梳理失败案例，并校对报告；**Zhiwen Luo** 负责数据集构建与清洗、去重、冲突隔离、划分冻结和数据集文档。报告没有给百分比，我也不编造百分比。

**English**: According to the report appendix: **Yaorong Huang** led the model, experiments, and edge deployment, including the PConv/P2 structure, controlled and ablation training, ONNX/H10/Pi testing, the NMS audit, the VLM negative result, and the report/reproduction materials; **Chunshen Yu** led the 13-page presentation, figures, speaker notes, Q&A backup, and the README-linked automatic deployment; **Yifan Zhai** led application testing and error analysis by background complexity, target size, and threshold, and proofread the report; **Zhiwen Luo** led dataset construction and cleaning, deduplication, conflict isolation, split freezing, and dataset documentation. The report gives no percentages, and I will not invent them.

## Q07. 最大的困难是什么？怎么解决的？

**中文**：最大的技术困难是“训练器重建出来的网络不一定是设计的网络”：自定义 PConv/P2 在重建时可能被丢弃或退回原生层。临时补丁会让训练、导出、部署走三条不同的路径。最后的解决办法是用版本锁定的 `UAVYOLO` 适配器，在模型构建时重建 PConv，并在每次重建后核对模块类型、参数量和输出；导出后再做逐层/逐框保真检查。这个问题也解释了为什么我们不信任“只在 notebook 里跑通”的结果。

**English**: The hardest technical problem was that the network rebuilt by the trainer was not necessarily the designed network: custom PConv/P2 modules could be dropped or reverted during reconstruction. Ad-hoc patches would make training, export, and deployment follow three different paths. The fix was a version-pinned `UAVYOLO` adapter that rebuilds PConv at construction time and checks module type, parameter count, and outputs after every rebuild, followed by layer/box fidelity checks after export. This is also why we do not trust “it ran once in a notebook.”

## Q08. 你们用了 VLM/LLM 吗？结论是什么？

**中文**：做过一轮**离线** VLM 候选复核，用 Qwen2.5-VL-3B-Instruct 在 RTX 2080 Ti 上测，不是最终管线的一部分，也没有部署到 H10。E0 是原始检测 323 TP/119 FP/163 FN；E1 纯阈值 184/11/302；E2 全 context 只有 1 TP；E3 选择性 context 184/12/302；E4 局部 183/12/303。689 条回答没有一条说“不确定”；查 141 个原 TP，126 个被判成背景、14 个鸟、1 个 UAV。E3 每次查询 236.93 ms，边缘上不可接受。结论是负面的：这个 VLM 不适合做小目标候选复核。

**English**: We ran one **offline** VLM candidate check with Qwen2.5-VL-3B-Instruct on an RTX 2080 Ti. It is not part of the final pipeline and was not deployed to H10. E0 is the raw detector at 323 TP/119 FP/163 FN; E1 threshold-only is 184/11/302; E2 with full context finds only 1 TP; E3 selective context is 184/12/302; E4 local is 183/12/303. None of the 689 answers said “uncertain”; of 141 original TPs queried, 126 were called background, 14 bird, and 1 UAV. E3 takes 236.93 ms per query, unacceptable at the edge. The conclusion is negative: this VLM is not suitable for tiny-target candidate verification.

## Q09. 这个模型是 SOTA 吗？能直接产品化吗？

**中文**：不是 SOTA，也不是产品。它是一个课程项目里的**可复现基线 + 边缘原型**：单数据集、单 seed、无独立测试视频、无功耗测量、无长期稳定性测试。22.89 FPS 说明“在 H10 上能跑到这个吞吐”，不说明“在真实场景里不会漏检”。要产品化，至少还需要独立视频验证、多场景数据、失败告警、人工复核、功耗/热测试和法规/隐私评估。

**English**: It is neither SOTA nor a product. It is a **reproducible baseline plus edge prototype** in a course project: one dataset, one seed, no independent test video, no power measurement, and no long-term stability test. 22.89 FPS shows the throughput on H10, not that it will not miss targets in the field. Productization would require independent video validation, multi-scene data, failure alerts, human review, power/thermal testing, and legal/privacy assessment.

## Q10. 这门课/这个项目你最大的收获是什么？

**中文**：三件事。第一，**数据质量不是预处理的小事**：494 张重复和 7 张冲突会直接改变验证结果，去重和冻结划分比多加一个模块更重要。第二，**评价口径决定结论**：同一个模型，原生 31.274、共同 FP32 25.186、H10 无 NMS 24.351、H10+NMS 31.740，四个数字都真实，但不能混着讲。第三，**部署会暴露训练里看不到的问题**：量化、NMS、GUI 帧率、网络延迟，每一个都能把“论文里的 AP”变成“现场能不能用”的问题。

**English**: Three things. First, **data quality is not a preprocessing detail**: 494 duplicates and 7 conflicts directly change validation results, and deduplication plus a frozen split matter more than adding another module. Second, **the evaluation protocol determines the conclusion**: the same model yields native 31.274, common FP32 25.186, H10 without NMS 24.351, and H10 with NMS 31.740; all four are real, but they cannot be mixed. Third, **deployment exposes what training does not**: quantization, NMS, GUI frame rate, and network latency can each turn a “paper AP” into a “can it be used on site” question.
