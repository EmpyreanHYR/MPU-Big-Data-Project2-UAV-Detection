# MPU Big Data Project 2 · 红外无人机检测

本项目研究小型红外无人机的检测与边缘部署。在YOLO26n上加入浅层风车卷积（PConv）和高分辨率P2检测分支，形成 **PinP2-YOLO**，并在树莓派5＋HAILO10H上完成实际推理测试。

**课程汇报** · [打开 HTML 汇报（含演示视频）](https://yaoronghuang.top/MPU-Big-Data-Project2-UAV-Detection/presentation/)

## GUI demonstration / 操作演示

https://github.com/user-attachments/assets/ad5af9a7-2ece-4dd1-8940-8daeae079ef7

**3分46秒**：树莓派本机真实H10检测，展示图片检测、时间文字过滤、视频检测及暂停／恢复。
英文讲解、双语字幕、操作放大，无背景音乐。上方为完整720p预览；
[下载1080p原版视频](https://github.com/EmpyreanHYR/MPU-Big-Data-Project2-UAV-Detection/releases/download/gui-h10-v1.0.0/PinP2_H10_GUI_narrated_demo.mp4) ·
[双语字幕](https://github.com/EmpyreanHYR/MPU-Big-Data-Project2-UAV-Detection/releases/download/gui-h10-v1.0.0/PinP2_H10_GUI_bilingual.srt) ·
[模型与视频Release](https://github.com/EmpyreanHYR/MPU-Big-Data-Project2-UAV-Detection/releases/tag/gui-h10-v1.0.0)。
视频检测素材为30张真实红外图片的循环播放，用于演示操作。同一素材在conf≥0.25、IoU≥0.5下正确检出0、漏检30，时间文字过滤使误报18→8；[同图诊断](docs/results/LOCALIZATION_DIAGNOSIS_20261116.md)给出FP32/H10对照与标注尺度分析。

## Real detection / 真实检测

已公开与本项目真机验收一致的 **HAILO10H HEF模型＋解码元数据**。
在树莓派的完整仓库中执行：

```sh
python3 scripts/download_gui_model.py
python3 scripts/download_gui_model.py --verify-only
```

模型安装到 `models/pinp2_h10/`，下载器自动核对压缩包及每个文件的SHA256。之后按[真机配置与启动步骤](docs/GUI_REPRODUCIBILITY.md#4-prepare-real-h10-detection--准备真机)
指定自己的图片／视频，即可实际推理。运行环境为树莓派5＋HAILO10H＋HailoRT5.1.1。

## Quick GUI check / 无设备检查界面

完整步骤见[GUI复现指南](docs/GUI_REPRODUCIBILITY.md)。使用Python3.12+，在仓库根目录执行：

```sh
python3 -m venv .venv-gui
.venv-gui/bin/python -m pip install -e '.[gui]' -c constraints/gui-desktop-20261116.txt
.venv-gui/bin/python scripts/prepare_gui_smoke_demo.py
.venv-gui/bin/python scripts/run_gui.py --config outputs/gui_smoke/demo.json
```

这个入口使用明确标注的合成图片和预测检查界面；真实图片／视频检测使用上方公开的模型包和树莓派5＋HAILO10H，配置模板位于[configs/gui](configs/gui/README.md)。自动检查运行 `python scripts/check_gui.py`。

## 组员从哪里开始

1. 阅读[项目进展与待办](docs/PROJECT_STATUS.md)，了解已做工作、结论和仍需补充的内容。
2. 阅读[中文报告](docs/report/report_zh.md)；汇报与提交以[英文报告PDF](docs/report/report.pdf)为准。
3. 做PPT时使用[当前网络图](docs/report/figures/final_pconv_p2.pdf)和[实验结果导航](docs/results/README.md)。
4. 修改代码前查看[环境说明](docs/ENVIRONMENT.md)、[配置导航](configs/README.md)和[部署入口](scripts/deployment/README.md)。
5. 课堂演示使用 [PyQt6 检测工作台](docs/GUI.md)：真实实验结果回放、H10 实时检测客户端、图片／视频导出和实验结果对比。Mac 可双击 `启动检测演示.command`；真机演示使用 [启动H10实时检测.command](启动H10实时检测.command)（先安装 GUI 依赖并准备私有连接配置）。树莓派显示器演示使用 [启动树莓派本机演示.command](启动树莓派本机演示.command)，素材缓存一次、本机检测；[演示与录制说明](docs/DEMO_REHEARSAL.md)。新版为 [3分46秒英文配音演示](docs/results/GUI_NARRATED_20261116.md)，含双语字幕、操作放大和时间文字过滤，另有[原始完整录屏](docs/results/GUI_RECORDING_20261116.md)和[图片与视频H10联调](docs/results/GUI_H10_20261116.md)记录。

## 已完成什么

| 工作 | 结果与入口 |
|---|---|
| 数据整理 | SIRST-UAVB固定1999张训练／500张验证，验证集486个UAV框；[来源与标注](docs/datasets/SOURCES.md) |
| 模型比较与消融 | 主比较11个从零100轮模型，累计19个有效权重；[四类实验表](docs/results/EXPERIMENT_TABLES_20261105.md) |
| 训练比例 | 500／1000／1999张训练图，统一500张验证；[三档实测](docs/results/TRAINING_FRACTIONS_20261107.md) |
| 边缘测试 | GPU19组、Pi CPU17组、H10兼容模型7组；[设备结果](docs/results/EDGE_EXTENSION_20261104.md) |
| 后处理改进 | NMS IoU0.4使H10误报119→62，检出323、漏检163不变；[审计与硬件实测](docs/results/NMS_VLM_AUDIT_20261115.md) |
| VLM候选复核 | Qwen2.5-VL-3B-Instruct的E0—E4共689条响应；[结果](docs/results/NMS_VLM_AUDIT_20261115.md)未优于相同召回率下的置信度阈值对照 |
| 报告与图表 | [10页IEEE报告、中文稿及可编辑图源](docs/report/README.md) |

当前PinP2/H10默认部署的AP50:95为 **31.740%**（内部验证集），三轮阈值基准为 **22.89±0.01 FPS**；原生训练验证、FP32、无NMS和NMS后的指标分别记录。最终模型是精度、速度与边缘可行性的综合取舍。

与大数据课程的联系包括数据真实性（像素去重、标注冲突与跨源标注差异）、数据规模（三档训练量及推理负载）和处理速度（边缘吞吐与内存）。VLM是已评价的离线组件。

## 目录怎么用

| 目录 | 内容 |
|---|---|
| `src/uav_detection/` | 模型结构、训练适配、数据处理 |
| `configs/` | 当前模型与部署参数，以及有日期说明的历史实验配置 |
| `scripts/` | 数据准备、训练入口、指标复算、部署、文档构建与检查 |
| `experiments/` | NMS审计和VLM候选复核的分析代码 |
| `docs/report/` | 当前报告、图表及复现说明 |
| `docs/results/` | 当前结果入口与有来源的历史对照证据 |
| `docs/proposal/` | 已提交提案 |
| `bibliography/`、`templates/`、`third_party/` | 统一文献、原始模板及第三方来源与许可 |

## Model weights / 模型权重

最终模型（YOLO26n＋PConv＋P2，从零100轮）的权重、ONNX和H10模型通过GitHub Release提供：

| 内容 | 位置 |
|---|---|
| `best.pt`（最佳AP95第85轮，FP32）、`model.onnx`（opset17）、`model.hef`，以及结构、配置和选型记录 | [pinp2-final-model-v1.1.0](https://github.com/EmpyreanHYR/MPU-Big-Data-Project2-UAV-Detection/releases/download/pinp2-final-model-v1.1.0/pinp2-final-model-v1.1.0.zip)（含`SHA256SUMS`） |
| GUI真机包（HEF＋解码元数据，逐文件SHA256自动核验）与3分46秒演示视频 | [gui-h10-v1.0.0](https://github.com/EmpyreanHYR/MPU-Big-Data-Project2-UAV-Detection/releases/tag/gui-h10-v1.0.0) |

PyTorch检查点使用仓库[模型构建入口](src/uav_detection/architecture.py)按`best.pt`内嵌的YAML元数据重建PConv层后加载。其余18组对照与消融模型的权重、逐图预测和完整设备记录保存在项目私有结果包中，版本与哈希见[复现说明](docs/report/REPRODUCIBILITY_NOTES.md)。

## Data / 数据

原始数据从各数据集的公开发布处获取。本项目使用SIRST-UAVB（训练与内部验证）、UAV-CB thermal、Tri-Modal Anti-UAV IR和AUVD-Seg300（外部评价），以及Anti-UAV-detection（外部UAV测试）。数据来源、作者链接与获取方式见[数据来源说明](docs/datasets/SOURCES.md)，处理流程见[数据处理流程](docs/datasets/PREPARATION.md)。

## 本地检查与报告构建

使用Python3.10+，在自己的虚拟环境中执行：

```sh
python -m pip install -e '.[evaluation]'
python scripts/check_project.py
```

检查入口收集Git跟踪的全部测试，其中模型集成测试在已配置依赖的Linux x86_64环境运行。

安装pdfLaTeX和BibTeX后，可用 `python scripts/build_report.py` 编译报告；提案构建使用 `python scripts/build_proposal.py`。文献修改以 `bibliography/references.bib` 为准，同步副本后运行检查。

报告与幻灯片截止 **2026年11月29日24:00（北京时间）**，12月3日汇报，10分钟讲述＋5分钟问答。3分46秒演示视频已完成，成员贡献与反思及提交包按[当前清单](docs/report/REVIEW_CHECKLIST.md)整理；仓库维护说明见[维护记录](docs/REPOSITORY_MAINTENANCE.md)。
