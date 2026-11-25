# COMP6132 · Q&A backup

1. **Why did you choose YOLO26n?**  
   It is a compact baseline with about 2.504 million parameters. Keeping the same detector family made the PConv and P2 contrasts interpretable and gave us a useful baseline for the edge benchmark.

2. **What did each module contribute? Why did PConv alone score lower?**  
   In the scratch100 ablation, PConv alone was −3.571 pp, P2 alone was +2.023 pp, and both together were +3.322 pp in native AP50:95. PConv changes shallow directional sampling, while P2 adds a finer prediction grid. We did not isolate the cause of the standalone drop. One seed and different physical batch sizes limit the interpretation.

3. **Why did AP rise with more training images?**  
   Larger nested subsets may expose the model to more kinds of targets and clutter. Fixed epochs also give larger sets more optimizer steps. Only seed 42 and one internal validation set were measured. Matched-step, multi-seed runs could separate these effects.

4. **Why not use NMS IoU 0.3 or 0.5?**  
   Both 0.3 and 0.4 produced 62 false positives at unchanged recall. We selected 0.4 as the largest tested threshold achieving that count, which suppresses less aggressively. At 0.5 there were 63 false positives. TP and FN remained 323 and 163, respectively. The threshold was selected on internal validation.

5. **What does your 22.89 FPS measure?**  
   It is the average image-pipeline rate across three Pi/H10 processes at IoU 0.4, including image loading, preprocessing, device inference, decoding and NMS. AP scoring, drawing and recording are outside that timing. GUI FPS and recorded playback speed measure different stages. The separate deployment acceptance run measured 22.56 FPS.

6. **Why did the VLM lose to confidence filtering? Does H10 run it?**  
   At the same recall, confidence filtering produced 11 false positives and selective VLM verification produced 12. Very small targets, crop design and domain mismatch are plausible contributors. The experiment used saved candidates on a separate GPU. The H10 pipeline uses the detector and NMS.

7. **Is the GUI demo an independent video test?**  
   It is a recorded workflow demonstration. The group brief describes a playback loop of 30 infrared stills. The available records do not verify the exact image list or per-image H10 hits. The older 300-frame SIA+CSP records refer to a different model and demonstration. We make no independent continuous-video accuracy claim.

8. **How does this relate to Big Data?**  
   The course themes match specific checks here: label checks, deduplication and a frozen split determine whether validation is trustworthy; the 500, 1,000 and 1,999-image runs test training scale; the H10 measurements report throughput and latency under three image workloads.

9. **What are the main limitations and next steps?**  
   Small targets account for 153 of 163 misses. Internal data was reused for model and NMS selection, and native AP50:95 on one external AUVD subset was 11.494%. Improve tiny-target localization, audit labels, run multiple seeds, and test new sensors and independently recorded continuous video. Try revised VLM crops and prompts only with a matched confidence baseline.

10. **Why do the slides show 31.274% and 31.740%?**  
    31.274% is the native validation score. 31.740% is the H10 deployment score with explicit NMS. Comparing common FP32 at 25.186% with H10 without NMS at 24.351% measures the documented conversion gap of 0.835 percentage points under the common deployment pipeline.

11. **Does PinP2 have the highest accuracy in every comparison?**  
    PConv + SD has a higher native AP50:95, at 32.93%. In the historical H10 cross-model setting, YOLO11n has higher AP and YOLOv8n a lower miss rate than PinP2. We selected PinP2 as a balance of accuracy, size and observed edge speed.
