"""Scratch torchvision Faster R-CNN, frozen four-source split, val-only selection.

Family-specific recipe: letterbox + horizontal flip, native scratch BatchNorm,
no Mosaic/EMA. AP matching and max-F1 P/R follow Ultralytics conventions.
"""
import csv
import json
import math
import random
import time
from pathlib import Path
import numpy as np
from PIL import Image, ImageOps
import torch
from torch.utils.data import Dataset, DataLoader
from torchvision.models.detection import fasterrcnn_resnet50_fpn
from torchvision.ops import box_iou


def build_faster(size=640):
    return fasterrcnn_resnet50_fpn(weights=None, weights_backbone=None,
        num_classes=2, min_size=size, max_size=size, trainable_backbone_layers=5,
        box_score_thresh=0.001, box_detections_per_img=300, box_nms_thresh=0.7)


class FrozenYoloDataset(Dataset):
    def __init__(self, root, split, size=640, augment=False):
        self.root, self.size, self.augment = Path(root), size, augment
        if split not in {"train", "val"}:
            raise ValueError("Training adapter may read only train/val")
        with (self.root / "provenance/manifest_exported.csv").open(encoding="utf-8-sig") as stream:
            self.rows = [r for r in csv.DictReader(stream) if r["split"] == split]

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, index):
        row = self.rows[index]
        with Image.open(self.root / row["output_image"]) as source:
            image = source.convert("RGB")
        w, h = image.size
        gain = self.size / max(w, h)
        nw, nh = round(w * gain), round(h * gain)
        left, top = (self.size - nw) // 2, (self.size - nh) // 2
        canvas = Image.new("RGB", (self.size, self.size), (114, 114, 114))
        canvas.paste(image.resize((nw, nh), Image.Resampling.BILINEAR), (left, top))
        boxes = []
        for line in (self.root / row["output_label"]).read_text().splitlines():
            cls, x, y, bw, bh = map(float, line.split())
            if cls != 0:
                raise ValueError("Expected single UAV class")
            boxes.append([(x - bw / 2) * nw + left, (y - bh / 2) * nh + top,
                          (x + bw / 2) * nw + left, (y + bh / 2) * nh + top])
        boxes = torch.tensor(boxes, dtype=torch.float32).reshape(-1, 4)
        if self.augment and torch.rand(()).item() < 0.5:
            canvas = ImageOps.mirror(canvas)
            boxes[:, [0, 2]] = self.size - boxes[:, [2, 0]]
        image = torch.from_numpy(np.array(canvas)).permute(2, 0, 1).float() / 255
        target = {"boxes": boxes, "labels": torch.ones(len(boxes), dtype=torch.int64),
                  "image_id": torch.tensor(index), "iscrowd": torch.zeros(len(boxes), dtype=torch.int64)}
        return image, target


def collate(batch):
    return tuple(zip(*batch))


def match_predictions(boxes, target, thresholds):
    """Greedy descending-IoU one-to-one assignment at each AP threshold."""
    correct = np.zeros((len(boxes), len(thresholds)), dtype=bool)
    if not len(boxes) or not len(target):
        return correct
    iou = box_iou(target, boxes).cpu().numpy()
    for column, threshold in enumerate(thresholds):
        gi, pi = np.where(iou >= threshold)
        if not len(gi):
            continue
        matches = np.stack((gi, pi, iou[gi, pi]), axis=1)
        matches = matches[matches[:, 2].argsort()[::-1]]
        matches = matches[np.unique(matches[:, 1], return_index=True)[1]]
        matches = matches[matches[:, 2].argsort()[::-1]]
        matches = matches[np.unique(matches[:, 0], return_index=True)[1]]
        correct[matches[:, 1].astype(int), column] = True
    return correct


@torch.no_grad()
def evaluate_faster(model, loader, device):
    from ultralytics.utils.metrics import ap_per_class
    model.eval()
    correct, confidence, classes, targets = [], [], [], []
    thresholds = np.linspace(0.5, 0.95, 10)
    for images, labels in loader:
        predictions = model([x.to(device) for x in images])
        for pred, label in zip(predictions, labels):
            keep = pred["labels"] == 1
            boxes, scores = pred["boxes"][keep].cpu(), pred["scores"][keep].cpu().numpy()
            correct.append(match_predictions(boxes, label["boxes"], thresholds))
            confidence.append(scores)
            classes.append(np.zeros(len(scores)))
            targets.append(np.zeros(len(label["boxes"])))
    tp, conf, cls, gt = map(np.concatenate, (correct, confidence, classes, targets))
    if not len(conf) or not len(gt) or not tp.any():
        return {"precision": 0.0, "recall": 0.0, "map50": 0.0, "map50_95": 0.0}
    metrics = ap_per_class(tp, conf, cls, gt, plot=False)
    return {"precision": float(metrics[2].mean()), "recall": float(metrics[3].mean()),
            "map50": float(metrics[5][:, 0].mean()), "map50_95": float(metrics[5].mean())}


