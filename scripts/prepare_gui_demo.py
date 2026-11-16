#!/usr/bin/env python3
"""Build a private, hash-verified replay bundle from existing predictions and validation ZIP."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from uav_detection.gui.core import Replay, ROOT, digest, safe_child


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--predictions', type=Path, required=True)
    parser.add_argument('--data-zip', type=Path, required=True)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--output', type=Path, default=ROOT / 'outputs/gui_demo')
    parser.add_argument('--limit', type=int, default=0, help='0 means all; otherwise first N manifest entries')
    args = parser.parse_args()
    if args.limit < 0:
        parser.error('--limit must be nonnegative')
    replay = Replay(args.predictions)
    rows = json.loads(args.manifest.read_text(encoding='utf-8'))['images']
    rows = rows[:args.limit] if args.limit else rows
    if not rows or len({row['image'] for row in rows}) != len(rows):
        raise ValueError('Empty or duplicate manifest')
    # Verify every selected byte before creating the output bundle; never extractall.
    verified = []
    with zipfile.ZipFile(args.data_zip) as archive:
        for row in rows:
            if row['image'] not in replay.records:
                raise ValueError('Missing prediction: ' + row['image'])
            data = archive.read(row['image'])
            label = archive.read(row['label'])
            if hashlib.sha256(data).hexdigest() != row['image_sha256']:
                raise ValueError('Image hash mismatch: ' + row['image'])
            if hashlib.sha256(label).hexdigest() != row['label_sha256']:
                raise ValueError('Label hash mismatch: ' + row['label'])
            verified.append((row, data, label))
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    with (output / 'detections.jsonl').open('w', encoding='utf-8') as stream:
        for row, data, label in verified:
            target = safe_child(output / 'images', row['image'])
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            target = safe_child(output / 'labels', str(Path(row['image']).with_suffix('.txt')))
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(label)
            stream.write(json.dumps({'image': row['image'], 'boxes_xyxy_score_class': replay.records[row['image']].tolist()}) + '\n')
    metadata = {**replay.metadata, 'source_prediction_sha256': digest(args.predictions),
                'source_manifest_sha256': digest(args.manifest),
                'selection': 'all manifest entries' if not args.limit else f'first {args.limit} manifest entries',
                'image_hashes': {r['image']: r['image_sha256'] for r in rows},
                'label_hashes': {r['image']: r['label_sha256'] for r in rows}}
    (output / 'detections.meta.json').write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding='utf-8')
    config = {'backend': 'replay', 'kind': 'folder', 'predictions': str(output / 'detections.jsonl'),
              'source': str(output / 'images'), 'labels': str(output / 'labels'), 'confidence': .25,
              'display_fps': 2, 'output_root': str(ROOT / 'outputs/gui'), 'save_images': False, 'save_video': False}
    (output / 'demo.json').write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f'Prepared {len(rows)} verified real replay images: {output}')


if __name__ == '__main__':
    main()
