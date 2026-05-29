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
                is_harmful=row.get("Behavior") == "harmful",
                created_at=datetime.now(UTC),
                raw=dict(row),
            )
            records.append(record)
        except Exception as e:
            dropped += 1
            log.warning("Dropped row: %s | Reason: %s", row.get("Goal", "?")[:50], e)

    log.info("Ingested %d records, dropped %d", len(records), dropped)
    return records


def ingest_advbench() -> list[AttackRecord]:
    """Load AdvBench and convert to AttackRecords."""
    dataset = load_dataset("AlignmentResearch/AdvBench", split="train")

    records = []
    dropped = 0

    for row in dataset:
        try:
            prompt = row["content"][0] if row["content"] else None
            if not prompt:
                raise ValueError("Empty prompt")

            record = AttackRecord(
                id=AttackRecord.make_id("advbench", prompt),
                source="advbench",
                prompt=prompt,
                target_behavior=row.get("gen_target"),
                attack_category=None,
                severity=None,
                is_harmful=None,
                created_at=datetime.now(UTC),
                raw=dict(row),
            )
            records.append(record)
        except Exception as e:
            dropped += 1
            log.warning("Dropped row: %s | Reason: %s", str(row)[:50], e)

    log.info("Ingested %d records, dropped %d", len(records), dropped)
    return records


def ingest_harmbench() -> list[AttackRecord]:
    """Load HarmBench and convert to AttackRecords."""
    test = load_dataset("swiss-ai/harmbench", "DirectRequest", split="test")
    val = load_dataset("swiss-ai/harmbench", "DirectRequest", split="val")
    dataset = [*test, *val]

    records = []
    dropped = 0

    for row in dataset:
        try:
            record = AttackRecord(
                id=AttackRecord.make_id("harmbench", row["Behavior"]),
                source="harmbench",
                prompt=row["Behavior"],
                target_behavior=None,
                attack_category=row.get("SemanticCategory"),
                severity=None,
                is_harmful=None,
                created_at=datetime.now(UTC),
                raw=dict(row),
            )
            records.append(record)
        except Exception as e:
            dropped += 1
            log.warning("Dropped row: %s | Reason: %s", str(row)[:50], e)

    log.info("Ingested %d records, dropped %d", len(records), dropped)
    return records


def ingest_donotanswer() -> list[AttackRecord]:
    """Load Do-Not-Answer and convert to AttackRecords."""
    dataset = load_dataset("LibrAI/do-not-answer", split="train")

    records = []
    dropped = 0

    for row in dataset:
        try:
            record = AttackRecord(
                id=AttackRecord.make_id("donotanswer", row["question"]),
                source="donotanswer",
                prompt=row["question"],
                target_behavior=row.get("specific_harms"),
                attack_category=row.get("risk_area"),
                severity=None,
                is_harmful=None,
                created_at=datetime.now(UTC),
                raw=dict(row),
            )
            records.append(record)
        except Exception as e:
            dropped += 1
            log.warning("Dropped row: %s | Reason: %s", str(row)[:50], e)

    log.info("Ingested %d records, dropped %d", len(records), dropped)
    return records


def ingest_inthewild() -> list[AttackRecord]:
    """Load In-the-Wild jailbreak prompts and convert to AttackRecords."""
    dataset = load_dataset(
        "TrustAIRLab/in-the-wild-jailbreak-prompts",
        "jailbreak_2023_12_25",
        split="train",
    )

    records = []
    dropped = 0

    for row in dataset:
        try:
            record = AttackRecord(
                id=AttackRecord.make_id("inthewild", row["prompt"]),
                source="inthewild",
                prompt=row["prompt"],
                target_behavior=None,
                attack_category=None,
                severity=None,
                is_harmful=None,
                created_at=datetime.now(UTC),
                raw=dict(row),
            )
            records.append(record)
        except Exception as e:
            dropped += 1
            log.warning("Dropped row: %s | Reason: %s", str(row)[:50], e)

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
    elif dataset == "advbench":
        records = ingest_advbench()
    elif dataset == "harmbench":
        records = ingest_harmbench()
    elif dataset == "donotanswer":
        records = ingest_donotanswer()
    elif dataset == "inthewild":
        records = ingest_inthewild()
    else:
        log.error("Unknown dataset: %s", dataset)
        raise typer.Exit(1)

    out.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame([r.model_dump() for r in records])
    df.to_parquet(out, index=False)
    log.info("Saved to %s", out)


if __name__ == "__main__":
    app()
