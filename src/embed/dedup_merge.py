"""Deduplication — collapse near-duplicate prompts into representative records
using union-find over pairs found by FAISS similarity search."""

import logging
from pathlib import Path

import pandas as pd
import typer

from src.embed.dedup import SIMILARITY_THRESHOLD, find_duplicate_pairs
from src.embed.search import SimilarityIndex

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)

app = typer.Typer()


class UnionFind:
    """Disjoint-set structure: turns pairwise duplicate edges into groups."""

    def __init__(self, items: list[str]) -> None:
        # each item starts as its own parent (its own group)
        self.parent = {item: item for item in items}

    def find(self, item: str) -> str:
        # path compression: flatten the tree as we walk it, so future
        # lookups for anything in this chain are O(1)
        if self.parent[item] != item:
            self.parent[item] = self.find(self.parent[item])
        return self.parent[item]

    def union(self, a: str, b: str) -> None:
        root_a, root_b = self.find(a), self.find(b)
        if root_a != root_b:
            # arbitrary but deterministic: smaller id string becomes the root
            if root_a < root_b:
                self.parent[root_b] = root_a
            else:
                self.parent[root_a] = root_b

    def groups(self) -> dict[str, list[str]]:
        result: dict[str, list[str]] = {}
        for item in self.parent:
            root = self.find(item)
            result.setdefault(root, []).append(item)
        return result


def build_groups(corpus: pd.DataFrame, pairs: list) -> dict[str, list[str]]:
    """Turn pairwise duplicates into connected-component groups."""
    uf = UnionFind(corpus["id"].tolist())
    for pair in pairs:
        uf.union(pair.id_a, pair.id_b)
    return uf.groups()


def pick_representative(group_ids: list[str], id_to_row: dict) -> dict:
    """Choose one record per duplicate group and merge useful metadata."""
    rows = [id_to_row[i] for i in group_ids]

    # deterministic ordering so reruns always pick the same representative
    rows_sorted = sorted(rows, key=lambda r: r["source"])
    rep = dict(rows_sorted[0])

    # if the chosen representative has no attack_category but another
    # member of the group does, borrow it rather than lose the label
    if rep.get("attack_category") is None:
        for row in rows_sorted:
            if row.get("attack_category") is not None:
                rep["attack_category"] = row["attack_category"]
                break

    rep["duplicate_count"] = len(rows)
    rep["duplicate_sources"] = sorted({r["source"] for r in rows})
    return rep


@app.command()
def main(
    input: Path = typer.Option(..., help="Directory containing parquet files"),
    embeddings: Path = typer.Option(..., help="Directory containing embeddings"),
    out: Path = typer.Option(..., help="Output path for deduplicated parquet"),
    threshold: float = typer.Option(SIMILARITY_THRESHOLD, help="Cosine sim cutoff"),
) -> None:
    """Deduplicate the corpus by collapsing near-duplicate prompt groups."""
    dfs = [pd.read_parquet(p) for p in sorted(input.glob("*.parquet"))]
    corpus = pd.concat(dfs, ignore_index=True)
    log.info("Loaded corpus: %d records", len(corpus))

    index = SimilarityIndex(embeddings)
    pairs = find_duplicate_pairs(index, corpus, threshold=threshold)
    log.info("Found %d near-duplicate pairs at threshold=%.2f", len(pairs), threshold)

    groups = build_groups(corpus, pairs)
    id_to_row = {row["id"]: row for _, row in corpus.iterrows()}

    deduped_records = [
        pick_representative(group_ids, id_to_row) for group_ids in groups.values()
    ]

    deduped = pd.DataFrame(deduped_records)
    log.info(
        "Deduplicated %d records -> %d records (%d removed)",
        len(corpus),
        len(deduped),
        len(corpus) - len(deduped),
    )

    multi_source = (deduped["duplicate_count"] > 1).sum()
    log.info("%d representatives absorbed 2+ duplicates", multi_source)

    out.parent.mkdir(parents=True, exist_ok=True)
    deduped.to_parquet(out, index=False)
    log.info("Saved deduplicated corpus to %s", out)


if __name__ == "__main__":
    app()
