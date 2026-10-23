# 项目提案

英文提案入口为 [main.tex](main.tex)，正文在 [body_en.tex](body_en.tex)，编译结果为 [main.pdf](main.pdf)，便于阅读的文本在 [proposal_en.md](proposal_en.md)。对应中文保留在 [main_zh.tex](main_zh.tex)、[body_zh.tex](body_zh.tex)及[中文阅读稿](项目提案_中文版.md)。

两份入口均保留原 ZIP 的宏包、IEEEtran 类、示例作者、thanks 与页眉；只改标题、正文和文献接口。四人职责在正文中说明，模板示例作者信息按要求原样保留。

`references.bib` 从仓库统一文献库同步，使用 IEEEtran 的 BibTeX 自动编号。`proposal_content.json` 与 `proposal_content_en.json` 分别维护两种语言内容；修改时同步对应 TeX。生成脚本核对双语引用顺序一致，更新双语阅读稿、文献分析与 citation_index.json。

在仓库根目录运行 `python scripts/build_proposal.py`。随后切换到本目录，执行 `pdflatex main.tex`、`bibtex main`、`pdflatex main.tex` 两次。英文内容无需增加中文宏包。中文入口保留既有模板与编辑器的中文编译设置。
