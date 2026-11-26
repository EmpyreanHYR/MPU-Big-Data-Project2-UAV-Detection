# 08 速答卡 / Quick Answer Card

> 考前 10 分钟只看这一页。先记结论和口径，再记数字。 / Review this page 10 minutes before the presentation. Learn the conclusions and protocols first, then the numbers.

## 20 个速答 / 20 Quick Answers

### 1. 项目一句话 / One-sentence project
**中**：在清洗后的 SIRST-UAVB 上，把浅层 PConv 和 stride-4 P2 接入 YOLO26n，从零训练 100 轮，原生 AP50:95 31.274%，部署到 Pi5 + H10 以 22.89 FPS 运行。  
**EN**: We added a shallow PConv and a stride-4 P2 branch to YOLO26n, trained from scratch for 100 epochs on cleaned SIRST-UAVB, reached 31.274% native AP50:95, and deployed to Pi5 + H10 at 22.89 FPS.

### 2. 为什么红外 / Why infrared
**中**：不依赖可见光照明，适合夜间/低照度被动监测；但低对比度、热交叉仍是难点。  
**EN**: It does not rely on visible illumination, so it suits passive night/low-light monitoring; low contrast and thermal crossover remain hard.

### 3. 和大数据的关系 / Big-data framing
**中**：真实性（494 重复/7 冲突）、体量（500/1000/1999 训练与 125/250/500 推理负载）、速度（H10 吞吐/延迟）。  
**EN**: Veracity (494 duplicates/7 conflicts), volume (500/1000/1999 training and 125/250/500 inference loads), and velocity (H10 throughput/latency).

### 4. 数据怎么清洗 / Data cleaning
**中**：3000 张 → 像素哈希去 494 张重复 → 隔离 7 张冲突 → 2499 张；seed42 按背景视图分 1999/500。  
**EN**: 3000 → remove 494 pixel duplicates → isolate 7 conflicts → 2499; split 1999/500 by background view with seed42.

### 5. 为什么 1999/500 / Why this split
**中**：约 80/20，验证集 486 个 UAV 框 + 15 负样本；够粗比较，不够窄置信区间。  
**EN**: About 80/20, with 486 UAV boxes and 15 negatives in validation; enough for coarse comparison, not narrow confidence intervals.

### 6. 为什么 YOLO26n / Why YOLO26n
**中**：2.504M 参数、单阶段、端到端头、部署简单；原生 27.952% 基线与改进空间。  
**EN**: 2.504M parameters, single-stage, end-to-end head, simple deployment; a 27.952% native baseline with room to improve.

### 7. PConv 是什么 / What PConv is
**中**：四方向非对称 padding，水平/垂直分支共享权重，2×2 融合；第 1 个下采样卷积 4,960 vs 4,672 参数，只 +288。  
**EN**: Four asymmetric-padding directions, shared horizontal/vertical weights, 2×2 fusion; the first downsampling convolution uses 4,960 vs 4,672 parameters, only +288.

### 8. P2 是什么 / What P2 is
**中**：stride-4、160×160 的浅层检测支路，形成 P2/P3/P4/P5 四尺度；代价是显存和延迟。  
**EN**: A stride-4, 160×160 shallow detection branch, giving P2/P3/P4/P5 scales; the cost is memory and latency.

### 9. 消融结果 / Ablation
**中**：B0 27.952，B1（PConv）24.381，B2（P2）29.975，B3（PinP2）31.274；组合 +3.322，PConv 单独 −3.571。  
**EN**: B0 27.952, B1 (PConv) 24.381, B2 (P2) 29.975, B3 (PinP2) 31.274; combination +3.322, PConv alone −3.571.

### 10. 和 YOLO11n/8n 比 / Versus YOLO11n/8n
**中**：原生 PinP2 更高；H10 上 YOLO11n AP 高 1.714 但慢（18.54 对 22.72 FPS）；YOLOv8n 漏检低 3.086、AP 略高 0.459，但参数多（3.011M）、速度略慢（18.85 FPS）。  
**EN**: PinP2 has higher native AP; on H10, YOLO11n is 1.714 AP higher but slower (18.54 vs 22.72 FPS), while YOLOv8n has a 3.086-point lower miss rate and 0.459 higher AP, but more parameters (3.011M) and slightly lower speed (18.85 FPS).

### 11. 原生最高是谁 / Highest native AP
**中**：PConv+SD 的 32.93%，但它是 YOLOv8n-P2 架构、H10 只有 18.125%/7.17 FPS/331 FP，不是同一消融。  
**EN**: PConv+SD at 32.93%, but it is a YOLOv8n-P2 architecture and only 18.125%/7.17 FPS/331 FPs on H10; it is not the same ablation.

