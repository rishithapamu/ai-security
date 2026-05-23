"""UMAP visualization of prompt embeddings."""

import logging
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import typer
import umap

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)

app = typer.Typer()


@app.command()
def main(
    input: Path = typer.Option(..., help="Directory containing parquet files"),
    embeddings: Path = typer.Option(..., help="Directory containing embeddings"),
    out: Path = typer.Option(..., help="Output HTML file path"),
) -> None:
    """Generate an interactive 2D UMAP plot of prompt embeddings."""
    # Load corpus
    dfs = []
    for parquet_file in sorted(input.glob("*.parquet")):
        dfs.append(pd.read_parquet(parquet_file))
    corpus = pd.concat(dfs, ignore_index=True)
    log.info("Loaded corpus: %d records", len(corpus))

    # Load embeddings and IDs
    emb = np.load(embeddings / "embeddings.npy").astype("float32")
    ids = np.load(embeddings / "ids.npy", allow_pickle=True).tolist()

    # Align corpus to embedding IDs
    id_to_row = {row["id"]: row for _, row in corpus.iterrows()}
    rows = [id_to_row[i] for i in ids if i in id_to_row]
    aligned_emb = np.array([emb[j] for j, i in enumerate(ids) if i in id_to_row])

    df = pd.DataFrame(rows).reset_index(drop=True)
    log.info("Aligned %d records with embeddings", len(df))

    # Run UMAP
    log.info("Running UMAP dimensionality reduction...")
    reducer = umap.UMAP(n_neighbors=15, min_dist=0.1, random_state=42)
    coords = reducer.fit_transform(aligned_emb)

    df["x"] = coords[:, 0]
    df["y"] = coords[:, 1]
    df["prompt_short"] = df["prompt"].str[:200]

    # Plot
    log.info("Building interactive plot...")
    fig = px.scatter(
        df,
        x="x",
        y="y",
        color="source",
        hover_data={
            "prompt_short": True,
            "attack_category": True,
            "x": False,
            "y": False,
        },
        title="Prompt Embedding Space — hover to see prompt text",
        labels={"source": "Dataset"},
        width=1200,
        height=800,
    )
    fig.update_traces(marker=dict(size=4, opacity=0.7))

    out.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(str(out))
    log.info("Saved interactive plot to %s", out)


if __name__ == "__main__":
    app()
