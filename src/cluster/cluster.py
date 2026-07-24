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
    combined = input_dir / "combined.parquet"
    if not combined.exists():
        raise FileNotFoundError(
            f"Expected {combined} — run `uv run python cli.py ingest` first."
        )
    corpus = pd.read_parquet(combined)
    log.info("Loaded %d records from %s", len(corpus), combined)
    return corpus


def reduce_dimensions(
    embeddings: np.ndarray,
    n_components: int = 5,
) -> np.ndarray:
    log.info(
        "Reducing %d dimensions → %d with UMAP…",
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
    log.info(
        "Running HDBSCAN (min_cluster_size=%d, min_samples=%d)…",
        min_cluster_size,
        min_samples,
    )
    clusterer = hdbscan.HDBSCAN(
        min_cluster_size=min_cluster_size,
        min_samples=min_samples,
        metric="euclidean",
    )
    return clusterer.fit_predict(embeddings)


def summarize_clusters(labels: np.ndarray, corpus: pd.DataFrame) -> None:
    n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
    n_noise = (labels == -1).sum()
    noise_rate = n_noise / len(labels) * 100

    log.info("Clusters: %d | Noise: %d (%.1f%%)", n_clusters, n_noise, noise_rate)

    if noise_rate > 50:
        log.warning("Noise rate > 50%% — parameters may be too strict.")

    # Temporary view for groupby — corpus is NOT modified
    temp = corpus.assign(cluster=pd.Series(labels, index=corpus.index))

    for cluster_id in sorted(set(labels)):
        if cluster_id == -1:
            continue
        rows = temp[temp["cluster"] == cluster_id]
        top_category = (
            rows["attack_category"].value_counts().index[0]
            if rows["attack_category"].notna().any()
            else "unknown"
        )
        log.info(
            "Cluster %d: %d prompts | top: %s", cluster_id, len(rows), top_category
        )
        for prompt in rows["prompt"].head(3):
            log.info("  - %s", prompt[:80])


def align_embeddings(
    corpus: pd.DataFrame,
    emb: np.ndarray,
    ids: list[str],
) -> tuple[pd.DataFrame, np.ndarray]:
    id_index_df = pd.DataFrame({"id": ids, "_emb_idx": range(len(ids))})
    merged = corpus.merge(id_index_df, on="id", how="inner")

    n_dropped = len(corpus) - len(merged)
    if n_dropped > 0:
        log.warning(
            "%d corpus rows have no embedding and will be excluded. "
            "Re-run `cli.py embed` if this is unexpected.",
            n_dropped,
        )

    aligned_corpus = merged.drop(columns=["_emb_idx"]).reset_index(drop=True)
    aligned_emb = emb[merged["_emb_idx"].values]

    log.info("Aligned %d records with embeddings.", len(aligned_corpus))
    return aligned_corpus, aligned_emb


@app.command()
def main(
    input: Path = typer.Option(..., help="Directory containing parquet files"),
    embeddings: Path = typer.Option(..., help="Directory containing embeddings"),
    out: Path = typer.Option(..., help="Output directory"),
    min_cluster_size: int = typer.Option(15, help="HDBSCAN min_cluster_size"),
    min_samples: int = typer.Option(5, help="HDBSCAN min_samples"),
) -> None:
    """Cluster attack records by behavioral similarity."""
    out.mkdir(parents=True, exist_ok=True)

    corpus = load_corpus(input)

    emb = np.load(embeddings / "embeddings.npy").astype("float32")
    ids = np.load(embeddings / "ids.npy", allow_pickle=True).tolist()

    # BEFORE: alignment logic was 5 lines of inline code here in main()
    # AFTER: named function — main() reads as a clean pipeline description
    aligned_corpus, aligned_emb = align_embeddings(corpus, emb, ids)

    reduced = reduce_dimensions(aligned_emb)
    labels = run_hdbscan(reduced, min_cluster_size, min_samples)

    summarize_clusters(labels, aligned_corpus)

    aligned_corpus["cluster"] = labels
    output_path = out / "clusters.parquet"
    aligned_corpus[["id", "source", "prompt", "attack_category", "cluster"]].to_parquet(
        output_path,
        index=False,
    )
    log.info("Saved → %s", output_path)


if __name__ == "__main__":
    app()
