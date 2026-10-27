# YOLO26 实验汇报讲稿与来源

每页讲者备注同时嵌入PPTX。数值以对应结果记录为准；H10尚未实测。

## 第1页

本汇报以仓库已核验结果为依据。报告快照已包含P2和数值诊断；本PPT另含最新红外序列参考。H10编译与设备测速未完成。资料：docs/PROJECT_STATUS.md；docs/report/report.tex；docs/results/infrared_fp32_reference_20261028.json。

## 第2页

研究对象是单类UAV原生框检测。B1只在layer1引入PConv；P2加入stride4分支，均使用版本固定的UAVYOLO适配器并保留端到端预测。PConv论文：https://arxiv.org/abs/2412.16986；官方YOLO26说明：https://docs.ultralytics.com/models/yolo26/。这里只说明假设与实际配置，不声称改进有效。

## 第3页

configs/datasets/sirst_uavb_scene_holdout_v3/README.md；docs/datasets/SOURCES.md。作者来源：https://github.com/JN-Yang/PConv-SDloss-Data。原2400/600发布划分有496幅验证图像与训练图像像素完全相同，另3组冲突标签。当前按推断背景视图分组，不等于已核验独立视频/地点；没有独立test。UAV使用native boxes，bird仅保留用于错误分析。

## 第4页

docs/experiments/MATCHED92.md；docs/results/yolo26n_baseline_20261025.json；docs/results/yolo26n_pconv_20261026.json；docs/results/yolo26n_p2_fp32_20261028.json；configs/models/README.md。公共预训练前缀0–16，B0/P2载入348张量、B1载入342张量，尾部随机初始化。B0有部分第93轮，B1/P2为92完整轮。P2验证和best选择为FP32，与历史AMP选择不相同；单seed结果不支持结构因果结论。

## 第5页

docs/results/yolo26n_baseline_20261025.md/json；docs/results/yolo26n_pconv_20261026.md/json。历史standalone最终复验，不覆盖为后续FP32诊断。B0 best第81轮，B1 best第68轮。B1训练92轮exit0，但11行验证loss NaN导致严格队列exit1。B0也有7行NaN。历史CSV保留，有限权重/检测指标不代表历史验证loss全部有限。

## 第6页

docs/results/numerical_replay_20261028.json/md。B0 stored epoch30、updates834；B1 stored epoch10、updates384，分别对应第31/11完成轮次，EMA身份和浮点状态已实核。batch8，505同序图像，共64批。两份最终best在两精度均无异常。27个异常AMP批相同raw预测转FP32 loss仍异常。首个捕获顶层异常model.22.C3k2；尚未定位内部算子，也未逐一覆盖所有历史epoch，不能归因于PConv。参数和BN前后哈希不变，无梯度回放。

## 第7页

docs/results/numerical_replay_20261028.json/md；docs/results/yolo26n_p2_fp32_20261028.json/md。B0/B1是同一官方训练validator路径的独立FP32复验；P2训练AMP但逐轮验证和best选择FP32。复验使用544x672矩形批，与旧standalone后端、批次、预处理路径有差异，不能把变化只归因于精度。P2并未超过B0，不能宣称架构收益。

## 第8页

docs/results/yolo26n_p2_fp32_20261028.json/md。实际92完整轮，matched_complete_epoch_limit，exit0。92行CSV连续且所有列有限，92条precision日志为FP32/505图，真实训练AMP保持。最终best完整505验证，参数/BN前后不变。全部29文件归档/成员SHA通过并ACK0，云平台已核验停机。CSV最高AP50:95第89轮，不当作额外EMA张量身份核验证据。

## 第9页

docs/results/infrared_fp32_reference_20261028.json/md；docs/results/infrared_sequence_readiness_20261028.json。作者Anti-UAV发布入口链接ModelScope ly261666/3rd_Anti-UAV。在任何模型执行前冻结字典序首validation/01_2192_0001-1500的帧1–300，所有帧均有目标。conf0.25，matchingIoU0.5，batch1，640square letterbox，one-to-one，无额外NMS。MacCPU Torch2.14.1 FP32参考，不是Pi/H10或云Torch2.1.2验证。原始预测有限、参数/BN未变、无训练。未使用素材调阈值或校准。

## 第10页

docs/results/infrared_sequence_readiness_20261028.json；docs/results/infrared_fp32_reference_20261028.json。300JPG和标注校验通过；与3000幅SIRST源图像无像素完全匹配，但无法证明来源视频独立。CSV Type与validation路径不一致的异常保留，仅新参考使用，不校准/训练/调阈值。没有目标缺失帧，不能估算背景误报/小时。原捕获帧率未知，25fps只是预览重建示意。未将来源媒体或带框视频重新分发到公共仓库。

## 第11页

docs/deployment/READINESS_20261028.md；configs/models/README.md；Ultralytics Hailo docs https://docs.ultralytics.com/integrations/hailo/。设备HAILO10H、RT/firmware5.1.1已实核；本项目新HEF编译、parse/configure、首帧及完整配对都未完成。默认exporter包含量化后finetune，需先编制隔离statistics-only校准协议，禁用finetune/Adaround/QAT，不在Windows训练。校准只用1438train，排除505val和新视频。先FP32/ONNX同输入一致性，再HEF验证。既有RGB HEF/性能不可冒充本模型。设备benchmark预热20，75/150/300嵌套前缀，3重复；完整视频/显示编码另测。

## 第12页

完整依据见docs/results/yolo26n_baseline_20261025.md、yolo26n_pconv_20261026.md、numerical_replay_20261028.md、yolo26n_p2_fp32_20261028.md、infrared_fp32_reference_20261028.md，以及docs/deployment/READINESS_20261028.md。当前报告为两页IEEE快照，已合并P2和诊断，待设备结果齐全后再同步IR和设备结论，保持原观测与模板。局限：单seed、推断背景划分、无独立test、序列单一、验证精度/路径变化。不得宣称PConv/P2提升或H10部署成功。
