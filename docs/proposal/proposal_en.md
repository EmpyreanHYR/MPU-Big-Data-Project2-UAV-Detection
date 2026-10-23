# Improved YOLO26 for Small Infrared UAV Target Detection

**Big Data Introduction · Group Project Proposal · English V4.0**

Team: Yaorong Huang, Chunshen Yu, Yifan Zhai, Zhiwen Luo

Date: 23 October 2026

## Abstract

This project studies infrared UAV detection in cluttered scenes, where targets occupy few pixels, exhibit low contrast, and resemble background distractors. Using YOLO26n as the detection framework, it investigates how shallow feature extraction and high-resolution prediction affect small-target detection. SIRST-UAVB serves as the main dataset, with additional infrared small-target datasets supporting complementary experiments. The study compares a pinwheel-shaped convolution (PConv) and a P2 prediction branch through controlled experiments, false-alarm analysis, and end-to-end latency measurements. Video inference on a Raspberry Pi with H10 acceleration connects model evaluation with edge deployment. Deliverables include a data-processing pipeline, detector implementations, experimental analysis, and course presentation materials.

## Background and Related Work

Infrared UAV targets often occupy only a few pixels. Their limited texture and low contrast make feature extraction, localization, and target--background discrimination closely related. YOLO26 combines a dual-head training design with end-to-end prediction. Its DFL-free regression head, progressive loss, and small-target-aware label assignment (STAL) address detection-head efficiency and positive-sample coverage for small objects. This project adopts YOLO26n and studies feature extraction and prediction resolution within this framework[1, 2].

For local feature modeling, the PConv proposed by Yang et al. uses pinwheel-shaped directional sampling to enlarge the shallow receptive field and model the spatial distribution of infrared targets[3]. EFLNet addresses target--background imbalance, sensitive small-box regression, and multi-level feature learning through an adaptive loss, normalized Wasserstein distance (NWD), and a dynamic detection head[4]. These studies motivate examining local sampling and cross-scale information use, and support a focused shallow-convolution replacement.

For prediction resolution and efficiency, TY-RIST combines high-resolution detection heads, fine-grained features, and branch pruning in a YOLO framework to investigate detection--computation trade-offs[5]. RDANet studies structural degradation during downsampling, while DNANet, ISNet, and ACM preserve weak-target information through dense feature interaction, shape and edge modeling, and contextual modulation, respectively[6, 7, 8, 9]. These findings motivate a P2 prediction branch as a second candidate and a comparison of its recall benefits and inference cost.

Small-box localization is also sensitive to pixel-level displacement. Wang et al. represent bounding boxes as Gaussian distributions and measure their similarity with NWD, providing a smoother geometric measure for tiny objects[10]. The initial study focuses on convolution and prediction-branch changes; localization-error analysis will inform subsequent investigation of geometric regression losses.

## Project Objectives

The project will establish a workflow for data preparation, model training, detection evaluation, and infrared UAV video inference. It will compare shallow-convolution adaptation with high-resolution prediction, and select a model using target-scale performance, background conditions, and inference cost. Outputs will include detector code, training records, comparative and ablation results, an edge-video demonstration, a course report, and presentation slides.

## Datasets and Data Processing

The main dataset is SIRST-UAVB, which contains 3,000 real infrared images with 2,955 UAV boxes and 1,742 bird boxes[3]. The detection task uses a UAV category, while bird annotations support analysis of confusion with visually similar flying objects. Data preparation will check image dimensions, box coordinates, and class mappings, and establish fixed training, validation, and test manifests.

Complementary experiments will use IRSTD-1k with 1,001 real images, NUDT-SIRST with 1,327 synthetic images, and SIRST with 427 real images[7, 8, 9]. These experiments will use a generic infrared-target category. Matching native boxes will be preferred; pixel annotations will be converted to enclosing boxes for target components, with checks for touching targets and tiny boxes. Provenance, image dimensions, and annotation-conversion records will accompany the prepared data.

Additional candidates are SIRST-V2 for complex backgrounds and box annotations, DenseSIRST for dense targets and background semantics, and NUDT-SIRST-Sea for maritime ship scenes[11, 12, 13]. Splits will follow source sequences or original large images. Cross-version and cross-dataset duplicates will be checked, with the inclusion of SIRST within SIRST-V2 recorded in the manifests.

