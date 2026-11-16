# MPU Big Data Project 2 · 红外无人机检测

本项目研究小型红外无人机的检测与边缘部署。在YOLO26n上加入浅层风车卷积（PConv）和高分辨率P2检测分支，形成 **PinP2-YOLO**，并在树莓派5＋HAILO10H上完成实际推理测试。

## GUI demonstration / 操作演示

https://github.com/user-attachments/assets/ad5af9a7-2ece-4dd1-8940-8daeae079ef7

**3分46秒**：树莓派本机真实H10检测，展示图片检测、时间文字过滤、视频检测及暂停／恢复。
英文讲解、双语字幕、操作放大，无背景音乐。上方为完整720p预览；
[下载1080p原版视频](https://github.com/EmpyreanHYR/MPU-Big-Data-Project2-UAV-Detection/releases/download/gui-h10-v1.0.0/PinP2_H10_GUI_narrated_demo.mp4) ·
[双语字幕](https://github.com/EmpyreanHYR/MPU-Big-Data-Project2-UAV-Detection/releases/download/gui-h10-v1.0.0/PinP2_H10_GUI_bilingual.srt) ·
[模型与视频Release](https://github.com/EmpyreanHYR/MPU-Big-Data-Project2-UAV-Detection/releases/tag/gui-h10-v1.0.0)。
视频检测素材由30张真实红外图片循环组成，用于演示操作，不是连续拍摄的视频或精度测试。
按原始标注、conf≥0.25和IoU≥0.5复核，这30张图的H10正确检出数为0；时间文字过滤使误报18→8，漏检30不变。[同图诊断](docs/results/LOCALIZATION_DIAGNOSIS_20261116.md)记录了FP32/H10对照和标注尺度检查，功能演示与检测质量分别评价。

## Real detection / 真实检测

已公开与本项目真机验收一致的 **HAILO10H HEF模型＋解码元数据**，无需另找维护者索取模型。
在树莓派的完整仓库中执行：

```sh
python3 scripts/download_gui_model.py
python3 scripts/download_gui_model.py --verify-only
```

模型安装到 `models/pinp2_h10/`，下载器自动核对压缩包及每个文件的SHA256。
随后按[真机配置与启动步骤](docs/GUI_REPRODUCIBILITY.md#4-prepare-real-h10-detection--准备真机)
指定自己的图片／视频，即可实际推理。需要树莓派5、HAILO10H和已配置的HailoRT5.1.1；
该HEF不适用于Hailo-8/8L，也不在普通电脑上执行检测。

## Quick GUI check / 无设备检查界面

完整步骤见[GUI复现指南](docs/GUI_REPRODUCIBILITY.md)。使用Python3.12+，在仓库根目录执行：

```sh
python3 -m venv .venv-gui
.venv-gui/bin/python -m pip install -e '.[gui]' -c constraints/gui-desktop-20261116.txt
.venv-gui/bin/python scripts/prepare_gui_smoke_demo.py
.venv-gui/bin/python scripts/run_gui.py --config outputs/gui_smoke/demo.json
```

这个入口生成明确标注的合成图片和预测，用于检查界面，不代表模型效果。真实图片／视频检测使用上方公开的模型包和树莓派5＋HAILO10H；配置模板位于[configs/gui](configs/gui/README.md)。自动检查运行 `python scripts/check_gui.py`，不加载模型或连接设备。

## 组员从哪里开始

1. 阅读[项目进展与待办](docs/PROJECT_STATUS.md)，了解已做工作、结论和仍需补充的内容。
2. 阅读[中文报告](docs/report/report_zh.md)；汇报与提交以[英文报告PDF](docs/report/report.pdf)为准。
3. 做PPT时使用[当前网络图](docs/report/figures/final_pconv_p2.pdf)和[实验结果导航](docs/results/README.md)，引用时保留评价口径。
4. 修改代码前查看[环境说明](docs/ENVIRONMENT.md)、[配置导航](configs/README.md)和[部署入口](scripts/deployment/README.md)。
5. 课堂演示使用 [PyQt6 检测工作台](docs/GUI.md)：真实实验结果回放、H10 实时检测客户端、图片／视频导出和实验结果对比。Mac 可双击 `启动检测演示.command`；真机演示使用 [启动H10实时检测.command](启动H10实时检测.command)（先安装 GUI 依赖并准备私有连接配置）。树莓派显示器演示使用 [启动树莓派本机演示.command](启动树莓派本机演示.command)，素材缓存一次、本机检测；[演示与录制说明](docs/DEMO_REHEARSAL.md)。新版为 [3分46秒英文配音演示](docs/results/GUI_NARRATED_20261116.md)，含双语字幕、操作放大和时间文字过滤；[原始完整录屏](docs/results/GUI_RECORDING_20261116.md)保留。已完成 [图片与视频H10联调](docs/results/GUI_H10_20261116.md)。

## 已完成什么

| 工作 | 结果与入口 |
|---|---|
| 数据整理 | SIRST-UAVB固定1999张训练／500张验证，验证集486个UAV框；[来源与标注](docs/datasets/SOURCES.md) |
| 模型比较与消融 | 主比较11个从零100轮模型，累计19个有效权重；[四类实验表](docs/results/EXPERIMENT_TABLES_20261105.md) |
| 训练比例 | 500／1000／1999张训练图，统一500张验证；[三档实测](docs/results/TRAINING_FRACTIONS_20261107.md) |
| 边缘测试 | GPU19组、Pi CPU17组、H10兼容模型7组；[设备结果](docs/results/EDGE_EXTENSION_20261104.md) |
| 后处理改进 | NMS IoU0.4使H10误报119→62，检出323、漏检163不变；[审计与硬件实测](docs/results/NMS_VLM_AUDIT_20261115.md) |
| VLM候选复核 | Qwen2.5-VL-3B-Instruct的E0—E4及689条响应已核验；[负面结果](docs/results/NMS_VLM_AUDIT_20261115.md)未优于相同召回率的置信度阈值对照，扩大实验暂停 |
| 报告与图表 | [10页IEEE报告、中文稿及可编辑图源](docs/report/README.md) |

当前PinP2/H10默认部署的AP50:95为 **31.740%**，三轮阈值基准为 **22.89±0.01 FPS**。这些是内部验证集上的部署结果；原生训练验证、FP32、无NMS和NMS后的指标分别记录。最终模型是综合取舍，不能声称所有精度和速度指标都最优。

与大数据课程的联系包括数据真实性（像素去重、标注冲突与跨源标注差异）、数据规模（三档训练量及推理负载）和处理速度（边缘吞吐与内存）。VLM是已经评价的离线组件，未纳入当前H10实时推理流程。

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

GUI所需HEF、匹配元数据和演示视频已发布到[GitHub Release](https://github.com/EmpyreanHYR/MPU-Big-Data-Project2-UAV-Detection/releases/tag/gui-h10-v1.0.0)，不占用Git源码历史。原始数据、训练权重、ONNX、逐图预测和完整设备记录仍不随仓库分发。需要复核完整实验时，应向项目维护者获取对应私有结果包，按[复现说明](docs/report/REPRODUCIBILITY_NOTES.md)核对版本与哈希。

## 本地检查与报告构建

使用Python3.10+，在自己的虚拟环境中执行：

```sh
python -m pip install -e '.[evaluation]'
python scripts/check_project.py
```

检查入口只收集Git跟踪的公开测试，不会收集本地私有云端脚本测试。Mac/Pi跳过模型集成测试；模型检查仅在已配置依赖的Linux x86_64环境进行。训练和设备部署须按对应环境与操作说明执行，不属于本地文档检查。

安装pdfLaTeX和BibTeX后，可用 `python scripts/build_report.py` 编译报告；提案构建使用 `python scripts/build_proposal.py`。文献修改以 `bibliography/references.bib` 为准，同步副本后运行检查。

报告、幻灯片和贡献文件截止为 **2026年11月29日24:00（北京时间）**；12月3日汇报，10分钟讲述＋5分钟问答。四位成员的实际贡献与反思、PPT/讲稿、Turnitin、AI使用声明及独立提交包仍待补齐；3分46秒演示视频已完成。具体核查见[当前清单](docs/report/REVIEW_CHECKLIST.md)。仓库清理范围与旧文件恢复方法见[维护记录](docs/REPOSITORY_MAINTENANCE.md)。
