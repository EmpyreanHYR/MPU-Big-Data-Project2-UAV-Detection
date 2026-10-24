# 基于改进 YOLO26 的红外小目标无人机检测研究

**《大数据概论》小组项目提案 · 中文版 V4.5**
小组成员：黄耀荣、余春申、翟逸凡、罗智文

日期：2026年10月24日

## 摘要

本项目研究复杂背景下的红外小目标无人机检测。以 YOLO26n 为基础，分别尝试用风车形卷积（PConv）替换浅层卷积，以及增加高分辨率 P2 预测分支。在 SIRST-UAVB 上比较两种改动对召回率、误报和推理速度的影响，再通过红外视频和树莓派/H10 部署验证所选模型的实际表现。

## 研究背景与文献分析

红外小目标无人机纹理少、对比度低，容易与鸟类及背景亮点混淆。YOLO26 支持端到端预测和小目标感知标签分配，其轻量版本 YOLO26n 可作为本项目研究浅层特征与预测分辨率的基础[1, 2]。

PConv 通过方向采样扩大浅层感受野[3]。EFLNet 结合自适应损失、归一化 Wasserstein 距离（NWD）和多层特征进行红外检测[4]。

TY-RIST 研究高分辨率检测头及其推理开销[5]。RDANet、DNANet、ISNet 和 ACM 分别探索特征提取中弱目标信息的保留方式[6, 7, 8, 9]。因此，本项目尝试增加 P2 分支：更细的空间特征可能有助于检出小目标，但也会增加计算量。NWD 为微小框定位提供了另一种分析视角[10]，可用于理解定位误差。

## 研究目标

比较浅层 PConv 与高分辨率 P2 分支在不同目标尺寸和背景下对召回率、误报的影响，同时测量增加的推理开销。

## 数据集与准备

主数据采用 SIRST-UAVB，包含 3000 幅真实红外图像、2955 个无人机框和 1742 个鸟类框[3]。训练采用无人机单类标签，鸟类标注用于分析误报。数据准备包括检查图像尺寸、框坐标与类别映射，并按来源序列建立训练、验证和测试划分。

IRSTD-1k（1001 幅真实图像）、NUDT-SIRST（1327 幅合成图像）和 SIRST（427 幅真实图像）用于独立的通用红外目标实验[7, 8, 9]。有原生框时直接使用；像素掩膜转换为目标外接框，并检查粘连和极小目标。

SIRST-V2、DenseSIRST 和 NUDT-SIRST-Sea 可分别扩展到复杂背景、密集目标及海面场景[11, 12, 13]。按序列或原始大图分组，检查跨来源重复，包括 SIRST 与 SIRST-V2 的重叠样本。

## 研究方法

各模型均采用保持宽高比的预处理，将输入统一为 640×640。B0 为 YOLO26n 基线，沿用其检测头、损失和标签分配[1, 2]；B1 用 PConv 替换一处浅层卷积[3]，考察方向采样的作用；B2 在 P3/P4/P5 之外增加步长为 4 的 P2 分支，利用更细的特征图进行预测。

B1、B2 分别与 B0 对比，再通过模块位置与组合消融分析各部分作用，依据验证集精度、微小目标召回及推理开销选择模型。

## 实验设计与评价

计划在云端 GPU 训练 300 轮，使用同源 COCO 预训练权重。各组统一数据划分、增强和输入尺寸，记录新增层初始化，以验证集 mAP@0.5:0.95 选择检查点，在同一测试集评价；采用配对随机种子考察多次运行结果的一致性。

以 Precision、Recall、F1、mAP@0.5 和 mAP@0.5:0.95 评价检测效果。按原图目标尺寸与背景复杂度分组，分析无人机漏检、鸟类误报和定位误差。置信度及匹配阈值在验证集选择。

效率测试统一预测分支和输出设置，使用约占评价帧 25%、50%、100% 的嵌套工作负载，记录帧数、总耗时、FPS、p50/p95 帧延迟和峰值内存。除模型延迟外，完整计时还覆盖解码、预处理、推理、坐标还原和显示，并结合排队、丢帧情况分析视频处理的性能限制。

## 视频验证与部署

选用独立红外无人机视频测试所选模型，覆盖远目标、鸟类干扰、背景亮点及目标进出画面，通过标注帧和连续片段评价检测表现。

部署阶段在树莓派/H10 平台依次完成浮点推理、ONNX 导出、量化、编译和视频运行。校准图像取自训练集，对比部署模型与浮点模型，观察量化对检测精度和速度的影响。

## 小组分工

黄耀荣负责模型开发、云端实验、报告统筹与技术答疑；余春申负责 PPT、性能图表及结果可视化；翟逸凡负责口头汇报、视频演示、讲稿和彩排；罗智文负责文献整理、数据准备、标注与划分检查及参考文献。

