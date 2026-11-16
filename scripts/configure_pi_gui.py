#!/usr/bin/env python3
"""Write a private native-GUI configuration using the verified public model."""
import argparse
import json
from pathlib import Path
from download_gui_model import ROOT, DEFAULT_OUTPUT, verify_package


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True, help='Actual image or video on the Pi')
    parser.add_argument('--model-dir', type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument('--shared-lock', type=Path, required=True)
    parser.add_argument('--additional-lock', type=Path, required=True)
    parser.add_argument('--kind', choices=['image', 'video'], help='Normally inferred from the extension')
    parser.add_argument('--loop', action='store_true', help='Repeat a video until stopped or timed out')
    parser.add_argument('--output', type=Path, default=ROOT / 'outputs/gui_pi_local.json')
    args = parser.parse_args()
    model, source = (p.expanduser().resolve() for p in (args.model_dir, args.source))
    verify_package(model)
    if not source.is_file():
        parser.error('Source file does not exist')
    images = {'.png', '.jpg', '.jpeg', '.bmp', '.tif', '.tiff', '.webp'}
    videos = {'.mp4', '.avi', '.mov', '.mkv', '.m4v', '.webm'}
    kind = args.kind or ('image' if source.suffix.lower() in images else
                         'video' if source.suffix.lower() in videos else None)
    if kind is None:
        parser.error('Unknown extension; choose --kind image or --kind video')
    locks = [p.expanduser().resolve() for p in (args.shared_lock, args.additional_lock)]
    if len(set(locks)) != 2 or not all(p.parent.is_dir() for p in locks):
        parser.error('Use two distinct shared lock paths with existing parent directories')
    config = {'backend': 'local', 'kind': kind, 'source': str(source), 'labels': '',
              'local_model_dir': str(model), 'local_locks': [str(p) for p in locks],
              'confidence': .25, 'display_fps': 30, 'max_seconds': 1800,
              'loop_video': bool(args.loop and kind == 'video'),
              'output_root': str(ROOT / 'outputs/gui'), 'save_images': False,
              'save_video': False, 'timestamp_filter': False, 'timestamp_profiles': {}}
    output = args.output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(config, ensure_ascii=False, indent=2) + '\n')
    print('Private config / 本机配置:', output)
    print('From a Pi desktop terminal: python3 scripts/run_pi_gui.py --config', output, '--fullscreen')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
