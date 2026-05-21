"""Tests for similarity search."""

from pathlib import Path

import numpy as np
import pytest

from src.embed.search import SimilarityIndex


def test_query_with_itself_returns_score_one(tmp_path: Path) -> None:
    """Querying with a vector that's in the index must return itself as top-1."""
    # Create fake embeddings
    embeddings = np.random.rand(10, 384).astype("float32")
    ids = [f"id_{i}" for i in range(10)]

    np.save(tmp_path / "embeddings.npy", embeddings)
    np.save(tmp_path / "ids.npy", np.array(ids))

    index = SimilarityIndex(tmp_path)

    # Query with the first vector
    results = index.find_similar(embeddings[0], k=5)

    assert results[0].id == "id_0"
    assert results[0].score == pytest.approx(1.0, abs=0.01)
    assert results[0].rank == 1
