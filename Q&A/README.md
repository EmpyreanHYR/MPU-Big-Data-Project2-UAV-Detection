# 项目问答库 / Project Q&A Bank

> 课程 / Course：COMP6132 大数据概论小组项目 / Big Data Group Project  
> 学校 / Institution：澳门理工大学 / Macao Polytechnic University  
> 项目 / Project：PinP2-YOLO 红外无人机检测 / Infrared UAV Detection  
> 版本 / Version：2026-11-24（与当前报告口径一致 / aligned with the current report）

## 这是什么 / What This Is

这是答辩和课堂提问用的双语问答库。内容按“选题—数据—模型—训练—结果—部署—局限”组织，每问都有中文回答和英文回答。英文不是逐字翻译，而是适合口头表达的版本。

This is a bilingual Q&A bank for the final presentation and classroom questions. It follows the path from problem and data to model, training, results, deployment, and limitations. Every question has a Chinese answer and an English answer; the English is written for speaking, not as a literal translation.

## 使用方法 / How to Use

1. **答辩前**：先读 [08_quick_answers.md](08_quick_answers.md)，把 20 个速答和关键数字过一遍。
2. **按主题准备**：用下面的索引找到对应文件；每个问题先看中文，再用英文复述一遍。
3. **回答顺序**：先给结论，再给数字，再解释原因，最后主动说边界。不要一上来讲实现细节。
4. **被追问时**：回到“口径”二字。很多看似矛盾的数字，差异来自评价路径不同，不是模型变了。

1. **Before the presentation**: read [08_quick_answers.md](08_quick_answers.md) first and review the 20 quick answers and key numbers.
2. **Prepare by topic**: use the index below. Read the Chinese answer, then say the English version aloud.
3. **Answer structure**: conclusion first, then the number, then the reason, then the boundary. Do not start with implementation details.
4. **Under follow-up questions**: return to the evaluation protocol. Most apparent contradictions come from different measurement paths, not from a different model.

## 三条口径 / Three Ground Rules

### 1. 原生评价 ≠ 部署评价 / Native evaluation is not deployment evaluation

- **原生 31.274% AP50:95**：训练框架的原生验证器，最佳检查点，用于模型间比较。
- **共同 FP32 部署路径 25.186%**：冻结导出、统一预处理/解码/置信度下限，用于跨设备比较。
- **H10 无 NMS 24.351%**：在共同路径上再做 Hailo 量化，和共同 FP32 比只差 0.835 个百分点。
- **H10 + NMS 0.4 31.740%**：这是加了后处理的部署路径，不能反过来当作“比原生 31.274 更高”的证据。

- **Native 31.274% AP50:95**: the trainer's native validator on the best checkpoint, used for model-to-model comparison.
- **Common FP32 deployment path 25.186%**: frozen export with unified preprocessing, decoding, and confidence floor, used for cross-device comparison.
- **H10 without NMS 24.351%**: the same path plus Hailo quantization; the gap to common FP32 is only 0.835 percentage points.
- **H10 with NMS 0.4 31.740%**: a post-processed deployment path. It must not be presented as proof that the model beats the native 31.274%.

### 2. 22.89 FPS 是 H10 基准，不是 GUI 帧率 / 22.89 FPS is the H10 benchmark, not the GUI frame rate

- **22.89 FPS / 43.70 ms**：500 张验证图、H10、固定 NMS 0.4 的基准测试。
- **22.56 FPS / 44.33 ms**：另一次 500 图验收运行，不是矛盾。
- **10–11 FPS**：录屏窗口中的 GUI 显示帧率。
- **16.51 FPS**：树莓派本机 5 分钟循环的平均绘制帧率。
- GUI 还包含 Qt 绘制、PNG 编码、SSH/Tailscale 传输和显示刷新，不能直接拿模型基准帧率代替界面帧率。

- **22.89 FPS / 43.70 ms**: the 500-image H10 benchmark with NMS 0.4.
- **22.56 FPS / 44.33 ms**: a separate 500-image acceptance run, not a contradiction.
- **10–11 FPS**: the GUI display rate in the recorded window.
- **16.51 FPS**: the average draw rate of a five-minute loop on the Raspberry Pi itself.
- The GUI also includes Qt drawing, PNG encoding, SSH/Tailscale transfer, and display refresh. The model benchmark cannot stand in for the interface frame rate.

### 3. 没测过的不说更好 / Do not claim what was not measured

- P1、SAHI、跟踪、多 seed、板端功耗没有测，不能说“会更好”或“已经支持”。
- SIA、SIA+CSP、MSF-GhostNet-III 没有本权重的 H10 结果，标为 E1，不是 0 分。
- RT-DETR-L 没有 H10 适配，标为 E2，不是模型失败。
- 30 帧外部素材零检出是域差和定位尺度问题，不是“模型在验证集上失效”。

- P1, SAHI, tracking, multiple seeds, and board power were not tested. Do not say they “would be better” or that they are supported.
- SIA, SIA+CSP, and MSF-GhostNet-III have no H10 result for their own weights. They are marked E1, not scored as zero.
- RT-DETR-L has no H10 adapter. It is marked E2, not a model failure.
- Zero detections on 30 external frames come from domain and localization-scale mismatch, not from a collapse on the validation set.

## 关键数字速记 / Key Numbers at a Glance

