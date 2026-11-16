"""Analyze returned paired Pi predictions without loading a detector."""
import argparse
import json
from pathlib import Path

import numpy as np

from audit_osd import audit, load_predictions, metrics, write_csv
from detection_eval import iou


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--returned", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    annotations = json.loads((args.returned / "manifest.json").read_text())["images"]
    summary, threshold_rows, roundtrips, localization = {}, [], [], []
    for backend in ["fp32", "h10"]:
        pred = load_predictions(args.returned / backend / "predictions.npz")
        before_nms = load_predictions(args.returned / backend / "before_nms.npz")
        summary[backend] = {}
        for group in ["external", "internal_control"]:
            ann = [a for a in annotations if a["group"] == group]
            subset = {a["image"]: pred[a["image"]] for a in ann}
            summary[backend][group] = metrics(subset, ann, .25, True)
            for conf in [.001, .01, .1, .25]:
                m = metrics(subset, ann, conf, True)
                threshold_rows.append({"backend": backend, "group": group, "confidence": conf,
                                       **{k: m[k] for k in ["TP", "FP", "FN", "Precision_fixed", "Recall_fixed"]}})
            if group == "external":
                regions = {a["image"]: [[14, 16, 171, 32]] for a in ann}
                summary[backend]["timestamp_audit"] = audit(subset, ann, regions)[0]
        for index, a in enumerate(annotations):
            with np.load(args.returned / backend / "raw" / f"{index:03}.npz", allow_pickle=False) as z:
                net = z["network_coordinate_boxes"].copy()
                scale, left, top, width, height = z["geometry"]
                net[:, [0, 2]] = ((net[:, [0, 2]] - left) / scale).clip(0, width)
                net[:, [1, 3]] = ((net[:, [1, 3]] - top) / scale).clip(0, height)
                net = net[(net[:, 2] > net[:, 0]) & (net[:, 3] > net[:, 1])]
                target = before_nms[a["image"]]
                assert net.shape == target.shape
                error = float(np.max(np.abs(net - target))) if len(net) else 0.
                assert error <= 1e-4
                roundtrips.append({"backend": backend, "image": a["image"], "max_abs_error_px": error,
                                   "scale": scale, "pad_left": left, "pad_top": top})
            if a["group"] != "external":
                continue
            p = pred[a["image"]]
            p = p[p[:, 4] >= .25]
            gt = np.asarray(a["UAV_boxes"], np.float32).reshape(-1, 4)
            centers = (p[:, :2] + p[:, 2:4]) / 2
            for gi, g in enumerate(gt):
                inside = ((centers >= g[:2]) & (centers <= g[2:])).all(1)
                eligible = np.flatnonzero(inside)
                if not len(eligible):
                    continue
                best = int(eligible[iou(p[eligible, :4], g[None]).ravel().argmax()])
                wh, gwh = p[best, 2:4] - p[best, :2], g[2:] - g[:2]
                inter = np.minimum(wh, gwh).prod()
                localization.append({"backend": backend, "index": index, "image": a["image"], "GT_index": gi,
                                     "IoU": float(iou(p[best:best + 1, :4], g[None])[0, 0]),
                                     "width_ratio": float(wh[0] / gwh[0]), "height_ratio": float(wh[1] / gwh[1]),
                                     "area_ratio": float(wh.prod() / gwh.prod()),
                                     "perfect_center_max_IoU": float(inter / (wh.prod() + gwh.prod() - inter)),
                                     "prediction": p[best].tolist(), "GT": g.tolist()})
    # Trace one observed small target back to the actual H10 LTRB head values.
    example = next(r for r in localization if r["backend"] == "h10" and r["index"] == 4)
    target = np.asarray(example["prediction"][:4]) + [0, 64, 0, 64]
    trace_candidates = []
    with np.load(args.returned / "h10/raw/004.npz", allow_pickle=False) as z:
        for level, stride in enumerate([4, 8, 16, 32]):
            reg = z[f"head_{2 * level}"][0]
            logits = z[f"head_{2 * level + 1}"][0, 0]
            for row, col in np.argwhere(logits >= np.log(.25 / .75)):
                left, top, right, bottom = reg[:, row, col].astype(float)
                ax, ay = (col + .5) * stride, (row + .5) * stride
                box = np.asarray([ax - left * stride, ay - top * stride,
                                  ax + right * stride, ay + bottom * stride])
                trace_candidates.append({"level": level, "stride": stride, "row": int(row), "col": int(col),
                                         "anchor_input_xy": [float(ax), float(ay)],
                                         "head_ltrb": [left, top, right, bottom],
                                         "decoded_input_xyxy": box.tolist(),
                                         "box_width_height": [float((left + right) * stride), float((top + bottom) * stride)],
                                         "max_difference_from_saved_network_box": float(np.abs(box - target).max())})
    trace = min(trace_candidates, key=lambda x: x["max_difference_from_saved_network_box"])
    assert trace["max_difference_from_saved_network_box"] < 1e-4
    summary["geometry_roundtrip_max_error_px"] = max(r["max_abs_error_px"] for r in roundtrips)
    summary["example_frame4_head_trace"] = trace
    summary["example_frame4"] = [r for r in localization if r["index"] == 4]
    (args.output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    (args.output / "localization.json").write_text(json.dumps(localization, indent=2) + "\n")
    write_csv(args.output / "threshold_diagnostics.csv", threshold_rows)
    write_csv(args.output / "geometry_roundtrips.csv", roundtrips)
    print(json.dumps({"summary": {b: {g: {k: summary[b][g][k] for k in ["TP", "FP", "FN"]}
                                       for g in ["external", "internal_control"]} for b in ["fp32", "h10"]},
                      "trace": trace, "roundtrip_error": summary["geometry_roundtrip_max_error_px"]}, indent=2))


if __name__ == "__main__":
    main()
