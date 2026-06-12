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


# ─────────────────────────────────────────────────────────────────────────────
# Step 1: Load everything we need
# ─────────────────────────────────────────────────────────────────────────────


def load_data(
    clusters_path: Path,
    labels_path: Path,
) -> tuple[pd.DataFrame, dict[int, str]]:
    """
    Load the clustered corpus and human-assigned cluster labels.

    We load two things:
      - clusters.parquet: the full corpus with a 'cluster' column
      - cluster_labels.csv: the human labels you assigned to each cluster ID

    The labels dict maps cluster number -> label string so we can print
    readable names in the report instead of just "Cluster 7".
    """
    corpus = pd.read_parquet(clusters_path)
    log.info("Loaded %d records from %s", len(corpus), clusters_path)

    # Load human labels if the file exists and has content
    cluster_labels: dict[int, str] = {}
    if labels_path.exists() and labels_path.stat().st_size > 0:
        labels_df = pd.read_csv(labels_path)

        # Try common column name patterns — adjust if yours differ
        # Expecting columns like: Number, behavior_label  (or similar)
        num_col = next(
            (c for c in labels_df.columns if c.lower() in ("number", "cluster", "id")),
            None,
        )
        label_col = next(
            (
                c
                for c in labels_df.columns
                if c.lower()
                in ("behavior_label", "cluster description", "label", "name")
            ),
            None,
        )

        if num_col and label_col:
            cluster_labels = dict(zip(labels_df[num_col], labels_df[label_col]))
            log.info("Loaded %d cluster labels", len(cluster_labels))
        else:
            log.warning(
                "Could not find expected columns in %s — columns found: %s",
                labels_path,
                list(labels_df.columns),
            )
    else:
        log.warning(
            "No labels file found at %s — will use cluster IDs only", labels_path
        )

    return corpus, cluster_labels


# ─────────────────────────────────────────────────────────────────────────────
# Step 2: Rebuild the embeddings in the same order HDBSCAN saw them
# ─────────────────────────────────────────────────────────────────────────────


def align_embeddings(
    corpus: pd.DataFrame,
    embeddings_dir: Path,
) -> np.ndarray:
    """
    Load the raw embeddings and align them to the corpus row order.

    Why do we need to align? The embeddings file stores vectors in the order
    they were embedded, which may not match the order of rows in clusters.parquet.
    We match by ID so each row in the corpus maps to the correct embedding vector.

    Returns a numpy array where row i is the embedding for corpus.iloc[i].
    """
    emb = np.load(embeddings_dir / "embeddings.npy").astype("float32")
    ids = np.load(embeddings_dir / "ids.npy", allow_pickle=True).tolist()

    id_to_idx = {id_: i for i, id_ in enumerate(ids)}

    # Only keep corpus rows that have an embedding
    has_embedding = corpus["id"].isin(id_to_idx)
    if not has_embedding.all():
        missing = (~has_embedding).sum()
        log.warning("%d corpus rows have no embedding — they will be skipped", missing)

    corpus_filtered = corpus[has_embedding].reset_index(drop=True)
    aligned_indices = [id_to_idx[row_id] for row_id in corpus_filtered["id"]]
    aligned_emb = emb[aligned_indices]

    log.info(
        "Aligned %d embeddings (shape: %s)", len(aligned_indices), aligned_emb.shape
    )
    return corpus_filtered, aligned_emb


# ─────────────────────────────────────────────────────────────────────────────
# Step 3: Re-run HDBSCAN — same params as your original run
# ─────────────────────────────────────────────────────────────────────────────


