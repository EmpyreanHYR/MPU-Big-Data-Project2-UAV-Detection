# 实测结果导航

更新：2026年11月16日。每条记录标注各自的模型、输入与计时范围。

| 当前内容 | 文件 |
|---|---|
| Pi本机GUI配音演示（时间文字过滤） | [说明](GUI_NARRATED_20261116.md) · [JSON](GUI_NARRATED_20261116.json) |
| 演示视频零正确检出诊断（坐标、标注尺度、FP32/H10对照） | [分析](LOCALIZATION_DIAGNOSIS_20261116.md) · [JSON](LOCALIZATION_DIAGNOSIS_20261116.json) |
| 时间文字误检审计（过滤前后FP/FN与指标） | [分析](TIMESTAMP_AUDIT_20261116.md) · [JSON](TIMESTAMP_AUDIT_20261116.json) |
| Pi本机完整GUI操作录屏 | [说明](GUI_RECORDING_20261116.md) · [JSON](GUI_RECORDING_20261116.json) |
| Pi本机视频速度与真实桌面稳定性 | [记录](GUI_NATIVE_20261116.md) · [JSON](GUI_NATIVE_20261116.json) |
| PyQt图片与视频检测、H10真机联调 | [说明](GUI_H10_20261116.md) · [汇总JSON](GUI_H10_20261116.json) |
| 基线比较、消融、训练比例、跨设备四类表格 | [EXPERIMENT_TABLES_20261105.md](EXPERIMENT_TABLES_20261105.md) |
| 11模型全部细项（GPU／Pi CPU／H10） | [CSV](EDGE_EXTENSION_20261104.csv) · [JSON](EDGE_EXTENSION_20261104.json) · [说明](EDGE_EXTENSION_20261104.md) |
| 最终模型规模与分组错误 | [说明](FINAL_MODEL_SCALING_ERRORS_20261105.md) · [工作负载CSV](FINAL_MODEL_SCALING_20261105.csv) · [错误CSV](FINAL_MODEL_ERRORS_20261105.csv) |
| 最终模型选型 | [依据](FINAL_SELECTION_PCONV_P2_20261104.md) · [结构图](../report/figures/final_pconv_p2.drawio) |
| 四源外部评价 | [ALL_MODEL_EXTERNAL_20261104.csv](ALL_MODEL_EXTERNAL_20261104.csv) |
| 从零100轮PConv／P2消融 | [原生指标](SCRATCH_ABLATIONS_20261104.md) |
| 训练比例500／1000／1999图 | [三档实测](TRAINING_FRACTIONS_20261107.md) |
| NMS默认策略、H10阈值测速与VLM实验 | [分析](NMS_VLM_AUDIT_20261115.md) · [硬件CSV](NMS_HARDWARE_20261115.csv) · [部署验收](NMS_DEPLOYMENT_ACCEPTANCE_20261115.json) |
| 早期模型／GPU／视频对照 | [ALL_MODEL_INFERENCE_20261103.md](ALL_MODEL_INFERENCE_20261103.md) · [GPU_EXTERNAL_VIDEO_20261103.md](GPU_EXTERNAL_VIDEO_20261103.md) |

共19组有效训练：GPU全部19组、Pi CPU 17组跑完500图。主范围是11个从零100轮模型，其中7个完成H10真机500图；预训练与150轮记录作为单独的历史对照，Faster R-CNN被取消、Ghost移植未完成，均不计入。

表中数值分别来自原生验证AP、GPU FP32部署AP和H10量化部署AP。固定阈值指标先按conf0.25筛选，再按IoU≥0.5一对一匹配；AP另用0.001置信度下限和10个IoU阈值计算。设备值按GPU／Pi CPU／Pi H10顺序排列，E1（导出或验证未通过）、E2（H10路径未覆盖）、NR（未运行）与NA（无定义）不算作0分。

最终GUI的HEF、匹配元数据、1080p配音演示、720p预览和双语字幕已发布到[GitHub Release](https://github.com/EmpyreanHYR/MPU-Big-Data-Project2-UAV-Detection/releases/tag/gui-h10-v1.0.0)，下载与配置见[GUI复现指南](../GUI_REPRODUCIBILITY.md)。原始图像、训练检查点、ONNX、其他模型的HEF和逐图预测保存在本地结果包。

25%与50%训练比例权重只做了GPU评价，未测Pi CPU与H10。跨模型表沿用各模型原来的后处理：YOLO26端到端路径不执行NMS，YOLOv8/YOLO11用NMS0.7；当前PinP2默认NMS0.4的结果单独一列。

演示视频由30张图循环组成，H10在原GT与IoU0.5口径下TP为0；时间文字过滤把FP从18降到8，FN保持30。内部500图的31.740% AP、H10硬件基准22.89 FPS、未录屏GUI 16.51 FPS、配音录屏GUI 10.57 FPS是四种不同条件的数值。详见上表的误检审计、定位诊断与GUI记录。
