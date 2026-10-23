# 课程报告

`main.tex` 从 `templates/ieee/source.zip` 的 IEEE 模板建立，保留前导、宏包、文档类、示例作者、thanks 和页眉。`body_zh.tex` 为报告章节框架；实验设置、结果、部署和结论随实测记录补充。

正文使用 `\cite{key}`，文献库从仓库 `bibliography/references.bib` 同步。修改正文后可用应用内 LaTeX 编辑器编译；引用检查执行 `python scripts/check_references.py`。
