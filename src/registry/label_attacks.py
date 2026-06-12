from pathlib import Path

import pandas as pd
import yaml

df = pd.read_parquet("data/clusters/clusters.parquet")

print(f"Loaded {len(df)} prompts")

with open(
    "src/registry/candidates/cluster_to_primitive.yaml",
) as f:
    primitive_yaml = yaml.safe_load(f)


cluster_to_primitive = {}

for primitive, clusters in primitive_yaml["Cluster_to_primitive"].items():
    for cluster in clusters:
        cluster_to_primitive[cluster] = primitive

with open(
    "src/registry/candidates/behaviors.yaml",
) as f:
    behavior_yaml = yaml.safe_load(f)

print(list(behavior_yaml.keys()))

cluster_to_behavior = {}

for behavior, info in behavior_yaml.items():
    if behavior == "notes":
        continue

    for cluster in info["clusters"]:
        cluster_to_behavior[cluster] = behavior

df["primitive_id"] = df["cluster"].map(cluster_to_primitive).fillna("unmapped")

df["behavior_id"] = df["cluster"].map(cluster_to_behavior).fillna("unmapped")

total = len(df)

primitive_mapped = (df["primitive_id"] != "unmapped").sum()

behavior_mapped = (df["behavior_id"] != "unmapped").sum()

print("\nCoverage Report")
print("-" * 40)

print(f"Total prompts: {total}")

print(
    f"Primitive coverage: "
    f"{primitive_mapped}/{total} "
    f"({primitive_mapped/total:.1%})"
)

print(
    f"Behavior coverage: "
    f"{behavior_mapped}/{total} "
    f"({behavior_mapped/total:.1%})"
)

output_path = "data/attacks_labeled.parquet"

Path("data/processed").mkdir(
    parents=True,
    exist_ok=True,
)

df.to_parquet(
    output_path,
    index=False,
)

df.to_csv("data/attacks_labeled.csv", index=False)

print(f"\nSaved labeled dataset to: " f"{output_path}")

print("\nSample rows:")

print(
    df[
        [
            "cluster",
            "primitive_id",
            "behavior_id",
        ]
    ].head(10)
)

unmapped_df = df[(df["primitive_id"] == "unmapped") | (df["behavior_id"] == "unmapped")]

print("\nUnmapped Analysis")
print("-" * 40)

print(f"Total unmapped rows: {len(unmapped_df)}")
print(f"Percentage unmapped: {len(unmapped_df) / len(df):.1%}")

print("\nUnmapped by cluster:")
print(unmapped_df["cluster"].value_counts().sort_values(ascending=False))

print("\nSample unmapped rows:")
print(unmapped_df[["cluster", "primitive_id", "behavior_id"]].head(1))
print("\nUnmapped primitive missing clusters:")
print(set(unmapped_df["cluster"]) - set(cluster_to_primitive.keys()))

print("\nUnmapped behavior missing clusters:")
print(set(unmapped_df["cluster"]) - set(cluster_to_behavior.keys()))
