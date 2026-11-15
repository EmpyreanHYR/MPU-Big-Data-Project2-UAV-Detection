# 当前结项报告

| 材料 | 用途 |
|---|---|
| [英文PDF](report.pdf) | 当前10页A4 IEEE报告，用于阅读和提交核对 |
| [LaTeX正文](report.tex)、[参考文献](references.bib) | 正式报告维护源；文献主本在 `bibliography/references.bib` |
| [中文对应稿](report_zh.md) | 组员理解方法、结果和准备讲稿 |
| [复现说明](REPRODUCIBILITY_NOTES.md) | 原生／部署评价口径、四源外部结果及公开材料的复现范围 |
| [核查清单](REVIEW_CHECKLIST.md) | 课程要求与仍未完成的贡献、反思和附件 |

当前稿包含26个公式、8张表、4幅图和24条参考文献。贡献与个人反思仍是占位内容，不能视为已经填写完成。

## 图表怎么取用

| 图 | 内容 | 文件 |
|---|---|---|
| 图1 | 实际30模块网络、39条主连接，合入PConv与P2细节；第2页 | [PDF](figures/final_pconv_p2.pdf) · [PNG](figures/final_pconv_p2.png) · [draw.io](figures/final_pconv_p2.drawio) |
| 图2 | 4张训练图与真实标注 | [PDF](figures/training_examples.pdf) · [PNG](figures/training_examples.png) |
| 图3 | 同图四配置真实保存预测 | [PDF](figures/qualitative_comparison.pdf) · [PNG](figures/qualitative_comparison.png) |
| 图4 | 同一验证图的无NMS及不同IoU检测框 | [PDF](figures/nms_same_image.pdf) · [PNG](figures/nms_same_image.png) · [来源](figures/nms_same_image.provenance.json) |

[模块可编辑源](figures/pinp2_modules.drawio)保留作图1的维护素材；独立模块图导出已删除，避免与合并后的图1混淆。[NMS统计图](figures/nms_selection.pdf)及[来源](figures/nms_selection.provenance.json)是结果分析补充，不是报告图4。

四类实验和设备指标见[结果导航](../results/README.md)。历史无NMS结果与当前NMS0.4部署分开呈现。外部评价正文聚焦事后选出的AUVD-Seg300案例，其余三源完整结果保留在复现说明中。

## 修改与构建

修改 `report.tex`，同步中文稿；使用 `python scripts/build_report.py` 编译PDF，检查未定义引用、排版溢出与10页上限。需要pdfLaTeX和BibTeX。随后执行 `python scripts/check_project.py` 核对模板、引用、链接和公开测试。

原始IEEE模板与[原件](../../templates/ieee/README.md)保持一致，提案与报告作者信息一致。编辑图时保留draw.io源并更新相关导出；涉及实验数值时从结果表核对，不依据图片估读。
