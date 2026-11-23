# YOLO26n 预训练初始化对照

2026-10-31 新增一组采用预训练权重的基准实验，接在原有十组从零训练实验全部正常完成之后运行。

唯一变量是初始化：采用 Ultralytics 官方 assets v8.4.0 的 COCO 预训练 `yolo26n.pt`，通过 GitHub release asset 的 SHA256 和大小校验，来源与本地哈希已保存。使用与从零基准相同的 `yolo26n-baseline.yaml` 和版本固定的 UAVYOLO 训练器，通过原生 `load` 加载全部形状兼容的权重，包括颈部和框回归分支；COCO 的 80 类分类输出按单类 UAV 重建。加载范围覆盖整个网络而非仅骨干，优化器、轮次计数器从本轮训练重新开始。

固定数据：5800 train、1450 val、2048 外部 test；同一来源清单与 seed42，类别为 `uav`。训练 150 轮、640 输入、batch32、nbs32、FP32、AdamW、lr0=0.001、lrf=0.01、weight_decay=0.0005、workers8、patience0。增强及训练默认值与原始基准使用相同环境和入口。最佳检查点只在训练与验证上选择，外部 test 用于事后评价。

配置：`configs/experiments/four_source150/baseline_coco_pretrained.json`；入口：`scripts/run_pretrained_baseline.py`。入口从原始基准配置派生运行参数，只覆盖 `pretrained=True`，并显式关闭 resume。运行日志、初始权重来源、完整训练参数、数据清单哈希及实际迁移成功的 tensor keys 单独保存。

独立等待器要求后三组适配实验的完成标记均为 150 轮，取得原串行锁后启动自己的唯一训练子进程；前置队列失败或停止时接续停止，单个训练进程最多 86400 秒。云端 CPU 的两图、128 输入、单轮检查验证加载、单类重建和原生训练流程。

报告时将此组标为“COCO 预训练”，与 scratch 基准直接比较初始化收益；随机初始化的模型结果与训练条件分开列出。

实际状态：官方权重发布哈希和大小已校验；696 个兼容 tensor 经重建后与来源一致。云端 CPU 单轮训练、保存、最佳检查点验证已通过，独立接续进程随后启动。见[检查记录](../checks/pretrained_baseline_20261031.json)。