def rerun_hdbscan(
    aligned_emb: np.ndarray,
    min_cluster_size: int,
    min_samples: int,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Re-run UMAP + HDBSCAN with the same parameters as the original clustering.

    Why re-run instead of loading saved results?
    The cluster assignments (the -1, 0, 1, 2... labels) are saved in clusters.parquet,
    but the HDBSCAN *object* itself — which contains the membership probabilities —
    is not saved. We need to re-run to get the probabilities_ attribute.

    This will produce the same cluster assignments as before (UMAP and HDBSCAN
    are both seeded with random_state=42), so the labels will match what you
    already have.

    Returns:
      labels        — the cluster assignment for each point (-1 = noise)
      probabilities — the soft membership score for each point (0.0 to 1.0)
    """
    log.info("Running UMAP (5D)...")
    reducer = umap.UMAP(
        n_components=5,
        n_neighbors=15,
        min_dist=0.0,
        random_state=42,  # MUST match your original run
    )
    reduced = reducer.fit_transform(aligned_emb)

    log.info(
        "Running HDBSCAN (min_cluster_size=%d, min_samples=%d)...",
        min_cluster_size,
        min_samples,
    )
    clusterer = hdbscan.HDBSCAN(
        min_cluster_size=min_cluster_size,
        min_samples=min_samples,
        metric="euclidean",
        # This is the key flag — tells HDBSCAN to compute soft memberships
        # for ALL clusters, not just the assigned one.
        prediction_data=True,
    )
    labels = clusterer.fit_predict(reduced)

    # probabilities_ is an array of shape (n_points,)
    # Each value is the confidence that this point belongs to its assigned cluster.
    probabilities = clusterer.probabilities_

    n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
    n_noise = (labels == -1).sum()
    log.info(
        "Clustering done: %d clusters, %d noise points (%.1f%%)",
        n_clusters,
        n_noise,
        n_noise / len(labels) * 100,
    )

    return labels, probabilities


# ─────────────────────────────────────────────────────────────────────────────
# Step 4: Find weak members — points below the probability threshold
# ─────────────────────────────────────────────────────────────────────────────


def find_weak_members(
    corpus: pd.DataFrame,
    labels: np.ndarray,
    probabilities: np.ndarray,
    threshold: float,
    cluster_labels: dict[int, str],
) -> pd.DataFrame:
    """
    Find all clustered points whose membership probability is below `threshold`.

    A 'weak member' is a point that HDBSCAN technically assigned to a cluster
    but with low confidence. These are the points most likely to be:
      - On the border between two clusters
      - Genuinely ambiguous / mixed-content prompts
      - Worth reviewing to see if they actually belong somewhere else

    We ignore noise points (label == -1) because they have no cluster assignment.

    Returns a DataFrame of weak members with columns:
      cluster_id, cluster_label, probability, prompt, source, attack_category
    """
    corpus = corpus.copy()
    corpus["cluster_id"] = labels
    corpus["probability"] = probabilities

    # Ignore noise points — they have no cluster to be a weak member of
    clustered = corpus[corpus["cluster_id"] != -1].copy()

    # Flag points below the threshold
    weak = clustered[clustered["probability"] < threshold].copy()

    # Add human-readable cluster label
    weak["cluster_label"] = weak["cluster_id"].map(
        lambda cid: cluster_labels.get(cid, f"cluster_{cid}")
    )

    # Sort by cluster, then by probability ascending (weakest first)
    weak = weak.sort_values(["cluster_id", "probability"]).reset_index(drop=True)

    log.info(
        "Found %d weak members (probability < %.2f) across %d clusters",
        len(weak),
        threshold,
        weak["cluster_id"].nunique(),
    )
    return weak


# ─────────────────────────────────────────────────────────────────────────────
# Step 5: Print the report
# ─────────────────────────────────────────────────────────────────────────────


def print_report(
    weak: pd.DataFrame,
    corpus: pd.DataFrame,
    labels: np.ndarray,
    probabilities: np.ndarray,
    threshold: float,
    cluster_labels: dict[int, str],
    top_n: int,
) -> None:
    """
    Print a human-readable report of weak cluster members.

    For each cluster that has weak members, we show:
      - The cluster label
      - How many total points are in the cluster
      - How many are weak (below threshold)
      - The weakest N prompts so you can read them and judge

    Reading the actual prompts is essential — a probability of 0.02 doesn't tell
    you *why* the point is a weak member. Only reading the prompt tells you that.
    """
    total_clustered = (labels != -1).sum()
    total_weak = len(weak)

    print("\n" + "=" * 80)
    print("CLUSTER QUALITY REPORT")
    print(f"Threshold: probability < {threshold}")
    print(f"Total clustered points: {total_clustered}")
    print(
        f"Total weak members: {total_weak} ({total_weak / total_clustered * 100:.1f}%)"
    )
    print("=" * 80)

    if total_weak == 0:
        print("\nNo weak members found. All points are confidently assigned.")
        return

    # Group by cluster and report
    for cluster_id in sorted(weak["cluster_id"].unique()):
        cluster_weak = weak[weak["cluster_id"] == cluster_id]
        cluster_label = cluster_labels.get(cluster_id, f"cluster_{cluster_id}")

        # Total size of this cluster (including strong members)
        total_in_cluster = (labels == cluster_id).sum()
        weak_count = len(cluster_weak)
        weak_pct = weak_count / total_in_cluster * 100

        print(f"\n{'─' * 80}")
        print(f"CLUSTER {cluster_id}: {cluster_label}")
        f"Total points: {total_in_cluster} | "
        f"Weak members: {weak_count} ({weak_pct:.1f}%)"
        print(f"{'─' * 80}")

        # Show the top_n weakest prompts
        for _, row in cluster_weak.head(top_n).iterrows():
            prob = row["probability"]
            src = row.get("source", "?")
            print(f"\n  [prob={prob:.3f}] source={src}")
            prompt = str(row.get("prompt", ""))
            # Wrap at 100 chars for readability
            print(f"  {prompt[:120]}")
            if len(prompt) > 120:
                print(f"  ...({len(prompt)} chars total)")

    print("\n" + "=" * 80)


# ─────────────────────────────────────────────────────────────────────────────
# Step 6: Save results to CSV
# ─────────────────────────────────────────────────────────────────────────────


def save_results(
    corpus: pd.DataFrame,
    labels: np.ndarray,
    probabilities: np.ndarray,
    weak: pd.DataFrame,
    out_dir: Path,
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    # Full corpus with probabilities
    full = corpus.copy()
    full["cluster_id"] = labels
    full["probability"] = probabilities
    full_path = out_dir / "all_with_probabilities.csv"
    full.to_csv(full_path, index=False)
    log.info("Saved full results to %s", full_path)

    # Weak members only
    weak_path = out_dir / "weak_members.csv"
    save_cols = [
        c
        for c in [
            "cluster_id",
            "cluster_label",
            "probability",
            "source",
            "attack_category",
            "prompt",
        ]
        if c in weak.columns
    ]
    weak[save_cols].to_csv(weak_path, index=False)
    log.info("Saved weak members to %s", weak_path)


# ─────────────────────────────────────────────────────────────────────────────
# CLI entry point
# ─────────────────────────────────────────────────────────────────────────────


@app.command()
def main(
    embeddings: Path = typer.Option(
        "data/embeddings/",
        help="Directory containing embeddings.npy and ids.npy",
    ),
    clusters: Path = typer.Option(
        "data/clusters/clusters.parquet",
        help="Clustered corpus parquet file",
    ),
    labels: Path = typer.Option(
        "data/clusters/cluster_labels.csv",
        help="CSV with human-assigned cluster labels",
    ),
    out: Path = typer.Option(
        "data/clusters/quality/",
        help="Output directory for quality report files",
    ),
    threshold: float = typer.Option(
        0.05,
        help="Membership probability below this is flagged as a weak member",
    ),
    min_cluster_size: int = typer.Option(
        15,
        help="Must match your original HDBSCAN run",
    ),
    min_samples: int = typer.Option(
        5,
        help="Must match your original HDBSCAN run",
    ),
    top_n: int = typer.Option(
        5,
        help="Number of weakest prompts to show per cluster in the report",
    ),
) -> None:
    """
    Identify cluster members that may not truly belong to their cluster.

    Uses HDBSCAN's soft membership probabilities to flag points that were
    assigned to a cluster but with low confidence. Low-probability points
    sit on cluster boundaries and may belong to a different cluster, or may
    represent genuinely ambiguous prompts.
    """
    # Load
    corpus, cluster_labels = load_data(clusters, labels)

    # Align embeddings to corpus row order
    corpus, aligned_emb = align_embeddings(corpus, embeddings)

    # Re-run HDBSCAN to get probabilities
    new_labels, probabilities = rerun_hdbscan(
        aligned_emb, min_cluster_size, min_samples
    )

    # Find weak members
    weak = find_weak_members(
        corpus, new_labels, probabilities, threshold, cluster_labels
    )

    # Print report
    print_report(
        weak, corpus, new_labels, probabilities, threshold, cluster_labels, top_n
    )

    # Save
    save_results(corpus, new_labels, probabilities, weak, out)

    log.info("Done. Review data/clusters/quality/weak_members.csv for follow-up.")


if __name__ == "__main__":
    app()
