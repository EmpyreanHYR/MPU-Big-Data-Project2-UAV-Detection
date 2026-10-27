# B0原始检测头的ONNX一致性检查

2026-10-28，从完整B0最终best导出opset11静态FP32 ONNX，并用已经冻结的同一300帧逐帧对照原模型。未训练、未校准、未编译HEF。六个原生one-to-one输出顺序固定为回归stride8/16/32，再分类stride8/16/32；输入为NCHW、1×3×640×640、RGB0..1和114letterbox填充。[机器可读结果](onnx_fp32_parity_20261028.json)。

全部六组原始输出在全部300帧有限且通过预先设定的atol1e-3/rtol1e-4比较，最大绝对误差7.82013e-5。使用固定版本官方Hailo host解码后，confidence≥0.25的检测数量、顺序和类别均与原模型匹配；最大坐标误差3.05176e-5像素、最大置信度误差1.57952e-6。预设检测门槛为坐标0.05像素、置信度1e-4，未据结果放宽。

恢复到原始JPEG坐标后，固定匹配IoU0.5，TP/FP/FN仍为60/5/240，与[原FP32参考](infrared_fp32_reference_20261028.md)一致。完整参数/BN状态与源权重摘要在导出及回放前后不变。原始模型、共享Ultralytics源码和依赖未修改；新增ONNX/ORT依赖仅在本项目独立目录。

ONNX SHA256：`97b802c9a83fee25ae4e0307470ad4de5e086ce17f2ccf49af9bec4d5704c8e4`。输出契约同时记录了六个实际Conv生产节点，供后续编译精确选取；模型文件保持私有。

此结果仅证明这300帧上的本机FP32导出与解码一致，不保证INT8量化精度、HEF编译、HailoRT兼容或实际H10性能。新编译环境的WSL启动返回资源错误0x800705aa，尚未进入DFC；没有修改共享环境、重启宿主或停止其他项目。H10后续仍须核对实际SDK及无梯度统计校准计划，参见[部署准备](../deployment/READINESS_20261028.md)。[官方Hailo文档](https://docs.ultralytics.com/integrations/hailo/)说明YOLO26使用原始头输出与host解码，nms=False选择one-to-one；本次检查未调用默认含finetune的Hailo导出入口。
