"""Lightweight SIA/CSP adaptation of PF-RPN, not the original universal RPN.

Source: Tang et al., CVPR 2026, Sec.3.2--3.3, equations1--3.
Original author code: github.com/tangqh03/PF-RPN, PFRPN methods
_build_sparse_moe_pseudo_text and cascade_self_prompt_enhancement.
This independent implementation uses one visual token and a single shared
cross-attention layer; YOLO features receive a new residual similarity gate.
"""
import torch
from torch import nn
from torch.nn import functional as F


class PFPromptNeck(nn.Module):
    def __init__(self, channels, embed_dim=32, topk=2, iterations=3,
                 threshold=0.3, heads=4):
        super().__init__()
        if not channels or any(type(c) is not int or c <= 0 for c in channels):
            raise ValueError('Positive input channels required')
        if type(topk) is not int or not 1 <= topk <= len(channels):
            raise ValueError('topk must be within pyramid level count')
        if type(iterations) is not int or not 0 <= iterations <= 3:
            raise ValueError('Use zero (SIA-only) or one to three CSP iterations')
        if type(embed_dim) is not int or embed_dim <= 0 or embed_dim % heads:
            raise ValueError('embed_dim must be positive and divisible by heads')
        if not -1 <= threshold <= 1:
            raise ValueError('Cosine threshold must be in [-1,1]')
        self.channels = tuple(channels)
        self.topk, self.iterations, self.threshold = topk, iterations, threshold
        self.project = nn.ModuleList(nn.Conv2d(c, embed_dim, 1, bias=False) for c in channels)
        self.prompt = nn.Parameter(torch.empty(1, 1, embed_dim))
        nn.init.normal_(self.prompt, std=0.02)
        self.router = nn.Linear(embed_dim, 1)
        self.attention = nn.MultiheadAttention(embed_dim, heads, batch_first=True)
        self.norm = nn.LayerNorm(embed_dim)
        self.gain = nn.Parameter(torch.full((len(channels),), 0.1))
        # Transient forward state, excluded from weights and persistent buffers.
        self.last_router_loss = None
        self.last_router_weights = None

    def __getstate__(self):
        state = super().__getstate__()
        state["last_router_loss"] = None
        state["last_router_weights"] = None
        return state

    def forward(self, features):
        if len(features) != len(self.channels):
            raise ValueError('Pyramid level count does not match configured channels')
        batch = features[0].shape[0]
        for x, c in zip(features, self.channels):
            if x.ndim != 4 or x.shape[0] != batch or x.shape[1] != c:
                raise ValueError('Expected BCHW tensors with matching batch/channels')
        maps = [project(x) for project, x in zip(self.project, features)]
        tokens = [x.flatten(2).transpose(1,2) for x in maps]
        globals_ = torch.stack([x.mean(1) for x in tokens], dim=1)
        logits = self.router(globals_).squeeze(-1)
        probabilities = logits.softmax(dim=1)
        self.last_router_loss = probabilities.std(dim=1, unbiased=False).mean()
        self.last_router_weights = probabilities.detach()
        values, indices = logits.topk(self.topk, dim=1)
        selected_weights = values.softmax(dim=1)
        query = self.prompt.expand(batch, -1, -1)
        mixed = torch.zeros_like(query)
        # Only selected sample/level pairs enter attention, as in the author code.
        for level, local in enumerate(tokens):
            selected = (indices == level).nonzero(as_tuple=False)
            if selected.numel() == 0:
                continue
            b_idx, k_idx = selected.unbind(dim=1)
            memory = torch.cat([globals_[b_idx,level,None,:], local[b_idx]], dim=1)
            context, _ = self.attention(query[b_idx], memory, memory, need_weights=False)
            expert = self.norm(query[b_idx] + context)
            mixed = mixed.index_add(0, b_idx, selected_weights[b_idx,k_idx,None,None] * expert)
        prompt = mixed
        # Paper deep-to-shallow order, repeated three times by default.
        for _ in range(self.iterations):
            for local in reversed(tokens):
                similarity = F.normalize(local,dim=-1) @ F.normalize(prompt,dim=-1).transpose(1,2)
                mask = (similarity > self.threshold).to(local.dtype)
                pooled = (local * mask).sum(1,keepdim=True) / mask.sum(1,keepdim=True).clamp_min(1.0)
                prompt = prompt + pooled
        normalized_prompt = F.normalize(prompt, dim=-1).transpose(1,2)
        output = []
        for level,(x,local) in enumerate(zip(features,tokens)):
            similarity = (F.normalize(local,dim=-1) @ normalized_prompt).transpose(1,2)
            gate = similarity.reshape(batch,1,x.shape[2],x.shape[3])
            # New YOLO-specific bridge: bounded residual modulation, no box pruning.
            output.append(x * (1 + self.gain[level].tanh() * gate))
        return output
