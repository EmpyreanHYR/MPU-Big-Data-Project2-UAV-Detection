# 评价与边缘推理

本目录包含历史500图评价使用的后处理、CPU/NPU程序及原始头解码。当前PinP2默认部署使用[显式NMS=0.4入口](../deployment/README.md)；本目录的原e2e评价路径保留无NMS行为，用于复现历史结果。数据、ONNX/HEF、原始预测数组和设备状态留在私有存储。

| 程序 | 作用 |
|---|---|
| `detection_eval.py` | NumPy预处理、解码后处理、NMS、独立固定阈值匹配和AP |
| `recompute_saved_predictions.py` | 从冻结清单、图像/标签和已保存NPZ重算指标，不加载模型 |
| `edge_evaluate.py` | Pi5上ONNX Runtime CPU、4线程、预热20次及500图实测 |
| `h10_evaluate.py` | Pi5/HAILO10H实际HEF推理，输出映射按已验证结构核验 |
| `raw_head_decode.py` | NumPy原始头解码，覆盖已验证的e2e/v8/v5输出 |

固定阈值为0.25：先筛选检测，再按IoU≥0.5一对一匹配。AP使用0.001置信度下限和0.50—0.95十个IoU阈值单独计算。漏检率为FN／GT。原生训练AP与这些部署指标并列报告。

只重算已有预测时，安装`python -m pip install -e '.[evaluation]'`后运行：

```sh
python scripts/evaluation/recompute_saved_predictions.py \
  --manifest /path/to/validation_manifest.json \
  --data-zip /path/to/validation_data.zip \
  --predictions /path/to/detections.npz \
  --output /path/to/new_audit.json
```

程序检查图像顺序、每图偏移、单类输出和图像/标签哈希；也可用`--data-root`读取已解压数据。它只依赖NumPy。

Pi CPU安装`.[edge]`依赖；H10使用设备配套的HailoRT Python SDK。推理需指定现有共享硬件锁，并通过有限运行窗口启动，例如：

```sh
timeout 900 python scripts/evaluation/edge_evaluate.py \
  --config /path/to/model/deployment_config.json \
  --data /path/to/validation_data --output /path/to/new_cpu_result \
  --shared-lock /path/to/shared_device.lock

timeout 900 python scripts/evaluation/h10_evaluate.py \
  --model-dir /path/to/h10_model --data /path/to/validation_data \
  --output /path/to/new_h10_result --shared-lock /path/to/shared_device.lock
```

设备既有流程还使用其他硬件锁时，H10可重复传入`--additional-lock`，各锁同时获取。公开副本把原设备的专用锁路径参数化，CPU程序增加显式共享锁；后处理和指标函数为已验证实现。输出目录为新建目录，已有结果文件按原样保留。

推理FPS包含预处理/推理/后处理，不含绘图、编码、网络、初始化和AP下限处理；同步H10调用包含PCIe传输和反量化。工作负载循环总时间单独记录。
