# Week 5 Notes — Coverage Analytics & Novelty

## What we built
- `cluster_assignments.yaml` — two-dimensional mapping of all 69 clusters to
  primitive (technique) and behavior (objective)
- `src/analytics/coverage_analysis.py` — primitive x behavior heatmap
- `src/analytics/novelty.py` — novelty scoring by distance to cluster centroids
- `docs/sparse-areas.md` — sparse cell analysis
- `docs/novelty-inspection.md` — top-20 manual inspection

## Three observations

### 1. The dataset is dominated by meta-attacks
20 of 69 clusters (29%) have `content_policy_circumvention` as their behavior — prompts whose only goal is unlocking the model, not causing specific downstream harm. The corpus knows a lot about DAN jailbreaks and almost nothing about what attackers do after the jailbreak succeeds.

### 2. Emotional manipulation is nearly invisible
`emotional_engagement` appears in only 2 clusters. Both sparse-area gaps flagged as high priority involve emotional manipulation — `emotional_engagement x harmful_advice` and `emotional_engagement x misinformation_generation`. These are common real-world patterns (users building parasocial relationships with AI to lower its guard) that academic datasets were never designed to capture.

### 3. High novelty score = artifact, not insight
The top-20 most novel prompts are dominated by encoding artifacts (morse code, unicode small caps, non-English text) and benign donotanswer questions. Only 2 of 20 represent genuine research findings. Embedding-based novelty scoring requires pre-filtering before it produces useful signal.

## Actionable insight for supervisor
**We should sample more emotional manipulation attacks.**

The dataset has 2 clusters covering emotional engagement out of 69 total. Both map to behaviors that are high-priority blind spots. A defense system trained on this corpus would have almost no signal for prompts that use relational framing, guilt, dependency, or intimacy to influence model responses. Week 6 augmentation should target `emotional_engagement x self_harm_enablement` and `emotional_engagement x harmful_advice` specifically — these combinations have zero or near-zero coverage and represent documented real-world attack patterns.

## Demo flow (15 minutes)
1. Open `reports/coverage_primitive_x_behavior.html` — point at white cells, explain 75% of the matrix is empty (2 min)
2. Walk through the 3 densest cells — what the dataset knows well (3 min)
3. Walk through the 5 sparse cells from `docs/sparse-areas.md` — dataset gaps vs rare attacks (5 min)
4. Show novelty distribution plot — explain the mean of 0.381 (3 min)
5. Read 3 examples from top-20: one artifact, one benign, one genuine finding — outlier != novel (2 min)
6. Land on the actionable insight: sample more emotional manipulation attacks
