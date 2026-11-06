# 环境与运行边界

模型代码要求Python3.10+，运行适配器固定为`ultralytics==8.4.193`，与`pyproject.toml`及`architecture.py`一致。`third_party/ultralytics-yolo26.yaml`保留来源标签v8.4.184的原始配置用于结构核对，不改写原件。

已保存的YOLO训练/GPU评价环境为PyTorch2.1.2＋cu118、RTX2080Ti、FP32。MSF-GhostNet使用单独的作者YOLOv5适配环境，附加依赖见[环境配置](../configs/environments/msf-adapter-extra.txt)。模型家族的参数和初始化分组见[实验说明](experiments/README.md)。

树莓派CPU评价使用ONNX Runtime1.23.2、CPUExecutionProvider和4线程；H10程序需要设备配套的HailoRT Python运行时，不提供CPU替代结果。数据与已保存预测的指标核验只需要Pillow/NumPy，不加载模型。

Mac仅执行文件、数据、指标和文档检查。模型构建/加载及GPU实验在明确指定的Linux GPU环境执行；Pi只执行设备推理，不训练。此仓库的整理与测试不启动训练、远端设备或历史控制队列。
