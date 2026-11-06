# 最终部署

当前模型：PinP2-YOLO（YOLO26n＋PConv＋P2），从零100轮，平台树莓派5＋HAILO10H。参数2.516M；GPU／Pi CPU管线38.59／4.13FPS；H10管线22.72FPS、AP50–95为24.351%、漏检33.539%。

[最终选型](../results/FINAL_SELECTION_PCONV_P2_20261104.md)、[硬件全表](../results/EDGE_EXTENSION_20261104.md)和[实际网络图](../results/figures/final_pconv_p2_20261104.png)为当前依据。本地结果入口中的“03_模型选择与部署”包含经哈希核验的该模型ONNX、HEF、原始权重、架构和实际推理程序。

[SIA＋CSP样例部署](PF_YOLO_PI5_20261103.md)为报告中视频／早期样例的原始记录，不属于最终组合模型的实测结果。

[公开评价程序](../../scripts/evaluation/README.md)提供NumPy指标重算、Pi CPU和H10推理入口。模型文件、验证数据、原始预测和设备配套SDK另行保存在本地；源程序使用模型哈希和冻结验证清单核对身份。单独运行时需要传入既有共享硬件锁，并使用有限执行窗口。
