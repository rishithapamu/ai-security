"""Clustering pipeline — group attack records by behavioral similarity."""

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


def load_corpus(input_dir: Path) -> pd.DataFrame:
    """Load corpus from combined parquet file."""
    corpus = pd.read_parquet(
        "/Users/rishithapamu/Desktop/internship_project/ai-sec-workbench/data/processed/combined.parquet"
    )
    log.info("Loaded corpus: %d records", len(corpus))
    return corpus


def reduce_dimensions(embeddings: np.ndarray, n_components: int = 5) -> np.ndarray:
    """Reduce embeddings to lower dimensions for clustering."""
    log.info(
        "Reducing %d dimensions to %d with UMAP...",
        embeddings.shape[1],
        n_components,
    )
    reducer = umap.UMAP(
        n_components=n_components,
        n_neighbors=15,
        min_dist=0.0,
        random_state=42,
    )
    reduced = reducer.fit_transform(embeddings)
    log.info("Reduced shape: %s", reduced.shape)
    return reduced


def run_hdbscan(
    embeddings: np.ndarray,
    min_cluster_size: int = 15,
    min_samples: int = 5,
) -> np.ndarray:
    """Run HDBSCAN clustering."""
    log.info(
        "Running HDBSCAN (min_cluster_size=%d, min_samples=%d)...",
        min_cluster_size,
        min_samples,
    )
    clusterer = hdbscan.HDBSCAN(
        min_cluster_size=min_cluster_size,
        min_samples=min_samples,
        metric="euclidean",
    )
    labels = clusterer.fit_predict(embeddings)
    return labels


def summarize_clusters(labels: np.ndarray, corpus: pd.DataFrame) -> None:
    """Print cluster summary statistics."""
    n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
    n_noise = (labels == -1).sum()
    noise_rate = n_noise / len(labels) * 100

    log.info("=== CLUSTERING RESULTS ===")
    log.info("Total points: %d", len(labels))
    log.info("Number of clusters: %d", n_clusters)
    log.info("Noise points: %d (%.1f%%)", n_noise, noise_rate)

    if noise_rate > 50:
        log.warning("Noise rate > 50%% — parameters may be too strict")

    log.info("\n=== CLUSTER BREAKDOWN ===")
    corpus = corpus.copy()
    corpus["cluster"] = labels

    for cluster_id in sorted(set(labels)):
        if cluster_id == -1:
            continue
        cluster_df = corpus[corpus["cluster"] == cluster_id]
        top_category = (
            cluster_df["attack_category"].value_counts().index[0]
            if cluster_df["attack_category"].notna().any()
            else "unknown"
        )
        log.info(
            "Cluster %d: %d points | top category: %s",
            cluster_id,
            len(cluster_df),
            top_category,
        )
        for prompt in cluster_df["prompt"].head(3):
            log.info("  - %s", prompt[:80])


@app.command()
def main(
    input: Path = typer.Option(..., help="Directory containing parquet files"),
    embeddings: Path = typer.Option(..., help="Directory containing embeddings"),
    out: Path = typer.Option(..., help="Output directory for cluster results"),
    min_cluster_size: int = typer.Option(15, help="HDBSCAN min_cluster_size"),
    min_samples: int = typer.Option(5, help="HDBSCAN min_samples"),
) -> None:
    """Cluster attack records by behavioral similarity."""
    out.mkdir(parents=True, exist_ok=True)

    corpus = load_corpus(input)

    # Load embeddings and align with corpus
    emb = np.load(embeddings / "embeddings.npy").astype("float32")
    ids = np.load(embeddings / "ids.npy", allow_pickle=True).tolist()

    id_to_idx = {id_: i for i, id_ in enumerate(ids)}
    aligned_indices = [
        id_to_idx[row["id"]] for _, row in corpus.iterrows() if row["id"] in id_to_idx
    ]
    aligned_emb = emb[aligned_indices]
    aligned_corpus = corpus[corpus["id"].isin(set(ids))].reset_index(drop=True)

    log.info("Aligned %d records with embeddings", len(aligned_corpus))

    # Reduce dimensions
    reduced = reduce_dimensions(aligned_emb)

    # Cluster
    labels = run_hdbscan(reduced, min_cluster_size, min_samples)

    # Summarize
    summarize_clusters(labels, aligned_corpus)

    # Save results
    aligned_corpus["cluster"] = labels
    aligned_corpus[["id", "source", "prompt", "attack_category", "cluster"]].to_parquet(
        out / "clusters.parquet", index=False
    )
    log.info("Saved cluster results to %s", out / "clusters.parquet")


if __name__ == "__main__":
    app()
