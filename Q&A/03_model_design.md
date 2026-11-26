# 03 模型结构与方法 / Model Design

## Q01. PinP2-YOLO 的整体结构是什么？

**中文**：它以 YOLO26n 为基线，做两处改动：第一，把 backbone 第 1 个 stride-2 卷积换成四方向 PConv；第二，在 P3 旁边增加一条 stride-4 的 P2 支路，形成 P2/P3/P4/P5 四个检测尺度。检测头仍然使用 YOLO26 的端到端头，损失仍是 CIoU + BCE + L1，没有引入 DFL。名字里的“Pin”指 PConv 的风车形四分支，“P2”指新增的浅层检测支路。

**English**: It starts from YOLO26n and makes two changes. First, the first stride-2 convolution in the backbone becomes a four-direction PConv. Second, a stride-4 P2 branch is added beside P3, giving four detection scales: P2/P3/P4/P5. The head remains YOLO26's end-to-end head, and the loss remains CIoU + BCE + L1 without DFL. “Pin” refers to the pinwheel-shaped four-branch PConv; “P2” refers to the added shallow detection branch.

## Q02. PConv 具体是怎么做的？为什么叫“风车形”？

**中文**：PConv 用四个方向的非对称零填充，把同一个 3×3 感受野拆成上、下、左、右四条分支；两条水平分支共享 1×3 卷积权重，两条垂直分支共享 3×1 权重；每条输出 c2/4 通道，拼接后用 2×2 卷积融合回 c2 通道。四个方向围绕中心，所以叫风车形。它的目的不是增加很多参数，而是让浅层特征在水平/垂直方向上有更明确的响应。

**English**: PConv uses four asymmetric zero-padding patterns to split a 3×3 receptive field into top, bottom, left, and right branches. The two horizontal branches share a 1×3 convolution, and the two vertical branches share a 3×1 convolution. Each branch outputs c2/4 channels; after concatenation, a 2×2 convolution fuses them back to c2. The four directions surround the center, hence “pinwheel.” The goal is not a large parameter increase, but sharper horizontal/vertical responses in shallow features.

**细节 / Detail**: 分支的 padding 是 `(k,0,1,0)`、`(0,k,0,1)`、`(0,1,k,0)`、`(1,0,0,k)`；分支输出略大于 H/2×W/2，2×2 融合后回到 H/2×W/2，所以下采样几何保持不变。 / The branch paddings are `(k,0,1,0)`, `(0,k,0,1)`, `(0,1,k,0)`, `(1,0,0,k)`. The branch outputs are slightly larger than H/2×W/2, and the 2×2 fusion returns to H/2×W/2, so the downsampling geometry is preserved.

## Q03. PConv 参数量为什么只增加 288？

**中文**：YOLO26n 的 width 是 0.25，第 1 个卷积实际是 16→32 通道。原来的 3×3 卷积加 BN 是 4,672 个参数；PConv 是 4,960 个，差 288。PConv 虽然有四条分支，但每条只做 c2/4 通道，且水平/垂直分支共享权重，所以没有把参数量翻几倍。整个 PinP2 相对基线增加约 0.48%，主要来自 P2 支路（约 11,786 个参数），不是 PConv。

**English**: YOLO26n uses a width of 0.25, so its first convolution is actually 16→32 channels. The original 3×3 convolution plus BN has 4,672 parameters; PConv has 4,960, a difference of 288. Although PConv has four branches, each branch uses only c2/4 channels and the horizontal/vertical branches share weights, so the parameter count does not multiply. PinP2 grows by about 0.48% over the baseline, mainly from the P2 branch (about 11,786 parameters), not from PConv.

## Q04. 为什么替换第 1 个下采样卷积？为什么只改一个位置？

**中文**：第 1 个 stride-2 卷积处在分辨率还高、细节还多的位置，适合做浅层方向性增强；再往后感受野变大，小目标的空间信息已经被压缩。只改一个位置，是为了把变量控制住：B0–B3 的差异可以归因到 PConv、P2 或两者组合，而不是“这里也改、那里也改”。我们没有说这是最优位置；P1 或其他层没有测。

