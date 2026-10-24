# SIRST-UAVB fixed background-view holdout

This manifest preserves native bounding boxes and maps class0 to UAV and class1 to bird. The PConv paper states that bird targets are excluded from masks; the full release matches 2955/2961 class0 boxes and only1/1747 class1 boxes to positive mask pixels. Six class0 mask-absence images and all pixel-identical copies are quarantined, together with three conflicting-label pixel groups. No native box is rewritten from a mask.

The release has no original video/session IDs. Groups here are **inferred background-view families**, not verified independent videos or locations. Exact-pixel deduplication, fixed luminance similarity, visual family merging and whole-component boundary quarantine produce1438 train /505 validation images. Validation holds out nearby facade views. The uneven sizes preserve these families. This baseline has no independent test split; later external video evaluation is separate.

The original3000-image2400/600 release is retained separately:496 validation images share identical pixels with training images. The public split contains1943 unique images,1421/491 native UAV boxes and925/227 bird boxes for train/validation; bird boxes remain in the audit manifest and are excluded from the UAV training labels. The policy JSON freezes thresholds, review corrections, source hashes and limitations. Quarantined originals are preserved outside Git.

Run preparation on the approved cloud after extracting only the manifest-referenced image/label members from the verified original archive:

```sh
python scripts/prepare_sirst_uavb.py prepare \
  --source-root data/raw \
  --manifest configs/datasets/sirst_uavb_scene_holdout_v3/source_manifest.csv \
  --class-map configs/datasets/sirst_uavb_scene_holdout_v3/class_map.json \
  --group-provenance configs/datasets/sirst_uavb_scene_holdout_v3/group_provenance.json \
  --train-val-only --output data/prepared-scene-v3
python scripts/prepare_sirst_uavb.py audit --output data/prepared-scene-v3
```

[Dataset author repository](https://github.com/JN-Yang/PConv-SDloss-Data) · [Paper, dataset section](https://arxiv.org/html/2412.16986v1#S3.SS3). Original imagery, cached labels, weights and experiment files are not distributed here.
