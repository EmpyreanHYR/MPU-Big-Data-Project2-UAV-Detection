"""Offline timestamp-region audit. Never loads weights or modifies source results.

Inputs: the existing NPZ prediction schema, annotation records with image/UAV_boxes,
and an explicit image -> list of timestamp xyxy rectangles JSON mapping. Empty lists
mean that the image was reviewed and has no timestamp; missing images are an error.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts/evaluation"))
from detection_eval import evaluate_records, match, summarize


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def load_predictions(path):
    with np.load(path, allow_pickle=False) as z:
        names = list(map(str, z["images"]))
        offsets, detections = z["offsets"], z["detections"]
        assert len(names) == len(set(names))
        assert len(offsets) == len(names) + 1 and offsets[0] == 0
        assert offsets[-1] == len(detections) and (np.diff(offsets) >= 0).all()
        assert detections.ndim == 2 and detections.shape[1] == 6
        assert np.isfinite(detections).all() and (detections[:, 5] == 0).all()
        assert (detections[:, 2:4] > detections[:, :2]).all()
        return {n: detections[offsets[i]:offsets[i + 1]].copy() for i, n in enumerate(names)}


def save_predictions(path, predictions):
    arrays = list(predictions.values())
    np.savez_compressed(path, images=np.asarray(list(predictions)),
                        offsets=np.r_[0, np.cumsum([len(p) for p in arrays])],
                        detections=np.concatenate(arrays, axis=0))


def overlap_fraction(boxes, regions):
    """Maximum intersection / prediction area, NOT intersection / ROI area."""
    boxes = np.asarray(boxes, dtype=np.float64).reshape(-1, 4)
    regions = np.asarray(regions, dtype=np.float64).reshape(-1, 4)
    if not len(boxes) or not len(regions):
        return np.zeros(len(boxes))
    assert np.isfinite(regions).all() and (regions[:, 2:] > regions[:, :2]).all()
    area = np.maximum(0, boxes[:, 2:] - boxes[:, :2]).prod(1)
    intersection = np.maximum(0, np.minimum(boxes[:, None, 2:], regions[None, :, 2:])
                              - np.maximum(boxes[:, None, :2], regions[None, :, :2])).prod(2)
    return (intersection / np.maximum(area[:, None], 1e-12)).max(1)


def metrics(predictions, annotations, confidence, ap_available):
    records = []
    for a in annotations:
        p = predictions[a["image"]]
        gt = np.asarray(a["UAV_boxes"], dtype=np.float32).reshape(-1, 4)
        r = evaluate_records(p, gt)
        r["correct_fixed"] = match(p[p[:, 4] >= confidence], gt)
        records.append(r)
    result = summarize(records, confidence)
    result["fixed_matching"] = "confidence filter first, then original IoU-first one-to-one matching"
    if not ap_available:
        for key in ("mAP50_deployment", "mAP50_95_deployment", "AP_by_IoU", "AP_confidence_floor"):
            result[key] = None
        result["AP_unavailable_reason"] = "Only fixed-threshold GUI predictions were saved; low-score predictions missing."
    return result


def audit(predictions, annotations, regions, confidence=.25, coverage=.5, ap_available=True):
    names = [a["image"] for a in annotations]
    assert len(names) == len(set(names))
    assert set(names) == set(predictions) == set(regions), "Require complete explicit ROI review"
    assert 0 < coverage <= 1
    before = metrics(predictions, annotations, confidence, ap_available)
    filtered, decisions, per_image = {}, [], []
    removed_tp = removed_fp = gt_overlap = 0
    for a in annotations:
        name = a["image"]
        p = predictions[name]
        gt = np.asarray(a["UAV_boxes"], dtype=np.float32).reshape(-1, 4)
        fractions = overlap_fraction(p[:, :4], regions[name])
        remove = fractions >= coverage
        filtered[name] = p[~remove].copy()
        fixed = p[:, 4] >= confidence
        original_correct = match(p[fixed], gt)[:, 0]
        correct_all = np.zeros(len(p), dtype=bool)
        correct_all[fixed] = original_correct
        remaining_correct = match(filtered[name][filtered[name][:, 4] >= confidence], gt)[:, 0]
        rtp = int((remove & fixed & correct_all).sum())
        rfp = int((remove & fixed & ~correct_all).sum())
        removed_tp += rtp
        removed_fp += rfp
        gt_overlap += int((overlap_fraction(gt, regions[name]) > 0).sum())
        for i in range(len(p)):
            decisions.append({"image": name, "prediction_index": i,
                              **dict(zip(("x1", "y1", "x2", "y2", "score", "class"), p[i].tolist())),
                              "timestamp_overlap_fraction": float(fractions[i]), "removed": bool(remove[i]),
                              "original_fixed_status": ("TP" if correct_all[i] else "FP") if fixed[i] else "below_threshold"})
        tp0, tp1 = int(original_correct.sum()), int(remaining_correct.sum())
        per_image.append({"image": name, "GT": len(gt), "TP_before": tp0, "TP_after": tp1,
                          "FP_before": int(fixed.sum()) - tp0,
                          "FP_after": int((filtered[name][:, 4] >= confidence).sum()) - tp1,
                          "FN_before": len(gt) - tp0, "FN_after": len(gt) - tp1,
                          "removed_original_TP": rtp, "removed_original_FP": rfp})
    after = metrics(filtered, annotations, confidence, ap_available)
    summary = {"before": before, "after": after, "coverage": coverage,
               "timestamp_FP": removed_fp, "timestamp_FP_share_of_original_FP": removed_fp / before["FP"] if before["FP"] else None,
               "removed_original_TP": removed_tp, "GT_boxes_intersecting_timestamp": gt_overlap,
               "images_with_timestamp_FP": sum(r["removed_original_FP"] > 0 for r in per_image),
               "images_with_new_misses": sum(r["FN_after"] > r["FN_before"] for r in per_image),
               "delta": {k: after[k] - before[k] if before[k] is not None else None
                         for k in ("TP", "FP", "FN", "Precision_fixed", "Recall_fixed", "F1_fixed",
                                   "mAP50_deployment", "mAP50_95_deployment")}}
    return summary, filtered, decisions, per_image


def write_csv(path, rows):
    if not rows:
        Path(path).write_text("")
        return
    with Path(path).open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--predictions", type=Path, required=True)
    p.add_argument("--annotations", type=Path, required=True)
    p.add_argument("--regions", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--confidence", type=float, default=.25)
    p.add_argument("--coverage", type=float, default=.5)
    p.add_argument("--fixed-only", action="store_true")
    args = p.parse_args()
    sources = {str(x.resolve()): sha(x) for x in (args.predictions, args.annotations, args.regions)}
    args.output.mkdir(parents=True, exist_ok=False)
    summary, filtered, decisions, rows = audit(load_predictions(args.predictions),
        json.loads(args.annotations.read_text()), json.loads(args.regions.read_text()),
        args.confidence, args.coverage, not args.fixed_only)
    save_predictions(args.output / "filtered_predictions.npz", filtered)
    write_csv(args.output / "prediction_decisions.csv", decisions)
    write_csv(args.output / "per_image.csv", rows)
    assert all(sha(k) == v for k, v in sources.items())
    summary["source_sha256_before_and_after"] = sources
    (args.output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary["delta"]))


if __name__ == "__main__":
    main()
