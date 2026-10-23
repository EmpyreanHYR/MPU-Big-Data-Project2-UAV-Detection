# Source provenance and licenses

`ultralytics-yolo26.yaml` is the unmodified YOLO26 configuration from Ultralytics tag `v8.4.184`, retained for structural comparison. Its header identifies AGPL-3.0 and links to the [Ultralytics license](https://github.com/ultralytics/ultralytics/blob/v8.4.184/LICENSE). The three project YAML configurations derive from it and retain that attribution. This repository does not replace upstream licensing with a different blanket license.

`src/uav_detection/pconv.py` adapts the PConv module from [model/APConv.py](https://github.com/JN-Yang/PConv-SDloss-Data/blob/a801f043c83f73aa9af9ab2f689e59ebef928fc4/model/APConv.py), commit `a801f043c83f73aa9af9ab2f689e59ebef928fc4`. The original MIT copyright and license are retained in `pconv-LICENSE.txt`. The implementation preserves opposite-direction weight sharing and adds input validation and the project model/trainer integration.

[sources.json](sources.json) records the retrieval URLs and SHA256 values of the retained upstream files. Dataset access and redistribution terms are tracked separately in [SOURCES.md](../docs/datasets/SOURCES.md).
