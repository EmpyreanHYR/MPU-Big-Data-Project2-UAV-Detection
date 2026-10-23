# 环境记录

模型代码使用 Python3.10+，可选依赖固定为 `ultralytics==8.4.184`。版本在2026-10-23从 [PyPI官方元数据](https://pypi.org/pypi/ultralytics/json)核对；[YOLO26官方文档](https://docs.ultralytics.com/models/yolo26/)和[配置说明](https://docs.ultralytics.com/usage/cfg/)作为模型及训练参数依据。

云端执行时另存Python、Ultralytics、PyTorch、CUDA、驱动、GPU名称和代码提交号。当前只完成依赖声明与静态检查，GPU运行环境尚待实际核验。

训练入口的 `time` 参数提供应用层时间限制；平台强制截止、累计费用/开机时长和训练后关机由云端管理流程执行。仓库整理期间不启动该流程。
