# 后续三组对比模型训练适配（2026-10-31）

用户授权在现有七组训练期间完成适配并供后续训练使用。Faster R-CNN、PConv+SD Loss/YOLOv8n-P2、MSF-GhostNet-III 已实现，云端CPU核心检查与真实小样本完整一轮训练/验证/保存检查均通过。CPU检查仅用2张train、2张val、128输入，不是正式结果。正式640输入的固定batch显存占用及完整150轮稳定性仍待各组启动时验证。

| 模型 | 正式物理 batch | 有效目标 batch | 入口与方法 |
|---|---:|---:|---|
| Faster R-CNN R50-FPN | 2，累积16次 | 32 | torchvision0.16.2，detector/backbone均weights=None；单UAV映射前景1，背景0；无目标样本保留 |
| PConv+SD / YOLOv8n-P2 | 8 | 32 | Ultralytics8.4.193，PConv固定浅层0/1，作者SDB回归损失delta0.5，保留原生DFL/分类/标签分配 |
| MSF-GhostNet-III | 16 | 32 | 作者III notebook图结构，独立补丁YOLOv5运行时与uv覆盖环境，anchors由训练数据原生拟合 |

三组均从零初始化、150轮、640输入、seed42、FP32、AdamW、lr0=0.001、lrf=0.01、weight_decay=0.0005。冻结数据为 `IR-UAV-DET-20261030-v1` 的5800train/1450val，Anti-UAV-detection2048图不用于训练、每轮验证、选点或本次检查。正式入口 `scripts/train_pending_adapter.py` 不接受恢复旧检查点或预训练权重参数。Faster的BatchNorm、letterbox+水平翻转、无EMA/无Mosaic是家族原生适配差异，不能称所有家族训练过程完全相同；最后不足32张的累积组按实际microbatch数归一化。

## 验证证据

Faster：正例与空目标共同反向传播、梯度有限、AdamW实际更新、state_dict精确重载、原生NMS；重复检测一对一匹配与空目标误报处理；实际完整CPU一轮产生验证指标、CSV及best/last。

PConv+SD：独立提取作者原始bbox_iou函数，与项目实现逐元素输出和梯度精确一致；PConv非零梯度与SD/DFL反向传播通过；训练器重建和完整检查点重载后保留模块与损失，输出精确一致；通过原生trainer完整一轮和最终best权重验证。位置0/1是项目明确选择的集成方式，不宣称逐项复制论文训练设置或原文成绩。

MSF：作者notebook结构逐项匹配nc/depth/width/anchors/backbone/head；Ghost模块、8/16/32步长、原生YOLOv5损失/更新/NMS和检查点输出精确重载通过；修复CSV-only日志初始化后，完整CPU一轮训练、验证、CSV和best/last通过。双图CPU夹具单独禁用autoanchor，正式训练仍保留仅根据训练标签的原生autoanchor。原始源码与补丁副本分开，补丁前后SHA256及修改文本保存在运行时 `adapter_patch_receipt.json`。MSF使用单独数据副本及逐文件哈希核对，避免旧版缓存或JPEG校验写入冻结数据或其他训练进程的缓存。

机器可读汇总：[检查记录](../checks/pending_adapters_20261031.json)。原始云端检查回执/日志、CPU夹具权重和运行时哈希保存在私有工作目录，不进入Git。

## 串行接续

`scripts/run_pending_suite.py` 使用独立控制器，等待前七组状态为completed且七份150轮完成标记齐备，再取得原控制器的文件锁，依次运行Faster R-CNN → 完整PConv+SD → MSF-GhostNet-III。不修改、不重启现有七组进程；原队列失败或停止时不会绕过它。每个新作业有有限独立子进程防挂起保护；异常、显存不足、未跑满150轮均停止，无自动降batch、模型替代、旧检查点恢复或平台关机。默认防挂起期限为7天/子作业，这是运行保护，不是性能或完成时间承诺。

代码、配置和检查回执先写入 `ADAPTERS_READY.json` 的哈希清单，接续启动前必须全部匹配。新输出目录必须不存在，避免覆盖。根目录创建 `STOP` 可在下一组启动前停止接续；已在运行的作业由其独立进程状态管理。正式结果放在各模型 `train/results.csv` 与 `train/weights/{best,last}.pt`，根目录包含plan/status/completed记录。仅验证集mAP50–95用于best选点。

MSF环境由 `scripts/setup_msf_environment.py` 通过uv新建，使用只读基础运行时依赖路径，并在本环境覆盖锁定的旧版兼容包：[覆盖依赖](../../configs/environments/msf-adapter-extra.txt)。基础Torch2.1.2+cu118、torchvision0.16.2+cu118与当前队列环境不修改。`scripts/prepare_msf_adapter.py` 仅复制并修改固定YOLOv5源码；不会运行作者notebook下载、账号或凭据单元。

## 来源

- [PConv-SDloss作者代码](https://github.com/JN-Yang/PConv-SDloss-Data)，commit `a801f043c83f73aa9af9ab2f689e59ebef928fc4`，MIT；项目保留原许可和未改动的SDIoU函数。
- [MSF作者代码](https://github.com/ZeeshanKaleem/MSF-GhostNet)，commit `32100ed6e00da3c2fb98ea25673dd535f9b51d6b`，仅提取III结构。
- [YOLOv5基础代码](https://github.com/ultralytics/yolov5)，commit `fbe67e465375231474a2ad80a4389efc77ecff99`，其源文件许可保留在运行时副本。
