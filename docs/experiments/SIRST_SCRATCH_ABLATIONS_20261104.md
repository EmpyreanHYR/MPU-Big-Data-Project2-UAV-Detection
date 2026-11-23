# YOLO26从零100轮：PConv／P2消融补充

2026年11月4日补充PConv、P2、PConv＋P2的随机初始化实验，每组100轮，与已有YOLO26n从零100轮控制组比较。

保持已验证的原有结构与冻结SIRST1999训练／500验证清单，seed42、640、FP32、AdamW、lr0=0.001、lrf=0.01、momentum=0.9、weight_decay=0.0005、warmup_bias_lr=0、nbs32、workers8。权重从随机初始化开始，训练100轮。PConv物理batch32，含P2的两组物理batch8；名义batch均为32，物理batch随结构配置。

| 模型 | 初始化 | 轮数 | batch／nbs | 结构 |
|---|---|---:|---|---|
| 原YOLO26n（已有控制） | 随机 | 100 | 32／32 | P3/P4/P5 |
| ＋PConv | 随机 | 100 | 32／32 | 层1风车形卷积 |
| ＋P2 | 随机 | 100 | 8／32 | 新增步长4检测尺度 |
| ＋PConv＋P2 | 随机 | 100 | 8／32 | 两项组合 |

配置：[PConv](../../configs/experiments/sirst_scratch100_ablations/pconv.json)、[P2](../../configs/experiments/sirst_scratch100_ablations/p2.json)、[组合](../../configs/experiments/sirst_scratch100_ablations/pconv_p2.json)。使用独立新目录、固定源码哈希和现有版本适配器。开训前逐组固定batch GPU前向／反向／优化器分配检查，训练器重建后检查PConv、检测尺度、随机初始化和100轮设置。每组独立限时；训练失败即停止该组并记录状态。

对照的已有基准mAP50=65.760%、mAP50–95=27.952%。各模型从同一个最佳内部验证AP95轮次的CSV行提取P/R/AP，计算F1及相对基准的百分点变化；外部集用于独立评价。原COCO预训练150轮结果独立保留。训练完成后检查100行有效CSV、完成标记和best/last哈希，回传结果，再更新中文结项报告。

启动情况：三组固定batch前向／反向／AdamW分配检查均通过，PConv先完成前2轮并继续训练，训练器重建检查通过。P2、组合版串行等待。预检为合成检查，不计入100轮或正式精度。
