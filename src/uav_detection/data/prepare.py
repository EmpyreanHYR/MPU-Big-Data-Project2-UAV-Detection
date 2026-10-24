"""Convert native YOLO/VOC boxes, split source groups and audit before publishing.

This module does not download a dataset or infer source class IDs or sequences.
"""
from collections import Counter, defaultdict
import csv
import hashlib
import json
import math
from pathlib import Path
import random
import re
import shutil
import struct
import tempfile
import xml.etree.ElementTree as ET

from PIL import Image

SPLITS = ("train", "val", "test")
TRAIN_VAL_SPLITS = ("train", "val")


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def image_info(path):
    with Image.open(path) as im:
        if getattr(im, "n_frames", 1) != 1 or im.mode not in {"L", "RGB"}:
            raise ValueError(f"Expected a single-frame 8-bit L/RGB image: {path}")
        if im.getexif().get(274, 1) != 1:
            raise ValueError("Normalize EXIF orientation and update boxes before preparation")
        im.load()
        w, h = im.size
        pixels = hashlib.sha256(struct.pack(">II", w, h) + im.convert("RGB").tobytes()).hexdigest()
    return w, h, pixels


def _inside(root, value):
    rel = Path(value)
    if not value or rel.is_absolute() or ".." in rel.parts:
        raise ValueError(f"Expected a source-root-relative path: {value}")
    result = (root / rel).resolve()
    if not result.is_relative_to(root) or not result.is_file():
        raise ValueError(f"Missing file or path outside source root: {value}")
    return result


def _box(role, values, w, h):
    x0, y0, x1, y1 = values
    if not all(math.isfinite(v) for v in values):
        raise ValueError("Non-finite box coordinate")
    if not (0 <= x0 < x1 <= w and 0 <= y0 < y1 <= h):
        raise ValueError(f"Invalid/out-of-bounds box {values} for {w}x{h}")
    return {"role": role, "xyxy": [x0, y0, x1, y1]}


def parse_boxes(path, fmt, mapping, w, h, voc_mode):
    result = []
    if fmt == "yolo":
        for number, line in enumerate(path.read_text().splitlines(), 1):
            parts = line.split()
            if not parts:
                continue
            if len(parts) != 5:
                raise ValueError(f"Expected native box label with five fields: {path}:{number}")
            cls, *coords = parts
            if cls not in mapping:
                raise ValueError(f"Unknown source class {cls}")
            cx, cy, bw, bh = map(float, coords)
            result.append(_box(mapping[cls], [(cx-bw/2)*w, (cy-bh/2)*h,
                                             (cx+bw/2)*w, (cy+bh/2)*h], w, h))
    elif fmt == "voc":
        if voc_mode not in {"one-based-inclusive", "zero-based-half-open"}:
            raise ValueError("VOC input requires an explicit coordinate convention")
        raw = path.read_bytes()
        if b"<!DOCTYPE" in raw.upper() or b"<!ENTITY" in raw.upper():
            raise ValueError("XML entities are not supported")
        tree = ET.fromstring(raw)
        size = tree.find("size")
        if size is not None and (int(size.findtext("width")), int(size.findtext("height"))) != (w, h):
            raise ValueError("VOC size differs from image dimensions")
        for obj in tree.findall("object"):
            cls = obj.findtext("name")
            if cls not in mapping:
                raise ValueError(f"Unknown source class {cls}")
            if obj.findtext("difficult", "0") != "0":
                raise ValueError("Resolve VOC difficult objects under an explicit ignore policy first")
            node = obj.find("bndbox")
            coords = [float(node.findtext(k)) for k in ("xmin", "ymin", "xmax", "ymax")]
            if voc_mode == "one-based-inclusive":
                coords[0] -= 1; coords[1] -= 1
            result.append(_box(mapping[cls], coords, w, h))
    else:
        raise ValueError(f"Unsupported annotation format: {fmt}")
    return result


def _signature(boxes):
    return sorted((b["role"], *[round(v, 7) for v in b["xyxy"]]) for b in boxes)


