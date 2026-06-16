"""
novelty.py — score each prompt by distance to its nearest cluster centroid.

novelty[i] = 1 - max_cosine_similarity(prompt_i, all_cluster_centroids)

Higher score = further from every known cluster = more novel.

Run with:
    PYTHONPATH=. uv run python src/analytics/novelty.py
"""

import logging
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import typer

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)

app = typer.Typer()


def load_embeddings(embeddings_dir: Path) -> tuple[np.ndarray, list[str]]:
    """
    Load embeddings and their IDs from disk.

    Returns:
        embeddings: float32 array of shape (n_prompts, embedding_dim)
        ids: list of prompt IDs in the same order as embeddings
    """
    emb = np.load(embeddings_dir / "embeddings.npy").astype("float32")
    ids = np.load(embeddings_dir / "ids.npy", allow_pickle=True).tolist()
    log.info("Loaded %d embeddings of dimension %d", len(ids), emb.shape[1])
    return emb, ids


def cosine_normalize(embeddings: np.ndarray) -> np.ndarray:
    """
    L2-normalize each embedding vector.

    After normalization, dot product == cosine similarity.
    This is more efficient than computing cosine similarity directly
    because we can use matrix multiplication instead of per-pair division.

    Why normalize here rather than at search time?
    We normalize once and reuse the normalized vectors for all centroid
    comparisons — O(n) normalization vs O(n*k) if done per comparison.
    """
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    # Avoid division by zero for zero vectors
    norms = np.where(norms == 0, 1, norms)
    return embeddings / norms


def compute_centroids(
    embeddings: np.ndarray,
    ids: list[str],
    clusters: pd.DataFrame,
) -> np.ndarray:
    """
    Compute the centroid embedding for each cluster.

    A centroid is the mean of all embeddings assigned to that cluster.
    We exclude noise points (cluster == -1) since they have no cluster.

    Why mean? It's the point that minimizes squared distance to all
    members — the geometric center of the cluster in embedding space.

    Returns:
        centroids: float32 array of shape (n_clusters, embedding_dim)
                   rows are ordered by cluster ID (0, 1, 2, ...)
    """
    id_to_idx = {id_: i for i, id_ in enumerate(ids)}

    # Only non-noise clusters
    clustered = clusters[clusters["cluster"] != -1].copy()
    cluster_ids = sorted(clustered["cluster"].unique())
    log.info("Computing centroids for %d clusters", len(cluster_ids))

    embedding_dim = embeddings.shape[1]
    centroids = np.zeros((len(cluster_ids), embedding_dim), dtype="float32")

    for i, cid in enumerate(cluster_ids):
        cluster_prompts = clustered[clustered["cluster"] == cid]
        # Get embedding indices for this cluster's prompts
        indices = [
            id_to_idx[row_id] for row_id in cluster_prompts["id"] if row_id in id_to_idx
        ]
        if not indices:
            log.warning("Cluster %d has no embeddings — skipping", cid)
            continue
        # Mean of all embeddings in this cluster
        centroids[i] = embeddings[indices].mean(axis=0)

    return centroids, cluster_ids


def compute_novelty_scores(
    embeddings: np.ndarray,
    centroids: np.ndarray,
) -> np.ndarray:
    """
    Compute novelty score for each prompt.

    novelty[i] = 1 - max(cosine_similarity(prompt_i, centroid_c) for all c)

    Steps:
    1. Normalize both embeddings and centroids (dot product = cosine similarity)
    2. Compute similarity matrix: (n_prompts, n_clusters)
       via matrix multiplication: normalized_emb @ normalized_centroids.T
    3. Take the max similarity across all clusters for each prompt
    4. Subtract from 1

    Why matrix multiplication?
    It computes all (prompt, centroid) similarities at once —
    O(n*k*d) where n=prompts, k=clusters, d=dimensions.
    Looping would be O(n*k) function calls with the same complexity
    but much higher Python overhead.
    """
    norm_emb = cosine_normalize(embeddings)
    norm_centroids = cosine_normalize(centroids)

    # Shape: (n_prompts, n_clusters)
    # Each row is the similarity of one prompt to all cluster centroids
    similarity_matrix = norm_emb @ norm_centroids.T

    # Max similarity to any centroid, per prompt
    max_similarity = similarity_matrix.max(axis=1)

    # Novelty = distance from nearest centroid
    novelty_scores = 1 - max_similarity

    log.info(
        "Novelty scores — min: %.3f, max: %.3f, mean: %.3f",
        novelty_scores.min(),
        novelty_scores.max(),
        novelty_scores.mean(),
    )
    return novelty_scores


