#!/usr/bin/env python3
"""Plot one verified validation image with frozen H10 detections at several NMS IoUs."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import sys
import zipfile

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'experiments/pinp2_vlm'))
from common import load_predictions, match
from detection_eval import nms, iou


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--images-zip', type=Path, required=True)
    p.add_argument('--annotations', type=Path, required=True)
    p.add_argument('--predictions', type=Path, required=True)
    p.add_argument('--output', type=Path, default=ROOT / 'docs/report/figures')
    a = p.parse_args()
    name = 'images/val/sirst__2859.jpg'
    annotation = next(r for r in json.loads(a.annotations.read_text()) if r['image'] == name)
    with zipfile.ZipFile(a.images_zip) as z:
        members = [n for n in z.namelist() if n.endswith(name)]
        assert len(members) == 1
        data = z.read(members[0])
    assert hashlib.sha256(data).hexdigest() == annotation['image_sha256']
    pixels = np.asarray(Image.open(io.BytesIO(data)).convert('RGB'))
    predictions = load_predictions(a.predictions)[name]
    predictions = predictions[predictions[:, 4] >= .25]
    assert len(predictions) == 2
    gt = np.asarray(annotation['UAV_boxes'], dtype=np.float32).reshape(-1, 4)
    bounds = [269, 233, 317, 265]  # One identical 48x32-original-pixel crop.
    x1, y1, x2, y2 = bounds
    assert np.all(predictions[:, 0] >= x1) and np.all(predictions[:, 2] <= x2)
    assert np.all(predictions[:, 1] >= y1) and np.all(predictions[:, 3] <= y2)
    crop = pixels[y1:y2, x1:x2]
    variants = [None, .3, .4, .5, .7]
    colors = ['#FFB000', '#FF6048']
    panels = []
    with plt.rc_context({'font.family': 'DejaVu Sans', 'font.size': 9,
                         'pdf.fonttype': 42, 'svg.fonttype': 'none'}):
        fig, axes = plt.subplots(2, 3, figsize=(7, 3.2))
        fig.subplots_adjust(left=.015, right=.985, bottom=.015, top=.92,
                            wspace=.10, hspace=.29)
        ax = axes.flat[0]
        ax.imshow(pixels, interpolation='nearest')
        ax.add_patch(Rectangle((x1, y1), x2-x1, y2-y1, fill=False,
                               edgecolor='white', linewidth=1.1))
        ax.set_title('(a) Original image', fontsize=10, pad=5)
        ax.set_axis_off()
        for ax, threshold, letter in zip(list(axes.flat)[1:], variants, 'bcdef'):
            keep = np.arange(len(predictions)) if threshold is None else nms(
                predictions[:, :4], predictions[:, 4], threshold)
            retained = predictions[keep]
            assert len(retained) == (1 if threshold in [.3, .4] else 2)
            ax.imshow(crop, extent=(x1, x2, y2, y1), interpolation='nearest')
            for box in gt:
                ax.add_patch(Rectangle(box[:2], box[2]-box[0], box[3]-box[1],
                                      fill=False, edgecolor='#00C7FF', linestyle='--',
                                      linewidth=1.05, zorder=3))
            for j in keep:
                box = predictions[j]
                ax.add_patch(Rectangle(box[:2], box[2]-box[0], box[3]-box[1],
                                      fill=False, edgecolor=colors[j], linewidth=1.15,
                                      zorder=4))
                label_y = box[3]+1.4 if j == 0 else box[1]-1.4
                ax.text(box[0], label_y, f'{box[4]:.3f}', color=colors[j], fontsize=8.5,
                        va='top' if j == 0 else 'bottom',
                        bbox={'facecolor': '#111111', 'edgecolor': 'none',
                              'alpha': .85, 'pad': 1}, zorder=5)
            title = 'No NMS' if threshold is None else f'IoU = {threshold:.1f}'
            if threshold == .4:
                title += ' (default)'
            ax.set_title(f'({letter}) {title}', fontsize=10, pad=5,
                         fontweight='bold' if threshold == .4 else 'normal')
            ax.set_xlim(x1, x2); ax.set_ylim(y2, y1); ax.set_axis_off()
            tp = int(match(retained, gt)[:, 0].sum())
            panels.append({'nms_iou': threshold, 'kept_source_indices': keep.tolist(),
                           'boxes_xyxy_score_class': retained.tolist(),
                           'TP': tp, 'FP': len(retained)-tp, 'FN': len(gt)-tp})
        a.output.mkdir(parents=True, exist_ok=True)
        for ext in ['pdf', 'png', 'svg']:
            fig.savefig(a.output / f'nms_same_image.{ext}', dpi=300, facecolor='white')
        plt.close(fig)
    provenance = {
        'image': name, 'image_sha256': annotation['image_sha256'],
        'annotations_sha256': sha(a.annotations), 'predictions_sha256': sha(a.predictions),
        'script_sha256': sha(__file__), 'crop_xyxy': bounds, 'confidence': .25,
        'source_prediction_pair_IoU': float(iou(predictions[:1, :4], predictions[1:, :4])[0, 0]),
        'UAV_boxes': gt.tolist(), 'panels': panels,
        'selection': 'The only validation image whose retained count differs between IoU0.4 and0.5; selected to illustrate the decision boundary, not as a representative accuracy sample.',
        'image_processing': 'Original RGB pixels and aspect ratios; identical48x32 crops; nearest-neighbor display; no intensity/contrast edits, no synthetic predictions.',
        'display': 'No footer. Orange/red solid boxes retain source score identity; cyan dashed box is UAV ground truth. Original-image white rectangle marks the crop.',
        'outputs': {f'nms_same_image.{ext}': sha(a.output / f'nms_same_image.{ext}') for ext in ['pdf', 'png', 'svg']}}
    (a.output / 'nms_same_image.provenance.json').write_text(json.dumps(provenance, indent=2)+'\n')
    print(json.dumps({'image': name, 'pair_IoU': provenance['source_prediction_pair_IoU'],
                      'panel_counts': [len(r['kept_source_indices']) for r in panels]}))


if __name__ == '__main__':
    main()
