"""Version-pinned PF-inspired YOLO26 integration; no global parser patches."""
from copy import deepcopy
import torch
from ultralytics.nn.modules.head import Detect
from ultralytics.utils import RANK
from .architecture import UAVDetectionModel, UAVDetectionTrainer, UAVYOLO
from .pf_prompt import PFPromptNeck


class PFPromptDetect(Detect):
    def __init__(self, original, spec):
        channels = tuple(branch[0].conv.in_channels for branch in original.cv2)
        self.legacy = original.legacy
        super().__init__(nc=original.nc,reg_max=original.reg_max,
                         end2end=original.end2end,ch=channels)
        # Preserve native head state and keys before registering extra modules.
        self.load_state_dict(original.state_dict(), strict=True)
        self.stride = original.stride.clone()
        self.end2end = original.end2end
        for name in ('i','f','type','inplace'):
            if hasattr(original,name): setattr(self,name,getattr(original,name))
        self.prompt_neck = PFPromptNeck(channels, **spec)
        self.np = sum(p.numel() for p in self.parameters())
        self.type = 'uav_detection.PFPromptDetect'

    def forward(self, x):
        return super().forward(self.prompt_neck(x))


class PFDetectionModel(UAVDetectionModel):
    def __init__(self, cfg='yolo26n.yaml',ch=3,nc=None,verbose=False):
        super().__init__(cfg,ch=ch,nc=nc,verbose=verbose)
        spec = deepcopy(self.yaml.get('pf_prompt'))
        if not isinstance(spec,dict):
            raise ValueError('PF variant requires explicit pf_prompt metadata')
        self.router_loss_weight = spec.pop('router_loss_weight',0.01)
        if not 0 <= self.router_loss_weight <= 1:
            raise ValueError('Invalid router balance loss weight')
        self.model[-1] = PFPromptDetect(self.model[-1],spec)

    def loss(self,batch,preds=None):
        detection, items = super().loss(batch,preds)
        router_loss = self.model[-1].prompt_neck.last_router_loss
        if router_loss is None:
            raise RuntimeError('Router loss requires a fresh PF head forward pass')
        auxiliary = self.router_loss_weight * router_loss
        self.model[-1].prompt_neck.last_router_loss = None
        # This pinned backend logs component dictionaries, including custom keys.
        if not isinstance(items, dict):
            raise RuntimeError('Expected the pinned backend loss-items dictionary')
        return detection.sum() + auxiliary * batch['img'].shape[0], {
            **items, 'router_loss': auxiliary.detach()}



class PFDetectionTrainer(UAVDetectionTrainer):
    def get_model(self,cfg=None,weights=None,verbose=True):
        model = self.set_model_names_for_load(PFDetectionModel(
            cfg,nc=self.data['nc'],ch=self.data.get('channels',3),verbose=verbose and RANK==-1))
        if weights is not None: model.load(weights)
        return model



class PFYOLO(UAVYOLO):
    @property
    def task_map(self):
        mapping = super().task_map
        mapping['detect'] = {**mapping['detect'],'model':PFDetectionModel,'trainer':PFDetectionTrainer}
        return mapping
