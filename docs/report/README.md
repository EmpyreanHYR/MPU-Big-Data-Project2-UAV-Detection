# 当前结项报告

| 材料 | 用途 |
|---|---|
| [英文PDF](report.pdf) | 当前10页A4 IEEE报告，用于阅读和提交核对 |
| [LaTeX正文](report.tex)、[参考文献](references.bib) | 正式报告维护源；文献主本在 `bibliography/references.bib` |
| [中文对应稿](report_zh.md) | 组员理解方法、结果和准备讲稿 |
| [复现说明](REPRODUCIBILITY_NOTES.md) | 原生／部署评价口径、四源外部结果及公开材料的复现范围 |
| [核查清单](REVIEW_CHECKLIST.md) | 课程要求对应的材料、提案与实际工作的差异及剩余事项 |

当前稿包含26个公式、8张表、4幅图和24条参考文献。

2026年11月16日核查：现有源文件在临时目录完整编译为10页A4，无未定义引用或排版溢出；8张表与保存结果一致。最新GUI、时间文字过滤及外部素材定位诊断见[结果导航](../results/README.md)。

## 图表怎么取用

| 图 | 内容 | 文件 |
|---|---|---|
| 图1 | 实际30模块网络、39条主连接，合入PConv与P2细节；第2页 | [PDF](figures/final_pconv_p2.pdf) · [PNG](figures/final_pconv_p2.png) · [draw.io](figures/final_pconv_p2.drawio) |
| 图2 | 4张训练图与标注 | [PDF](figures/training_examples.pdf) · [PNG](figures/training_examples.png) |
| 图3 | 同图四配置保存的预测框 | [PDF](figures/qualitative_comparison.pdf) · [PNG](figures/qualitative_comparison.png) |
| 图4 | 同一验证图的无NMS及不同IoU检测框 | [PDF](figures/nms_same_image.pdf) · [PNG](figures/nms_same_image.png) · [来源](figures/nms_same_image.provenance.json) |

[模块可编辑源](figures/pinp2_modules.drawio)用于维护作图1的素材；独立模块图导出已并入图1。[NMS统计图](figures/nms_selection.pdf)及[来源](figures/nms_selection.provenance.json)是结果分析的补充材料，不是报告图4。

四类实验和设备指标见[结果导航](../results/README.md)。历史无NMS结果与当前NMS0.4部署分开呈现。外部评价正文聚焦AUVD-Seg300案例，其余三源结果保留在复现说明中。

## 修改与构建

仅更新说明文档时，执行 `python scripts/check_repository.py` 和 `python scripts/check_references.py` 检查模板、引用及本地链接即可。检查记录见[REPOSITORY_CHECKS.json](../REPOSITORY_CHECKS.json)。

修改提交稿时，维护 `report.tex` 并同步中文稿，再使用 `python scripts/build_report.py` 编译PDF；该命令会替换正式PDF，需要pdfLaTeX和BibTeX，并检查未定义引用、排版溢出与10页上限。涉及代码修改时按范围运行 `python scripts/check_project.py`。

原始IEEE模板与[原件](../../templates/ieee/README.md)保持一致，提案与报告作者信息一致。编辑图时保留draw.io源并更新相关导出；实验数值从结果表核对。

最新正文范围：外部实验仅保留AUVD-Seg300的设置、结果及单一来源验证限制；中英文均已移除四源比较、其他测试结果及正文中的补充结果指引。历史原始实验记录未改动。
