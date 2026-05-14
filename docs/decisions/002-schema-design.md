# 002 — Attack Record Schema Design

## Status
Accepted

## Context
The workbench ingests data from multiple datasets — JailbreakBench, AdvBench, HarmBench, Do-Not-Answer, and In-the-Wild — each with a different structure and label schema. Without a normalized representation, downstream code would have to handle each dataset separately, making analysis inconsistent and error-prone. A single shared schema means any dataset can be ingested once and used uniformly everywhere.

## Decision
The attack record is the class that defines the normalized label schema of the dataset. It contains the id, source, prompt, target behaviour, severity, attack category and the date and time it was created, as well as raw. the raw is required as a safety net so we do not lose the original data in case our normalized schema does not have a field for eveything.

## Field Trade-offs

**severity is optional and user-assigned** — none of the datasets we looked at provide severity ratings, so this field cannot be populated during ingestion. It will need to be assigned manually or by a classifier later.
**raw is required** — we don't want to lose any fields that exist in the original dataset but not in our normalized schema, as they may contain important information about the prompt that could be required later.
**target_behavior, attack_category and severity are optional** — not all datasets provide these labels. AdvBench for example has no label schema at all, so these fields cannot be populated during ingestion and must default to None.

## Consequences
Every dataset ingester must map its own structure into AttackRecord — no dataset can be ingested as-is. If the schema needs to change in the future, for example adding a new field, it can be done without data loss because the original data is always preserved in the raw field and records can be re-ingested from scratch.
