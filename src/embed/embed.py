"""Embedding pipeline — batch embed all attack records, cache by ID."""

import logging
from pathlib import Path

import numpy as np
import pandas as pd
import typer
from sentence_transformers import SentenceTransformer

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)

app = typer.Typer()

MODEL_NAME = "all-MiniLM-L6-v2"
EMBEDDINGS_FILE = "embeddings.npy"
IDS_FILE = "ids.npy"


def load_corpus(input_dir: Path) -> pd.DataFrame:
    """Load all parquet files from input directory into one DataFrame."""
    dfs = []
    for parquet_file in sorted(input_dir.glob("*.parquet")):
        df = pd.read_parquet(parquet_file)
        dfs.append(df)
        log.info("Loaded %d records from %s", len(df), parquet_file.name)
    corpus = pd.concat(dfs, ignore_index=True)
    log.info("Total corpus: %d records", len(corpus))
    return corpus


def load_existing_embeddings(
    out_dir: Path,
) -> tuple[np.ndarray | None, set[str]]:
    """Load existing embeddings and their IDs if they exist."""
    embeddings_path = out_dir / EMBEDDINGS_FILE
    ids_path = out_dir / IDS_FILE

    if embeddings_path.exists() and ids_path.exists():
        embeddings = np.load(embeddings_path)
        ids = set(np.load(ids_path, allow_pickle=True).tolist())
        log.info("Found %d existing embeddings", len(ids))
        return embeddings, ids

    return None, set()


@app.command()
def main(
    input: Path = typer.Option(..., help="Directory containing parquet files"),
    out: Path = typer.Option(..., help="Directory to save embeddings"),
) -> None:
    """Batch embed all attack records, skipping already-embedded ones."""
    out.mkdir(parents=True, exist_ok=True)

    corpus = load_corpus(input)
    existing_embeddings, existing_ids = load_existing_embeddings(out)

    # Filter to only records that need embedding
    new_records = corpus[~corpus["id"].isin(existing_ids)]
    log.info(
        "Need to embed %d new records, skipping %d cached",
        len(new_records),
        len(existing_ids),
    )

    if len(new_records) == 0:
        log.info("Nothing to embed. Re-running is a no-op.")
        return

    # Embed new records
    model = SentenceTransformer(MODEL_NAME)
    prompts = new_records["prompt"].tolist()
    new_embeddings = model.encode(prompts, batch_size=64, show_progress_bar=True)

    # Combine with existing embeddings
    if existing_embeddings is not None:
        all_embeddings = np.vstack([existing_embeddings, new_embeddings])
        all_ids = list(existing_ids) + new_records["id"].tolist()
    else:
        all_embeddings = new_embeddings
        all_ids = new_records["id"].tolist()

    # Save to disk
    np.save(out / EMBEDDINGS_FILE, all_embeddings)
    np.save(out / IDS_FILE, np.array(all_ids))

    log.info(
        "Saved %d total embeddings to %s",
        len(all_ids),
        out,
    )


if __name__ == "__main__":
    app()
