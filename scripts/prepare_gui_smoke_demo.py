#!/usr/bin/env python3
"""Generate an explicitly synthetic GUI fixture; no dataset or detector required."""
import argparse
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from PIL import Image, ImageDraw
from uav_detection.gui.core import digest


def prepare(output):
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    images, labels = output / 'images', output / 'labels'
    images.mkdir()
    labels.mkdir()
    rows, image_hashes, label_hashes = [], {}, {}
    for i in range(12):
        name = f'{i:02d}.png'
        image = Image.new('RGB', (640, 360), (17, 28, 40))
        draw = ImageDraw.Draw(image)
        draw.text((12, 10), 'SYNTHETIC GUI FIXTURE - NOT MODEL INFERENCE', fill='white')
        draw.text((12, 32), '00:00:00 TEST TIMESTAMP', fill='white')
        draw.text((12, 330), f'Frame {i + 1}/12 - generated shapes and predictions', fill='white')
        x, y = 90 + i * 28, 140 + (i % 3) * 20
        draw.rectangle((x, y, x + 24, y + 16), fill=(220, 230, 240))
        image.save(images / name)
        boxes = [[x, y, x + 24, y + 16, .9, 0]]
        if i == 0:
            boxes.append([12, 30, 142, 45, .6, 0])
        rows.append({'image': name, 'boxes_xyxy_score_class': boxes})
        label = labels / f'{i:02d}.txt'
        label.write_text(f'0 {(x+12)/640:.10f} {(y+8)/360:.10f} {24/640:.10f} {16/360:.10f}\n')
        image_hashes[name], label_hashes[name] = digest(images / name), digest(label)
    (output / 'detections.jsonl').write_text(''.join(json.dumps(row) + '\n' for row in rows))
    metadata = {'model_id': 'SYNTHETIC_GUI_FIXTURE_NOT_MODEL_OUTPUT',
                'synthetic_fixture': True, 'confidence_floor': .25,
                'provenance': 'Generated shapes and manually specified boxes; no inference or experimental evidence.',
                'image_hashes': image_hashes, 'label_hashes': label_hashes}
    (output / 'detections.meta.json').write_text(json.dumps(metadata, indent=2))
    # Relative to the checkout, as with the documented GUI launch commands.
    # Regenerating is unnecessary when the whole checkout is moved together.
    def relative(path):
        try:
            return Path(os.path.relpath(path, ROOT)).as_posix()
        except ValueError:  # Windows: output explicitly selected on another drive.
            return str(path)
    config = {'backend': 'replay', 'kind': 'folder',
              'source': relative(images), 'labels': relative(labels),
              'predictions': relative(output / 'detections.jsonl'),
              'output_root': relative(output / 'results'), 'confidence': .25,
              'display_fps': 2, 'max_seconds': 60, 'save_images': False,
              'save_video': False, 'timestamp_filter': False}
    (output / 'demo.json').write_text(json.dumps(config, indent=2))
    filtered = {**config, 'kind': 'image', 'source': relative(images / '00.png'),
                'timestamp_filter': True,
                'timestamp_profiles': {image_hashes['00.png']: {
                    'name': 'SYNTHETIC FIXTURE ONLY', 'size': [640, 360],
                    'region': [8, 28, 210, 48], 'coverage': .5}}}
    (output / 'timestamp_demo.json').write_text(json.dumps(filtered, indent=2))
    return config


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'outputs/gui_smoke')
    args = parser.parse_args()
    prepare(args.output)
    print(f'Created 12 SYNTHETIC fixtures (not model results): {args.output}')
    print(f'From the repository root: python scripts/run_gui.py --config {args.output}/demo.json')


if __name__ == '__main__':
    main()
