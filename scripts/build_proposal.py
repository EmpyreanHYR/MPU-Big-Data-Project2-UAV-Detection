#!/usr/bin/env python3
"""Compile proposal.tex without leaving LaTeX build state beside the document."""
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / 'docs/proposal'


def executable(name):
    path = shutil.which(name)
    fallback = Path('/Library/TeX/texbin') / name
    if path:
        return path
    if fallback.exists():
        return str(fallback)
    raise RuntimeError(f'{name} is required to build the proposal')


def main():
    canonical = (ROOT / 'bibliography/references.bib').read_bytes()
    for kind in ('proposal', 'report'):
        target = ROOT / 'docs' / kind / 'references.bib'
        if target.read_bytes() != canonical:
            target.write_bytes(canonical)
    with tempfile.TemporaryDirectory(prefix='uav-proposal-build-') as temporary:
        work = Path(temporary)
        for name in ('proposal.tex', 'IEEEtran.cls', 'references.bib'):
            shutil.copy2(PROJECT / name, work / name)
        latex = [executable('pdflatex'), '-interaction=nonstopmode',
                 '-halt-on-error', 'proposal.tex']
        commands = [latex, [executable('bibtex'), 'proposal'], latex, latex]
        for command in commands:
            result = subprocess.run(command, cwd=work, capture_output=True, text=True)
            if result.returncode:
                raise RuntimeError(result.stdout + result.stderr)
            if command[0] == executable('bibtex') and 'Warning--' in result.stdout:
                raise RuntimeError(result.stdout)
        log = (work / 'proposal.log').read_text()
        if 'undefined' in log or 'Overfull' in log:
            raise RuntimeError('Unresolved references or overflowing text:\n' + log)
        pages = re.search(r'Output written on proposal\.pdf \((\d+) pages?', log)
        if not pages or pages[1] != '2':
            raise RuntimeError('Proposal must remain two pages:\n' + log)
        pending = PROJECT / 'proposal.pdf.tmp'
        shutil.copy2(work / 'proposal.pdf', pending)
        pending.replace(PROJECT / 'proposal.pdf')
    print('PASS: proposal.pdf compiled, 2 pages; temporary build files removed')


if __name__ == '__main__':
    main()