def read_manifest(manifest, source_root, class_map, voc_mode=None):
    root = Path(source_root).resolve()
    if not root.is_dir():
        raise ValueError("Source root is not a directory")
    mapping = json.loads(Path(class_map).read_text())
    if not isinstance(mapping, dict) or set(mapping.values()) != {"uav", "bird"}:
        raise ValueError("Class map must explicitly map source IDs/names to uav and bird")
    if any(not isinstance(k, str) or not k or "<" in k for k in mapping):
        raise ValueError("Replace placeholder source class IDs/names using the original label contract")
    rows, seen = [], set()
    with Path(manifest).open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        if not {"image", "annotation", "format", "group", "split"} <= set(reader.fieldnames or []):
            raise ValueError("Manifest needs image,annotation,format,group,split columns")
        for item in reader:
            image = _inside(root, item["image"])
            if str(image) in seen:
                raise ValueError("Repeated image path in manifest")
            seen.add(str(image))
            group = item["group"].strip()
            if not group:
                raise ValueError("Every image needs an explicit source sequence/group")
            split = item["split"].strip()
            if split and split not in SPLITS:
                raise ValueError(f"Invalid split: {split}")
            w, h, pixel_hash = image_info(image)
            fmt = item["format"].strip()
            if fmt == "negative":
                if item["annotation"].strip():
                    raise ValueError("Verified negative rows must have an empty annotation field")
                annotation, boxes, label_hash = None, [], None
            else:
                annotation = _inside(root, item["annotation"])
                boxes = parse_boxes(annotation, fmt, mapping, w, h, voc_mode)
                label_hash = sha256(annotation)
            rows.append({"source_image": item["image"], "source_annotation": item["annotation"],
                         "format": fmt, "group": group, "split": split, "width": w, "height": h,
                         "source_sha256": sha256(image), "source_label_sha256": label_hash,
                         "pixel_sha256": pixel_hash, "boxes": boxes,
                         "_image": image, "_annotation": annotation})
    if not rows:
        raise ValueError("Empty manifest")
    return rows, mapping


def assign_splits(rows, seed=42, ratios=(0.7, 0.15, 0.15), splits=SPLITS):
    if splits not in (SPLITS, TRAIN_VAL_SPLITS):
        raise ValueError("Unsupported split protocol")
    if len(ratios) != len(splits) or any(not math.isfinite(v) or v <= 0 for v in ratios) or abs(sum(ratios)-1) > 1e-8:
        raise ValueError("Positive split ratios summing to one are required")
    if any(r["split"] and r["split"] not in splits for r in rows):
        raise ValueError("Input split is outside the declared protocol")
    parent = {r["group"]: r["group"] for r in rows}
    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]; x = parent[x]
        return x
    by_pixels = {}
    for row in rows:
        key = row["pixel_sha256"]
        if key in by_pixels:
            other = by_pixels[key]
            if _signature(row["boxes"]) != _signature(other["boxes"]):
                raise ValueError("Identical pixels have conflicting annotations")
            left, right = sorted((find(row["group"]), find(other["group"])))
            parent[right] = left
        else:
            by_pixels[key] = row
    clusters = defaultdict(list)
    for row in rows:
        clusters[find(row["group"])].append(row)
    provided = [bool(r["split"]) for r in rows]
    if any(provided):
        if not all(provided):
            raise ValueError("Either supply every split or leave all split fields empty")
        for cluster in clusters.values():
            if len({r["split"] for r in cluster}) != 1:
                raise ValueError("Source group or identical image crosses splits")
    else:
        positives = [k for k, v in clusters.items() if any(b["role"] == "uav" for r in v for b in r["boxes"])]
        if len(positives) < len(splits):
            raise ValueError("Each split needs a separate UAV-positive group")
        rng = random.Random(seed)
        positives = sorted(positives); rng.shuffle(positives)
        counts = Counter()
        assignments = dict(zip(positives[:len(splits)], splits))
        for group, split in assignments.items():
            counts[split] += len(clusters[group])
        rest = sorted(set(clusters) - set(assignments)); rng.shuffle(rest)
        # Whole groups are assigned; image ratios are approximate.
        for group in rest:
            split = max(splits, key=lambda s: (ratios[splits.index(s)]*len(rows)-counts[s]) /
                        (ratios[splits.index(s)]*len(rows)))
            assignments[group] = split; counts[split] += len(clusters[group])
        for group, cluster in clusters.items():
            for row in cluster:
                row["split"] = assignments[group]
    for split in splits:
        part = [r for r in rows if r["split"] == split]
        if not part or not any(b["role"] == "uav" for r in part for b in r["boxes"]):
            raise ValueError(f"Split {split} must contain images and at least one UAV")


