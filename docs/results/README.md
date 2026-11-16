# 实测结果导航

更新：2026年11月16日。按下表查看当前证据；有日期的记录保留各自的模型、输入及计时范围。

| 当前内容 | 文件 |
|---|---|
| 英文配音、双语字幕与时间文字过滤后的GUI演示 | [说明](GUI_NARRATED_20261116.md) · [JSON](GUI_NARRATED_20261116.json) |
| 演示零正确检出：坐标、标注尺度及同图FP32/H10诊断 | [分析](LOCALIZATION_DIAGNOSIS_20261116.md) · [JSON](LOCALIZATION_DIAGNOSIS_20261116.json) |
| 时间文字误检占比、过滤前后FP/FN与指标审计 | [分析](TIMESTAMP_AUDIT_20261116.md) · [JSON](TIMESTAMP_AUDIT_20261116.json) |
| Pi本机完整GUI操作录屏 | [说明](GUI_RECORDING_20261116.md) · [JSON](GUI_RECORDING_20261116.json) |
| Pi本机视频速度与真实桌面稳定性 | [记录](GUI_NATIVE_20261116.md) · [JSON](GUI_NATIVE_20261116.json) |
| PyQt图片与视频实时检测、H10真机联调 | [说明](GUI_H10_20261116.md) · [汇总JSON](GUI_H10_20261116.json) |
| 基线比较、消融、训练比例、跨设备四类表格 | [EXPERIMENT_TABLES_20261105.md](EXPERIMENT_TABLES_20261105.md) |
| 11模型全部细项 | [CSV](EDGE_EXTENSION_20261104.csv) · [JSON](EDGE_EXTENSION_20261104.json) · [说明](EDGE_EXTENSION_20261104.md) |
| 最终模型规模与分组错误 | [说明](FINAL_MODEL_SCALING_ERRORS_20261105.md) · [工作负载CSV](FINAL_MODEL_SCALING_20261105.csv) · [错误CSV](FINAL_MODEL_ERRORS_20261105.csv) |
| 最终模型选型 | [依据](FINAL_SELECTION_PCONV_P2_20261104.md) · [结构图](../report/figures/final_pconv_p2.drawio) |
| 四源60组外部评价 | [ALL_MODEL_EXTERNAL_20261104.csv](ALL_MODEL_EXTERNAL_20261104.csv) |
| 从零100轮PConv／P2消融 | [原生指标](SCRATCH_ABLATIONS_20261104.md) |
| 训练比例500／1000／1999图 | [三档实测](TRAINING_FRACTIONS_20261107.md) |
| NMS默认策略、24次硬件测速与VLM负面结果 | [分析](NMS_VLM_AUDIT_20261115.md) · [硬件CSV](NMS_HARDWARE_20261115.csv) · [部署验收](NMS_DEPLOYMENT_ACCEPTANCE_20261115.json) |
| 较早的模型／GPU／视频对照 | [ALL_MODEL_INFERENCE_20261103.md](ALL_MODEL_INFERENCE_20261103.md) · [GPU_EXTERNAL_VIDEO_20261103.md](GPU_EXTERNAL_VIDEO_20261103.md) |

累计19组有效训练、GPU19组和Pi CPU17组500图；主范围11个从零100轮模型，其中7个完成H10真实500图。历史预训练和150轮记录是对照证据，不作为新100轮权重的测试结果。取消的Faster R-CNN及未完成Ghost移植不计入完成数量。

原生验证AP、共同FP32部署AP和H10量化部署AP各自保留口径。固定置信度0.25先筛选，再按IoU≥0.5独立一对一匹配；AP另用0.001置信度下限及10个IoU阈值计算。设备三元值按GPU／Pi CPU／Pi H10顺序排列，未运行、导出失败及未定义结果不作为零分。

这里提交经过整理的汇总和模型/协议哈希。最终GUI的HEF、匹配元数据、1080p配音演示、720p预览和双语字幕已发布到[GitHub Release](https://github.com/EmpyreanHYR/MPU-Big-Data-Project2-UAV-Detection/releases/tag/gui-h10-v1.0.0)，下载与配置见[GUI复现指南](../GUI_REPRODUCIBILITY.md)。二进制附件不写入Git源码历史；原始图像、训练检查点、ONNX、其他模型的HEF、逐图预测数组和完整设备记录仍保存在私有结果包。

新增两个训练比例权重仅完成GPU评价，未测Pi CPU/H10。跨模型表保留原各模型后处理设置，其中YOLO26端到端路径未执行NMS，YOLOv8/YOLO11使用NMS0.7；当前PinP2默认NMS0.4的结果单列。较早日期的记录用于追溯来源；阅读当前结论从上表开始。

最新演示素材为30张图循环：H10在原GT及IoU0.5口径下TP为0，时间文字过滤使FP18→8、FN30不变。内部500图的31.740% AP、硬件基准22.89 FPS、未录屏GUI16.51 FPS及配音录屏GUI10.57 FPS分别保留，不能合并为视频准确率或同一测速结果。对应证据见上表的误检审计、定位诊断和GUI记录。
