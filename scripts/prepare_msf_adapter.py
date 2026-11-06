#!/usr/bin/env python3
"""Create a separately patched copy of the author's pinned YOLOv5 base."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil


def prepare(source, destination):
    source, destination = Path(source), Path(destination)
    shutil.copytree(source, destination)
    receipt = []
    def change(relative, old, new, count=1):
        path = destination / relative
        text = path.read_text()
        if text.count(old) != count:
            raise ValueError(f"Unexpected pinned source at {relative}: {old}")
        before = hashlib.sha256(text.encode()).hexdigest()
        text = text.replace(old, new)
        path.write_text(text)
        receipt.append({"file": relative, "old": old, "new": new,
                        "before_sha256": before, "after_sha256": hashlib.sha256(text.encode()).hexdigest()})
    change("train.py", "amp = check_amp(model)", "amp = False")
    change("train.py", "nbs = 64", "nbs = 32")
    # Native AP50/AP95 weighted fitness is replaced with AP95-only selection.
    change("utils/metrics.py", "w = [0.0, 0.0, 0.1, 0.9]", "w = [0.0, 0.0, 0.0, 1.0]")
    change("train.py", "model=attempt_load(f, device).half(),", "model=attempt_load(f, device).float(),")
    change("val.py", "half=True,", "half=False,")
    change("train.py", "        model.train()", "        model.train()\n        if epoch == epochs - 10:\n            dataset.mosaic = False\n            if hasattr(train_loader.iterator, '_shutdown_workers'):\n                train_loader.iterator._shutdown_workers()\n            train_loader.iterator = torch.utils.data.DataLoader.__iter__(train_loader)")
    change("utils/dataloaders.py", ".astype(np.int)", ".astype(int)", count=3)
    # Disable optional remote logger before any login or module side effects.
    change("utils/loggers/__init__.py", "    import wandb", "    raise ImportError('Remote logger disabled for this experiment')")
    change("utils/loggers/__init__.py", "include=LOGGERS", "include=('csv',)")
    # Native checkpoint storage is half precision; retain FP32 for this protocol.
    change("train.py", "deepcopy(de_parallel(model)).half()", "deepcopy(de_parallel(model)).float()")
    change("train.py", "deepcopy(ema.ema).half()", "deepcopy(ema.ema).float()")
    change("utils/general.py", "x['model'].half()", "x['model'].float()")
    (destination / "adapter_patch_receipt.json").write_text(json.dumps(receipt, indent=2))
    return receipt


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.source, args.destination), indent=2))
