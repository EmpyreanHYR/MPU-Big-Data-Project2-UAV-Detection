#!/usr/bin/env python3
"""Compile the IEEE report with BibTeX in a temporary directory."""
from pathlib import Path
import shutil
import subprocess
import tempfile

from build_proposal import executable

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / 'docs/report'


def main():
    canonical = ROOT / 'bibliography/references.bib'
    if (PROJECT / 'references.bib').read_bytes() != canonical.read_bytes():
        shutil.copy2(canonical, PROJECT / 'references.bib')
    with tempfile.TemporaryDirectory(prefix='uav-report-build-') as temporary:
        work = Path(temporary)
        for name in ('report.tex', 'IEEEtran.cls', 'references.bib'):
            shutil.copy2(PROJECT / name, work / name)
        shutil.copytree(PROJECT / 'figures', work / 'figures')
        latex = [executable('pdflatex'), '-interaction=nonstopmode',
                 '-halt-on-error', 'report.tex']
        for command in (latex, [executable('bibtex'), 'report'], latex, latex):
            result = subprocess.run(command, cwd=work, capture_output=True, text=True)
            if result.returncode:
                raise RuntimeError(result.stdout + result.stderr)
            if command[0] == executable('bibtex') and 'Warning--' in result.stdout:
                raise RuntimeError(result.stdout)
        log = (work / 'report.log').read_text()
        if 'undefined' in log or 'Overfull' in log:
            raise RuntimeError('Unresolved references or overflowing text:\n' + log)
        pending = PROJECT / 'report.pdf.tmp'
        shutil.copy2(work / 'report.pdf', pending)
        pending.replace(PROJECT / 'report.pdf')
    print('PASS: report.pdf compiled with BibTeX; no undefined references or overflowing text')


if __name__ == '__main__':
    main()