def _label_lines(row):
    w, h = row["width"], row["height"]
    lines = []
    for box in row["boxes"]:
        if box["role"] == "uav":
            x0, y0, x1, y1 = box["xyxy"]
            lines.append(f"0 {(x0+x1)/(2*w):.10f} {(y0+y1)/(2*h):.10f} {(x1-x0)/w:.10f} {(y1-y0)/h:.10f}")
    return lines


def _dataset_yaml(root, splits=SPLITS):
    return ("path: "+json.dumps(str(root))+"\n" +
            "".join(f"{split}: images/{split}\n" for split in splits) + "names:\n  0: uav\n")


def _validate_group_provenance(document):
    expected = {"video_identity": "unknown", "protocol": "inferred-view-holdout",
                "test_policy": "no_independent_test"}
    if not isinstance(document, dict) or any(document.get(k) != v for k, v in expected.items()):
        raise ValueError("Train/val-only requires the explicit unknown-video inferred-view/no-test policy")
    if not isinstance(document.get("grouping_basis"), str) or not document["grouping_basis"].strip():
        raise ValueError("The inferred group policy needs a grouping_basis description")
    evidence = document.get("evidence")
    if (not isinstance(evidence, list) or not evidence or
        any(not isinstance(item, (str, dict)) or not item or
            (isinstance(item, str) and not item.strip()) for item in evidence)):
        raise ValueError("The inferred group policy needs nonempty auditable evidence")
    return document


def _manifest_splits(manifest, output):
    if manifest.get("target_class") != "uav":
        raise ValueError("Unsupported prepared target class")
    if manifest.get("schema") == 1:
        if "splits" in manifest and manifest["splits"] != list(SPLITS):
            raise ValueError("Schema 1 requires train/val/test")
        return SPLITS
    if manifest.get("schema") != 2 or manifest.get("splits") != list(TRAIN_VAL_SPLITS):
        raise ValueError("Unsupported prepared manifest contract")
    document = _validate_group_provenance(manifest.get("group_provenance"))
    if manifest.get("group_provenance_file") != "group_provenance.json":
        raise ValueError("Missing frozen group provenance file")
    path = _inside(output, manifest["group_provenance_file"])
    if (sha256(path) != manifest.get("group_provenance_sha256") or
        json.loads(path.read_text(encoding="utf-8-sig")) != document):
        raise ValueError("Frozen group provenance differs from the audited policy")
    return TRAIN_VAL_SPLITS


def audit_prepared(output, require_config=True):
    output = Path(output).resolve()
    manifest = json.loads((output / "manifest.json").read_text())
    splits = _manifest_splits(manifest, output)
    if require_config and (output/"dataset.yaml").read_text() != _dataset_yaml(output, splits):
        raise ValueError("Dataset YAML differs from the audited layout/root")
    groups, pixels, counts = defaultdict(set), defaultdict(set), Counter()
    positives = Counter()
    expected = set()
    for row in manifest["images"]:
        split = row["split"]
        if split not in splits:
            raise ValueError("Invalid output split")
        image = _inside(output, row["image"])
        label = _inside(output, row["label"])
        if str(image) in expected or str(label) in expected:
            raise ValueError("Repeated prepared path")
        expected.update((str(image), str(label)))
        w, h, pixel_hash = image_info(image)
        if (w, h, pixel_hash, sha256(image)) != (row["width"], row["height"], row["pixel_sha256"], row["source_sha256"]):
            raise ValueError("Prepared image changed after source validation")
        if not row["group"]:
            raise ValueError("Missing source group")
        for box in row["boxes"]:
            if box["role"] not in {"uav", "bird"}:
                raise ValueError("Unknown box role")
            _box(box["role"],box["xyxy"],w,h)
            positives[split] += box["role"] == "uav"
        if label.read_text().splitlines() != _label_lines(row):
            raise ValueError("Prepared labels do not match audited UAV boxes")
        groups[row["group"]].add(split); pixels[pixel_hash].add(split)
        counts[split] += 1
    actual = {str(x.resolve()) for name in ("images", "labels") for x in (output/name).rglob("*") if x.is_file()}
    if expected != actual:
        raise ValueError("Unmanifested or missing prepared image/label")
    if any(len(x) > 1 for x in list(groups.values()) + list(pixels.values())):
        raise ValueError("Source group or pixel duplicate leakage")
    if any(counts[s] == 0 or positives[s] == 0 for s in splits):
        raise ValueError("Empty split")
    result = {"status": "PASS", "images": dict(counts), "source_groups": len(groups),
            "duplicate_image_count": len(manifest["images"]) - len(pixels),
            "uav_boxes": sum(b["role"] == "uav" for r in manifest["images"] for b in r["boxes"]),
            "bird_boxes_for_error_analysis": sum(b["role"] == "bird" for r in manifest["images"] for b in r["boxes"])}
    if manifest["schema"] == 2:
        result.update(splits=list(splits), test_policy="no_independent_test",
                      group_protocol="inferred-view-holdout", video_identity="unknown",
                      group_provenance_sha256=manifest["group_provenance_sha256"])
    return result


