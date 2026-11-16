# 项目提案

- [proposal.tex](proposal.tex)：英文提案，正文直接在此编辑。
- [proposal.pdf](proposal.pdf)：两页PDF。
- [proposal_zh.md](proposal_zh.md)：中文阅读稿。

该目录保留原提案计划，不作为当前训练参数。2026年11月16日只读核查确认PDF为两页Letter（612×792 pt），而课程提案要求为A4；此差异记录在[核查清单](../report/REVIEW_CHECKLIST.md)，原提案文件保留不变。是否已经提交及获得教师批准，不能仅凭本地文件确认。

在仓库根目录运行 `python scripts/build_proposal.py`，使用临时目录编译并更新PDF，不在本目录留下中间文件。`references.bib` 从统一文献库同步，`IEEEtran.cls` 保留原模板版本。修改英文内容后同步核对中文阅读稿。

作者栏包含四位成员及澳门理工大学；文档类、宏包、纸型、页眉等模板设置保持原样。
