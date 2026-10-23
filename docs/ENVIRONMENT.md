# 环境记录

模型代码使用 Python3.10+，可选依赖固定为 `ultralytics==8.4.184`。版本在2026-10-23从 [PyPI官方元数据](https://pypi.org/pypi/ultralytics/json)核对；[YOLO26官方文档](https://docs.ultralytics.com/models/yolo26/)和[配置说明](https://docs.ultralytics.com/usage/cfg/)作为模型及训练参数依据。

云端执行时另存Python、Ultralytics、PyTorch、CUDA、驱动、GPU名称和代码提交号。目前已完成下述本地 CPU 检查，GPU运行环境尚待实际核验。

训练入口的 `time` 参数提供应用层时间限制；平台强制截止、累计费用/开机时长和训练后关机由云端管理流程执行。仓库整理期间不启动该流程。

2026-10-23 更新：本地在 Git 忽略的 `.venv` 安装检查环境并完成 CPU 验证：macOS arm64、Python3.12.14、Ultralytics8.4.184、PyTorch2.14.1、torchvision0.29.1、Pillow13.0.0。新增数据可选依赖 `pillow>=10,<14`。本地仅构建、无梯度前向和临时合成检查点测试，没有训练。实际 GPU/CUDA 环境需另行核验，不能用本地 CPU 检查替代。

训练入口在模型构建前按配置 seed 初始化随机状态，保存实际迁移张量及摘要。三个模型需使用同一经过核验的预训练来源和来源隔离的数据清单。模型适配器严格检查 Ultralytics8.4.184，其他版本应先适配和重新检查。
