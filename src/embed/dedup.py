"""Near-duplicate detection using FAISS similarity search."""

import logging
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import typer

from src.embed.search import SimilarityIndex

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)

app = typer.Typer()
SIMILARITY_THRESHOLD = 0.95


@dataclass
class DuplicatePair:
    id_a: str
    id_b: str
    score: float
    source_a: str
    source_b: str
    prompt_a: str
    prompt_b: str


def find_duplicate_pairs(
    index: SimilarityIndex,
    corpus: pd.DataFrame,
    threshold: float = SIMILARITY_THRESHOLD,
) -> list[DuplicatePair]:
    """Find all pairs of prompts with similarity above threshold."""
    embeddings = np.load("data/embeddings/embeddings.npy").astype("float32")
    id_to_row = {row["id"]: row for _, row in corpus.iterrows()}

    pairs = []
    seen = set()

    for i, record_id in enumerate(index.ids):
        if record_id not in id_to_row:
            continue

        results = index.find_similar(embeddings[i], k=20)

        for result in results:
            if result.id == record_id:
                continue
            if result.score < threshold:
                continue

            pair_key = tuple(sorted([record_id, result.id]))
            if pair_key in seen:
                continue
            seen.add(pair_key)

            row_a = id_to_row[record_id]
            row_b = id_to_row.get(result.id)
            if row_b is None:
                continue

            pairs.append(
                DuplicatePair(
                    id_a=record_id,
                    id_b=result.id,
                    score=result.score,
                    source_a=row_a["source"],
                    source_b=row_b["source"],
                    prompt_a=row_a["prompt"],
                    prompt_b=row_b["prompt"],
                )
            )

    return pairs


@app.command()
def main(
    input: Path = typer.Option(..., help="Directory containing parquet files"),
    embeddings: Path = typer.Option(..., help="Directory containing embeddings"),
) -> None:
    """Find near-duplicate prompts across all datasets."""
    # Load corpus
    dfs = []
    for parquet_file in sorted(input.glob("*.parquet")):
        dfs.append(pd.read_parquet(parquet_file))
    corpus = pd.concat(dfs, ignore_index=True)
    log.info("Loaded corpus: %d records", len(corpus))

    # Build index
    index = SimilarityIndex(embeddings)

    # Find duplicates
    log.info("Finding pairs with similarity > %.2f...", SIMILARITY_THRESHOLD)
    pairs = find_duplicate_pairs(index, corpus)

    log.info("Found %d near-duplicate pairs", len(pairs))

    # Cross-source pairs
    cross_source = [p for p in pairs if p.source_a != p.source_b]
    log.info("Cross-source pairs: %d", len(cross_source))

    # Print some examples
    log.info("\n--- SAME SOURCE EXAMPLES ---")
    for p in [p for p in pairs if p.source_a == p.source_b][:3]:
        log.info("[%s] %.3f", p.source_a, p.score)
        log.info("  A: %s", p.prompt_a[:80])
        log.info("  B: %s", p.prompt_b[:80])

    log.info("\n--- CROSS SOURCE EXAMPLES ---")
    for p in cross_source[:5]:
        log.info("[%s vs %s] %.3f", p.source_a, p.source_b, p.score)
        log.info("  A: %s", p.prompt_a[:80])
        log.info("  B: %s", p.prompt_b[:80])


if __name__ == "__main__":
    app()
