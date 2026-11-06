# YOLO26从零100轮：PConv／P2消融补充

2026年11月4日，用户要求补充PConv、P2、PConv＋P2的随机初始化实验，每组100轮，与已有YOLO26n从零100轮控制组比较。

保持已验证的原有结构与冻结SIRST1999训练／500验证清单，seed42、640、FP32、AdamW、lr0=0.001、lrf=0.01、momentum=0.9、weight_decay=0.0005、warmup_bias_lr=0、nbs32、workers8。不加载COCO、主干或其他实验权重，不恢复轮次。PConv物理batch32，含P2的两组物理batch8；名义batch均为32，物理batch差异保留，不声称控制了所有训练因素。

| 模型 | 初始化 | 轮数 | batch／nbs | 结构 |
|---|---|---:|---|---|
| 原YOLO26n（已有控制） | 随机 | 100 | 32／32 | P3/P4/P5 |
| ＋PConv | 随机 | 100 | 32／32 | 层1风车形卷积 |
| ＋P2 | 随机 | 100 | 8／32 | 新增步长4检测尺度 |
| ＋PConv＋P2 | 随机 | 100 | 8／32 | 两项组合 |

配置：[PConv](../../configs/experiments/sirst_scratch100_ablations/pconv.json)、[P2](../../configs/experiments/sirst_scratch100_ablations/p2.json)、[组合](../../configs/experiments/sirst_scratch100_ablations/pconv_p2.json)。使用独立新目录、固定源码哈希和现有版本适配器。开训前逐组固定batch GPU前向／反向／优化器分配检查，实际训练器重建后再次核验PConv、检测尺度、随机初始化和100轮设置。每组独立限时，失败即停止，无自动重试、降batch或检查点恢复。

对照的已有基准mAP50=65.760%、mAP50–95=27.952%。各模型从同一个最佳内部验证AP95轮次的CSV行提取P/R/AP，计算F1及相对基准的百分点变化；外部集不参与选点。原COCO预训练150轮结果独立保留。训练完成后核验100行有效CSV、完成标记和best/last哈希，回传结果，再更新中文结项报告；未完成时不填写新精度。

启动核验：三组固定batch前向／反向／AdamW分配检查均通过，PConv已正式完成前2轮并继续训练，训练器重建核验通过。P2、组合版串行等待。预检为合成检查，不计入100轮或正式精度；实时进度以运行回执为准。