### 12. 31.274 还是 31.740 / Which final number
**中**：31.274 是原生最佳检查点；31.740 是 H10 + NMS 0.4 部署路径。权重冻结，NMS 不找回漏检。  
**EN**: 31.274 is the native best checkpoint; 31.740 is the H10 + NMS 0.4 deployment path. Weights are frozen, and NMS does not recover misses.

### 13. H10 为什么掉 / Why H10 is lower
**中**：原生→共同 FP32 差 6.088 pp 是评价路径；共同 FP32 25.186→H10 24.351 的 0.835 pp 才是量化。  
**EN**: The 6.088-point native-to-common-FP32 gap is evaluation path; the 0.835-point common-FP32-to-H10 gap (25.186→24.351) is quantization.

### 14. 22.89 FPS 是什么 / What 22.89 FPS means
**中**：500 图、H10、NMS 0.4、无绘图/网络；43.70 ms；不是 GUI 帧率。  
**EN**: 500 images, H10, NMS 0.4, no drawing/network; 43.70 ms; not the GUI frame rate.

### 15. 为什么 NMS 0.4 / Why NMS 0.4
**中**：0.3/0.4/0.5 的 FP 是 62/62/63，AP 31.742/31.740/31.676；0.4 是召回不变、FP 最低中较大的一档。  
**EN**: FP at 0.3/0.4/0.5 is 62/62/63, AP 31.742/31.740/31.676; 0.4 is the larger threshold with unchanged recall and the lowest FP.

### 16. 演示为什么 0 检出 / Why demo shows zero
**中**：30 张外部静图，FP32 也 0 TP；域差 + 框尺度/形状不匹配 + 低置信度；演示不代表验证集精度。  
**EN**: 30 external stills; FP32 also gives 0 TP; domain shift + box scale/shape mismatch + low confidence; the demo is not validation accuracy.

### 17. GUI 为什么 10–16 FPS / Why GUI is 10–16 FPS
**中**：Qt 绘制、PNG 编码、SSH/Tailscale、录屏开销；Pi 本机 5 分钟 16.51 FPS；H10 处理约 46 ms。  
**EN**: Qt drawing, PNG encoding, SSH/Tailscale, and recording overhead; Pi-native five-minute loop is 16.51 FPS; H10 processing is about 46 ms.

### 18. 外部 AUVD / External AUVD
**中**：300 图、冻结权重、不调阈值；AP50 33.008、AP50:95 11.494；域差明显，不能代表所有真实场景。  
**EN**: 300 images, frozen weights, no threshold tuning; AP50 33.008, AP50:95 11.494; clear domain shift, not representative of all real scenes.

### 19. 最大局限 / Biggest limitations
**中**：无独立测试集（选择和阈值同集）、单 seed、无独立连续视频；另有物理 batch 不同、密集场景未测。  
**EN**: No independent test set (selection and threshold on the same split), one seed, no independent continuous video; plus different physical batches and untested dense scenes.

### 20. 团队分工 / Team roles
**中**：Yaorong Huang 模型/实验/部署；Chunshen Yu 汇报/可视化；Yifan Zhai 应用测试/误差分析；Zhiwen Luo 数据构建/清洗。  
**EN**: Yaorong Huang: model/experiments/deployment; Chunshen Yu: presentation/visualization; Yifan Zhai: application testing/error analysis; Zhiwen Luo: dataset construction/cleaning.

> 姓名以报告英文名为准；现场如需中文名，按团队确认的写法，不要临场猜字。 / Use the English names as listed in the report; if Chinese names are needed on stage, use the team-confirmed spelling rather than guessing characters.

## 30 秒项目介绍 / 30-Second Pitch

**中文**：我们的项目是红外无人机检测。数据是 SIRST-UAVB，原始 3000 张，我们去掉了 494 张像素重复、隔离了 7 张标注冲突，保留 2499 张，按背景视图分成 1999 训练、500 验证。模型以 YOLO26n 为基线，把第 1 个下采样卷积换成浅层 PConv，再加一条 stride-4 的 P2 检测支路，从零训练 100 轮。原生 AP50:95 是 31.274%，比基线高 3.322 个百分点；PConv 单独会掉 3.571，说明收益来自组合而不是单个模块。最后我们把模型编译到 Hailo-10H，在树莓派 5 上以 22.89 FPS 运行，并用 NMS 0.4 把部署路径的 AP 从 24.351 提到 31.740。我们也如实报告了局限：没有独立测试视频、单 seed、密集场景没测。

