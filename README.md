# MPU Big Data Project 2 · YOLO26红外无人机检测

最终模型为**PinP2-YOLO（从零初始化100轮）**，部署于树莓派5＋HAILO10H。H10实测部署AP50–95为24.351%、漏检率33.539%、含前后处理22.72FPS，参数量2.516M。

| 内容 | 当前文件 |
|---|---|
| 模型配置与实验协议 | [配置导航](configs/README.md) · [实验说明](docs/experiments/README.md) |
| 最终模型规模与错误分析 | [125／250／500张H10实测与分组结果](docs/results/FINAL_MODEL_SCALING_ERRORS_20261105.md) |
| 实验分组表格 | [对比／消融／训练比例／边缘部署](docs/results/EXPERIMENT_TABLES_20261105.md) · [细项CSV](docs/results/EDGE_EXTENSION_20261104.csv) · [缺项说明](docs/results/EDGE_EXTENSION_20261104.md) |
| 最终选型 | [依据与限制](docs/results/FINAL_SELECTION_PCONV_P2_20261104.md) |
| 实际网络结构 | [PNG](docs/results/figures/final_pconv_p2_20261104.png) · [draw.io](docs/results/figures/final_pconv_p2_20261104.drawio) · [SVG](docs/results/figures/final_pconv_p2_20261104.svg) |
| 项目状态 | [PROJECT_STATUS.md](docs/PROJECT_STATUS.md) |
| 评价与边缘推理程序 | [使用说明](scripts/evaluation/README.md) · [部署说明](docs/deployment/README.md) |
| 数据来源与整理 | [来源](docs/datasets/SOURCES.md) · [处理流程](docs/datasets/PREPARATION.md) |
| 已提交阶段的提案 | [PDF](docs/proposal/proposal.pdf) · [TeX](docs/proposal/proposal.tex) · [中文稿](docs/proposal/proposal_zh.md) |
| 模型、数据和实验代码 | [src](src/uav_detection/) · [scripts](scripts/) · [configs](configs/) |
| 文献与原始模板 | [BibTeX](bibliography/references.bib) · [IEEE原件](templates/ieee/README.md) |

SIRST-UAVB固定1999张训练、500张验证图像，验证集有486个无人机框。当前主要比较11个从零100轮模型；累计保留17组有效训练、GPU和Pi CPU各17组500图推理，以及60组四源外部评价和三段既有视频演示。7个兼容模型均完成H10真实500图；SIA、SIA＋CSP、MSF和RT-DETR保留当前导出兼容性缺口。

原生训练验证AP与共同部署AP分别报告。H10使用实际量化模型重新评价，不继承FP32精度。最终模型是精度、漏检、参数量和速度的综合取舍；YOLO11n的H10 AP更高、YOLOv8n漏检更低的事实保留。

新增训练数据比例实验按25%／50%／100%（500／1000／1999训练图）分别评价，固定使用同500张验证图。100%结果已核验可复用，25%和50%新训练尚未启动，表内明确NR；原125／250／500张H10实验属于推理负载补充。

仓库保留当前模型代码、实验配置、适配器来源、数据协议和有效实验记录。原始数据、权重、ONNX/HEF与完整结果包保存在本地项目结果目录，受Git忽略规则保护。Mac只用于文件、文稿和NumPy指标整理；整理操作不运行训练或模型推理。

代码及数据检查：

```sh
python scripts/check_repository.py
python -m unittest discover -s tests -v
```

数据与评价检查使用Pillow/NumPy即可运行。模型集成测试仅在具备依赖的Linux x86_64环境执行，Mac和Pi跳过，不加载模型。边缘推理程序须在对应设备安装运行时，具体参数见其说明。

课程报告仍在完善，本次仓库整理与更新不包含报告正文、报告PDF、专用图表、文献或构建脚本的改动。仓库已有的阶段文稿保留原版本，不作为当前完成稿。
