"""Near-duplicate detection and corpus deduplication using FAISS similarity search."""

import logging
from pathlib import Path

import numpy as np
import pandas as pd
import typer

from src.embed.search import SimilarityIndex

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)

app = typer.Typer()

SIMILARITY_THRESHOLD = 0.95


def load_corpus(input_dir: Path) -> pd.DataFrame:
    """Load the original combined corpus only."""
    corpus_path = input_dir / "combined.parquet"

    if not corpus_path.exists():
        raise FileNotFoundError(f"Expected {corpus_path}")

    corpus = pd.read_parquet(corpus_path)

    log.info(
        "Loaded corpus: %d rows | %d unique ids",
        len(corpus),
        corpus["id"].nunique(),
    )

    return corpus


def find_duplicate_pairs(
    index: SimilarityIndex,
    corpus: pd.DataFrame,
    embeddings: np.ndarray,
    threshold: float = SIMILARITY_THRESHOLD,
) -> set[str]:
    """
    Find duplicate IDs using similarity search.

    Returns IDs that should be removed.
    Keeps the first occurrence and removes later duplicates.
    """

    id_to_row = {row["id"]: idx for idx, row in corpus.iterrows()}

    duplicate_ids = set()
    seen_pairs = set()

    for i, record_id in enumerate(index.ids):
        if record_id not in id_to_row:
            continue

        results = index.find_similar(
            embeddings[i],
            k=20,
        )

        for result in results:
            if result.id == record_id:
                continue

            if result.score < threshold:
                continue

            pair = tuple(sorted([record_id, result.id]))

            if pair in seen_pairs:
                continue

            seen_pairs.add(pair)

            # Remove the later occurrence
            idx_a = id_to_row.get(record_id)
            idx_b = id_to_row.get(result.id)

            if idx_a is None or idx_b is None:
                continue

            if idx_a < idx_b:
                duplicate_ids.add(result.id)
            else:
                duplicate_ids.add(record_id)

    return duplicate_ids


@app.command()
def main(
    input: Path = typer.Option(
        ...,
        help="Directory containing combined.parquet",
    ),
    embeddings: Path = typer.Option(
        ...,
        help="Directory containing embeddings",
    ),
    out: Path = typer.Option(
        ...,
        help="Output deduplicated parquet file",
    ),
) -> None:
    """Remove near-duplicate prompts."""

    corpus = load_corpus(input)

    embedding_file = embeddings / "embeddings.npy"

    emb = np.load(embedding_file).astype("float32")

    log.info(
        "Loaded embeddings: %d vectors",
        len(emb),
    )

    index = SimilarityIndex(embeddings)

    log.info(
        "Finding duplicates above %.2f similarity...",
        SIMILARITY_THRESHOLD,
    )

    duplicate_ids = find_duplicate_pairs(
        index,
        corpus,
        emb,
    )

    log.info(
        "Duplicate IDs found: %d",
        len(duplicate_ids),
    )

    # Remove near duplicates
    deduped = corpus[~corpus["id"].isin(duplicate_ids)].copy()

    # Also remove exact duplicate IDs
    deduped = deduped.drop_duplicates(subset="id").reset_index(drop=True)

    log.info(
        "After deduplication: %d rows | %d unique ids",
        len(deduped),
        deduped["id"].nunique(),
    )

    out.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    deduped.to_parquet(
        out,
        index=False,
    )

    log.info(
        "Saved → %s",
        out,
    )


if __name__ == "__main__":
    app()