**English**: Our project is infrared UAV detection. We start from SIRST-UAVB: 3000 raw images, from which we remove 494 pixel duplicates and isolate 7 annotation conflicts, keeping 2499 and splitting them by background view into 1999 training and 500 validation. The model is based on YOLO26n: the first downsampling convolution becomes a shallow PConv, and a stride-4 P2 detection branch is added. We train from scratch for 100 epochs. Native AP50:95 is 31.274%, 3.322 points above the baseline; PConv alone drops by 3.571, so the gain comes from the combination, not from either module alone. We compile the final model for Hailo-10H, run it on a Raspberry Pi 5 at 22.89 FPS, and use NMS 0.4 to raise the deployment-path AP from 24.351 to 31.740. We also report the limitations honestly: no independent test video, one seed, and no dense-scene test.

## 四个 AP 数字，别混 / Four AP Numbers, Do Not Mix

| 说法 / Label | 数字 / Value | 用在哪里 / Use |
|---|---:|---|
| 原生 AP50:95 / Native | **31.274%** | 模型间比较 / model comparison |
| 共同 FP32 部署 / Common FP32 | 25.186% | 跨设备同路径 / cross-device common path |
| H10 无 NMS / H10 no NMS | 24.351% | 量化后、无后处理 / quantized, no post-processing |
| H10 + NMS 0.4 | **31.740%** | 默认部署验收 / default deployment acceptance |

**一句话**：31.274 和 31.740 都是真的，但前者是原生、后者是部署；不要用后者证明“模型比原生更好”。 / Both 31.274 and 31.740 are real, but the first is native and the second is deployment; do not use the second to claim the model is better than native.

## 禁语清单 / Phrases to Avoid

- ❌ “我们的模型是 SOTA / 全面最优。” → ✅ “在我们比较的 11 个模型里，PinP2 是精度/速度/体积比较均衡的一个。”
- ❌ “H10 31.740 比原生 31.274 高，所以部署后更准。” → ✅ “31.740 是加了 NMS 的部署路径，TP/FN 没变，不是模型变强。”
- ❌ “22.89 FPS 就是 GUI 帧率。” → ✅ “22.89 是 H10 管线基准；GUI 显示约 10–16 FPS。”
- ❌ “PConv 单独也有效。” → ✅ “PConv 单独下降 3.571，和 P2 组合才观察到 +3.322。”
- ❌ “SIA/MSF/RT-DETR 是 0 分。” → ✅ “E1/E2 是没有测到，不是 0 分。”
- ❌ “量化掉了 6.9 个点。” → ✅ “原生→共同路径 6.088 是口径差；量化差是 0.835。”
- ❌ “已经支持视频/密集目标。” → ✅ “演示是 30 张静图循环；密集场景没有充分测。”
- ❌ “功耗很低。” → ✅ “没有测功耗，只记录了温度和降频标志。”
- ❌ “所有模型完全公平。” → ✅ “数据/评价一致，但 B2/B3 物理 batch 不同，是局限。”

## 被问住时怎么说 / When You Are Stuck

- **中文**：“这个我们还没有测，我不能给结论。我可以说明为什么没测，以及下一步怎么补。”
- **English**: “We have not measured that, so I cannot give a conclusion. I can explain why and how we would test it next.”
- **中文**：“这个数字要看口径。我先确认是原生、共同 FP32，还是 H10 部署。”
- **English**: “That number depends on the protocol. Let me first confirm whether it is native, common FP32, or H10 deployment.”
- **中文**：“具体数值我记不清，报告的表里有，我不猜。”
- **English**: “I do not remember the exact value; it is in the report table, and I will not guess.”
- **中文**：“这部分是队友负责的，我请他来补充。”
- **English**: “A teammate owns that part; I will ask them to add detail.”

## 最后检查 / Final Checklist

- [ ] 能不看稿说出 31.274 / 31.740 / 24.351 / 25.186 四个数的区别。
- [ ] 能解释 22.89 FPS 不是 GUI 帧率。
- [ ] 能说出 494 / 7 / 2499 / 1999 / 500 的清洗链路。
- [ ] 能说出 B0–B3 和 +3.322 / −3.571 / +1.299。
- [ ] 能主动说三个局限：无独立测试、单 seed、无连续视频。
- [ ] 不会把 E1/E2 说成 0 分，不会说 SOTA，不会报未测的功耗。

- [ ] Can explain the difference among 31.274 / 31.740 / 24.351 / 25.186 without notes.
- [ ] Can explain that 22.89 FPS is not the GUI frame rate.
- [ ] Can state the cleaning chain: 494 / 7 / 2499 / 1999 / 500.
- [ ] Can state B0–B3 and +3.322 / −3.571 / +1.299.
- [ ] Can volunteer three limitations: no independent test, one seed, no continuous video.
- [ ] Never call E1/E2 zero, never claim SOTA, never report unmeasured power.
