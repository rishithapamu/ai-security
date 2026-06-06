import sys
from pathlib import Path

sys.path.append("/Users/rishithapamu/Desktop/internship_project/ai-sec-workbench")

import pandas as pd
import typer

from src.ingest.ingest import (
    ingest_advbench,
    ingest_donotanswer,
    ingest_harmbench,
    ingest_inthewild,
    ingest_jailbreakbench,
)

app = typer.Typer()

DATASETS = {
    "jailbreakbench": (ingest_jailbreakbench, 200),
    "advbench": (ingest_advbench, 520),
    "harmbench": (ingest_harmbench, 400),
    "donotanswer": (ingest_donotanswer, 939),
    "inthewild": (ingest_inthewild, 1405),
}


@app.command("ingest")
def ingest(
    dataset: str = typer.Argument("all", help="Dataset to ingest or 'all'"),
    out: Path = typer.Option(
        "data/processed/combined.parquet",
        help="Output parquet path",
    ),
):
    """Ingest one or all datasets and save to parquet."""
    if dataset == "all":
        to_ingest = DATASETS
    elif dataset in DATASETS:
        to_ingest = {dataset: DATASETS[dataset]}
    else:
        print(f"Unknown dataset: {dataset}")
        print(f"Available: {list(DATASETS.keys())} or 'all'")
        raise typer.Exit(1)

    all_records = []
    summary = []

    for name, (ingest_fn, expected) in to_ingest.items():
        print(f"Ingesting {name}...")
        records = ingest_fn()
        ingested = len(records)
        dropped = expected - ingested
        all_records.extend(records)
        summary.append(
            {
                "dataset": name,
                "expected": expected,
                "ingested": ingested,
                "dropped": dropped,
            }
        )
    print("\n=== INGESTION SUMMARY ===")
    df_summary = pd.DataFrame(summary)
    print(df_summary.to_string(index=False))
    print(f"\nTotal ingested: {len(all_records)}")

    df = pd.DataFrame([r.model_dump() for r in all_records])
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out, index=False)
    print(f"Saved to {out}")


@app.command("embed")
def embed(
    input: Path = typer.Option(
        "data/processed/",
        help="Directory containing parquet files",
    ),
    out: Path = typer.Option(
        "data/embeddings/",
        help="Directory to save embeddings",
    ),
):
    """Batch embed all attack records."""
    from src.embed.embed import main as embed_main

    embed_main(input=input, out=out)


@app.command("search")
def search(
    prompt: str = typer.Argument(..., help="Prompt to search for"),
    k: int = typer.Option(10, help="Number of similar prompts to return"),
    embeddings_dir: Path = typer.Option(
        "data/embeddings/",
        help="Directory containing embeddings",
    ),
    corpus_dir: Path = typer.Option(
        "data/processed/",
        help="Directory containing parquet files",
    ),
):
    """Find the k most similar prompts to a given query."""
    import pandas as pd
    from sentence_transformers import SentenceTransformer

    from src.embed.search import SimilarityIndex

    # Load corpus
    dfs = []
    for parquet_file in sorted(corpus_dir.glob("*.parquet")):
        dfs.append(pd.read_parquet(parquet_file))
    corpus = pd.concat(dfs, ignore_index=True)
    id_to_prompt = dict(zip(corpus["id"], corpus["prompt"]))
    id_to_source = dict(zip(corpus["id"], corpus["source"]))
    id_to_category = dict(zip(corpus["id"], corpus["attack_category"]))
    id_to_harmful = dict(zip(corpus["id"], corpus["is_harmful"]))

    # Build index
    index = SimilarityIndex(embeddings_dir)

    # Embed the query
    model = SentenceTransformer("all-MiniLM-L6-v2")
    query_embedding = model.encode([prompt])[0]

    # Search
    results = index.find_similar(query_embedding, k=k + 1)

    print(f"\nQuery: {prompt}")
    print(f"\nTop {k} similar prompts:\n")
    print(
        f"{'Rank':<6} "
        f"{'Score':<8} "
        f"{'Harmful':<10} "
        f"{'Source':<20} "
        f"{'Category':<30} "
        f"Prompt"
    )
    print("-" * 120)

    shown = 0

    for r in results:
        matched_prompt = id_to_prompt.get(r.id, "?")
        if matched_prompt == prompt:
            continue
        source = id_to_source.get(r.id, "?")
        category = str(id_to_category.get(r.id, "unknown"))[:28]
        harmful = "Harmful" if id_to_harmful.get(r.id, False) else "Benign"
        print(
            f"{r.rank:<6} "
            f"{r.score:<8.3f} "
            f"{harmful:<10} "
            f"{source:<20} "
            f"{category:<30} "
            f"{matched_prompt[:60]}"
        )

        shown += 1
        if shown >= k:
            break


if __name__ == "__main__":
    app()
