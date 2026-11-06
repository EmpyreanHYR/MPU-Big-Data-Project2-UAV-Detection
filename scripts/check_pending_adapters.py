#!/usr/bin/env python3
"""Bounded cloud CPU checks; never occupies the active experiment's CUDA GPU."""
import argparse
import ast
import json
from pathlib import Path
import platform
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", choices=["faster", "sd", "msf"], required=True)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--msf-source", type=Path)
    parser.add_argument("--author-source", type=Path)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    if platform.system() != "Linux" or platform.machine().lower() not in {"x86_64", "amd64"}:
        raise RuntimeError("Model checks are authorized only on the cloud Linux host")
    import torch
    torch.set_num_threads(2)
    torch.manual_seed(42)
    checks = []
    if args.model == "faster":
        from uav_detection.faster_adapter import build_faster, FrozenYoloDataset, evaluate_faster, collate
        dataset = FrozenYoloDataset(args.data, "train", size=128)
        image, target = next(dataset[i] for i in range(len(dataset)) if len(dataset[i][1]["boxes"]))
        model = build_faster(128)
        model.train()
        empty = {"boxes": torch.empty((0, 4)), "labels": torch.empty(0, dtype=torch.long)}
        optimizer = torch.optim.AdamW(model.parameters(), lr=0.001)
        before = next(model.parameters()).detach().clone()
        losses = model([image, image], [target, empty])
        loss = sum(losses.values())
        assert torch.isfinite(loss)
        loss.backward()
        assert all(torch.isfinite(p.grad).all() for p in model.parameters() if p.grad is not None)
        optimizer.step()
        assert not torch.equal(before, next(model.parameters()))
        checks += ["positive_and_negative_loss_backward", "optimizer_updated_weights"]
        with tempfile.TemporaryDirectory() as temporary:
            p = Path(temporary) / "roundtrip.pt"
            torch.save(model.state_dict(), p)
            restored = build_faster(128)
            restored.load_state_dict(torch.load(p, map_location="cpu", weights_only=True))
            assert all(torch.equal(v, restored.state_dict()[k]) for k, v in model.state_dict().items())
            from torch.utils.data import DataLoader, Subset
            metrics = evaluate_faster(restored, DataLoader(Subset(dataset, [0, 1]), batch_size=2, collate_fn=collate), "cpu")
            assert all(__import__('math').isfinite(v) for v in metrics.values())
        checks += ["checkpoint_roundtrip_exact", "native_nms_and_val_metrics"]
    elif args.model == "sd":
        from types import SimpleNamespace
        from ultralytics.utils import DEFAULT_CFG_DICT
        from uav_detection.pconv_sd import SDDetectionModel, SDTrainer, SDBboxLoss
        from uav_detection.pconv import PConv
        from uav_detection.sd_reference import bbox_iou
        # Compare the independently loaded original author's function and gradient.
        text = args.author_source.read_text()
        node = next(n for n in ast.parse(text).body if isinstance(n, ast.FunctionDef) and n.name == "bbox_iou")
        namespace = {"torch": torch, "math": __import__('math')}
        exec(compile(ast.Module(body=[node], type_ignores=[]), "author-bbox-iou", "exec"), namespace)
        pred = torch.tensor([[1., 1., 2., 2.], [1., 3., 8., 9.], [2., 4., 24., 32.]], requires_grad=True)
        truth = torch.tensor([[1., 1., 2., 2.], [2., 2., 6., 9.], [4., 2., 25., 35.]])
        expected = namespace["bbox_iou"](pred, truth, xywh=False, SDIoU=True, delta=0.5)
        actual = bbox_iou(pred, truth, xywh=False, SDIoU=True, delta=0.5)
        assert torch.equal(actual, expected)
        assert torch.equal(torch.autograd.grad(actual.sum(), pred, retain_graph=True)[0],
                           torch.autograd.grad(expected.sum(), pred)[0])
        checks += ["author_sdiou_forward_exact", "author_sdiou_gradient_exact"]
        model = SDDetectionModel(nc=1)
        model.args = SimpleNamespace(**DEFAULT_CFG_DICT)
        model.train()
        batch = {"img": torch.rand(2, 3, 128, 128), "batch_idx": torch.tensor([0.]),
                 "cls": torch.zeros(1, 1), "bboxes": torch.tensor([[.5, .5, .12, .12]])}
        loss, components = model.loss(batch)
        loss.sum().backward()
        pieces = components.values() if isinstance(components, dict) else [components]
        assert all(torch.isfinite(value).all() for value in pieces)
        assert isinstance(model.criterion.bbox_loss, SDBboxLoss)
        for layer in [0, 1]:
            assert isinstance(model.model[layer], PConv)
            assert any(p.grad is not None and p.grad.abs().sum() > 0 for p in model.model[layer].parameters())
        assert all(torch.isfinite(p.grad).all() for p in model.parameters() if p.grad is not None)
        checks += ["pconv_and_sdb_and_dfl_backward", "pconv_gradients_nonzero"]
        trainer = object.__new__(SDTrainer)
        trainer.args = SimpleNamespace(**DEFAULT_CFG_DICT)
        trainer.data = {"nc": 1, "channels": 3, "names": {0: "uav"}}
        rebuilt = trainer.get_model(model.yaml, verbose=False)
        rebuilt.args = trainer.args  # BaseTrainer attaches hyperparameters after get_model.
        assert all(isinstance(rebuilt.model[layer], PConv) for layer in [0, 1])
        assert isinstance(rebuilt.init_criterion().bbox_loss, SDBboxLoss)
        with tempfile.TemporaryDirectory() as temporary:
            p = Path(temporary) / "roundtrip.pt"
            torch.save({"model": model}, p)
            restored = torch.load(p, map_location="cpu", weights_only=False)["model"]
            assert isinstance(restored.init_criterion().bbox_loss, SDBboxLoss)
            model.eval(); restored.eval()
            with torch.no_grad():
                a, b = model(batch["img"])[0], restored(batch["img"])[0]
            assert torch.equal(a, b)
        checks += ["trainer_rebuild_keeps_modules_and_loss", "checkpoint_roundtrip_outputs_exact"]
    else:
        import yaml
        sys.path.insert(0, str(args.msf_source))
        from models.yolo import Model
        from utils.loss import ComputeLoss
        from utils.metrics import fitness
        from utils.general import non_max_suppression
        model = Model(str(ROOT / "configs/models/msf-ghostnet-iii.yaml"), ch=3, nc=1)
        model.hyp = yaml.safe_load((args.msf_source / "data/hyps/hyp.scratch-high.yaml").read_text())
        model.gr = 1.0
        from models.common import C3Ghost, GhostConv
        assert any(isinstance(m, C3Ghost) for m in model.modules())
        assert any(isinstance(m, GhostConv) for m in model.modules())
        assert list(model.stride.cpu().tolist()) == [8., 16., 32.]
        model.train()
        optimizer = torch.optim.AdamW(model.parameters(), lr=0.001)
        x = torch.rand(2, 3, 128, 128)
        loss, parts = ComputeLoss(model)(model(x), torch.tensor([[0, 0, .5, .5, .12, .12]]))
        assert torch.isfinite(loss) and torch.isfinite(parts).all()
        loss.backward()
        assert all(torch.isfinite(p.grad).all() for p in model.parameters() if p.grad is not None)
        optimizer.step()
        checks += ["author_ghost_graph_and_strides", "native_yolov5_loss_backward_optimizer"]
        assert float(fitness(__import__('numpy').array([[0., 0., .99, .2]]))[0]) == .2
        model.eval()
        with torch.no_grad():
            prediction = model(x)[0]
            outputs = non_max_suppression(prediction, conf_thres=0.001)
        assert len(outputs) == 2
        with tempfile.TemporaryDirectory() as temporary:
            p = Path(temporary) / "roundtrip.pt"
            torch.save({"model": model.float()}, p)
            restored = torch.load(p, map_location="cpu", weights_only=False)["model"].float().eval()
            with torch.no_grad():
                assert torch.equal(prediction, restored(x)[0])
        import train, val
        assert __import__('inspect').signature(val.run).parameters["half"].default is False
        checks += ["ap95_only_fitness", "native_nms", "checkpoint_roundtrip_outputs_exact", "training_entry_and_fp32_validator_import"]
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps({"model": args.model, "status": "passed", "device": "cloud_cpu",
         "torch": torch.__version__, "checks": checks, "full_640_batch_vram_test": "pending_job_start"}, indent=2))
    print(json.dumps({"model": args.model, "status": "passed", "checks": checks}), flush=True)


if __name__ == "__main__":
    main()
