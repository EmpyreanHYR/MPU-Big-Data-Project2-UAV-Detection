# 配置导航

当前主比较使用SIRST-UAVB固定1999训练／500验证、seed42、640输入、FP32、从零100轮。训练与选点只使用该单源划分，其他四源分别作外部评价。

| 配置 | 用途 |
|---|---|
| [sirst_scratch100](experiments/sirst_scratch100/) | 可由通用训练入口读取的YOLO26基准、PConv、P2和PinP2-YOLO配置 |
| [sirst_scratch100_ablations](experiments/sirst_scratch100_ablations/) | 三组已完成补充消融保存的原生训练参数，保留`resume=false`与`split=val`字段 |
| [sirst100_pf_sia](experiments/sirst100_pf_sia.json)／[SIA＋CSP](experiments/sirst100_pf_sia_csp.json) | 两组100轮PF启发适配 |
| [sirst_comparison150](experiments/sirst_comparison150/) | 比较模型的原始命名目录；以文件内实际轮数为准，YOLO11/8的旧150轮与追加100轮实测分开记录 |
| [sirst_only150](experiments/sirst_only150/) | 历史COCO初始化150轮结构对照，与从零组分开 |
| [four_source150](experiments/four_source150/) | 已停止使用的四源历史配置及适配器注册信息；不代表当前训练组成 |
| [models](models/README.md) | 模型图、PConv/P2组合与其他适配器说明 |
| [environments](environments/) | 独立比较模型的附加环境依赖 |

`sirst_scratch100`由已保存参数整理，保留100轮、FP32、AdamW、lr0=0.001、nbs32。基准和PConv物理batch32，P2与组合batch8。原生导出的参数保留在原目录，通用入口版本补充`variant/model/task`并移除入口固定处理的`resume/split`字段。

根目录较早的300轮计划和matched92配置仅用于历史数值与入口测试，不代表实际完成300轮。所有新运行都需要另行指定数据、输出和截止时间；配置整理不启动作业。
