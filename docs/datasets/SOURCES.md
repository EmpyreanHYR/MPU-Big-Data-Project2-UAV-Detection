# 当前数据来源与用途

主任务为红外无人机边界框检测，标签统一为`uav`单类。训练及内部验证使用清理后的SIRST-UAVB；其他来源分别用于跨数据集评价。

| 来源 | 本项目实际数量 | 用途及标注 |
|---|---:|---|
| SIRST-UAVB | 清理后2499图，1999训练／500验证 | 原生UAV框；鸟类作为审计记录，合规负样本保留 |
| UAV-CB thermal | 3391图 | 红外图像，矩形标签转换为检测框 |
| Tri-Modal Anti-UAV IR | 1060图 | IR图像和UAV框 |
| AUVD-Seg300 | 300图 | 无人机分割多边形的外接矩形，派生检测框 |
| Anti-UAV-detection | 2048图 | 派生发布的单类检测框及无目标图像 |

四个外部来源共6799张，分别统计，用于冻结模型的迁移评价；训练、内部选点、阈值调参和选型只使用SIRST。SIRST数据按推断背景视图分组，来源以背景视图族计。

作者来源：

- SIRST-UAVB：[PConv论文](https://arxiv.org/abs/2412.16986)及[作者数据/代码](https://github.com/JN-Yang/PConv-SDloss-Data)。
- UAV-CB：[作者论文](https://arxiv.org/abs/2603.17492)。
- Tri-Modal：[作者项目](https://github.com/eulerbaby123/Tri-Modal-Anti-UAV)。
- AUVD-Seg300：[作者论文](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0330074)。
- Anti-UAV-detection：[派生数据发布](https://github.com/SSDIC-CV/Anti-UAV-detection)。

原始下载包按私有存档索引保存在指定数据存储位置，不提交到Git。完整SIRST-UAVB原件由已校验的原件恢复；本机只保留部分原始包。标签映射、固定清单和文件哈希保存在实际训练来源及结果包中。[处理流程](PREPARATION.md)与[单源协议](../experiments/SIRST_CROSSDATA_20261102.md)说明实际采用的数据组成。
