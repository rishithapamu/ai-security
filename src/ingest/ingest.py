"""Ingestion pipeline — converts raw datasets into normalized AttackRecords."""

import logging
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import typer
from datasets import load_dataset

from src.ingest.schema import AttackRecord

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)

app = typer.Typer()


def ingest_jailbreakbench() -> list[AttackRecord]:
    """Load JailbreakBench and convert to AttackRecords."""
    harmful = load_dataset("JailbreakBench/JBB-Behaviors", "behaviors", split="harmful")
    benign = load_dataset("JailbreakBench/JBB-Behaviors", "behaviors", split="benign")
    dataset = [*harmful, *benign]

    records = []
    dropped = 0

    for row in dataset:
        try:
            record = AttackRecord(
                id=AttackRecord.make_id("jailbreakbench", row["Goal"]),
                source="jailbreakbench",
                prompt=row["Goal"],
                target_behavior=row.get("Target"),
                attack_category=row.get("Category"),
                severity=None,
                created_at=datetime.now(UTC),
                raw=dict(row),
            )
            records.append(record)
        except Exception as e:
            dropped += 1
            log.warning("Dropped row: %s | Reason: %s", row.get("Goal", "?")[:50], e)

    log.info("Ingested %d records, dropped %d", len(records), dropped)
    return records


@app.command()
def main(
    dataset: str = typer.Argument(..., help="Dataset to ingest"),
    out: Path = typer.Option(..., help="Output parquet path"),
) -> None:
    """Ingest a dataset and save as parquet."""
    if dataset == "jailbreakbench":
        records = ingest_jailbreakbench()
    else:
        log.error("Unknown dataset: %s", dataset)
        raise typer.Exit(1)

    out.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame([r.model_dump() for r in records])
    df.to_parquet(out, index=False)
    log.info("Saved to %s", out)


if __name__ == "__main__":
    app()