## Technical Approach and Model Design

The workflow comprises data preparation, YOLO26n baseline training, candidate-module comparison, model selection, video validation, and edge deployment. The input size will be 640 by 640 pixels with aspect-ratio-preserving preprocessing. The detector will output UAV bounding boxes and confidence scores.

Baseline B0 uses YOLO26n with its detection head, losses, and label-assignment mechanism[1, 2]. Variant B1 replaces one shallow standard convolution with PConv to examine local receptive fields and directional sampling[3]. Variant B2 adds a stride-4 P2 prediction branch to the YOLO26n feature pyramid, alongside P3, P4, and P5, to study higher spatial resolution.

B1 and B2 will be compared separately with B0. Validation accuracy, tiny-target recall, and computational cost will guide the main model choice. Further ablations will compare module placement and combined configurations to explain each component's contribution.

## Experimental Design and Evaluation

Training will use a cloud GPU, a common COCO-pretrained weight source, and a planned schedule of 300 epochs. All conditions will share data partitions, input size, augmentation, and model-selection rules. Newly introduced layers and their initialization will be recorded. Validation mAP@0.5:0.95 will select checkpoints for test evaluation, and paired random seeds will examine the stability of the main findings.

Detection evaluation will report precision, recall, F1, mAP@0.5, and mAP@0.5:0.95. Results will be grouped by target size in the original image and by background complexity to analyze weak-target misses, bird false positives, and small-box localization errors. Confidence and matching thresholds will be selected on validation data, and unmatched predicted boxes per image will quantify false positives.

Inference comparisons will use the same YOLO26 end-to-end prediction branch and output-selection settings. Measurements will include model-call latency, end-to-end frames per second, p50/p95 frame latency, and peak memory. The complete processing interval will cover video decoding, preprocessing, inference, coordinate restoration, and visualization.

## Video Validation and Edge Deployment

Independent real infrared UAV videos will be organized by source sequence, with representative frames and continuous segments annotated for evaluation. Scenarios will include distant targets, bird interference, bright background points, and targets entering or leaving the frame. Quantitative results and overlaid detection videos will illustrate the behavior of the selected model.

Edge deployment will use a Raspberry Pi with H10 acceleration. Validation will progress through the floating-point model, ONNX export, quantization calibration, compilation, and video inference. Calibration images will be drawn from the training partition. Runtime, compiler, and firmware versions will be recorded, and the deployed model will be compared with the floating-point model for detection quality and end-to-end speed.

## Team Responsibilities

Yaorong Huang will lead algorithm design, module implementation, cloud training, report coordination, and technical questions. His deliverables will include model code, experiment records, and the technical sections of the report.

Chunshen Yu will prepare presentation slides, experimental charts, result visualizations, and demonstration materials.

Yifan Zhai will organize the oral presentation, video demonstration, script, and defense rehearsal, including the demonstration workflow and anticipated questions.

Zhiwen Luo will manage literature searches, datasets, box-annotation checks, split verification, and references, producing dataset documentation, literature analysis, and annotation records.

## Schedule and Expected Outcomes

Week 1 will cover literature and data preparation and establish the training and evaluation workflow. Week 2 will develop the YOLO26n baseline and candidate modules. Week 3 will complete the main comparisons, ablations, and complementary dataset experiments, and organize detection and efficiency results. Week 4 will complete video validation, the report, slides, and presentation rehearsal.

The expected outcomes are a YOLO26-based infrared UAV detector, a documented data and experiment workflow, and an edge-video inference pipeline for the Raspberry Pi and H10. The analysis will explain how shallow sampling and high-resolution prediction behave across target scales, background conditions, and computational budgets.

## References

