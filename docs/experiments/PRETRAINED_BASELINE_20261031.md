# YOLO26n 预训练初始化对照

2026-10-31 用户明确新增一组采用预训练权重的基准实验。原有十组从零训练实验继续按原计划执行，新增组接在全部十组正常完成之后。

唯一计划变量是初始化：采用 Ultralytics 官方 assets v8.4.0 的 COCO 预训练 `yolo26n.pt`，通过 GitHub release asset 的 SHA256 和大小核验，保留来源与本地哈希。采用与从零基准相同的 `yolo26n-baseline.yaml` 和版本固定的 UAVYOLO 训练器，通过原生 `load` 加载所有形状兼容的权重，包括颈部和框回归分支；COCO 的 80 类分类输出按单类 UAV 重建。不是仅加载骨干网络，也不恢复旧实验的优化器、轮次或检查点。

固定数据：5800 train、1450 val、2048 外部 test；同一来源清单与 seed42，类别为 `uav`。训练 150 轮、640 输入、batch32、nbs32、FP32、AdamW、lr0=0.001、lrf=0.01、weight_decay=0.0005、workers8、patience0。其余增强及训练默认值与原始基准使用相同环境和入口。测试集不参与训练或最佳检查点选择。

配置：`configs/experiments/four_source150/baseline_coco_pretrained.json`；入口：`scripts/run_pretrained_baseline.py`。入口从原始基准配置派生运行参数，只覆盖 `pretrained=True`，另显式禁止 resume。运行日志、初始权重来源、完整训练参数、数据清单哈希及实际迁移成功的 tensor keys 单独保存。

独立等待器要求后三组适配实验的完成标记均为 150 轮，并在获取原串行锁之后启动自己的唯一训练子进程。前置队列失败或停止时停止接续；单个训练进程最多 86400 秒，无自动重试或 batch 回退。云端 CPU 的两图、128 输入、单轮检查仅验证加载、单类重建和原生训练流程，不作为正式精度或固定 batch 的 GPU 显存证据。

报告时将此组单独标为“COCO 预训练”，与 scratch 基准直接比较初始化收益；不得把预训练收益归因于 PConv/P2 结构改进，也不能与随机初始化比较模型混写训练条件。

实际状态：官方权重发布哈希和大小已核验；696 个兼容 tensor 经重建后与来源一致。云端 CPU 单轮训练、保存、最佳检查点验证已通过；独立接续进程已经启动，状态为 `waiting_previous_ten`，正式训练尚未开始。见[检查记录](../checks/pretrained_baseline_20261031.json)。
