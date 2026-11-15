# MPU Big Data Project 2 · 红外无人机检测

本项目研究小型红外无人机的检测与边缘部署。在YOLO26n上加入浅层风车卷积（PConv）和高分辨率P2检测分支，形成 **PinP2-YOLO**，并在树莓派5＋HAILO10H上完成实际推理测试。

## 组员从哪里开始

1. 阅读[项目进展与待办](docs/PROJECT_STATUS.md)，了解已做工作、结论和仍需补充的内容。
2. 阅读[中文报告](docs/report/report_zh.md)；汇报与提交以[英文报告PDF](docs/report/report.pdf)为准。
3. 做PPT时使用[当前网络图](docs/report/figures/final_pconv_p2.pdf)和[实验结果导航](docs/results/README.md)，引用时保留评价口径。
4. 修改代码前查看[环境说明](docs/ENVIRONMENT.md)、[配置导航](configs/README.md)和[部署入口](scripts/deployment/README.md)。

## 已完成什么

| 工作 | 结果与入口 |
|---|---|
| 数据整理 | SIRST-UAVB固定1999张训练／500张验证，验证集486个UAV框；[来源与标注](docs/datasets/SOURCES.md) |
| 模型比较与消融 | 主比较11个从零100轮模型，累计19个有效权重；[四类实验表](docs/results/EXPERIMENT_TABLES_20261105.md) |
| 训练比例 | 500／1000／1999张训练图，统一500张验证；[三档实测](docs/results/TRAINING_FRACTIONS_20261107.md) |
| 边缘测试 | GPU19组、Pi CPU17组、H10兼容模型7组；[设备结果](docs/results/EDGE_EXTENSION_20261104.md) |
| 后处理改进 | NMS IoU0.4使H10误报119→62，检出323、漏检163不变；[审计与硬件实测](docs/results/NMS_VLM_AUDIT_20261115.md) |
| VLM候选复核 | 已完成负面结果分析，当前策略未优于相同召回率的置信度阈值对照；后续扩展暂停 |
| 报告与图表 | [10页IEEE报告、中文稿及可编辑图源](docs/report/README.md) |

当前PinP2/H10默认部署的AP50:95为 **31.740%**，三轮阈值基准为 **22.89±0.01 FPS**。这些是内部验证集上的部署结果；原生训练验证、FP32、无NMS和NMS后的指标分别记录。最终模型是综合取舍，不能声称所有精度和速度指标都最优。

## 目录怎么用

| 目录 | 内容 |
|---|---|
| `src/uav_detection/` | 模型结构、训练适配、数据处理 |
| `configs/` | 当前模型与部署参数，以及有日期说明的历史实验配置 |
| `scripts/` | 数据准备、训练入口、指标复算、部署、文档构建与检查 |
| `experiments/` | NMS审计和VLM候选复核的分析代码 |
| `docs/report/` | 当前报告、图表及复现说明 |
| `docs/results/` | 当前结果入口与有来源的历史对照证据 |
| `docs/proposal/` | 已提交提案，保留当时计划，不作为当前实验参数 |
| `bibliography/`、`templates/`、`third_party/` | 统一文献、原始模板及第三方来源与许可 |

原始数据、权重、ONNX/HEF、逐图预测和设备运行记录不在Git中。需要复核完整实验时，应向项目维护者获取对应私有结果包，按[复现说明](docs/report/REPRODUCIBILITY_NOTES.md)核对版本与哈希。

## 本地检查与报告构建

使用Python3.10+，在自己的虚拟环境中执行：

```sh
python -m pip install -e '.[evaluation]'
python scripts/check_project.py
```

检查入口只收集Git跟踪的公开测试，不会收集本地私有云端脚本测试。Mac/Pi跳过模型集成测试；模型检查仅在已配置依赖的Linux x86_64环境进行。训练和设备部署须按对应环境与操作说明执行，不属于本地文档检查。

安装pdfLaTeX和BibTeX后，可用 `python scripts/build_report.py` 编译报告；提案构建使用 `python scripts/build_proposal.py`。文献修改以 `bibliography/references.bib` 为准，同步副本后运行检查。

贡献说明、个人反思和提交附件仍待组员补齐。仓库清理范围与旧文件恢复方法见[维护记录](docs/REPOSITORY_MAINTENANCE.md)。
