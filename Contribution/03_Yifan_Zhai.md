# Individual Work Contribution and Reflection

**Name:** Yifan Zhai

## 1. Specific Work Carried Out

I was responsible for application testing, error analysis and report proofreading for the infrared UAV detection system. In application testing, I examined the image and video detection workflow, including the visualisation of detection results, the display of bounding boxes, the output of confidence scores and the export of results, and checked that these functions were complete and stable. I also compared the system's response and application behaviour under different operating conditions to ensure that the detection workflow met the project requirements.

In error analysis, I used the experimental results to examine false positives and false negatives caused by complex backgrounds, small targets and different confidence thresholds. I assessed detection accuracy, inference efficiency and system stability, identified limitations in practical use and proposed possible improvements. In addition, I reviewed and proofread the project report, checking technical terminology, grammar, logical connections, figure and table descriptions and formatting, so that the technical descriptions were accurate, the experimental results were consistent and the final report was clearer and easier to read.

## 2. Main Difficulty and How It Was Resolved

One observed failure could have had several plausible causes, because a missed target may result from a strong background, a small target size or an unsuitable confidence threshold. A single example therefore could not tell us which factor was responsible. I kept the tests separate, changed only one factor at a time, and recorded the scene and the threshold behind every failure before drawing a conclusion.

## 3. Reflection

Error analysis is more useful than a single accuracy figure, but it must remain tied to visible examples; otherwise it becomes a list of guesses. This work would have been stronger if the team had agreed on a failure-taxonomy sheet before testing began. I also found that proofreading is not only a language task: an inconsistent term or an unexplained figure can change how an experiment is understood, so the report needs the same careful checking as the code.