def save_distribution_plot(scores: np.ndarray, out_path: Path) -> None:
    """
    Save a histogram of the novelty score distribution.

    Why a histogram? We want to see the shape of the distribution:
    - Is it uniform? (scores spread evenly — no clear outliers)
    - Is it skewed right? (most prompts are typical, few are very novel)
    - Are there gaps? (suggests discrete clusters of novelty)

    nbins=50 gives enough resolution to see the shape without noise.
    """
    fig = px.histogram(
        x=scores,
        nbins=50,
        labels={"x": "Novelty Score", "y": "Count"},
        title="Novelty Score Distribution",
    )
    fig.update_layout(
        xaxis_title="Novelty Score (1 = maximally novel)",
        yaxis_title="Number of Prompts",
        bargap=0.1,
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(str(out_path))
    log.info("Saved distribution plot → %s", out_path)


def print_top_novel(df: pd.DataFrame, n: int = 20) -> None:
    """
    Print the top-n most novel prompts for manual inspection.

    This is the key analytical step. Read each prompt and ask:
    - Is this actually a new attack type the clustering missed?
    - Or is it an artifact (encoding error, very short, non-English)?
    - Or is it just a weird prompt that doesn't fit neatly anywhere?

    The spec's opinion: most will be garbage. Verify that yourself.
    """
    top = df.nlargest(n, "novelty_score")

    print(f"\n{'=' * 80}")
    print(f"TOP {n} MOST NOVEL PROMPTS")
    print(f"{'=' * 80}")

    for rank, (_, row) in enumerate(top.iterrows(), 1):
        print(
            f"\nRank {rank} | Score: {row['novelty_score']:.4f} | "
            f"Cluster: {row['cluster']} | Source: {row['source']}"
        )
        print(f"  {str(row['prompt'])[:200]}")

    print(f"\n{'=' * 80}")


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
    out: Path = typer.Option(
        Path("reports/"),
        help="Output directory",
    ),
    top_n: int = typer.Option(
        20,
        help="Number of most novel prompts to inspect",
    ),
) -> None:
    """Score each prompt by distance to its nearest cluster centroid."""

    # Load embeddings
    emb, ids = load_embeddings(embeddings)

    # Load cluster assignments
    clusters_df = pd.read_parquet(clusters)
    log.info("Loaded %d clustered records", len(clusters_df))

    # Align embeddings to cluster dataframe
    id_to_idx = {id_: i for i, id_ in enumerate(ids)}
    clusters_df = clusters_df[clusters_df["id"].isin(id_to_idx)].copy()
    aligned_indices = [id_to_idx[row_id] for row_id in clusters_df["id"]]
    aligned_emb = emb[aligned_indices]
    log.info("Aligned %d records with embeddings", len(clusters_df))

    # Compute centroids
    centroids, cluster_ids = compute_centroids(
        aligned_emb, clusters_df["id"].tolist(), clusters_df
    )

    # Compute novelty scores
    novelty_scores = compute_novelty_scores(aligned_emb, centroids)
    clusters_df["novelty_score"] = novelty_scores

    # Save scored dataset
    out.mkdir(parents=True, exist_ok=True)
    scored_path = out / "novelty_scores.parquet"
    clusters_df.to_parquet(scored_path, index=False)
    log.info("Saved scored dataset → %s", scored_path)

    csv_path = out / "novelty_scores.csv"
    clusters_df[["id", "source", "cluster", "novelty_score", "prompt"]].to_csv(
        csv_path, index=False
    )
    log.info("Saved CSV → %s", csv_path)

    # Plot distribution
    save_distribution_plot(novelty_scores, out / "novelty_distribution.html")

    # Print top novel prompts for manual inspection
    print_top_novel(clusters_df, top_n)


if __name__ == "__main__":
    app()
