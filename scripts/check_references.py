#!/usr/bin/env python3
"""Check citation keys and synchronized BibTeX databases without model imports."""
from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parents[1]


def main():
    canonical = (ROOT / "bibliography/references.bib").read_bytes()
    keys = re.findall(r"@\w+\{([^,]+),", canonical.decode())
    assert len(keys) == len(set(keys)), "Duplicate BibTeX keys"
    report = {}
    for name in ("proposal", "report"):
        folder = ROOT / "docs" / name
        assert (folder / "references.bib").read_bytes() == canonical, "Run scripts/build_proposal.py to sync bibliographies"
        text = (folder / "body_zh.tex").read_text()
        used = [k.strip() for call in re.findall(r"\\cite\{([^}]+)\}", text) for k in call.split(",")]
        missing = sorted(set(used) - set(keys))
        assert not missing, (name, missing)
        if name == "proposal":
            assert set(used) == set(keys), "Unused proposal reference"
            index = json.loads((folder / "citation_index.json").read_text())
            assert list(index) == list(dict.fromkeys(used)), "Regenerate citation index"
            english = (folder / "body_en.tex").read_text()
            en_used = [k.strip() for call in re.findall(r"\\cite\{([^}]+)\}", english) for k in call.split(",")]
            assert en_used == used, "English and Chinese citation calls differ"
            assert "\\input{body_en}" in (folder / "main.tex").read_text()
            assert "\\input{body_zh}" in (folder / "main_zh.tex").read_text()
            report["proposal_en"] = {"cited_keys": len(set(en_used)), "missing_keys": []}
        report[name] = {"cited_keys": len(set(used)), "missing_keys": missing}
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
