# 仓库维护约定

本文件说明文档、结果与制品的放置方式。当前统计与仓库检查摘要见[REPOSITORY_CHECKS.json](REPOSITORY_CHECKS.json)：19个有效权重、11个scratch100主比较、GPU19组/Pi CPU17组/H10七组；视觉语言候选复核已完成，多query复核未超过纯阈值调整；GUI模型与3分46秒视频通过公开Release提供。课程材料对应关系与剩余事项见[核查清单](report/REVIEW_CHECKLIST.md)。

## 文档入口

- 根README、[项目状态](PROJECT_STATUS.md)与[当前报告](report/README.md)是组员的主要入口；进度只写在一处，其他文档链接到它。
- [实验导航](experiments/README.md)汇总实验协议和结果导航；[结果导航](results/README.md)指向最新表格、设备比较与规模／错误分析。
- 提交报告的PDF、TeX、中文稿、BibTeX、IEEE类文件与全部图表作为最终字节保留。文档检查与受保护文件哈希见[检查摘要](REPOSITORY_CHECKS.json)。

## 新增内容

- 新指标写入结果文件，注明模型、数据、初始化与评价口径，再更新结果导航。
- 报告图同时保留draw.io编辑源和实际使用的导出（如[当前报告网络图](report/figures/final_pconv_p2.pdf)、[模块编辑源](report/figures/pinp2_modules.drawio)）；同一内容只保留当前一份成品。
- 数据集元数据以当前协议为准：当前使用SIRST-UAVB，SIRST-V2等早期候选计数不再随仓库分发。
- 有效实验、失败与取消说明、可编辑图源、模型适配器、仍被脚本／测试引用的历史配置按原样保留，历史证据按日期解读。原始数据、权重、私有运行记录及模板原件保持私有。

## 变更检查

仅修改说明文件时运行：

```sh
python scripts/check_repository.py
python scripts/check_references.py
git diff --check
```

代码变更另运行适用测试；报告正文或图表需要重建时才运行 `python scripts/build_report.py`，它会替换正式PDF。

历史文件可用Git查阅，例如：

```sh
git log --oneline -- 文件路径
git show <提交>:文件路径
```

## 当前维护状态

各GitHub Actions工作流在最近一次推送（2026-11-24，尚无与本次文档修订对应的运行）均成功，运行记录可在仓库Actions页查看。

## 数据与制品

- 原始数据、PT/ONNX/HEF、本机设备路径和账号信息保存在私有存储，不进入Git；最终GUI HEF、匹配元数据与演示媒体通过Release提供，下载时用发布清单校验哈希。
- 结果文件与原始预测数组保存在Git忽略的 `outputs/` 及私有结果包中，公开文档引用其汇总值。
- PT权重、ONNX、HEF与原始预测是结果来源，继续保留。
