#!/usr/bin/env python3
"""Recompute fixed-threshold detection metrics/AP from saved arrays; no model inference."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import zipfile

import numpy as np
from PIL import Image
from detection_eval import evaluate_records, sha, summarize, xywh2xyxy


def recompute(manifest_path, predictions_path, *, data_root=None, data_zip=None):
    if (data_root is None) == (data_zip is None):
        raise ValueError('Provide exactly one data root or data ZIP')
    manifest_path = Path(manifest_path)
    predictions_path = Path(predictions_path)
    manifest = json.loads(manifest_path.read_text())
    samples = manifest['images']
    archive = zipfile.ZipFile(data_zip) if data_zip is not None else None

    def read(relative):
        if archive is not None:
            return archive.read(relative)
        return (Path(data_root) / relative).read_bytes()

    records = []
    try:
        with np.load(predictions_path, allow_pickle=False) as saved:
            detections = saved['detections']
            offsets = saved['offsets']
            if saved['images'].tolist() != [row['image'] for row in samples]:
                raise ValueError('Prediction image order differs from the frozen manifest')
            if (offsets.ndim != 1 or len(offsets) != len(samples) + 1 or
                offsets.dtype.kind not in 'iu' or offsets[0] != 0 or
                offsets[-1] != len(detections) or np.any(np.diff(offsets) < 0)):
                raise ValueError('Invalid per-image prediction offsets')
            if detections.ndim != 2 or detections.shape[1] != 6 or not np.isfinite(detections).all():
                raise ValueError('Predictions must be finite Nx6 [xyxy, score, class] arrays')
            if np.any(detections[:, 5] != 0):
                raise ValueError('This protocol expects a single UAV class')
            for i, row in enumerate(samples):
                image_bytes = read(row['image'])
                label_bytes = read(row['label'])
                for kind, blob in [('image', image_bytes), ('label', label_bytes)]:
                    if hashlib.sha256(blob).hexdigest() != row[kind + '_sha256']:
                        raise ValueError(f'{kind} hash mismatch: {row[kind]}')
                with Image.open(io.BytesIO(image_bytes)) as image:
                    width, height = image.size
                boxes = []
                for line in label_bytes.decode().splitlines():
                    if not line.strip():
                        continue
                    cls, x, y, box_width, box_height = map(float, line.split())
                    if cls != 0 or box_width <= 0 or box_height <= 0:
                        raise ValueError('Invalid single-class ground-truth box')
                    boxes.append([x * width, y * height, box_width * width, box_height * height])
                ground_truth = xywh2xyxy(np.asarray(boxes, dtype=np.float32).reshape(-1, 4))
                records.append(evaluate_records(detections[offsets[i]:offsets[i + 1]], ground_truth))
    finally:
        if archive is not None:
            archive.close()
    metrics = summarize(records)
    if 'GT' in manifest and metrics['GT'] != manifest['GT']:
        raise ValueError('Ground-truth total differs from the frozen manifest')
    return {
        'kind': 'saved-prediction NumPy audit; no model inference',
        'validation_manifest_sha256': sha(manifest_path),
        'predictions_sha256': sha(predictions_path),
        'metrics': metrics,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', required=True, type=Path)
    parser.add_argument('--predictions', required=True, type=Path)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--data-root', type=Path)
    source.add_argument('--data-zip', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('Choose a new audit output; original results are preserved')
    result = recompute(args.manifest, args.predictions, data_root=args.data_root, data_zip=args.data_zip)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x') as output:
        output.write(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(result['metrics'], ensure_ascii=False))


if __name__ == '__main__':
    main()
