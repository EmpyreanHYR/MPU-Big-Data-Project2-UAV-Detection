# 数据集来源与使用约定

本项目主任务为红外无人机框检测。原始数据保存在本地原始数据目录并保持原件；仓库的 Git 忽略目录 `data/` 用于处理与传输缓存。仓库记录来源、版本、划分与转换流程。

| 数据集 | 来源 | 规模与标注 | 项目用途 |
|---|---|---|---|
| SIRST-UAVB | [PConv 论文](https://arxiv.org/abs/2412.16986)、[作者仓库与下载入口](https://github.com/JN-Yang/PConv-SDloss-Data) | 3000幅实拍红外图像，2955个UAV框、1742个鸟框 | 无人机单类主实验；鸟框用于误报分析 |
| IRSTD-1k | [ISNet 作者页](https://github.com/RuiZhang97/ISNet)；框标注另核对 [PConv](https://github.com/JN-Yang/PConv-SDloss-Data) / [EFLNet](https://github.com/YangBo0411/infrared-small-target) | 1001幅真实图像，原像素标注及相应框标注版本 | 通用红外目标补充实验 |
| NUDT-SIRST | [DNANet 作者页](https://github.com/YeRen123455/Infrared-Small-Target-Detection) | 1327幅合成图像，256×256，像素标注 | 单独通用target实验，核对框或生成派生框 |
| SIRST / NUAA-SIRST | [作者数据页](https://github.com/YimianDai/sirst) | 427幅真实图像；使用匹配的框或由目标区域生成外接框 | 小样本补充实验 |
| SIRST-V2 | [作者数据页](https://github.com/YimianDai/open-sirst-v2)、[版本关系](https://github.com/YimianDai/open-sirst-v2/issues/2) | 完整发布清单1024幅，含背景图与框等标注；包含V1 | 复杂背景扩展；与V1按包含关系去重 |
| DenseSIRST | [作者数据页](https://github.com/GrokCV/DenseSIRST)、[论文v3](https://arxiv.org/abs/2407.20078v3) | 1024幅真实/合成混合图像、13655个目标，有框/掩膜/点标注 | 密集目标扩展 |
| NUDT-SIRST-Sea | [MTU-Net 作者论文与数据说明](https://arxiv.org/abs/2209.13756) | 48幅10000×10000星载图像、17598个像素级舰船标注 | 海面通用目标扩展，按原大图划分再切块 |

## 标注与划分

SIRST-UAVB 映射为 `uav` 单类；保留原始鸟类框用于错误归因。其他数据集单独采用通用 `target` 标签，并记录框版本。需要从掩膜生成框时，固定连通域和像素边界约定，保留一像素目标，抽查粘连与碎裂目标，记录原掩膜和转换程序版本。

划分按来源序列或原始大图组织，固定训练、验证和测试清单；合成数据记录其背景来源。各模型使用同一标注和清单。SIRST-V2 的完整清单统计保存在 [metadata](metadata/)；该记录来自作者仓库 Git 树与ID文本，未包含图像。

## 每次取得数据时记录

记录作者入口、实际下载页、取得日期、文件版本和SHA256，以及下载包内的许可与署名要求。将原始包、转换结果和划分清单分开保存；README中的规模与实际清单统计共同保留。数据再分发按各来源的实际许可安排，仓库仅保存来源说明和处理代码。

数据配置从 [示例](../../configs/datasets/sirst_uavb.example.yaml)复制到本地 `data/`，填写真实路径和固定的划分清单。Git中不包含数据图像或权重。

本次已加入 native YOLO/VOC 框适配、UAV/bird 分离、来源组划分、原像素重复检测和独立审计；操作见 [PREPARATION.md](PREPARATION.md)。真实数据包现已在Windows取得，原包完整性和原生框检查已完成；源类别语义、来源分组及正式划分审计仍待完成，当前没有正式处理后的数据划分或训练结果。

2026-10-24 较早接收检查仅完成大小、SHA256、目录和标签初步计数；该阶段已由下方全包审计更新替代。设备、原始路径及传输恢复记录仅保存在本地。

2026-10-24 全包审计更新：3000幅图像为640×512灰度图，原标签class0/class1实测2961/1747框，无完全重复标签行。原训练/验证之间有496组像素完全相同的图像，另3组相同像素标注存在差异。去重并隔离冲突后的候选为2395train/104val，尚不构成来源序列独立的正式划分；类别语义、来源组和独立test仍待核验。未将该候选用于训练。

2026-10-24 后续核验：结合论文“掩膜排除鸟类”的说明，确认class0=UAV、class1=bird。隔离标注冲突、掩膜缺失和背景边界近邻后，已固定1438train/505val；云端真实转换及独立审计通过，零像素重复。原视频编号未发布，采用明确标注的推断背景视图留出协议，没有独立test。清单、类别映射和政策依据见 [固定划分](../../configs/datasets/sirst_uavb_scene_holdout_v3/README.md)。
