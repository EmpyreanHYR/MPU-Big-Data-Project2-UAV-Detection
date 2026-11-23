# PinP2-YOLO 候选区域视觉语言复核

使用冻结 H10 预测与 Qwen/Qwen2.5-VL-3B-Instruct 进行离线复核。主方案仅查询 0.25≤score<0.60 的候选，每图按置信度升序取至多 2 个。`BIRD/BACKGROUND` 删除；`UAV/UNCERTAIN/非法输出` 保留。E2 查询全部候选，E4 使用同一组选择性候选的局部裁剪。

公开结论见 [NMS与视觉语言结果分析](../../docs/results/NMS_VLM_AUDIT_20261115.md)。完整中文结果、指标CSV、FP–Recall图及设备信息保存在被Git忽略的私有 `outputs/` 中。检测器权重在本实验全程冻结。

## 本轮实测结论（2026-11-15）

E0—E4 已完成，689 条原始响应和远端环境已备份并复核。主方案 E3 的 TP/FP/FN 为 **184/12/302**，基线为 **323/119/163**：误报从 119 降到 12，召回率从 **66.46% 降到 37.86%**。相同召回率下，YOLO-only 阈值约 0.598 已得到 **184/11/302**，FP 比视觉语言方案少 1。多query语义复核在该设置下与阈值调整相当，故未纳入 H10 部署路径。

E3 调用 247 次，平均 236.93 ms、P95 270.70 ms，累计 58.52 秒。全部 689 条回答中没有 UNCERTAIN，保守退让规则未触发。

报告V-J及表VIII已收录该结果。清晰语义正例与数值控制作为后续扩展方向。

## 复现

本机用 Python、NumPy、Pillow 做裁剪与原评价器重放；绘图额外使用 Matplotlib。模型加载和推理在GPU服务器执行。

```sh
python prepare_candidates.py --predictions /path/to/detections.npz \
  --annotations /path/to/annotation_groups.json \
  --images-zip /path/to/validation_data.zip --out outputs
```

该命令要求目标目录不存在，验证 500 张图像和标签哈希，并断言基线 TP/FP/FN=323/119/163、AP50:95≈0.243511。`box_id` 指向原始低阈值检测列表。裁剪边界用整数向下取整，边长向上取整并平移到图像内部；原始 PNG 保留原图像素，推理时以 Pillow BILINEAR 缩放至 448×448。

将 `config.json`、`candidates.jsonl` 和 `crops/` 组成无真值的 GPU 输入目录。服务器独立 venv 复用既有 Torch 2.1.2+cu118，并安装 Transformers 4.51.3、Accelerate 1.6.0、HuggingFace Hub 0.30.2、Pillow 11.2.1、ModelScope 1.25.0。精确依赖以运行输出 `environment.json` 为准。

`download_model.py`、`run_vlm.py`及监督脚本包含本机连接设置，在GPU服务器执行。公开代码提供候选准备和保存响应的指标重放，完整推理流程如下：

```sh
python download_model.py
# GPU 服务器：模型目录按实际下载位置填写。
timeout --signal=TERM --kill-after=30s 2h python run_vlm.py \
  --input /path/to/gt_free_input --output /path/to/vlm_outputs --model /path/to/model
```

`run_vlm.py` 持有项目GPU锁并校验运行主机；逐条 fsync 缓存，重跑只用相同输入、配置和模型哈希继续未完成键。CUDA 错误/OOM 等异常中止本次运行。单次超时和不合法文本按 UNCERTAIN 处理。前 4 条记录为 smoke test；1 次预热单独记录，稳态延迟不含预热。生成使用 greedy decoding，最多 16 tokens，batch 1、FP16、eager attention。

把 GPU 输出复制回本机 `outputs/` 后运行：

```sh
python fuse_and_eval.py --out outputs
python compare_experiments.py --out outputs
```

评估调用 `scripts/evaluation/detection_eval.py`，原评价器保持不变。图像顺序固定为原验证标注清单顺序，同分预测使用原评价器的稳定排序；E3 NPZ 导出使用同一顺序，同分 AP 与原评价器一致。固定阈值指标在过滤之后重新匹配；AP 使用原 0.001 下限完整列表，只删除被复核判为负例的 ≥0.25 候选，低分未查询候选继续参与 AP。E1 穷举保存预测在 ≥0.25 的置信度断点，并与 E3 最接近召回及不低于其召回的最少 FP 工作点比较。

这 500 张图像是内部验证集，参数和提示词在运行前冻结，因此直接报告全体内部验证结果，作为内部验证评价。Qwen 官方模型来源：[Hugging Face 模型卡](https://huggingface.co/Qwen/Qwen2.5-VL-3B-Instruct)和[ModelScope 同名模型](https://modelscope.cn/models/Qwen/Qwen2.5-VL-3B-Instruct)。
