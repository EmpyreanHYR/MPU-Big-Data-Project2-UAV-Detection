# 课程报告

[report.tex](report.tex) 为英文报告源码，[report.pdf](report.pdf) 为两页编译结果。2026-10-28更新已合并真实数据审计、B0/B1历史观测、早期EMA的AMP/FP32回放、FP32验证恢复及P2的92轮结束结果。P2全程CSV有限，最终AP50/AP50:95为47.405%/20.652%，未超过B0独立FP32复验；报告明确披露best选择精度和验证路径差异，不宣称结构收益。

历史指标与新的FP32训练验证路径复验分别列于表II、III；原B0/B1的7轮/11轮NaN记录保持，具体内部算子尚未逐一定位。详细来源见[基线实测](../results/yolo26n_baseline_20261025.md)、[PConv实测](../results/yolo26n_pconv_20261026.md)、[数值回放](../results/numerical_replay_20261028.md)及[P2实测](../results/yolo26n_p2_fp32_20261028.md)。原B0验证AP曲线保留。

运行 `python scripts/build_report.py`，使用临时目录执行pdflatex、BibTeX和两次引用解析，不在本目录遗留编译中间文件。文献来自统一的 `bibliography/references.bib`，使用 `\cite{key}` 自动编号。

原IEEE模板的宏包、文档类、格式与页眉保持，作者及学校与提案一致；两页PDF已逐页视觉检查。H10部署、真实视频速度及鸟类误报和目标尺寸分组分析仍待实测，报告据实区分已完成与后续工作。
