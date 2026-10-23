#!/usr/bin/env python3
"""Validate ZIP provenance, protected template content and local document links."""
from pathlib import Path
import hashlib
import json
import re
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def normalized_prefix(text):
    prefix = text.split("\\maketitle", 1)[0] + "\\maketitle"
    return re.sub(r"\\title\{.*?\}\n", "TITLE\n", prefix, count=1, flags=re.S)


def main():
    folder = ROOT / "templates/ieee"
    manifest = json.loads((folder / "manifest.json").read_text())
    archive = folder / manifest["source_archive"]
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == manifest["archive_sha256"]
    with zipfile.ZipFile(archive) as z:
        for name, digest in manifest["members"].items():
            original = z.read(name)
            assert hashlib.sha256(original).hexdigest() == digest
            assert (folder / "original" / name).read_bytes() == original
        expected = normalized_prefix(z.read("bare_jrnl_new_sample4.tex").decode())
        for kind in ("proposal", "report"):
            doc = ROOT / "docs" / kind
            assert normalized_prefix((doc / "main.tex").read_text()) == expected, kind
            assert (doc / "IEEEtran.cls").read_bytes() == z.read("IEEEtran.cls")
        assert normalized_prefix((ROOT / "docs/proposal/main_zh.tex").read_text()) == expected
    for item in json.loads((ROOT / "third_party/sources.json").read_text()):
        assert hashlib.sha256((ROOT / "third_party" / item["file"]).read_bytes()).hexdigest() == item["sha256"]
    missing = []
    # Respect .gitignore: installed environments and local data are not project docs.
    paths = subprocess.check_output(["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], cwd=ROOT).decode().split("\0")
    for name in sorted(set(paths)):
        if not name.endswith(".md"):
            continue
        md = ROOT / name
        for link in re.findall(r"\]\(([^)]+)\)", md.read_text()):
            if "://" in link or link.startswith("#"):
                continue
            local = link.split("#", 1)[0]
            if local and not (md.parent / local).exists():
                missing.append((str(md.relative_to(ROOT)), link))
    assert not missing, missing
    print("PASS: original ZIP and six members; protected English/Chinese proposal and report templates; source hashes; Markdown links")


if __name__ == "__main__":
    main()
