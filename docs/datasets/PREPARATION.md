# SIRST-UAVB 数据处理

处理入口为 `scripts/prepare_sirst_uavb.py`。本次完成转换程序和合成样例检查，尚未取得实际 SIRST-UAVB 图像、确认下载包的类别 ID 或生成正式划分。来源见 [SOURCES.md](SOURCES.md)。

## 原始清单

安装 `python -m pip install -e '.[data]'`。原始包存入 Git 忽略的 `data/`，记录下载入口、版本、许可、取得时间和包 SHA256。解包后核对标注格式及类别定义，再建立 CSV，必需列为：

```csv
image,annotation,format,group,split
images/example.png,labels/example.txt,yolo,sequence_001,train
```

`image` 和 `annotation` 是相对于 `--source-root` 的文件路径。支持 `yolo`、`voc` 和 `negative`。`group` 必须来自来源序列、拍摄批次或原始大图，同一来源使用同一组；不能简单用每张图像的文件名代替来源分组。`split` 全部填写 train/val/test，或全部留空。留空时按 seed 对完整来源组划分，默认目标比例 70%/15%/15%；完整组不可拆分，实际比例会偏离目标。至少需要三个彼此独立且含 UAV 的组，确保三份均有正样本。

按照原包核验结果填写类别映射 JSON，例如将源 ID 或 VOC 类别名映射到 `uav`、`bird`。必须包含两种语义，程序拒绝未映射的类别。仓库的 [类别映射示例](../../configs/datasets/class_map.example.json)使用占位符，须先替换；它没有假定 SIRST-UAVB 的真实类别编号。[清单示例](../../configs/datasets/manifest.example.csv)也需换成真实路径和来源组。

YOLO 标注每行五字段：类别、归一化中心点 x/y、宽/高。VOC 必须显式选择坐标约定；`one-based-inclusive` 可保留一像素目标，`zero-based-half-open` 使用零基半开区间。VOC 的尺寸必须匹配图像；difficult 对象需另定忽略策略，当前直接拒绝。`negative` 只用于人工确认的无目标图，annotation 留空，不能用来替代缺失标注。

## 转换和审计

```sh
python scripts/prepare_sirst_uavb.py prepare \
  --source-root data/sirst-uavb/raw \
  --manifest data/sirst-uavb/source_manifest.csv \
  --class-map data/sirst-uavb/class_map.json \
  --output data/sirst-uavb/prepared \
  --seed 42
python scripts/prepare_sirst_uavb.py audit --output data/sirst-uavb/prepared
```

VOC 数据在 prepare 命令追加 `--voc-mode one-based-inclusive` 或经核验的另一种约定。转换保留原像素和长宽比，不在该阶段缩放；输入限 8-bit L/RGB 单帧、无 EXIF 旋转的图像，其他编码需先建立有记录的标准化步骤。

程序检查坐标、尺寸、有限数值、路径边界、类别和来源分组，计算文件 SHA256 与解码 RGB 像素 SHA256。相同像素的重编码副本也不能跨划分；相同图像而标注不同会报错。提供的划分若冲突则拒绝；自动划分将重复图及其来源组合并后分配。程序无法推断图像中未记录的拍摄序列，来源组需从数据包说明核实。

输出包括 `images/{train,val,test}`、`labels/{train,val,test}`、`dataset.yaml`、`manifest.json` 和 `audit.json`。训练标签仅保留 class 0 UAV；鸟框和原类别保留在 manifest，用于错误归因。manifest 记录原标注摘要、坐标约定、原图与像素摘要和来源组。独立 audit 会重新核对图像、输出标签、清单完整性及划分隔离。输出目录必须不存在；失败清理暂存目录，不覆盖已有结果。

`dataset.yaml` 保存实际绝对根目录，转移到云端后应在目标环境重新执行准备流程。云端训练入口会再次审计整个 prepared 目录。当前适配 native YOLO/VOC 框；其他红外数据的掩膜到框转换需另行实现并记录连通域规则。
