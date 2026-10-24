# MPU Big Data Project 2 · YOLO26 红外无人机检测

本仓库是后续开发的统一维护入口，管理模型代码、配置、数据来源、项目提案、报告与汇报材料。项目以 YOLO26n 为基线，研究浅层 PConv 和高分辨率 P2 分支在红外小目标无人机检测中的作用。

## 内容导航

| 内容 | 位置 | 当前状态 |
|---|---|---|
| 模型构建与训练入口 | [src/uav_detection](src/uav_detection/) / [scripts](scripts/) | 三种结构、训练器重建及检查点恢复检查通过 |
| 实验与数据配置 | [configs](configs/) | 三份实验配置、原始清单和类别映射示例 |
| 数据集来源与标注 | [SOURCES.md](docs/datasets/SOURCES.md) | 主数据及补充数据说明 |
| 提案 | [TeX](docs/proposal/proposal.tex) / [PDF](docs/proposal/proposal.pdf) / [中文阅读稿](docs/proposal/proposal_zh.md) | 英文 PDF 2 页 |
| 报告 | [TeX](docs/report/report.tex) / [说明](docs/report/README.md) | 已建立章节框架 |
| PPT | [大纲](docs/slides/outline_zh.md) | 已建立目录与汇报大纲 |
| 参考文献 | [references.bib](bibliography/references.bib) | 统一 BibTeX 文献源 |
| 原始 IEEE 模板 | [压缩包](templates/ieee/source.zip) / [说明](templates/ieee/README.md) | 原件及六个成员完整保留 |

## 目录结构

```text
src/uav_detection/       模型构建、训练配置与训练入口逻辑
configs/                数据集、模型和实验配置
scripts/                构建、训练与仓库检查
bibliography/           统一 BibTeX 文献源
docs/proposal/          proposal.tex、proposal.pdf 和中文阅读稿
docs/report/            report.tex 报告框架
docs/slides/            PPT、讲稿和展示材料
docs/research/          段落式文献分析
docs/datasets/          数据来源、标注约定与元数据
templates/ieee/         原始 ZIP、完整解压模板与哈希清单
tests/                  模型结构、数据处理与训练运行条件检查
data/                   本地数据，Git 忽略
models/                 本地权重和导出模型，Git 忽略
outputs/                本地实验输出，Git 忽略
```

## 模型代码

Python 3.10+。模型可选依赖固定为 `ultralytics==8.4.184`，版本信息来自 PyPI；执行环境的 PyTorch/CUDA 版本随云端环境记录。

```sh
python -m pip install -e '.[model]'
python scripts/build_model.py --help
python scripts/train.py --help
```

`scripts/build_model.py --variant baseline|pconv|p2` 构建相应结构，可用 `--weights` 读取本地权重。三份实验配置分别为 `configs/experiments/yolo26n_baseline.json`、`yolo26n_pconv.json`、`yolo26n_p2.json`。具体结构和公共前缀权重迁移策略见 [模型说明](configs/models/README.md)。

SIRST-UAVB 通过显式原始清单、来源组和类别映射处理，支持 YOLO/VOC 框、UAV/bird 分离与跨划分重复检查，见 [数据处理流程](docs/datasets/PREPARATION.md)。实际数据尚未取得。

训练入口要求 Linux x86_64、单张 RTX 2080 Ti、通过审计的数据、本地权重、带时区的截止时间和最多8小时的单次窗口。Mac和树莓派不进行训练。以下仅供后续云端执行，本次未启动：

```sh
python scripts/train.py --config configs/experiments/yolo26n_baseline.json \
  --data data/sirst-uavb/prepared/dataset.yaml --weights models/yolo26n.pt \
  --output outputs/baseline-seed42 --deadline 2026-10-25T02:25:00+08:00 --max-hours 8
```

训练操作按已有授权预算和截止安排；平台强停与训练后关机由云端运行管理流程负责。当前仓库整理没有启动训练。当前进度与下一步见 [PROJECT_STATUS.md](docs/PROJECT_STATUS.md)。

## 提案、报告与引用

提案和报告均从用户提供 ZIP 中的 `bare_jrnl_new_sample4.tex` 建立。标题、正文和文献接口按项目填写；宏包、IEEEtran 文档类和页眉保持原样；提案与报告使用相同的四位成员姓名和学校信息。每个文档目录可以独立用 LaTeX 编辑器打开；正文直接写在对应的 `proposal.tex` 或 `report.tex` 中。

文献采用 `\cite{key}` 与 `\bibliography{references}`。修改统一文献库后执行：

```sh
python scripts/build_proposal.py
python scripts/check_references.py
python scripts/check_repository.py
python -m unittest discover -s tests -v
```

提案构建使用 pdflatex、BibTeX 与 IEEEtran.bst；中间文件在临时目录生成，文档目录只保留源码和最终 PDF。文档检查不导入模型；完整测试使用 model/data 可选依赖，进行 CPU 随机权重前向、训练器构建/恢复及合成数据检查，不调用训练循环或下载权重。结构检查可通过 `python scripts/verify_models.py --output docs/checks/model_smoke_20261023.json` 记录。

本地设备、云端账号及运行记录由 `.gitignore` 排除，公开仓库保留模型、数据处理代码和课程文稿。
