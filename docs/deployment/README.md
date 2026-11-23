# 最终部署

当前模型：PinP2-YOLO（YOLO26n＋PConv＋P2），从零100轮，部署于树莓派5＋HAILO10H。默认**NMS IoU=0.4、conf=0.25、max300**；H10 AP50:95为31.740%，TP323／FP62／FN163，三轮阈值基准22.89±0.01 FPS。不加NMS时为AP50:95 24.351%、22.72 FPS。

入口与用法见[PinP2部署程序](../../scripts/deployment/README.md)；500图部署验收通过，版本20261115-nms04，单次22.56 FPS，与三轮阈值基准分开记录。旧baseline／SIA路径不属于该版本。选择依据见[NMS审计](../results/NMS_VLM_AUDIT_20261115.md)。

[最终选型](../results/FINAL_SELECTION_PCONV_P2_20261104.md)、[硬件全表](../results/EDGE_EXTENSION_20261104.md)和[实际网络图](../report/figures/final_pconv_p2.png)为当前依据。本地结果入口的“03_模型选择与部署”包含该模型的ONNX、HEF、原始权重、架构和推理程序。

[SIA＋CSP样例部署](PF_YOLO_PI5_20261103.md)是报告视频与早期样例使用的模型，不是最终组合模型。

[历史评价程序](../../scripts/evaluation/README.md)提供NumPy指标重算以及Pi CPU、H10的历次评价入口。最终GUI的HEF和匹配元数据已公开，按[模型下载说明](../../models/README.md)及[GUI复现指南](../GUI_REPRODUCIBILITY.md)准备；验证数据、原始预测、其他模型和设备SDK需另行获取。程序启动时用模型哈希和固定验证清单核对身份，运行时需持有共享硬件锁。
