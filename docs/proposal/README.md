# 项目提案

当前中文提案采用 YOLO26n，分别考察浅层 PConv 与 P2 分支。`main.tex` 与原 ZIP 模板在标题以外的前导、宏包、示例作者及页眉上保持一致；正文位于 `body_zh.tex`。

`references.bib` 从仓库 `bibliography/references.bib` 同步。`python scripts/build_proposal.py` 调用 BibTeX，按正文首次引用生成编号并更新中文阅读稿和文献分析。`proposal_content.json` 用于更新阅读稿，正文变更时保持其段落与 TeX 正文一致。
