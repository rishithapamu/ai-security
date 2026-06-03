"""Analyze effect of HDBSCAN cluster_selection_epsilon."""

import logging
from pathlib import Path

import hdbscan
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.express as px
import typer
import umap
from sklearn.metrics import silhouette_score

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
) -> tuple[np.ndarray, np.ndarray]:
    """Create clustering and visualization embeddings."""

    log.info("Generating 5D UMAP embedding...")

    reducer_5d = umap.UMAP(
        n_components=5,
        n_neighbors=15,
        min_dist=0.0,
        random_state=42,
    )

    reduced_5d = reducer_5d.fit_transform(embeddings)

    log.info("Generating 2D UMAP embedding...")

    reducer_2d = umap.UMAP(
        n_components=2,
        n_neighbors=15,
        min_dist=0.0,
        random_state=42,
    )

    reduced_2d = reducer_2d.fit_transform(embeddings)

    return reduced_5d, reduced_2d


def save_cluster_scatter(
    embedding_2d: np.ndarray,
    labels: np.ndarray,
    epsilon: float,
    output_dir: Path,
) -> None:
    """Save UMAP cluster visualization."""

    plt.figure(figsize=(14, 10))

    unique_labels = np.unique(labels)
    num_clusters = len(unique_labels)
    colors = plt.get_cmap(
        "gist_ncar",
        num_clusters,
    )

    #
    # Plot each cluster separately
    #
    for cluster_id in unique_labels:
        mask = labels == cluster_id

        if cluster_id == -1:
            plt.scatter(
                embedding_2d[mask, 0],
                embedding_2d[mask, 1],
                c="lightgray",
                s=8,
                alpha=0.5,
                label="Noise",
            )

        else:
            plt.scatter(
                embedding_2d[mask, 0],
                embedding_2d[mask, 1],
                color=colors(cluster_id),
                s=8,
                alpha=0.8,
            )

            #
            # Put cluster number at center
            #
            center_x = embedding_2d[mask, 0].mean()
            center_y = embedding_2d[mask, 1].mean()

            cluster_size = mask.sum()

            plt.text(
                center_x,
                center_y,
                f"{cluster_id}\n({cluster_size})",
                fontsize=8,
                fontweight="bold",
                ha="center",
            )

    plt.title(f"HDBSCAN Clusters (epsilon={epsilon})")

    plt.xlabel("UMAP-1")
    plt.ylabel("UMAP-2")

    plt.tight_layout()

    plt.savefig(
        output_dir / f"clusters_eps_{epsilon:.2f}.png",
        dpi=300,
        bbox_inches="tight",
    )

    plt.close()

    plt.close()


def save_interactive_cluster_plot(
    embedding_2d: np.ndarray,
    labels: np.ndarray,
    corpus: pd.DataFrame,
    epsilon: float,
    output_dir: Path,
) -> None:
    """Save interactive HTML cluster plot."""

    df = pd.DataFrame(
        {
            "x": embedding_2d[:, 0],
            "y": embedding_2d[:, 1],
            "cluster": labels.astype(str),
            "prompt": corpus["prompt"],
            "source": corpus["source"],
            "attack_category": corpus["attack_category"],
            "severity": corpus["severity"],
        }
    )

    fig = px.scatter(
        df,
        x="x",
        y="y",
        color="cluster",
        hover_data={
            "cluster": True,
            "attack_category": True,
            "source": True,
            "severity": True,
            "prompt": True,
            "x": False,
            "y": False,
        },
        title=f"HDBSCAN Clusters (epsilon={epsilon})",
    )

    fig.write_html(output_dir / f"clusters_eps_{epsilon:.2f}.html")


def save_cluster_size_histogram(
    labels: np.ndarray,
    epsilon: float,
    output_dir: Path,
) -> None:
    """Save cluster size distribution."""

    cluster_sizes = pd.Series(labels).value_counts().drop(-1, errors="ignore")

    if len(cluster_sizes) == 0:
        return

    plt.figure(figsize=(8, 5))

    plt.hist(
        cluster_sizes,
        bins=min(20, len(cluster_sizes)),
    )

    plt.title(f"Cluster Size Distribution (epsilon={epsilon})")

    plt.xlabel("Cluster Size")
    plt.ylabel("Count")

    plt.tight_layout()

    plt.savefig(
        output_dir / f"cluster_sizes_eps_{epsilon:.2f}.png",
        dpi=300,
    )

    plt.close()


