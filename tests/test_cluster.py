"""
tests/test_cluster.py

Run with:
    PYTHONPATH=. uv run pytest tests/test_cluster.py -v
"""

import numpy as np
import pandas as pd

from src.cluster.cluster import align_embeddings


def test_align_embeddings_correct_order():
    """
    The embedding at row i must correspond to the corpus row at row i.

    We construct embeddings in REVERSED order on purpose. If the alignment
    just uses positional indexing (wrong approach), every row gets the wrong
    embedding. The test only passes if alignment matches by ID.

    Concretely: embedding [2.0, 2.0] belongs to id "id_2". After alignment,
    the corpus row with id "id_2" must sit next to the [2.0, 2.0] embedding.
    We verify this by checking that the first value of each embedding equals
    the numeric suffix of the corpus row's id.
    """
    corpus = pd.DataFrame(
        {
            "id": ["id_0", "id_1", "id_2"],
            "prompt": ["p0", "p1", "p2"],
        }
    )

    # Embeddings in reversed order — id_2 first, id_0 last
    # Each embedding encodes its id's index as both values: [2, 2] for id_2
    ids = ["id_2", "id_1", "id_0"]
    emb = np.array(
        [
            [2.0, 2.0],  # embedding for id_2
            [1.0, 1.0],  # embedding for id_1
            [0.0, 0.0],  # embedding for id_0
        ],
        dtype="float32",
    )

    aligned_corpus, aligned_emb = align_embeddings(corpus, emb, ids)

    # After alignment, row i of aligned_corpus must pair with aligned_emb[i]
    for i, row in aligned_corpus.iterrows():
        id_suffix = int(row["id"].split("_")[1])  # "id_2" → 2
        emb_value = aligned_emb[i][0]  # first dim of embedding i
        assert id_suffix == emb_value, (
            f"Row {i}: corpus id {row['id']} got embedding {aligned_emb[i]} "
            f"— expected [{id_suffix}, {id_suffix}]"
        )


def test_align_embeddings_drops_unmatched_rows():
    """
    Corpus rows with no matching embedding should be dropped, not crash.

    This models what happens when a prompt failed to embed (network error,
    model timeout, etc.) and is missing from embeddings.npy. The correct
    behaviour is to continue with what we have, not raise a KeyError.

    We also verify the output length is exactly the number of matched rows,
    and the unmatched id does not appear in the result.
    """
    corpus = pd.DataFrame(
        {
            "id": ["id_0", "id_1", "id_MISSING"],
            "prompt": ["p0", "p1", "this one has no embedding"],
        }
    )

    # id_MISSING is not in ids — its corpus row should be dropped
    ids = ["id_0", "id_1"]
    emb = np.array([[0.0], [1.0]], dtype="float32")

    aligned_corpus, aligned_emb = align_embeddings(corpus, emb, ids)

    assert len(aligned_corpus) == 2, "Should have 2 rows after dropping unmatched"
    assert len(aligned_emb) == 2, "Should have 2 embeddings after dropping unmatched"
    assert (
        "id_MISSING" not in aligned_corpus["id"].values
    ), "Unmatched id should not appear in aligned result"
