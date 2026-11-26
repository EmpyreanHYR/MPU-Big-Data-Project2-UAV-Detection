# Individual Work Contribution and Reflection

**Name:** Yaorong Huang

## 1. Specific Work Carried Out

I was responsible for the model design, the experimental programme and the edge deployment of PinP2-YOLO. On the architecture side, I added a shallow, directionally sampled PConv module and a stride-4 P2 branch to YOLO26n, keeping the original detection head and using shallow detail to recover localisation evidence for small targets. I also prepared the drawing of the actual network. On the experimental side, I unified the training configuration for all comparison models and for the PConv/P2 ablations, trained from scratch, and compared YOLO26n, YOLO11n, YOLOv8n and RT-DETR. I further arranged the training-data-fraction, inference-workload and error-stratification experiments, so that results could be recomputed under one protocol. On the deployment side, I handled ONNX export, Hailo-10H compilation and Raspberry Pi testing, and compared accuracy, speed and memory on GPU, Pi CPU and H10 using the same validation set.

I also found that the end-to-end head of YOLO26 does not actually apply non-maximum suppression. I re-examined the sources of false positives, replayed several thresholds and cross-checked an independent implementation before choosing the suppression setting used in the final deployment. In addition, I carried out one vision-language-model review and kept it as a negative result, helped build the demonstration system and diagnosed why the demo material produced almost no detections, and wrote the reproducibility material, the report and the presentation material.

## 2. Main Difficulty and How It Was Resolved

The largest difficulty was that the network rebuilt by the training pipeline, and therefore trained, might not be the network that was designed. Because the trainer reconstructs the model from configuration, our custom PConv and P2 modules could be dropped or reverted to native layers. Temporary patches avoided the symptom but gave poor traceability and could not keep the training, export and deployment paths consistent. I moved the modules into a single version-pinned adapter layer that restores them on reconstruction, checked module types and parameter counts after every rebuild, and compared outputs across the training, export and deployment stages. This work produced no experiment number of its own, but it made the later model comparisons and edge results trustworthy.

## 3. Reflection

The effect of a structural change cannot be judged from the combined result alone. PConv alone lowered accuracy and only the PConv-plus-P2 combination improved it, which convinced me that every change must be verified by factor ablation. The gain came mainly from better localisation, while small isolated targets were still frequently missed; later blind parameter tuning did not solve that problem. The experimental design also has limitations: only one random seed was used, the physical batch sizes differed across ablation groups, and the suppression threshold was selected on the same validation set. In time management, repeated work on the environment and tool chain took time from writing and literature review. Given another chance, I would validate the deployment path earlier and put a stable, reproducible experiment pipeline first.
