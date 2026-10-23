# YOLO26n 模型配置

三个配置固定 `ultralytics==8.4.184`，`nc=1`、`scale=n`、`end2end=true`、`reg_max=1`。来源和许可见 [third_party](../../third_party/README.md)。构建必须经过 `uav_detection.modeling.build_detector`，保留自定义模块和训练器；不要直接用通用 YOLO CLI 读取 PConv 配置。

| 变体 | 配置 | 修改位置 | 输出步长 | 完整双头参数量 |
|---|---|---|---|---|
| B0 baseline | [yolo26n-baseline.yaml](yolo26n-baseline.yaml) | 官方 n 尺度，单类 | 8/16/32 | 2,504,190 |
| B1 pconv | [yolo26n-pconv.yaml](yolo26n-pconv.yaml) | 第二个 backbone Conv，层1 | 8/16/32 | 2,504,478 |
| B2 p2 | [yolo26n-p2.yaml](yolo26n-p2.yaml) | 新增 stride4 路径，Detect 接19/22/25/28 | 4/8/16/32 | 2,515,976 |

参数量是 nc=1、融合前、保留 one-to-many 与 one-to-one 的模型构建统计；部署融合后的统计另记。B1、B2 分别与 B0 比较，当前未实现组合变体。

## 构建与模块

```sh
python -m pip install -e '.[model,data]'
python scripts/build_model.py --variant baseline
python scripts/build_model.py --variant pconv
python scripts/build_model.py --variant p2
```

PConv 使用四个不对称补零方向，两个水平方向共享卷积、两个垂直方向共享卷积，再拼接融合。替换层保持下采样倍率及输出通道；输入需满足该层步长整除条件，YOLO 的 stride32 补齐可满足此约束。源码参考作者固定 commit，保留 MIT 许可。

适配器先用版本固定的官方 parser 构建通道和图，再按 `pconv_layers` 元数据替换层1。`UAVDetectionTrainer.get_model` 会从保存的 YAML 恢复该替换，避免训练器重建时丢失 PConv。没有修改 Ultralytics 全局 parser。检查点恢复使用 `UAVYOLO`，且需安装本仓库 Python 包，才能反序列化自定义类。

P2 在原0–16层公共图之后，从浅层2接入 P2 融合路径，再回到 P3/P4/P5，保留 YOLO26 双头结构。适配器显式启用端到端预测，`nms=False`；三种模型使用相同输出分支。

## 初始化与训练入口

`--weights` 仅接受已有本地 YOLO26 检查点，不自动下载。三种条件采用同一迁移策略：只拷贝层0–16的同名同形张量；PConv 的层1跳过；层17及之后的预测路径均重新初始化。这防止 P2 层编号移动后意外加载形状相同但语义不同的张量。不能据此称全部 COCO 权重都已加载。迁移明细、数据清单与权重摘要写入 `initialization.json`。

三份实验配置位于 [configs/experiments](../experiments/)。云端调用示例见 [README](../../README.md)，本地构建及测试均不训练。训练器会保留已迁移的模型参数，按相同自定义类重建；测试覆盖此过程和检查点恢复。

CPU 随机权重前向检查使用640×640输入（单元测试另含128×128、128×160），结果见 [model_smoke_20261023.json](../../docs/checks/model_smoke_20261023.json)。它只验证结构、步长和有限输出，不代表模型检测能力、GPU训练兼容或H10可部署性。
