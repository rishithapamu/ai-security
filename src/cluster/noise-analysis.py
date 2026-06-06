"""Analyze noise points that become clustered as epsilon increases."""

import logging
from pathlib import Path

import hdbscan
import numpy as np
import pandas as pd
import typer
import umap

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)

app = typer.Typer()

EPSILONS = [0.00, 0.05, 0.10, 0.20, 0.30, 0.50]


def load_corpus(input_dir: Path) -> pd.DataFrame:
    """Load corpus from combined parquet file."""

    corpus = pd.read_parquet(
        "/Users/rishithapamu/Desktop/internship_project/"
        "ai-sec-workbench/data/processed/combined.parquet"
    )

    log.info("Loaded corpus: %d records", len(corpus))
    return corpus


def build_umap_embeddings(
    embeddings: np.ndarray,
) -> np.ndarray:
    """Create clustering embedding."""

    log.info("Generating 5D UMAP embedding...")

    reducer = umap.UMAP(
        n_components=5,
        n_neighbors=15,
        min_dist=0.0,
        random_state=42,
    )

    return reducer.fit_transform(embeddings)


@app.command()
def main(
    input: Path = typer.Option(...),
    embeddings: Path = typer.Option(...),
    out: Path = typer.Option(
        Path(
            "/Users/rishithapamu/Desktop/internship_project/"
            "ai-sec-workbench/data/plots"
        )
    ),
) -> None:
    """Analyze noise points absorbed into clusters."""

    out.mkdir(parents=True, exist_ok=True)
    cluster_labels_df = pd.read_csv("data/clusters/cluster_labels.csv")

    cluster_labels = dict(
        zip(
            cluster_labels_df["Number"],
            cluster_labels_df["Cluster Description"],
        )
    )

    corpus = load_corpus(input)

    emb = np.load(embeddings / "embeddings.npy").astype("float32")

    ids = np.load(
        embeddings / "ids.npy",
        allow_pickle=True,
    ).tolist()

    id_to_idx = {id_: i for i, id_ in enumerate(ids)}

    aligned_corpus = corpus[corpus["id"].isin(set(ids))].copy()
    aligned_corpus["emb_idx"] = aligned_corpus["id"].map(id_to_idx)
    aligned_corpus = aligned_corpus.dropna(subset=["emb_idx"])
    aligned_corpus["emb_idx"] = aligned_corpus["emb_idx"].astype(int)
    aligned_corpus = aligned_corpus.sort_values("emb_idx").reset_index(drop=True)
    aligned_indices = aligned_corpus["emb_idx"].tolist()
    aligned_emb = emb[aligned_indices]

    log.info(
        "Aligned %d records with embeddings",
        len(aligned_corpus),
    )

    reduced_5d = build_umap_embeddings(aligned_emb)
    assert len(aligned_emb) == len(aligned_corpus), "Alignment mismatch!"
    all_labels = {}

    #
    # Run clustering for all epsilons
    #
    for epsilon in EPSILONS:
        log.info(
            "Running epsilon=%s",
            epsilon,
        )

        clusterer = hdbscan.HDBSCAN(
            min_cluster_size=15,
            min_samples=5,
            cluster_selection_epsilon=epsilon,
            metric="euclidean",
        )

        labels = clusterer.fit_predict(reduced_5d)

        all_labels[epsilon] = labels

    #
    # Baseline noise points
    #
    baseline_noise = all_labels[0.00] == -1

    print("\n")
    print("=" * 80)
    print("BASELINE EPSILON = 0.00")
    print(f"Noise points: {baseline_noise.sum()}")
    print("=" * 80)

    #
    # Compare against higher epsilons
    #
    for epsilon in EPSILONS[1:]:
        labels = all_labels[epsilon]
        noise_idx = np.where(baseline_noise)[0]
        became_clustered_idx = noise_idx[labels[noise_idx] != -1]
        count = len(became_clustered_idx)

        print("\n")
        print("=" * 80)
        print(f"EPSILON = {epsilon:.2f}")
        print("=" * 80)

        print(f"{count} noise points became clustered")

        if count == 0:
            continue

        absorbed = aligned_corpus.iloc[became_clustered_idx].copy()
        absorbed["new_cluster"] = labels[became_clustered_idx]

        absorbed["cluster_label"] = absorbed["new_cluster"].map(cluster_labels)
        assert len(absorbed) == len(became_clustered_idx)

        #
        # Save all results
        #
        absorbed.to_csv(
            out / f"noise_to_cluster_eps_{epsilon:.2f}.csv",
            index=False,
        )
        report_path = out / f"noise_review_eps_{epsilon:.2f}.md"
        with open(report_path, "w") as f:
            for cluster_id in sorted(absorbed["new_cluster"].unique()):
                cluster_prompts = absorbed[absorbed["new_cluster"] == cluster_id]

                cluster_label = cluster_prompts["cluster_label"].iloc[0]
                f.write("=" * 80 + "\n")

                f.write(f"CLUSTER {cluster_id}\n")

                f.write(f"LABEL: {cluster_label}\n")

                f.write(f"ABSORBED NOISE POINTS: " f"{len(cluster_prompts)}\n")

                f.write("=" * 80 + "\n\n")
                for i, (
                    _,
                    row,
                ) in enumerate(
                    cluster_prompts.iterrows(),
                    start=1,
                ):
                    f.write(f"PROMPT {i}\n")

                    f.write(f"Source: " f"{row['source']}\n")

                    f.write(f"Category: " f"{row['attack_category']}\n\n")

                    f.write(row["prompt"])

                    f.write("\n\n")

                    f.write("-" * 80)

                    f.write("\n\n")
        cluster_counts = absorbed["new_cluster"].value_counts().sort_index()
        print("LEN corpus:", len(aligned_corpus))
        print("LEN embeddings:", len(aligned_emb))
        print("LEN labels (eps=0.0):", len(all_labels[0.0]))
        print("\nCluster counts:")

        for cluster_id, n in cluster_counts.items():
            cluster_name = cluster_labels.get(
                cluster_id,
                "Unknown Cluster",
            )
            print(f"Cluster {cluster_id}")
            print(f"Label: {cluster_name}")
            print(f"Absorbed prompts: {n}")
            print()

        #
        # Print first 5 prompts per cluster
        #
        for cluster_id in sorted(absorbed["new_cluster"].unique()):
            print("\n")
            print("-" * 80)
            cluster_name = cluster_labels.get(
                cluster_id,
                "Unknown Cluster",
            )
            print(f"CLUSTER {cluster_id}")

            print(f"LABEL: {cluster_name}")
            print("-" * 80)

            examples = absorbed[absorbed["new_cluster"] == cluster_id].head(5)

            for i, (
                _,
                row,
            ) in enumerate(
                examples.iterrows(),
                start=1,
            ):
                print(f"\nExample {i}")

                print(f"Source: " f"{row['source']}")

                print(f"Category: " f"{row['attack_category']}")

                print("\nPrompt:")

                print(row["prompt"])

                print()

    log.info(
        "\nSaved CSV outputs to %s",
        out,
    )


if __name__ == "__main__":
    app()