**English**: The first stride-2 convolution is still at a high resolution with rich detail, which makes it suitable for shallow directional enhancement. Deeper layers have larger receptive fields, and tiny-object spatial information is already compressed. We change only one location to control the variable: differences across B0–B3 can be attributed to PConv, P2, or their combination rather than to many simultaneous edits. We do not claim this is the optimal location; P1 and other layers were not tested.

## Q05. P2 支路是什么？为什么用 stride 4？

**中文**：P2 支路从 stride-4、160×160（输入 640 时）的浅层特征引出，经过上采样/拼接和 C3k2 融合，再接到检测头，使网络多出一个 160×160 的检测层。stride 4 是一个折中：比 stride 8 保留更多小目标位置，又不像 stride 2 那样把计算和显存推高。验证集 486 个 UAV 框里有 441 个小于 8 px，所以浅层高分辨率是有针对性的。

**English**: The P2 branch taps the stride-4, 160×160 shallow feature (for a 640 input), applies upsampling/concatenation and C3k2 fusion, and feeds an extra 160×160 detection level. Stride 4 is a compromise: it preserves more tiny-object location information than stride 8, without the compute and memory cost of stride 2. Of the 486 validation UAV boxes, 441 are below 8 px, so the shallow high-resolution path targets the actual scale distribution.

## Q06. 四个检测头会不会太贵？代价是什么？

**中文**：会贵。P2 的 160×160 特征图比 P3 的 80×80 多四倍空间位置，显存和计算都上升。实测 H10 上 PinP2 是 22.72 FPS，基线 YOLO26n 是 30.06 FPS；Pi CPU 上分别是 4.13 和 6.51 FPS；Pi CPU 峰值 RSS 从 165.9 MiB 升到 250.4 MiB。这就是“用小目标精度换吞吐和内存”的具体代价。

**English**: Yes. The 160×160 P2 map has four times as many spatial positions as the 80×80 P3 map, so both memory and compute increase. On H10, PinP2 runs at 22.72 FPS versus 30.06 FPS for the YOLO26n baseline; on the Pi CPU, 4.13 versus 6.51 FPS; peak Pi CPU RSS rises from 165.9 MiB to 250.4 MiB. That is the concrete cost of trading throughput and memory for tiny-object accuracy.

## Q07. 为什么不做 P1？P1 不是更细吗？

**中文**：P1 是 stride-2、320×320，空间位置又是 P2 的四倍，显存和延迟会明显更差；而且在红外小目标里，过浅的特征语义弱、噪声和纹理干扰更重。P2 是我们在“细节”和“可部署”之间的选择。P1 没有做实验，所以不能说 P1 一定不好，也不能说 P2 一定最优。

**English**: P1 would be stride-2 at 320×320, four times the spatial positions of P2, with clearly worse memory and latency. At the same time, very shallow features have weaker semantics and more texture/noise interference for infrared tiny targets. P2 is our choice between detail and deployability. We did not test P1, so we cannot say P1 is worse, nor that P2 is optimal.

## Q08. 损失函数是什么？和基线一致吗？

**中文**：一致。PinP2 沿用 YOLO26 的检测损失：分类用 BCE，框回归用 CIoU，另有 L1 项；端到端头同时有一对多和一对一分支，训练时两者加权。PConv+SD 对比模型里的 SD Loss 是另一条实验线，**没有**加进 PinP2。这样 B0–B3 的差异不会混入损失函数变化。

**English**: It is the same. PinP2 keeps YOLO26's detection loss: BCE for classification, CIoU for box regression, plus an L1 term; the end-to-end head has one-to-many and one-to-one branches with a training weight. The SD Loss in the PConv+SD comparison is a separate line of work and is **not** added to PinP2. This keeps loss changes out of the B0–B3 comparison.

