# Cluster Tuning Results

## Parameter Sweep

| min_cluster_size | n_clusters | n_noise | noise_rate_pct | silhouette_score |
|---|---|---|---|---|
| 5 | 150 | 737 | 21.3% | 0.663 |
| 10 | 99 | 809 | 23.4% | 0.664 |
| 15 | 70 | 832 | 24.0% | 0.649 |
| 25 | 43 | 900 | 26.0% | 0.619 |
| 50 | 16 | 411 | 11.9% | 0.504 |

## Chosen Setting

**min_cluster_size = 15**

This setting produces 70 clusters with a 24% noise rate and silhouette score of 0.649. While min_cluster_size=10 produces a marginally better silhouette score (0.664), it results in 99 clusters which is too many to label and interpret meaningfully.

min_cluster_size=15 strikes the right balance — clusters are specific enough to represent a single attack behavior (e.g. all bomb-making prompts in one cluster) without being so broad that unrelated attack types get lumped together. min_cluster_size=50 was rejected because 16 clusters is too coarse — it would merge distinct behaviors like DAN jailbreaks and financial fraud into the same group.

The silhouette score is used as a guide only. The deciding factor is interpretability — whether a cluster's prompts can be described in one sentence.
