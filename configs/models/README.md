# YOLO26模型配置

主消融使用`ultralytics==8.4.193`、`nc=1`、`scale=n`、`end2end=true`及`reg_max=1`。通过`uav_detection.modeling.build_detector`构建，自定义模块和训练器与该入口配套；PConv/P2配置经此入口读取。

| 变体 | 配置 | 结构变化 | 输出步长 | 参数量 |
|---|---|---|---|---:|
| baseline | [yolo26n-baseline.yaml](yolo26n-baseline.yaml) | 原YOLO26n | 8/16/32 | 2,504,190 |
| pconv | [yolo26n-pconv.yaml](yolo26n-pconv.yaml) | 层1替换为PConv | 8/16/32 | 2,504,478 |
| p2 | [yolo26n-p2.yaml](yolo26n-p2.yaml) | 增加P2分支 | 4/8/16/32 | 2,515,976 |
| pconv_p2 / PinP2-YOLO | [yolo26n-pconv-p2.yaml](yolo26n-pconv-p2.yaml) | 浅层PConv与P2组合 | 4/8/16/32 | 2,516,264 |

参数量为nc=1、融合前、保留one-to-many及one-to-one分支的实际结构统计。部署融合后的大小在设备对比中另列。当前匹配从零100轮设置见[配置导航](../README.md)，预训练150轮结果作为独立组保留。

在指定GPU环境安装模型依赖后，可用以下入口检查结构：

```sh
python -m pip install -e '.[model,data]'
python scripts/build_model.py --variant baseline
python scripts/build_model.py --variant pconv
python scripts/build_model.py --variant p2
python scripts/build_model.py --variant pconv_p2
```

PConv采用四个非对称补零方向，水平两支共享卷积、垂直两支共享卷积，再拼接融合。替换层保持输出通道和下采样倍率。P2在公共前缀后增加高分辨率融合路径，Detect连接19/22/25/28层。自定义训练器从模型YAML恢复PConv/P2结构，Ultralytics全局parser保持原样。

从零100轮协议从随机初始化开始，`pretrained=false`。显式传入本地权重时，通用适配器迁移0—16层的同名同形参数；替换的PConv层跳过，分叉后路径随机初始化，加载范围为COCO权重的公共前缀。历史预训练基准的完整兼容加载与改进模型的公共前缀策略分别记录。

另保留[SIA](yolo26n-pf-sia.yaml)、[SIA＋CSP](yolo26n-pf-sia-csp.yaml)的PF启发适配，属于YOLO中的局部迁移。[msf_ghost](yolo26n-msf-ghost.yaml)为未形成有效完成训练的支线配置，不计入19组有效训练记录。兼容性和实测结果见[当前对比](../../docs/results/EDGE_EXTENSION_20261104.md)。

[早期结构检查](../../docs/checks/model_smoke_20261023.json)覆盖对应版本的结构和有限输出。来源、固定提交及许可见[third_party](../../third_party/README.md)。