def prepare_dataset(manifest, source_root, class_map, output, seed=42,
                    ratios=(0.7, 0.15, 0.15), voc_mode=None,
                    train_val_only=False, group_provenance=None):
    root, out = Path(source_root).resolve(), Path(output).resolve()
    if out.exists() or root.is_relative_to(out) or out.is_relative_to(root):
        raise ValueError("Output must be new and separate from the raw source tree")
    provenance_raw, provenance = None, None
    if train_val_only:
        if group_provenance is None:
            raise ValueError("Train/val-only requires an explicit group provenance JSON")
        provenance_raw = Path(group_provenance).read_bytes()
        provenance = _validate_group_provenance(json.loads(provenance_raw.decode("utf-8-sig")))
    elif group_provenance is not None:
        raise ValueError("Group provenance for the inferred two-split policy needs train_val_only=True")
    rows, mapping = read_manifest(manifest, root, class_map, voc_mode)
    splits = TRAIN_VAL_SPLITS if train_val_only else SPLITS
    if train_val_only and any(row["split"] not in splits for row in rows):
        raise ValueError("Inferred train/val-only requires every CSV row to have a fixed train or val split")
    assign_splits(rows, seed, (0.8, 0.2) if train_val_only else ratios, splits)
    out.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".uav-prepare-", dir=out.parent))
    try:
        for split in splits:
            (stage/"images"/split).mkdir(parents=True); (stage/"labels"/split).mkdir(parents=True)
        rendered = []
        for row in rows:
            name = re.sub(r"[^A-Za-z0-9_-]", "_", row["_image"].stem)[:50]
            name += "_" + hashlib.sha256(row["source_image"].encode()).hexdigest()[:16]
            image_rel = f"images/{row['split']}/{name}{row['_image'].suffix.lower()}"
            label_rel = f"labels/{row['split']}/{name}.txt"
            shutil.copy2(row["_image"], stage/image_rel)
            (stage/label_rel).write_text("\n".join(_label_lines(row)) + ("\n" if _label_lines(row) else ""))
            rendered.append({k: v for k, v in row.items() if not k.startswith("_")} | {"image": image_rel, "label": label_rel})
        contract = {"schema": 2 if train_val_only else 1, "target_class": "uav", "class_map": mapping,
                    "seed": seed, "requested_ratios": None if train_val_only else ratios, "voc_coordinate_mode": voc_mode,
                    "input_manifest_sha256": sha256(manifest), "images": rendered}
        if train_val_only:
            (stage/"group_provenance.json").write_bytes(provenance_raw)
            contract.update(splits=list(splits), group_provenance=provenance,
                            group_provenance_file="group_provenance.json",
                            group_provenance_sha256=hashlib.sha256(provenance_raw).hexdigest())
        (stage/"manifest.json").write_text(json.dumps(contract, indent=2, ensure_ascii=False)+"\n")
        audit = audit_prepared(stage, require_config=False)
        (stage/"audit.json").write_text(json.dumps(audit, indent=2)+"\n")
        # Absolute YAML root: Ultralytics resolves relative roots against its datasets directory.
        (stage/"dataset.yaml").write_text(_dataset_yaml(out, splits))
        if out.exists():
            raise FileExistsError(out)
        stage.rename(out)
        return audit
    except BaseException:
        shutil.rmtree(stage, ignore_errors=True)
        raise
