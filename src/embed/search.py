"""Similarity search using FAISS."""

import logging
from dataclasses import dataclass
from pathlib import Path

import faiss
import numpy as np

log = logging.getLogger(__name__)

EMBEDDINGS_FILE = "embeddings.npy"
IDS_FILE = "ids.npy"


@dataclass
class SearchResult:
    id: str
    score: float
    rank: int


class SimilarityIndex:
    """FAISS-backed similarity search over attack record embeddings."""

    def __init__(self, embeddings_dir: Path) -> None:
        embeddings_path = embeddings_dir / EMBEDDINGS_FILE
        ids_path = embeddings_dir / IDS_FILE

        if not embeddings_path.exists() or not ids_path.exists():
            raise FileNotFoundError(
                f"No embeddings found in {embeddings_dir}. "
                "Run the embed pipeline first."
            )

        embeddings = np.load(embeddings_path).astype("float32")
        self.ids = np.load(ids_path, allow_pickle=True).tolist()

        # Normalize for cosine similarity
        faiss.normalize_L2(embeddings)

        # Build index
        self.index = faiss.IndexFlatIP(embeddings.shape[1])
        self.index.add(embeddings)

        log.info("Built FAISS index with %d vectors", self.index.ntotal)

    def find_similar(
        self, query_embedding: np.ndarray, k: int = 10
    ) -> list[SearchResult]:
        """Find k most similar records to the query embedding."""
        query = query_embedding.astype("float32").reshape(1, -1)
        faiss.normalize_L2(query)

        scores, indices = self.index.search(query, k)

        results = []
        for rank, (idx, score) in enumerate(zip(indices[0], scores[0]), 1):
            if idx == -1:
                continue
            results.append(
                SearchResult(
                    id=self.ids[idx],
                    score=float(score),
                    rank=rank,
                )
            )
        return results
