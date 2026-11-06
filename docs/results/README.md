# 实测结果导航

| 当前内容 | 文件 |
|---|---|
| 基线比较、消融、训练比例、跨设备四类表格 | [EXPERIMENT_TABLES_20261105.md](EXPERIMENT_TABLES_20261105.md) |
| 11模型全部细项 | [CSV](EDGE_EXTENSION_20261104.csv) · [JSON](EDGE_EXTENSION_20261104.json) · [说明](EDGE_EXTENSION_20261104.md) |
| 最终模型规模与分组错误 | [说明](FINAL_MODEL_SCALING_ERRORS_20261105.md) · [工作负载CSV](FINAL_MODEL_SCALING_20261105.csv) · [错误CSV](FINAL_MODEL_ERRORS_20261105.csv) |
| 最终模型选型 | [依据](FINAL_SELECTION_PCONV_P2_20261104.md) · [结构图](figures/final_pconv_p2_20261104.drawio) |
| 四源60组外部评价 | [ALL_MODEL_EXTERNAL_20261104.csv](ALL_MODEL_EXTERNAL_20261104.csv) |
| 从零100轮PConv／P2消融 | [原生指标](SCRATCH_ABLATIONS_20261104.md) |
| 较早的模型／GPU／视频对照 | [ALL_MODEL_INFERENCE_20261103.md](ALL_MODEL_INFERENCE_20261103.md) · [GPU_EXTERNAL_VIDEO_20261103.md](GPU_EXTERNAL_VIDEO_20261103.md) |

累计17组有效训练、GPU和Pi CPU各17组500图；主范围11个从零100轮模型，其中7个完成H10真实500图。历史预训练和150轮记录是对照证据，不作为新100轮权重的测试结果。取消的Faster R-CNN及未完成Ghost移植不计入完成数量。

原生验证AP、共同FP32部署AP和H10量化部署AP各自保留口径。固定置信度0.25先筛选，再按IoU≥0.5独立一对一匹配；AP另用0.001置信度下限及10个IoU阈值计算。设备三元值按GPU／Pi CPU／Pi H10顺序排列，未运行、导出失败及未定义结果不作为零分。

这里提交经过整理的汇总和模型/协议哈希。原始图像、检查点、ONNX/HEF、逐图预测数组、设备与回传记录保存在本地结果包，不提交到Git。