| 项目 / Item | 数值 / Value | 口径 / Scope |
|---|---:|---|
| 原始 / 清洗后图像 / Raw → cleaned images | 3000 → 2499 | 494 张像素重复，7 张标注冲突隔离 / 494 pixel duplicates, 7 conflicts isolated |
| 训练 / 验证 / Train / val | 1999 / 500 | seed42，按推断背景视图分组 / grouped by inferred background view |
| 验证集 UAV 框 / Val UAV boxes | 486 | 另 15 张负样本 / plus 15 negatives |
| PinP2 参数量 / Parameters | 2,516,264（2.516M） | 从零训练模型 / scratch model |
| 原生 AP50:95 / Native AP50:95 | **31.274%** | 最佳检查点，原生验证器 / best checkpoint, native validator |
| 原生 AP50 / Native AP50 | **69.606%** | 同上 / same |
| 共同 FP32 AP50:95 / Common FP32 AP50:95 | 25.186% | 冻结导出、统一部署路径 / frozen export, unified path |
| H10 无 NMS AP50:95 / H10 no-NMS | 24.351% | 量化后、无后处理 / quantized, no post-processing |
| H10 + NMS 0.4 AP50:95 | **31.740%** | 默认部署路径 / default deployment path |
| H10 + NMS 0.4 漏检 / Miss rate | 33.539% | 163 FN / 486 |
| H10 基准帧率 / H10 benchmark | 22.89 FPS / 43.70 ms | 500 图、NMS 0.4 / 500 images, NMS 0.4 |
| Pi CPU 帧率 / Pi CPU | 4.13 FPS | 同一 500 图 / same 500 images |
| 模型体积 / Model size | ONNX 9.96 MiB / HEF 4.02 MiB | 最终 PinP2 / final PinP2 |
| 外部 AUVD AP50:95 / External AUVD | 11.494% | 300 图，冻结权重 / 300 images, frozen weights |
| 训练预算 / Training budget | 100 epochs, 640, seed42, FP32 | 当前 scratch100 组 / current scratch100 group |

> 这些数字以 `docs/report/report_zh.md` 和 `docs/results/` 下的当前表格为准。若报告数字更新，本文件夹要同步更新，不能留下两套口径。  
> These numbers follow the current tables in `docs/report/report_zh.md` and `docs/results/`. If the report changes, update this folder too; do not keep two versions of the truth.

## 文件索引 / File Index

| 文件 / File | 内容 / Content | 建议用时 / Suggested time |
|---|---|---|
| [01_topic_and_bigdata.md](01_topic_and_bigdata.md) | 选题动机、课程关联、创新点、伦理 / motivation, big-data framing, novelty, ethics | 8 分钟 / 8 min |
| [02_data_quality.md](02_data_quality.md) | 数据来源、去重、冲突、划分、鸟框、外部集 / sources, dedup, conflicts, split, birds, external set | 12 分钟 / 12 min |
| [03_model_design.md](03_model_design.md) | YOLO26n、PConv、P2、损失、端到端头 / YOLO26n, PConv, P2, loss, end-to-end head | 15 分钟 / 15 min |
| [04_training_experiments.md](04_training_experiments.md) | 训练配置、消融、训练比例、指标、公平性 / recipe, ablations, data fractions, metrics, fairness | 12 分钟 / 12 min |
| [05_results_errors.md](05_results_errors.md) | 主结果、对比、误差分层、外部集、统计边界 / main results, comparisons, error slices, external set, statistics | 15 分钟 / 15 min |
| [06_edge_gui.md](06_edge_gui.md) | Pi5/H10、量化、NMS、GUI、演示、复现 / Pi5/H10, quantization, NMS, GUI, demo, reproducibility | 15 分钟 / 15 min |
| [07_limits_team.md](07_limits_team.md) | 局限、展望、团队分工、收获 / limitations, future work, roles, lessons | 10 分钟 / 10 min |
| [08_quick_answers.md](08_quick_answers.md) | 20 个速答、30 秒项目介绍、禁语 / 20 quick answers, 30-second pitch, phrases to avoid | 考前 10 分钟 / 10 min before |

## 一句话版本 / One-Sentence Version

**中文**：我们在清洗后的 SIRST-UAVB 上，把浅层 PConv 和 stride-4 P2 融合接入 YOLO26n，从零训练 100 轮，得到 31.274% 的原生 AP50:95；最终模型在树莓派 5 + Hailo-10H 上以 22.89 FPS 运行，并用 NMS 0.4 把部署路径的 AP50:95 从 24.351% 提到 31.740%。

**English**: On cleaned SIRST-UAVB, we added a shallow PConv and a stride-4 P2 fusion branch to YOLO26n, trained from scratch for 100 epochs, and reached 31.274% native AP50:95. The final model runs at 22.89 FPS on a Raspberry Pi 5 with Hailo-10H, where NMS 0.4 raises the deployment-path AP50:95 from 24.351% to 31.740%.

## 维护约定 / Maintenance

- 新增问题：先判断属于哪个主题，再追加到对应文件末尾，编号连续。
- 新增数字：必须能指向 `docs/results/` 或 `docs/report/` 中的具体表；不能只写在问答里。
- 修改结论：同时检查 README 的“三条口径”和 08 的速答卡，避免前后矛盾。
- 不把内部路径、账号、设备凭据、未公开数据写进本文件夹。

- New questions go to the matching topic file, appended with a continuous number.
- Every new number must point to a specific table in `docs/results/` or `docs/report/`; never exist only in the Q&A.
- When a conclusion changes, update the three ground rules here and the quick card in 08 together.
- Do not put internal paths, accounts, device credentials, or non-public data in this folder.