## Q09. 什么是端到端头？没有 DFL 是什么意思？为什么还加 NMS？

**中文**：YOLO26 的检测头设置 `end2end=true`、`reg_max=1`，框回归直接预测距离，不做 DFL 的离散区间积分；推理时走一对一分支，取 top-300，理论上不需要 NMS。但“不需要”不等于“没有重复框”：我们在 H10 上仍看到同一目标附近的重复预测。于是把 NMS 作为显式后处理加进去，并单独测它对 AP、FP 和速度的影响。NMS 不是模型的一部分。

**English**: YOLO26 sets `end2end=true` and `reg_max=1`; box regression directly predicts distances instead of DFL's discrete-bin integration. Inference uses the one-to-one branch and keeps the top 300, so NMS is not required in principle. But “not required” does not mean “no duplicate boxes”: on H10 we still saw duplicates around the same target. We therefore add NMS as explicit post-processing and measure its effect on AP, FP, and speed separately. NMS is not part of the model.

## Q10. 为什么不用注意力、Transformer 或更复杂的模块？

**中文**：我们比较过 RT-DETR-L：原生 AP50:95 27.49%，但参数 32.808M，Pi CPU 只有 0.57 FPS，而且没有 H10 适配，边缘部署不现实。SIA 和 SIA+CSP 也试过：原生 24.88% 和 28.58%，没有超过 PinP2，而且本权重的 H10 导出/数值验证没有通过。注意力不是不能用，而是在这个数据规模和边缘预算下，没有表现出足够稳定的收益。

**English**: We compared RT-DETR-L: 27.49% native AP50:95, but 32.808M parameters, only 0.57 FPS on the Pi CPU, and no H10 adapter, which makes edge deployment impractical. We also tried SIA and SIA+CSP: 24.88% and 28.58% native, neither beating PinP2, and their own-weight H10 export/numerical validation did not pass. Attention is not unusable; at this data scale and edge budget, it did not show a sufficiently stable gain.

## Q11. 参数量只多一点，为什么速度会下降？

**中文**：参数量只反映权重数量，不反映激活图大小和乘加次数。P2 的 160×160 特征图让卷积在更高分辨率上运行，FLOPs 和内存带宽都上升；检测头的候选位置也更多。H10 的 22.72 FPS 对 30.06 FPS、Pi CPU 的 4.13 对 6.51，都是实测，不是从参数量推出来的。

**English**: Parameter count reflects weights, not activation size or multiply-accumulate work. The 160×160 P2 map runs convolutions at a higher resolution, increasing FLOPs and memory bandwidth; the head also has more candidate locations. The measured 22.72 versus 30.06 FPS on H10 and 4.13 versus 6.51 FPS on the Pi CPU come from hardware runs, not from parameter counts.

## Q12. 训练器重建模型时，怎么保证 PConv 没被换掉？

**中文**：我们没有改 Ultralytics 的全局解析器，而是用版本锁定的 `UAVYOLO` 适配器：`UAVDetectionModel` 在构建时读取 YAML 里的 `pconv_layers`，在 `super().__init__` 之后把第 1 层替换成 PConv，并把 `i`、`f`、`type`、`np` 元数据补齐。训练器用的是这个子类，所以保存/加载/重建都保留 PConv；另有 inference-only 测试检查层类型和输出。

**English**: We did not patch Ultralytics' global parser. We use the version-pinned `UAVYOLO` adapter: `UAVDetectionModel` reads `pconv_layers` from the YAML, replaces layer 1 with PConv after `super().__init__`, and restores the `i`, `f`, `type`, and `np` metadata. The trainer uses this subclass, so save/load/rebuild preserves PConv; inference-only tests check the layer type and outputs.

**边界 / Boundary**: 适配器锁定 `ultralytics==8.4.193`；换版本要先重跑检查，不能假设兼容。 / The adapter pins `ultralytics==8.4.193`; a version change requires rerunning the checks, not assuming compatibility.
