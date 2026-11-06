# 四源红外无人机数据集整理与逐图溯源

`consolidate_ir_datasets.py` 是纯数据整理程序，使用 Pillow/NumPy，不导入 Torch，不训练、不加载权重。输入为已逐文件校验的五源 IR 图像/标注目录，以及完整原始归档的成员索引和 SHA256。输出必须是一个此前不存在的新目录；不覆盖原始数据或既有实验。

```sh
python scripts/consolidate_ir_datasets.py \
  --raw-root data/raw-ir \
  --inventory data/source_inventory.json \
  --legacy-groups configs/datasets/sirst_uavb_scene_holdout_v3/source_manifest.csv \
  --output data/IR-UAV-DET-20261030-v1 --seed 42
```

SIRST-UAVB、UAV-CB、Tri-Modal Anti-UAV、AUVD-Seg300 组成 train/val，Anti-UAV-detection 仅 test。原包已有 train/val/test 名称不决定项目划分，来源记录保留这些名字。类别统一为 `0: uav`；SIRST class1 鸟框只留审计，鸟类单独出现的负样本保留。UAV-CB 只取 thermal 的 LabelMe rectangle；Tri-Modal 只取 ir_；AUVD 三个 UAV 尺度类别的分割多边形转换成最小轴对齐外接框。

图像保留原字节、格式和尺寸；规范标签使用十位小数。边界外延不超过 2 像素且仍有可见面积的框裁至图像边界，逐框保留修正前后坐标和逐图计数；零面积、反向或越界更大的源标注图像隔离并记录错误，不改成负样本。缺失标注、未知类别等源错误有明确诊断，不静默改标签。导出时验证每一个图片/标签对、框数、类别、范围和图像哈希。

## 下载包结构

- `dataset.yaml`：不嵌入服务器绝对路径，解压后用该文件定位数据根目录。
- `images/{train,val,test}` 和 `labels/{train,val,test}`：文件名添加数据源前缀，空标签为无人机负样本。
- `original_annotations/`：全部被选择 IR 候选的原标注，含隔离项。
- `README_数据说明.md`：实际逐来源划分数量、使用方式与限制。
- `SHA256SUMS.txt`：逐文件校验和；另附整包 `.zip.sha256`。

## 对应名单

| 文件 | 覆盖范围 | 主要用途 |
|---|---|---|
| `provenance/original_image_to_split.csv` | 原始归档的全部图像，包括 SIRST 多份目录副本、RGB/Event、去重和隔离项 | 按原始数据集、原始文件名查询最终去向 |
| `provenance/manifest_exported.csv` | 实际导出的每一张图像 | 查询 train/val/test、输出图片/标签、原标注和文件哈希 |
| `provenance/manifest_all_selected_ir.csv` | 全部选定 IR 候选，包括未导出项 | 审核筛选过程 |
| `provenance/excluded_and_quarantined.csv` | 未导出的候选 | 查看重复对象、标注冲突及测试近似内容隔离原因 |
| `provenance/instances.jsonl` | 每个 IR 候选的框 | 查看统一 UAV 框及被排除的鸟框 |
| `provenance/near_identical_pairs.csv` | 固定规则检出的近相同内容对 | 复核图像相似性及是否涉及 test |
| `provenance/source_archive_inventory.json` | 完整原包的名称、SHA256、成员名、字节数、CRC | 追溯原始归档，不把只传 IR 的副本误称为完整原包 |
| `provenance/audit.json` | 本次整理的实际结果和软件版本 | 核对计数、组/像素交叉检查与限制 |

CSV 使用 UTF-8 BOM，可用 Excel 打开。逐图字段包含 `dataset`、`source_image`、`source_annotation`、`split`、`output_image`、`output_label`、`original_classes`、`uav_instances`、`bird_instances_excluded`、`negative`、`group`、`group_basis`、`status`、`reason`、`duplicate_of` 和 SHA256。原图总表另有 `relationship_to_canonical`，区分选定原图与原包中指向同一输出的副本；非红外图像明确标为 excluded。

## 隔离与划分

像素完全相同而标注冲突的整个组隔离；重复图像只留一个代表，涉及 test 时保留 test 并排除训练副本。来源前缀、已人工审阅的 SIRST 推断背景组及严格图像相似组不跨 train/val。用 seed42 在完整组上进行子集分配，总体 train/val 为 8:2，各来源比例允许小幅差异；如果无法保持组完整并达到总体比例，程序报错，不拆组兜底。

近相同内容规则：16×12 去均值单位化亮度 NCC≥0.995、64×48 灰度 MAE≤0.5、图像灰度标准差≥4。该规则仅用于保守内容隔离，不能证明原始视频身份相同。涉及 test 时固定测试集，隔离受影响的完整训练内容组。部分来源没有已核实原始视频 ID，因此应报告“推断组不跨划分”，不能宣传为已证实所有视频/地点独立。数据整理完成不等于获准开训。
