"""Pinwheel-shaped convolution adapted from JN-Yang/PConv-SDloss-Data (MIT).

Reference commit: a801f043c83f73aa9af9ab2f689e59ebef928fc4, model/APConv.py.
The two opposite horizontal branches share weights, as do the vertical branches.
"""
import torch
from torch import nn
from ultralytics.nn.modules import Conv


class PConv(nn.Module):
    def __init__(self, c1: int, c2: int, kernel: int = 3, stride: int = 2):
        super().__init__()
        if c2 < 4 or c2 % 4 or kernel < 1 or stride not in (1, 2):
            raise ValueError("PConv requires c2 divisible by 4, positive kernel, stride 1 or 2")
        self.stride_value = stride
        pads = [(kernel, 0, 1, 0), (0, kernel, 0, 1),
                (0, 1, kernel, 0), (1, 0, 0, kernel)]
        self.pads = nn.ModuleList(nn.ZeroPad2d(pad) for pad in pads)
        self.horizontal = Conv(c1, c2 // 4, (1, kernel), stride, p=0)
        self.vertical = Conv(c1, c2 // 4, (kernel, 1), stride, p=0)
        self.fuse = Conv(c2, c2, 2, 1, p=0)

    def forward(self, x):
        # Official asymmetric-padding geometry uses H/stride and W/stride.
        if x.shape[-1] % self.stride_value or x.shape[-2] % self.stride_value:
            raise ValueError("PConv input dimensions must be divisible by its stride")
        branches = [self.horizontal(self.pads[0](x)), self.horizontal(self.pads[1](x)),
                    self.vertical(self.pads[2](x)), self.vertical(self.pads[3](x))]
        return self.fuse(torch.cat(branches, dim=1))
