"""CPU construction/inference tests only: no loss, backward, optimizer or training."""
import importlib.util
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"src"))
os.environ.setdefault("YOLO_AUTOINSTALL", "false")
os.environ.setdefault("YOLO_CONFIG_DIR", str(ROOT/".venv/yolo-settings"))
os.environ.setdefault("MPLCONFIGDIR", str(ROOT/".venv/matplotlib"))
AVAILABLE = all(importlib.util.find_spec(name) for name in ("torch", "ultralytics"))


@unittest.skipUnless(AVAILABLE, "Install the model optional dependency for CPU integration checks")
class ModelIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import torch
        torch.set_num_threads(2)

    def test_shapes_and_no_state_updates(self):
        import torch
        from uav_detection.modeling import build_detector
        for variant, expected in [("baseline", [8,16,32]), ("pconv", [8,16,32]), ("p2", [4,8,16,32])]:
            with self.subTest(variant=variant):
                model = build_detector(variant).model.cpu().eval()
                self.assertEqual(model.stride.tolist(), expected)
                self.assertTrue(model.end2end)
                self.assertEqual(model.model[-1].nl, len(expected))
                self.assertEqual(model.model[-1].reg_max, 1)
                before = {k: x.clone() for k,x in model.state_dict().items()}
                for height, width in [(128,128),(128,160)]:
                    with torch.inference_mode():
                        output, raw = model(torch.zeros(1,3,height,width))
                    self.assertEqual(output.shape[-1], 6)
                    self.assertTrue(torch.isfinite(output).all())
                    self.assertEqual([x.shape[-2:] for x in raw["one2one"]["feats"]],
                                     [(height//s,width//s) for s in expected])
                for key, value in model.state_dict().items():
                    self.assertTrue(torch.equal(before[key], value), key)
                self.assertTrue(all(x.grad is None for x in model.parameters()))

    def test_pconv_shared_branches_and_geometry(self):
        import torch
        from uav_detection.pconv import PConv
        module = PConv(16,32).eval()
        with torch.inference_mode():
            self.assertEqual(tuple(module(torch.zeros(1,16,32,40)).shape), (1,32,16,20))
        self.assertEqual(len(list(module.children())), 4)  # pads, horizontal, vertical, fuse
        with self.assertRaises(ValueError):
            module(torch.zeros(1,16,31,40))
        with self.assertRaises(ValueError):
            PConv(16,30)

    def test_trainer_rebuild_keeps_pconv(self):
        import torch
        from uav_detection.modeling import build_detector
        from uav_detection.architecture import UAVDetectionTrainer
        from uav_detection.pconv import PConv
        original = build_detector("pconv").model
        original.names = {0:"uav"}
        with torch.no_grad():
            original.model[1].horizontal.conv.weight.fill_(0.125)
        trainer = UAVDetectionTrainer.__new__(UAVDetectionTrainer)
        trainer.data = {"nc":1,"channels":3,"names":{0:"uav"}}
        trainer.args = SimpleNamespace(cls_remap=True)
        rebuilt = trainer.get_model(cfg=original.yaml, weights=original, verbose=False)
        self.assertIsInstance(rebuilt.model[1], PConv)
        self.assertTrue(torch.equal(rebuilt.model[1].horizontal.conv.weight,
                                    original.model[1].horizontal.conv.weight))
        self.assertTrue(rebuilt.end2end)

    def test_transfer_excludes_reindexed_heads(self):
        import torch
        from uav_detection.modeling import build_detector
        from uav_detection.architecture import transfer_shared_prefix
        source = build_detector("baseline").model
        target = build_detector("p2").model
        untouched = {k:v.clone() for k,v in target.state_dict().items() if int(k.split('.')[1]) >= 17}
        with torch.no_grad():
            source.model[0].conv.weight.fill_(0.125)
        report = transfer_shared_prefix(target, source)
        self.assertGreater(report["copied_tensors"], 0)
        self.assertTrue(torch.equal(source.model[0].conv.weight,target.model[0].conv.weight))
        for key, value in untouched.items():
            self.assertTrue(torch.equal(value,target.state_dict()[key]), key)
        pconv = build_detector("pconv").model
        self.assertEqual(transfer_shared_prefix(pconv,source)["excluded_layers"],[1])

    def test_checkpoint_roundtrip_and_pretrained_path(self):
        import torch
        from uav_detection.architecture import UAVYOLO
        from uav_detection.modeling import build_detector
        from uav_detection.pconv import PConv
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/"synthetic-test.pt"
            original = build_detector("pconv")
            original.save(path)
            restored = UAVYOLO(str(path), task="detect")
            self.assertIsInstance(restored.model.model[1],PConv)
            self.assertEqual(restored.model.yaml["uav_variant"],"pconv")
            for key, value in original.model.state_dict().items():
                torch.testing.assert_close(restored.model.state_dict()[key].float(),value.half().float(),rtol=0,atol=0)
            loaded = build_detector("p2",path)
            self.assertGreater(loaded.transfer_report["copied_tensors"],0)
            self.assertEqual(loaded.model.stride.tolist(),[4,8,16,32])


if __name__ == "__main__":
    unittest.main()
