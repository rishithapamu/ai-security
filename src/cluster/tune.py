"""Parameter sweep for HDBSCAN clustering."""

import logging
from pathlib import Path

import hdbscan
import numpy as np
import pandas as pd
import typer
import umap
from sklearn.metrics import silhouette_score

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)

app = typer.Typer()

MIN_CLUSTER_SIZES = [5, 10, 15, 25, 50]


def run_sweep(reduced_embeddings: np.ndarray) -> list[dict]:
    """Sweep min_cluster_size and collect results."""
    results = []

    for min_size in MIN_CLUSTER_SIZES:
        log.info("Testing min_cluster_size=%d...", min_size)

        clusterer = hdbscan.HDBSCAN(
            min_cluster_size=min_size,
            min_samples=5,
            metric="euclidean",
        )
        labels = clusterer.fit_predict(reduced_embeddings)

        n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
        n_noise = (labels == -1).sum()
        noise_rate = n_noise / len(labels) * 100

        # Only compute silhouette if we have at least 2 clusters
        if n_clusters >= 2:
            # Exclude noise points for silhouette
            mask = labels != -1
            if mask.sum() > n_clusters:
                sil_score = silhouette_score(
                    reduced_embeddings[mask],
                    labels[mask],
                    sample_size=min(1000, mask.sum()),
                )
            else:
                sil_score = None
        else:
            sil_score = None

        results.append(
            {
                "min_cluster_size": min_size,
                "n_clusters": n_clusters,
                "n_noise": n_noise,
                "noise_rate_pct": round(noise_rate, 1),
                "silhouette_score": round(sil_score, 3) if sil_score else "N/A",
            }
        )

        log.info(
            "  clusters=%d, noise=%d (%.1f%%), silhouette=%s",
            n_clusters,
            n_noise,
            noise_rate,
            round(sil_score, 3) if sil_score else "N/A",
        )

    return results


@app.command()
def main(
    input: Path = typer.Option(..., help="Directory containing parquet files"),
    embeddings: Path = typer.Option(..., help="Directory containing embeddings"),
    out: Path = typer.Option(..., help="Output markdown file"),
) -> None:
    """Sweep HDBSCAN parameters and write results to markdown."""
    # Load corpus
    dfs = []
    for parquet_file in sorted(input.glob("*.parquet")):
        dfs.append(pd.read_parquet(parquet_file))
    corpus = pd.concat(dfs, ignore_index=True)
    log.info("Loaded corpus: %d records", len(corpus))

    # Load embeddings
    emb = np.load(embeddings / "embeddings.npy").astype("float32")
    ids = np.load(embeddings / "ids.npy", allow_pickle=True).tolist()

    id_to_idx = {id_: i for i, id_ in enumerate(ids)}
    aligned_indices = [
        id_to_idx[row["id"]] for _, row in corpus.iterrows() if row["id"] in id_to_idx
    ]
    aligned_emb = emb[aligned_indices]

    # Reduce dimensions once — reuse for all sweeps
    log.info("Running UMAP reduction...")
    reducer = umap.UMAP(
        n_components=5,
        n_neighbors=15,
        min_dist=0.0,
        random_state=42,
    )
    reduced = reducer.fit_transform(aligned_emb)

    # Run sweep
    log.info("Running parameter sweep...")
    results = run_sweep(reduced)

    # Print table
    df_results = pd.DataFrame(results)
    log.info("\n%s", df_results.to_string(index=False))

    # Write markdown
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w") as f:
        f.write("# Cluster Tuning Results\n\n")
        f.write("## Parameter Sweep\n\n")
        f.write("| min_cluster_size | n_clusters | n_noise | noise_rate_pct | ")
        f.write("silhouette_score |\n")
        f.write("|---|---|---|---|---|\n")
        for r in results:
            f.write(
                f"| {r['min_cluster_size']} | {r['n_clusters']} | "
                f"{r['n_noise']} | {r['noise_rate_pct']}% | "
                f"{r['silhouette_score']} |\n"
            )
        f.write("\n## Chosen Setting\n\n")
        f.write("<!-- Fill this in after reviewing the results -->\n")

    log.info("Saved results to %s", out)


if __name__ == "__main__":
    app()
