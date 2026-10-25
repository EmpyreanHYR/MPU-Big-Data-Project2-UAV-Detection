# 课程报告

[report.tex](report.tex) 为英文报告源码，[report.pdf](report.pdf) 为编译结果。正文已更新真实SIRST-UAVB数据审计、YOLO26n训练设置、最终验证表和AP曲线；中文结果与权重核验范围见[基线实测记录](../results/yolo26n_baseline_20261025.md)。

运行 `python scripts/build_report.py`，使用临时目录执行pdflatex、BibTeX和两次引用解析，不在本目录遗留编译中间文件。文献来自统一的 `bibliography/references.bib`，使用 `\cite{key}` 自动编号。

原IEEE模板的宏包、文档类、格式与页眉保持，作者及学校与提案一致。PConv/P2训练对照、H10部署和真实视频速度仍待实测，报告据实区分已完成与后续实验。
