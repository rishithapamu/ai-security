from pathlib import Path

import pandas as pd
import yaml

df = pd.read_parquet("data/clusters/clusters.parquet")
print(f"Loaded {len(df)} prompts")

# Single source of truth — do NOT read cluster_to_primitive.yaml or
# behaviors.yaml, they are stale drafts from before the registry was
# finalized (see ADR 004). cluster_assignments.yaml is authoritative.
with open("src/registry/candidates/cluster_assignments.yaml") as f:
    assignments_yaml = yaml.safe_load(f)

cluster_assignments = {
    int(k): v for k, v in assignments_yaml["cluster_assignments"].items()
}

cluster_to_primitive = {c: info["primitive"] for c, info in cluster_assignments.items()}
cluster_to_behavior = {c: info["behavior"] for c, info in cluster_assignments.items()}

df["primitive_id"] = df["cluster"].map(cluster_to_primitive).fillna("unmapped")
df["behavior_id"] = df["cluster"].map(cluster_to_behavior).fillna("unmapped")

total = len(df)
primitive_mapped = (df["primitive_id"] != "unmapped").sum()
behavior_mapped = (df["behavior_id"] != "unmapped").sum()

print("\nCoverage Report")
print("-" * 40)
print(f"Total prompts: {total}")
print(
    f"Primitive coverage: {primitive_mapped}/{total} ({primitive_mapped / total:.1%})"
)
print(f"Behavior coverage: {behavior_mapped}/{total} ({behavior_mapped / total:.1%})")

output_path = "data/attacks_labeled.parquet"
Path("data/processed").mkdir(parents=True, exist_ok=True)
df.to_parquet(output_path, index=False)
df.to_csv("data/attacks_labeled.csv", index=False)
print(f"\nSaved labeled dataset to: {output_path}")

print("\nSample rows:")
print(df[["cluster", "primitive_id", "behavior_id"]].head(10))

unmapped_df = df[(df["primitive_id"] == "unmapped") | (df["behavior_id"] == "unmapped")]
print("\nUnmapped Analysis")
print("-" * 40)
print(f"Total unmapped rows: {len(unmapped_df)}")
if len(unmapped_df):
    print(f"Percentage unmapped: {len(unmapped_df) / len(df):.1%}")
    print("\nUnmapped by cluster:")
    print(unmapped_df["cluster"].value_counts().sort_values(ascending=False))
