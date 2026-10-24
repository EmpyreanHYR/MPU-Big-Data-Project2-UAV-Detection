#!/usr/bin/env python3
"""Check citation keys and BibTeX copies against the canonical bibliography."""
from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parents[1]


def main():
    canonical = (ROOT / 'bibliography/references.bib').read_bytes()
    keys = re.findall(r'@\w+\{([^,]+),', canonical.decode())
    assert len(keys) == len(set(keys)), 'Duplicate BibTeX keys'
    report = {}
    for name in ('proposal', 'report'):
        folder = ROOT / 'docs' / name
        assert (folder / 'references.bib').read_bytes() == canonical, 'Run scripts/build_proposal.py to sync bibliographies'
        text = (folder / f'{name}.tex').read_text()
        used = [key.strip() for call in re.findall(r'\\cite\{([^}]+)\}', text)
                for key in call.split(',')]
        missing = sorted(set(used) - set(keys))
        assert not missing, (name, missing)
        if name == 'proposal':
            assert set(used) == set(keys), 'Unused proposal reference'
            assert '\\input{body_' not in text, 'Proposal must be self-contained'
        report[name] = {'cited_keys': len(set(used)), 'missing_keys': missing}
    print(json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    main()
