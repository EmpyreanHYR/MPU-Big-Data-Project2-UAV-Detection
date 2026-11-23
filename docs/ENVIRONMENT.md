# 环境说明

模型代码要求Python3.10+，运行适配器固定为`ultralytics==8.4.193`，与`pyproject.toml`及`architecture.py`一致。`third_party/ultralytics-yolo26.yaml`保留来源标签v8.4.184的原始配置用于结构核对。

训练与GPU评价环境为PyTorch2.1.2＋cu118、RTX2080Ti、FP32。MSF-GhostNet使用单独的YOLOv5适配环境，附加依赖见[环境配置](../configs/environments/msf-adapter-extra.txt)。模型家族的参数和初始化分组见[实验说明](experiments/README.md)。

树莓派CPU评价使用ONNX Runtime1.23.2、CPUExecutionProvider和4线程；H10程序需要设备配套的HailoRT Python运行时，结果按H10实测报告。数据与已保存预测的指标核验只需要Pillow/NumPy。

GUI桌面环境：macOS ARM64、Python3.14.6、PyQt6 6.12.1／Qt6 6.12.0、NumPy2.5.4、Pillow13.0.0、opencv-python-headless4.14.0.94，由[GUI约束文件](../constraints/gui-desktop-20261116.txt)固定。Pi本机验收使用系统PyQt5 5.15.11／Qt5.15.15、NumPy2.2.4、Pillow11.1.0和HailoRT5.1.1；GUI兼容PyQt5和PyQt6。

拉取本机GUI后无需设备，可按[复现指南](GUI_REPRODUCIBILITY.md)运行合成样例；真机检测按[模型说明](../models/README.md)下载并校验HAILO10H HEF及解码元数据，该路径不加载PT权重或ONNX。训练环境、Pi CPU模型评价和H10推理各自使用独立依赖。
