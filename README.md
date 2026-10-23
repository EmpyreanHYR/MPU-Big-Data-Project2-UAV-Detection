# MPU Big Data Project 2 · YOLO26 红外无人机检测

本仓库是后续开发的统一维护入口，管理模型代码、配置、数据来源、项目提案、报告与汇报材料。项目以 YOLO26n 为基线，研究浅层 PConv 和高分辨率 P2 分支在红外小目标无人机检测中的作用。

## 内容导航

| 内容 | 位置 | 当前状态 |
|---|---|---|
| 模型构建与训练入口 | [src/uav_detection](src/uav_detection/) / [scripts](scripts/) | 已建立 YOLO26n 基线入口；PConv/P2 待实现 |
| 实验与数据配置 | [configs](configs/) | 基线配置与数据路径示例 |
| 数据集来源与标注 | [SOURCES.md](docs/datasets/SOURCES.md) | 主数据及补充数据说明 |
| 中文提案 | [阅读稿](docs/proposal/项目提案_中文版.md) / [TeX](docs/proposal/main.tex) | 已迁入当前 V4 |
| 报告 | [TeX](docs/report/main.tex) / [说明](docs/report/README.md) | 已建立章节框架 |
| PPT | [大纲](docs/slides/outline_zh.md) | 已建立目录与汇报大纲 |
| 参考文献 | [references.bib](bibliography/references.bib) | 统一 BibTeX 文献源 |
| 原始 IEEE 模板 | [压缩包](templates/ieee/source.zip) / [说明](templates/ieee/README.md) | 原件及六个成员完整保留 |

## 目录结构

```text
src/uav_detection/       模型构建、训练配置与训练入口逻辑
configs/                数据集、模型和实验配置
scripts/                构建、训练、文献生成和仓库检查
bibliography/           统一 BibTeX 文献源
docs/proposal/          提案 TeX、正文、中文阅读稿
docs/report/            报告 TeX 与章节框架
docs/slides/            PPT、讲稿和展示材料
docs/research/          段落式文献分析
docs/datasets/          数据来源、标注约定与元数据
templates/ieee/         原始 ZIP、完整解压模板与哈希清单
tests/                  配置与训练运行条件检查
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

`scripts/build_model.py` 构建 YOLO26n 结构，可通过 `--weights` 读取本地权重。云端训练采用 [基线配置](configs/experiments/yolo26n_baseline.json)，数据示例复制到本地 `data/` 并设置实际路径。训练入口要求 Linux x86_64、单张 RTX 2080 Ti、本地数据与权重、带时区的截止时间和最多8小时的单次时间窗口。Mac和树莓派用于资料处理与部署，不进行模型训练。

训练操作按已有授权预算和截止安排；平台强停与训练后关机由云端运行管理流程负责。当前仓库整理没有启动训练。当前进度与下一步见 [PROJECT_STATUS.md](docs/PROJECT_STATUS.md)。

## 提案、报告与引用

提案和报告均从用户提供 ZIP 中的 `bare_jrnl_new_sample4.tex` 建立。标题、正文和文献接口按项目填写；宏包、IEEEtran 文档类、示例作者、thanks、页眉保持原样。每个文档目录可以独立用 LaTeX 编辑器打开。

文献采用 `\cite{key}` 与 `\bibliography{references}`。修改统一文献库后执行：

```sh
python scripts/build_proposal.py
python scripts/check_references.py
python scripts/check_repository.py
python -m unittest discover -s tests -v
```

生成提案阅读稿需要 BibTeX 与 IEEEtran.bst。检查脚本和单元测试不导入模型、不下载权重、不运行训练。
