# 模型方案

B0 使用 Ultralytics 的 `yolo26n.yaml` 检测模型，构建入口为 `scripts/build_model.py`。

B1 在浅层替换一处 PConv；B2 在 YOLO26n 上新增步长4的 P2 预测分支。两项属于待实现方案，后续分别放入 `src/uav_detection/` 与 `configs/`，配套记录修改位置、参数量和与 B0 的对照。新增分支延续 YOLO26 的端到端检测结构。
