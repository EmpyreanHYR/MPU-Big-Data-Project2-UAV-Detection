"""Render the Chinese reading copy using the actual IEEEtran BibTeX order."""
from pathlib import Path
import json
import re
import subprocess
import shutil

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / 'docs' / 'proposal'
for kind in ('proposal', 'report'):
    target = ROOT / 'docs' / kind / 'references.bib'
    target.write_bytes((ROOT / 'bibliography' / 'references.bib').read_bytes())
source = json.loads((PROJECT / 'proposal_content.json').read_text())
body = (PROJECT / 'body_zh.tex').read_text()
bib = (PROJECT / 'references.bib').read_text()
keys = re.findall(r'@\w+\{([^,]+),', bib)
calls = re.findall(r'\\cite\{([^}]+)\}', body)
used = [k.strip() for call in calls for k in call.split(',')]
assert len(keys) == len(set(keys)), 'Duplicate BibTeX keys'
assert set(used) == set(keys), 'Missing or unused bibliography entry'
aux = '\\relax\n' + ''.join('\\citation{' + c + '}\n' for c in calls)
aux += '\\bibstyle{IEEEtran}\n\\bibdata{references}\n'
(PROJECT / 'citation_check.aux').write_text(aux)
result = subprocess.run([shutil.which('bibtex') or '/Library/TeX/texbin/bibtex', 'citation_check'],
                        cwd=PROJECT, text=True, capture_output=True)
assert result.returncode == 0, result.stdout + result.stderr
assert 'Warning--' not in result.stdout, result.stdout
bbl = (PROJECT / 'citation_check.bbl').read_text()
entries = re.findall(r'\\bibitem\{([^}]+)\}\s*(.*?)(?=\\bibitem\{|\\end\{thebibliography\})',
                     bbl, re.S)
order = [k for k, _ in entries]
assert order == list(dict.fromkeys(used)), 'Order differs from first citation'
index = {key: i for i, key in enumerate(order, 1)}

def render_cites(text):
    def replace(match):
        return '[' + ', '.join(str(v) for v in sorted({index[k.strip()] for k in match[1].split(',')})) + ']'
    return re.sub(r'\\cite\{([^}]+)\}', replace, text)

def plain_reference(text):
    text = re.sub(r'\\BIBentry(?:ALT|STD)interwordspacing', '', text)
    text = re.sub(r'\\url\{([^}]+)\}', lambda m: '[在线来源](' + m[1] + ')', text)
    text = re.sub(r'\\emph\{([^}]+)\}', lambda m: '*' + m[1] + '*', text)
    text = text.replace('{', '').replace('}', '').replace('~', ' ')
    text = text.replace('``', '“').replace("''", '”').replace('--', '–')
    return re.sub(r'\s+', ' ', text).strip()

md = '# ' + source['title'] + '\n\n'
md += '**《大数据概论》小组项目提案 · 中文版 V4.0**  \n'
md += '小组成员：成员甲、成员乙、成员丙、成员丁  \n日期：2026年10月23日\n\n'
md += '## 摘要\n\n' + source['abstract'] + '\n\n'
for section in source['sections']:
    md += '## ' + section['title'] + '\n\n'
    md += '\n\n'.join(render_cites(x) for x in section['paragraphs']) + '\n\n'
md += '## 参考文献\n\n'
md += '\n\n'.join('[' + str(index[k]) + '] ' + plain_reference(v) for k, v in entries) + '\n'
(PROJECT / '项目提案_中文版.md').write_text(md)
(PROJECT / 'citation_index.json').write_text(json.dumps(index, ensure_ascii=False, indent=2) + '\n')
# The literature reading copy is prose and shares the bibliography's generated index.
lit = '# YOLO26 红外小目标检测：文献分析\n\n'
lit += '\n\n'.join(render_cites(x) for x in source['sections'][0]['paragraphs'])
lit += '\n\n参考条目与编号见[中文提案](../proposal/项目提案_中文版.md)；引用源为 '
lit += '[references.bib](../../bibliography/references.bib)。\n'
(ROOT / 'docs/research/literature_review_zh.md').write_text(lit)
print(json.dumps({'entries': len(index), 'body_citation_calls': len(calls),
                  'missing_keys': [], 'unused_keys': [],
                  'BibTeX_warnings': [], 'order': index}, ensure_ascii=False))