[1] G. Jocher, J. Qiu, M. Liu, S. Lyu, F. C. Akyon, and M. E. Kalfaoglu, “Ultralytics YOLO26: Unified real-time end-to-end vision models,” arXiv:2606.03748, 2026. [Online]. Available: [Online](https://arxiv.org/abs/2606.03748)

[2] Ultralytics, “YOLO26 model documentation,” 2026, accessed: Oct. 23, 2026. [Online]. Available: [Online](https://docs.ultralytics.com/models/yolo26/)

[3] J. Yang, S. Liu, J. Wu, X. Su, N. Hai, and X. Huang, “Pinwheel-shaped convolution and scale-based dynamic loss for infrared small target detection,” in *Proceedings of the AAAI Conference on Artificial Intelligence*, vol. 39, no. 9, 2025, pp. 9202–9210. [Online]. Available: [Online](https://ojs.aaai.org/index.php/AAAI/article/view/32996)

[4] B. Yang, X. Zhang, J. Zhang, J. Luo, M. Zhou, and Y. Pi, “EFLNet: Enhancing feature learning network for infrared small target detection,” *IEEE Transactions on Geoscience and Remote Sensing*, vol. 62, pp. 1–11, 2024. [Online]. Available: [Online](https://arxiv.org/abs/2307.14723)

[5] A. Atrash, O. Moured, Y. Chen, J. Zhang, S. Ertekin, and O. Ugur, “TY-RIST: Tactical YOLO tricks for real-time infrared small target detection,” arXiv:2509.22909, 2025, accepted at the ICCV 2025 MIRA Workshop. [Online]. Available: [Online](https://arxiv.org/abs/2509.22909)

[6] R. Liu, J. Nie, and Y. Fu, “RDANet: Relative degradation aware network for infrared small target detection,” *IEEE Transactions on Geoscience and Remote Sensing*, 2026, early access. [Online]. Available: [Online](https://arxiv.org/abs/2608.20870)

[7] B. Li, C. Xiao, L. Wang, Y. Wang, Z. Lin, M. Li, W. An, and Y. Guo, “Dense nested attention network for infrared small target detection,” *IEEE Transactions on Image Processing*, vol. 32, pp. 1745–1758, 2023. [Online]. Available: [Online](https://arxiv.org/abs/2106.00487)

[8] M. Zhang, R. Zhang, Y. Yang, H. Bai, J. Zhang, and J. Guo, “ISNet: Shape matters for infrared small target detection,” in *Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition*, 2022, pp. 867–876. [Online]. Available: [Online](https://openaccess.thecvf.com/content/CVPR2022/html/Zhang_ISNet_Shape_Matters_for_Infrared_Small_Target_Detection_CVPR_2022_paper.html)

[9] Y. Dai, Y. Wu, F. Zhou, and K. Barnard, “Asymmetric contextual modulation for infrared small target detection,” in *2021 IEEE Winter Conference on Applications of Computer Vision (WACV)*, 2021, pp. 949–958. [Online]. Available: [Online](https://openaccess.thecvf.com/content/WACV2021/html/Dai_Asymmetric_Contextual_Modulation_for_Infrared_Small_Target_Detection_WACV_2021_paper.html)

[10] J. Wang, C. Xu, W. Yang, and L. Yu, “A normalized Gaussian Wasserstein distance for tiny object detection,” arXiv:2110.13389v2, 2022. [Online]. Available: [Online](https://arxiv.org/abs/2110.13389v2)

[11] Y. Dai, X. Li, F. Zhou, Y. Qian, Y. Chen, and J. Yang, “One-stage cascade refinement networks for infrared small target detection,” *IEEE Transactions on Geoscience and Remote Sensing*, vol. 61, pp. 1–17, 2023. [Online]. Available: [Online](https://arxiv.org/abs/2212.08472)

[12] M. Xiao, Y. Zhu, Y. Zhu, B. Li, F. Zhang, H. Wang, M. Cai, and Y. Dai, “Background semantics matter: Cross-task feature exchange network for clustered infrared small target detection,” arXiv:2407.20078v3, 2025. [Online]. Available: [Online](https://arxiv.org/abs/2407.20078v3)

[13] T. Wu, B. Li, Y. Luo, Y. Wang, C. Xiao, T. Liu, J. Yang, W. An, and Y. Guo, “MTU-Net: Multilevel TransUNet for space-based infrared tiny ship detection,” *IEEE Transactions on Geoscience and Remote Sensing*, vol. 61, pp. 1–15, 2023. [Online]. Available: [Online](https://arxiv.org/abs/2209.13756)
