#!/usr/bin/env python3
"""Download and verify the public PinP2 HAILO10H package; never load a model."""
import argparse
import hashlib
import json
from pathlib import Path
import stat
import tempfile
from urllib.request import Request, urlopen
import zipfile

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / 'configs/deployment/pinp2_h10_release.json'
POLICY = ROOT / 'configs/deployment/pinp2_h10.json'
DEFAULT_OUTPUT = ROOT / 'models/pinp2_h10'


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def verify_files(folder, manifest):
    folder = Path(folder)
    for name, expected in manifest['files'].items():
        if Path(name).name != name or name in {'.', '..'} or '\\' in name:
            raise ValueError('Unsafe package filename')
        path = folder / name
        if (not path.is_file() or path.is_symlink()
                or path.stat().st_size != expected['bytes']
                or sha256(path) != expected['sha256']):
            raise ValueError('Missing or modified package file: ' + name)


def verify_package(folder):
    manifest = json.loads(MANIFEST.read_text())
    verify_files(folder, manifest)
    policy = json.loads(POLICY.read_text())
    metadata = json.loads((Path(folder) / 'h10_metadata.json').read_text())
    if json.loads((Path(folder) / 'deployment_policy.json').read_text()) != policy:
        raise ValueError('Package policy differs from the checkout; use its matching release')
    for name in ('model_id', 'family', 'weights_sha256', 'hef_sha256'):
        if metadata[name] != policy[name]:
            raise ValueError('Model identity mismatch: ' + name)
    if sha256(Path(folder) / 'model.hef') != policy['hef_sha256']:
        raise ValueError('HEF differs from the frozen policy')
    return manifest


def install_archive(archive, output, manifest):
    archive, output = Path(archive), Path(output)
    if archive.stat().st_size != manifest['bytes'] or sha256(archive) != manifest['sha256']:
        raise ValueError('Model ZIP size/SHA256 mismatch; no files installed')
    if output.exists():
        raise FileExistsError('Output already exists: ' + str(output))
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.pinp2-extract-', dir=output.parent) as tmp:
        stage = Path(tmp) / 'model'
        stage.mkdir()
        with zipfile.ZipFile(archive) as z:
            entries = z.infolist()
            if len(entries) != len(manifest['files']) or {i.filename for i in entries} != set(manifest['files']):
                raise ValueError('Unexpected or duplicate ZIP entries')
            for item in entries:
                name = item.filename
                if (Path(name).name != name or name in {'.', '..'} or '\\' in name
                        or item.is_dir() or stat.S_ISLNK(item.external_attr >> 16)):
                    raise ValueError('Unsafe ZIP entry')
                if item.file_size != manifest['files'][name]['bytes']:
                    raise ValueError('Unexpected uncompressed file size')
                (stage / name).write_bytes(z.read(item))
        verify_files(stage, manifest)
        stage.rename(output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument('--archive', type=Path, help='Use a previously downloaded ZIP (offline)')
    parser.add_argument('--verify-only', action='store_true', help='Check installed files without network access')
    args = parser.parse_args()
    output = args.output.expanduser().resolve()
    manifest = json.loads(MANIFEST.read_text())
    if args.verify_only or output.exists():
        verify_package(output)
        print('Verified existing model / 已核验模型:', output)
        return 0
    if args.archive:
        install_archive(args.archive.expanduser(), output, manifest)
    else:
        output.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='.pinp2-download-', dir=output.parent) as tmp:
            archive = Path(tmp) / 'model.zip'
            count = 0
            request = Request(manifest['url'], headers={'User-Agent': 'PinP2-GUI-model-downloader'})
            with urlopen(request, timeout=60) as response, archive.open('xb') as stream:
                while block := response.read(1024 * 1024):
                    count += len(block)
                    if count > manifest['bytes']:
                        raise ValueError('Download exceeds the pinned package size')
                    stream.write(block)
            install_archive(archive, output, manifest)
    verify_package(output)
    print('Installed verified HAILO10H model / 模型已下载并核验:', output)
    print('Next: python3 scripts/configure_pi_gui.py --help')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
