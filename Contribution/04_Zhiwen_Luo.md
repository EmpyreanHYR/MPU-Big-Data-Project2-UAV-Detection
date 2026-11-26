# Individual Work Contribution and Reflection

**Name:** Zhiwen Luo

## 1. Specific Work Carried Out

I designed and built the dataset and managed its full lifecycle. Aligned with the research objectives, I investigated possible data sources, collected and aggregated the raw data, and defined the processing specifications, annotation framework and quality-review criteria. I clarified the annotation definitions, the treatment of edge cases and the rules for adjudicating disputed samples, coordinated the annotation work and cross-checked it, and corrected annotation drift to improve consistency between annotations.

I performed systematic cleaning, filtering and desensitisation to handle noise, duplicate samples, outliers and bias in the raw data. I then carried out the stratified splitting, adjusted the sample balance, standardised the formats, and established a version-control mechanism with revision logs so that the data remained traceable and reproducible. I also wrote the dataset documentation, recording the provenance, sample distribution, construction pipeline, known limitations and usage constraints, and worked with the modelling team on data delivery, issue feedback and iterative refinement.

## 2. Main Difficulty and How It Was Resolved

The raw pool was not clean: duplicated images appeared under different file names, and some annotations disagreed with each other. File names could not be trusted as identities, so I audited by image content and source group instead, quarantined conflicting annotations rather than deleting them outright, and fixed the training and validation split so that later code could not move images between the two sets. The adjudication rules were recorded in the dataset documentation so that the same decision could be reproduced later.

## 3. Reflection

Data work is mostly bookkeeping, and an error there is invisible in the final results. My main doubt concerns scale: a small validation set makes most differences coarse, and a single duplicated sample can inflate its accuracy more than extra training data can correct. I also learned that documentation written while the work is fresh is far more useful than notes reconstructed later. Given more time, I would add an automated duplicate check before the split instead of relying on manual inspection alone.
