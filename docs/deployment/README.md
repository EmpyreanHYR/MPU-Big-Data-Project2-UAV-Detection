# 最终部署

当前模型：PinP2-YOLO（YOLO26n＋PConv＋P2），从零100轮，树莓派5＋HAILO10H。默认**NMS IoU=0.4、conf=0.25、max300**，实际调用NMS后处理；H10 AP50:95为31.740%，TP323／FP62／FN163，三轮阈值基准22.89±0.01 FPS。原无NMS结果AP24.351%／22.72 FPS保留历史口径。

当前入口与用法见[PinP2部署程序](../../scripts/deployment/README.md)，500图实际部署验收已经通过并发布为20261115-nms04；旧baseline／SIA路径不代表该默认版本。验收单次22.56 FPS与阈值测速单独记录。选择依据及限制见[NMS审计](../results/NMS_VLM_AUDIT_20261115.md)。

[最终选型](../results/FINAL_SELECTION_PCONV_P2_20261104.md)、[硬件全表](../results/EDGE_EXTENSION_20261104.md)和[实际网络图](../report/figures/final_pconv_p2.png)为当前依据。本地结果入口中的“03_模型选择与部署”包含经哈希核验的该模型ONNX、HEF、原始权重、架构和实际推理程序。

[SIA＋CSP样例部署](PF_YOLO_PI5_20261103.md)为报告中视频／早期样例的原始记录，不属于最终组合模型的实测结果。

[历史评价程序](../../scripts/evaluation/README.md)保留NumPy指标重算、Pi CPU和H10历史评价入口；当前PinP2实际部署使用上方显式NMS入口。模型文件、验证数据、原始预测和设备配套SDK另行保存在本地；源程序使用模型哈希和冻结验证清单核对身份。单独运行时需要传入既有共享硬件锁，并使用有限执行窗口。
