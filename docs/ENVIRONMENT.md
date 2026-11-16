# 环境与运行边界

模型代码要求Python3.10+，运行适配器固定为`ultralytics==8.4.193`，与`pyproject.toml`及`architecture.py`一致。`third_party/ultralytics-yolo26.yaml`保留来源标签v8.4.184的原始配置用于结构核对，不改写原件。

已保存的YOLO训练/GPU评价环境为PyTorch2.1.2＋cu118、RTX2080Ti、FP32。MSF-GhostNet使用单独的作者YOLOv5适配环境，附加依赖见[环境配置](../configs/environments/msf-adapter-extra.txt)。模型家族的参数和初始化分组见[实验说明](experiments/README.md)。

树莓派CPU评价使用ONNX Runtime1.23.2、CPUExecutionProvider和4线程；H10程序需要设备配套的HailoRT Python运行时，不提供CPU替代结果。数据与已保存预测的指标核验只需要Pillow/NumPy，不加载模型。

GUI桌面安装要求Python3.12+，依赖以[GUI约束文件](../constraints/gui-desktop-20261116.txt)及[复现指南](GUI_REPRODUCIBILITY.md)为准。原Pi本机验收使用系统PyQt5 5.15.11／Qt5.15.15及HailoRT5.1.1；GUI兼容PyQt5和PyQt6，具体环境不能直接用训练依赖替代。

真实GUI所需的最终HAILO10H HEF及解码元数据已公开，按[模型说明](../models/README.md)下载并校验。该路径不需要加载PT权重或ONNX；无设备时可运行明确标注的合成回放检查。训练环境、Pi CPU模型评价和真实H10推理仍各自保留依赖及执行范围。

Mac仅执行文件、数据、指标和文档检查。模型构建/加载及GPU实验在明确指定的Linux GPU环境执行；Pi只执行设备推理，不训练。此仓库的整理与测试不启动训练、远端设备或历史控制队列。
