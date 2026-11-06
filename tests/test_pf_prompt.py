"""Cloud-only CPU synthetic integration checks; never import Torch on Mac/Pi."""
import importlib.util
import os
from pathlib import Path
import platform
import socket
import sys
import tempfile
import unittest
from copy import deepcopy
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
AVAILABLE = (platform.system()=='Linux' and platform.machine().lower() in {'x86_64','amd64'}
             and socket.gethostname()=='autodl-container-31da11b852-51b08bdd'
             and all(importlib.util.find_spec(x) for x in ('torch','ultralytics')))


@unittest.skipUnless(AVAILABLE,'Run synthetic model checks only on the authorized cloud host')
class PFIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import torch
        torch.set_num_threads(2)
        torch.manual_seed(42)
        assert not torch.cuda.is_initialized(), 'CPU fixtures must not use GPU'

    def test_identity_empty_masks_and_batch_independence(self):
        import torch
        from uav_detection.pf_prompt import PFPromptNeck
        neck=PFPromptNeck([8,16,32],iterations=3,threshold=1.0).eval()
        features=[torch.randn(2,c,h,w) for c,h,w in [(8,16,20),(16,8,10),(32,4,5)]]
        with torch.no_grad():
            output=neck(features)
            for batch in range(2):
                single=neck([x[batch:batch+1] for x in features])
                for actual,expected in zip(single,output):
                    torch.testing.assert_close(actual,expected[batch:batch+1],rtol=1e-5,atol=1e-6)
            neck.gain.zero_()
            for actual,expected in zip(neck(features),features):
                torch.testing.assert_close(actual,expected,rtol=0,atol=0)
        self.assertTrue(all(torch.isfinite(x).all() for x in output))
        self.assertIsNone(deepcopy(neck).last_router_loss)
        with self.assertRaises(ValueError):PFPromptNeck([8,16],topk=3)
        with self.assertRaises(ValueError):neck(features[:2])

    def test_forward_loss_and_gradients(self):
        import torch
        from ultralytics.cfg import get_cfg
        from uav_detection.modeling import build_detector
        from uav_detection.pf_architecture import PFPromptDetect
        for variant in ('pf_sia','pf_sia_csp'):
            model=build_detector(variant).model.cpu()
            self.assertIsInstance(model.model[-1],PFPromptDetect)
            self.assertEqual(model.stride.tolist(),[8,16,32])
            self.assertTrue(model.end2end)
            model.eval()
            with torch.no_grad():
                for h,w in [(128,128),(128,160)]:
                    output,raw=model(torch.rand(1,3,h,w))
                    self.assertEqual(output.shape[-1],6)
                    self.assertTrue(torch.isfinite(output).all())
                    self.assertEqual(len(raw['one2one']['feats']),3)
            model.train(); model.args=get_cfg()
            batch={'img':torch.rand(2,3,128,160),'batch_idx':torch.tensor([0.,1.]),
                   'cls':torch.zeros(2,1),'bboxes':torch.tensor([[.5,.5,.125,.125],[.4,.4,.1,.1]])}
            loss,items=model(batch)
            self.assertEqual(loss.numel(),1)
            self.assertEqual(len(items),4)
            self.assertIn("router_loss",items)
            self.assertTrue(torch.isfinite(loss).all())
            loss.sum().backward()
            neck=model.model[-1].prompt_neck
            for parameter in (neck.router.weight,neck.project[0].weight,neck.prompt,neck.gain):
                self.assertIsNotNone(parameter.grad)
                self.assertTrue(torch.isfinite(parameter.grad).all())
                self.assertGreater(parameter.grad.abs().sum().item(),0)
            self.assertIsNone(neck.last_router_loss)
            self.assertIsNone(deepcopy(model).model[-1].prompt_neck.last_router_loss)

    def test_trainer_rebuild_validator_and_checkpoint(self):
        import torch
        from uav_detection.modeling import build_detector
        from uav_detection.pf_architecture import PFDetectionTrainer,PFYOLO,PFPromptDetect
        model=build_detector('pf_sia_csp').model
        model.names={0:'uav'}
        trainer=PFDetectionTrainer.__new__(PFDetectionTrainer)
        trainer.data={'nc':1,'channels':3,'names':{0:'uav'}}
        trainer.args=SimpleNamespace(cls_remap=True)
        rebuilt=trainer.get_model(cfg=model.yaml,weights=model,verbose=False)
        self.assertIsInstance(rebuilt.model[-1],PFPromptDetect)
        for k,v in model.state_dict().items():torch.testing.assert_close(v,rebuilt.state_dict()[k])
        rebuilt.eval();model.eval()
        x=torch.rand(1,3,128,128)
        with torch.no_grad():torch.testing.assert_close(model(x)[0],rebuilt(x)[0])
        wrapper=build_detector('pf_sia_csp')
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'synthetic.pt';wrapper.save(p)
            restored=PFYOLO(str(p),task='detect')
            self.assertIsInstance(restored.model.model[-1],PFPromptDetect)
            self.assertEqual(restored.model.yaml['pf_prompt']['iterations'],3)
        # Exercise the real native validator construction and its loss labels.
        from ultralytics.cfg import get_cfg
        with tempfile.TemporaryDirectory() as folder:
            trainer.test_loader=[];trainer.save_dir=Path(folder)
            trainer.args=get_cfg();trainer.callbacks={}
            validator=trainer.get_validator()
            self.assertIsNotNone(validator)


if __name__=='__main__': unittest.main(verbosity=2)
