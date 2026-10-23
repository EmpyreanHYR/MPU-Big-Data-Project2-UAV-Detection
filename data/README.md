# 本地数据

图像、框标注、划分清单和本地 dataset YAML 放在本目录。来源与处理约定见 [数据来源](../docs/datasets/SOURCES.md)，配置示例见 [SIRST-UAVB](../configs/datasets/sirst_uavb.example.yaml)。

主数据使用 `uav` 单类映射；保留原标签作为只读副本，转换输出单独存放。此目录的实验数据被 Git 忽略，仓库中只保留本说明。
