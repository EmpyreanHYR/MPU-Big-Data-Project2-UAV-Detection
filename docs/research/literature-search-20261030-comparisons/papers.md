# 近期红外无人机检测方法筛选

检索日期：2026-10-30；时间范围 2024–2026；以作者仓库、论文和机构存档为依据。筛查重点：相机检测无人机，而非无人机航拍检测地面车辆。公开仓库存在不代表完整可复现。

| 方法 | 年份与任务 | 原始依据 | 结论 |
|---|---|---|---|
| PConv + SD Loss | AAAI 2025，红外小目标框/掩膜；含 SIRST-UAVB | [论文](https://ojs.aaai.org/index.php/AAAI/article/view/32996)、[作者代码](https://github.com/JN-Yang/PConv-SDloss-Data) | 选入；有实际模块代码，需集成 YOLOv8n-P2；并非专门的完整 UAV 检测仓库 |
| MSF-GhostNet | JSTARS 18 (2025):3840–3851；红外无人机检测，DOI 含 2024（在线发表年份） | [论文](https://doi.org/10.1109/JSTARS.2024.3524379)、[作者代码](https://github.com/ZeeshanKaleem/MSF-GhostNet) | 选入 III 变体；notebook 包含完整 Ghost 模型结构，可提取，但不是即用训练包 |
| YOLO-LIRTU | 2026，红外无人机 | [作者仓库](https://github.com/jinxinhuo/YOLO-LIRTU) | 暂不选：归档中未找到完整自定义网络依赖，train.py 引用缺失实现 |
| TY-RIST | ICCV 2025 workshop，通用红外小目标 | [作者仓库](https://github.com/moured/TY-RIST) | 暂不选：公开归档主要为 README/图片，代码需要申请 |
| YOLO11-AU-IR | 2025，红外 UAV 实例分割 | [作者仓库](https://github.com/chen-yuzhi/YOLO11-AU-IR) | 暂不作同任务框检测基准：原方法为分割，四源不都具有真实实例掩膜 |

PConv 源参考 commit `a801f043c83f73aa9af9ab2f689e59ebef928fc4`。MSF 源 commit `32100ed6e00da3c2fb98ea25673dd535f9b51d6b`，其 notebook 固定 YOLOv5 `fbe67e465375231474a2ad80a4389efc77ecff99`。MSF 提取结构保存在 `configs/models/msf-ghostnet-iii.yaml`。本次不执行作者 notebook 中的数据下载/账户配置部分。

检索路径：红外 UAV detection GitHub 2024/2025/2026 → 核对作者与论文 → 静态检查代码归档 → 核对检测/分割和无人机/航拍地面目标差异 → 固定源码/记录适配缺口。检索不保证覆盖全部方法；尚未训练，未比较精度或速度。