@app.command()
def main(
    input: Path = typer.Option(
        ...,
        help="Directory containing parquet files",
    ),
    embeddings: Path = typer.Option(
        ...,
        help="Directory containing embeddings",
    ),
    out: Path = typer.Option(
        Path(
            "/Users/rishithapamu/Desktop/internship_project/"
            "ai-sec-workbench/data/plots"
        ),
        help="Output directory",
    ),
) -> None:
    """Analyze HDBSCAN epsilon parameter."""

    out.mkdir(
        parents=True,
        exist_ok=True,
    )

    corpus = load_corpus(input)

    emb = np.load(embeddings / "embeddings.npy").astype("float32")

    ids = np.load(
        embeddings / "ids.npy",
        allow_pickle=True,
    ).tolist()

    id_to_idx = {id_: i for i, id_ in enumerate(ids)}

    aligned_indices = [
        id_to_idx[row["id"]] for _, row in corpus.iterrows() if row["id"] in id_to_idx
    ]

    aligned_emb = emb[aligned_indices]

    aligned_corpus = corpus[corpus["id"].isin(set(ids))].reset_index(drop=True)
    print(aligned_corpus.columns)

    log.info(
        "Aligned %d records with embeddings",
        len(aligned_corpus),
    )

    reduced_5d, reduced_2d = build_umap_embeddings(aligned_emb)

    results = []

    for epsilon in EPSILONS:
        log.info(
            "\nRunning epsilon=%s",
            epsilon,
        )

        clusterer = hdbscan.HDBSCAN(
            min_cluster_size=15,
            min_samples=5,
            cluster_selection_epsilon=epsilon,
            metric="euclidean",
        )

        labels = clusterer.fit_predict(reduced_5d)

        n_clusters = len(set(labels)) - (1 if -1 in labels else 0)

        n_noise = (labels == -1).sum()

        noise_rate = (n_noise / len(labels)) * 100

        silhouette = np.nan

        if n_clusters >= 2:
            mask = labels != -1

            if mask.sum() > n_clusters:
                silhouette = silhouette_score(
                    reduced_5d[mask],
                    labels[mask],
                    sample_size=min(
                        1000,
                        mask.sum(),
                    ),
                )

        results.append(
            {
                "epsilon": epsilon,
                "n_clusters": n_clusters,
                "n_noise": n_noise,
                "noise_rate_pct": round(
                    noise_rate,
                    2,
                ),
                "silhouette_score": (
                    round(
                        float(silhouette),
                        4,
                    )
                    if not np.isnan(silhouette)
                    else np.nan
                ),
            }
        )

        epsilon_corpus = aligned_corpus.copy()

        epsilon_corpus["cluster"] = labels

        epsilon_corpus.to_parquet(
            out / f"clusters_eps_{epsilon:.2f}.parquet",
            index=False,
        )

        save_cluster_scatter(
            reduced_2d,
            labels,
            epsilon,
            out,
        )
        save_interactive_cluster_plot(
            reduced_2d,
            labels,
            aligned_corpus,
            epsilon,
            out,
        )
        save_cluster_size_histogram(
            labels,
            epsilon,
            out,
        )

        log.info(
            "Clusters=%d | Noise=%.2f%%",
            n_clusters,
            noise_rate,
        )

    results_df = pd.DataFrame(results)

    results_df.to_csv(
        out / "summary.csv",
        index=False,
    )

    #
    # Clusters vs epsilon
    #
    plt.figure(figsize=(8, 5))

    plt.plot(
        results_df["epsilon"],
        results_df["n_clusters"],
        marker="o",
        label="Number of Clusters",
    )
    plt.legend()

    plt.xlabel("cluster_selection_epsilon")
    plt.ylabel("Number of Clusters")
    plt.title("Clusters vs Epsilon")

    plt.grid(True)

    plt.tight_layout()

    plt.savefig(
        out / "clusters_vs_epsilon.png",
        dpi=300,
    )

    plt.close()

    #
    # Noise vs epsilon
    #
    plt.figure(figsize=(8, 5))

    plt.plot(
        results_df["epsilon"],
        results_df["noise_rate_pct"],
        marker="o",
        label="Noise Rate (%)",
    )
    plt.legend()

    plt.xlabel("cluster_selection_epsilon")
    plt.ylabel("Noise Rate (%)")
    plt.title("Noise Rate vs Epsilon")

    plt.grid(True)

    plt.tight_layout()

    plt.savefig(
        out / "noise_vs_epsilon.png",
        dpi=300,
    )

    plt.close()

    #
    # Silhouette vs epsilon
    #
    plt.figure(figsize=(8, 5))

    plt.plot(
        results_df["epsilon"],
        results_df["silhouette_score"],
        marker="o",
        label="Silhouette Score",
    )
    plt.legend()
    plt.xlabel("cluster_selection_epsilon")
    plt.ylabel("Silhouette Score")

    plt.title("Silhouette Score vs Epsilon")

    plt.grid(True)

    plt.tight_layout()

    plt.savefig(
        out / "silhouette_vs_epsilon.png",
        dpi=300,
    )

    plt.close()

    #
    # Combined comparison plot
    #

    plt.figure(figsize=(10, 6))

    plt.plot(
        results_df["epsilon"],
        results_df["n_clusters"],
        marker="o",
        label="Clusters",
    )
    plt.plot(
        results_df["epsilon"],
        results_df["noise_rate_pct"],
        marker="s",
        label="Noise Rate (%)",
    )
    plt.plot(
        results_df["epsilon"],
        results_df["silhouette_score"] * 100,
        marker="^",
        label="Silhouette x100",
    )

    plt.xlabel("cluster_selection_epsilon")

    plt.title("Effect of Epsilon on HDBSCAN Clustering")

    plt.legend()

    plt.grid(True)

    plt.tight_layout()

    plt.savefig(
        out / "epsilon_comparison.png",
        dpi=300,
    )

    plt.close()

    log.info(
        "Saved analysis outputs to %s",
        out,
    )


if __name__ == "__main__":
    app()
