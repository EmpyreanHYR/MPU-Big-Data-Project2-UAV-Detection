#!/usr/bin/env python3
"""Recreate MSF overrides without modifying the verified base runtime."""
import argparse
import json
from pathlib import Path
import platform
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--uv", type=Path, required=True)
    parser.add_argument("--base-python", type=Path, required=True)
    parser.add_argument("--venv", type=Path, required=True)
    parser.add_argument("--index-url", default="https://pypi.org/simple")
    args = parser.parse_args()
    if platform.system() != "Linux" or platform.machine().lower() not in {"x86_64", "amd64"}:
        raise RuntimeError("Cloud only")
    if args.venv.exists():
        raise FileExistsError("Choose a new environment; never overwrite the active runtime")
    subprocess.run([str(args.uv), "venv", "--system-site-packages", "--python", str(args.base_python), str(args.venv)], check=True)
    python = args.venv / "bin/python"
    query = 'import sysconfig; print(sysconfig.get_path("purelib"))'
    base_site = subprocess.check_output([str(args.base_python), "-c", query], text=True).strip()
    own_site = subprocess.check_output([str(python), "-c", query], text=True).strip()
    (Path(own_site) / "verified-base-runtime.pth").write_text(base_site + "\n")
    requirements = Path(__file__).resolve().parents[1] / "configs/environments/msf-adapter-extra.txt"
    subprocess.run([str(args.uv), "pip", "install", "--python", str(python), "--index-url", args.index_url,
                    "--no-deps", "-r", str(requirements)], check=True)
    # Real-data autoanchor imports SciPy lazily; synthetic model checks miss it.
    subprocess.run([str(python), "-c",
                    "import scipy; from scipy.cluster.vq import kmeans; assert scipy.__version__ == '1.11.4'"], check=True)
    frozen = subprocess.check_output([str(args.uv), "pip", "freeze", "--python", str(python)], text=True)
    (args.venv / "verified-freeze.txt").write_text(frozen)


if __name__ == "__main__":
    main()