## 参考文献

[1] G. Jocher, J. Qiu, M. Liu, S. Lyu, F. C. Akyon, and M. E. Kalfaoglu, “Ultralytics YOLO26: Unified real-time end-to-end vision models,” arXiv:2606.03748, 2026. [Online]. Available: [在线来源](https://arxiv.org/abs/2606.03748)

[2] Ultralytics, “YOLO26 model documentation,” 2026, accessed: Oct. 23, 2026. [Online]. Available: [在线来源](https://docs.ultralytics.com/models/yolo26/)

[3] J. Yang, S. Liu, J. Wu, X. Su, N. Hai, and X. Huang, “Pinwheel-shaped convolution and scale-based dynamic loss for infrared small target detection,” in *Proceedings of the AAAI Conference on Artificial Intelligence*, vol. 39, no. 9, 2025, pp. 9202–9210. [Online]. Available: [在线来源](https://ojs.aaai.org/index.php/AAAI/article/view/32996)

[4] B. Yang, X. Zhang, J. Zhang, J. Luo, M. Zhou, and Y. Pi, “EFLNet: Enhancing feature learning network for infrared small target detection,” *IEEE Transactions on Geoscience and Remote Sensing*, vol. 62, pp. 1–11, 2024. [Online]. Available: [在线来源](https://arxiv.org/abs/2307.14723)

[5] A. Atrash, O. Moured, Y. Chen, J. Zhang, S. Ertekin, and O. Ugur, “TY-RIST: Tactical YOLO tricks for real-time infrared small target detection,” arXiv:2509.22909, 2025, accepted at the ICCV 2025 MIRA Workshop. [Online]. Available: [在线来源](https://arxiv.org/abs/2509.22909)

[6] R. Liu, J. Nie, and Y. Fu, “RDANet: Relative degradation aware network for infrared small target detection,” *IEEE Transactions on Geoscience and Remote Sensing*, 2026, early access. [Online]. Available: [在线来源](https://arxiv.org/abs/2608.20870)

[7] B. Li, C. Xiao, L. Wang, Y. Wang, Z. Lin, M. Li, W. An, and Y. Guo, “Dense nested attention network for infrared small target detection,” *IEEE Transactions on Image Processing*, vol. 32, pp. 1745–1758, 2023. [Online]. Available: [在线来源](https://arxiv.org/abs/2106.00487)

[8] M. Zhang, R. Zhang, Y. Yang, H. Bai, J. Zhang, and J. Guo, “ISNet: Shape matters for infrared small target detection,” in *Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition*, 2022, pp. 867–876. [Online]. Available: [在线来源](https://openaccess.thecvf.com/content/CVPR2022/html/Zhang_ISNet_Shape_Matters_for_Infrared_Small_Target_Detection_CVPR_2022_paper.html)

[9] Y. Dai, Y. Wu, F. Zhou, and K. Barnard, “Asymmetric contextual modulation for infrared small target detection,” in *2021 IEEE Winter Conference on Applications of Computer Vision (WACV)*, 2021, pp. 949–958. [Online]. Available: [在线来源](https://openaccess.thecvf.com/content/WACV2021/html/Dai_Asymmetric_Contextual_Modulation_for_Infrared_Small_Target_Detection_WACV_2021_paper.html)

[10] J. Wang, C. Xu, W. Yang, and L. Yu, “A normalized Gaussian Wasserstein distance for tiny object detection,” arXiv:2110.13389v2, 2022. [Online]. Available: [在线来源](https://arxiv.org/abs/2110.13389v2)

[11] Y. Dai, X. Li, F. Zhou, Y. Qian, Y. Chen, and J. Yang, “One-stage cascade refinement networks for infrared small target detection,” *IEEE Transactions on Geoscience and Remote Sensing*, vol. 61, pp. 1–17, 2023. [Online]. Available: [在线来源](https://arxiv.org/abs/2212.08472)

[12] M. Xiao, Y. Zhu, Y. Zhu, B. Li, F. Zhang, H. Wang, M. Cai, and Y. Dai, “Background semantics matter: Cross-task feature exchange network for clustered infrared small target detection,” arXiv:2407.20078v3, 2025. [Online]. Available: [在线来源](https://arxiv.org/abs/2407.20078v3)

[13] T. Wu, B. Li, Y. Luo, Y. Wang, C. Xiao, T. Liu, J. Yang, W. An, and Y. Guo, “MTU-Net: Multilevel TransUNet for space-based infrared tiny ship detection,” *IEEE Transactions on Geoscience and Remote Sensing*, vol. 61, pp. 1–15, 2023. [Online]. Available: [在线来源](https://arxiv.org/abs/2209.13756)