def train_faster(data, output, epochs=150, device="cuda:0", workers=8, *, size=640,
                 expected_counts=(5800, 1450)):
    random.seed(42)
    np.random.seed(42)
    torch.manual_seed(42)
    torch.use_deterministic_algorithms(True, warn_only=True)
    torch.backends.cudnn.benchmark = False
    train = FrozenYoloDataset(data, "train", size=size, augment=True)
    val = FrozenYoloDataset(data, "val", size=size)
    assert (len(train), len(val)) == expected_counts
    model = build_faster(size).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=0.001, betas=(0.9, 0.999), weight_decay=0.0005)
    loader = DataLoader(train, batch_size=2, shuffle=True, num_workers=workers, collate_fn=collate,
                        generator=torch.Generator().manual_seed(42))
    validation = DataLoader(val, batch_size=2, num_workers=workers, collate_fn=collate)
    output = Path(output)
    (output / "weights").mkdir(parents=True, exist_ok=False)
    recipe = {"epochs": epochs, "imgsz": size, "batch": 2, "accumulation": 16,
              "weights": None, "weights_backbone": None, "seed": 42, "amp": False,
              "augmentation": "letterbox-horizontal-flip-only", "ema": False,
              "optimizer": "AdamW", "lr0": 0.001, "lrf": 0.01, "warmup_epochs": 3,
              "checkpoint_selection": "val_map50_95", "test_used": False}
    (output / "recipe.json").write_text(json.dumps(recipe, indent=2))
    best = -1
    start = time.time()
    with (output / "results.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["epoch", "time", "train_loss", "precision", "recall", "map50", "map50_95"])
        writer.writeheader()
        for epoch in range(epochs):
            model.train()
            optimizer.zero_grad(set_to_none=True)
            total = 0
            for step, (images, labels) in enumerate(loader):
                warmup = min(1, (epoch * len(loader) + step + 1) / (3 * len(loader)))
                lr = 0.001 * (1 - epoch / epochs * 0.99) * warmup
                for group in optimizer.param_groups:
                    group["lr"] = lr
                losses = model([x.to(device) for x in images],
                               [{k: v.to(device) for k, v in y.items()} for y in labels])
                loss = sum(losses.values())
                if not torch.isfinite(loss):
                    raise RuntimeError(f"Nonfinite Faster R-CNN loss: {losses}")
                group_size = min(16, len(loader) - (step // 16) * 16)
                (loss / group_size).backward()
                total += loss.item()
                if (step + 1) % 16 == 0 or step + 1 == len(loader):
                    torch.nn.utils.clip_grad_norm_(model.parameters(), 10, error_if_nonfinite=True)
                    optimizer.step()
                    optimizer.zero_grad(set_to_none=True)
                if step % 100 == 0:
                    print(f"epoch={epoch+1}/{epochs} batch={step+1}/{len(loader)} loss={loss.item():.5f}", flush=True)
            metrics = evaluate_faster(model, validation, device)
            if not all(math.isfinite(v) for v in metrics.values()):
                raise RuntimeError("Nonfinite validation metric")
            row = {"epoch": epoch + 1, "time": time.time() - start, "train_loss": total / len(loader), **metrics}
            writer.writerow(row)
            stream.flush()
            print(json.dumps(row), flush=True)
            checkpoint = {"model_state_dict": model.state_dict(), "epoch": epoch + 1, "recipe": recipe, "metrics": metrics}
            torch.save(checkpoint | {"optimizer_state_dict": optimizer.state_dict()}, output / "weights/last.pt")
            if metrics["map50_95"] > best:
                best = metrics["map50_95"]
                torch.save(checkpoint, output / "weights/best.pt")
            if (epoch + 1) % 10 == 0:
                torch.save(checkpoint, output / f"weights/epoch{epoch+1}.pt")
