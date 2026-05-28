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


@app.command()
def ingest(
    dataset: str = typer.Argument("all", help="Dataset to ingest or 'all'"),
    out: Path = typer.Option(
        "/Users/rishithapamu/Desktop/internship_project/ai-sec-workbench/data/processed/combined.parquet",
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


if __name__ == "__main__":
    app()
