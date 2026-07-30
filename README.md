## ai-sec-workbench

A jailbreak, in this context, refers specifically to a prompt or sequence of prompts engineered to cause a model to bypass its own safety training and produce a response it would otherwise refuse.

I designed a two-axis taxonomy — attack technique (primitive) and attacker objective (behavior) — and built the pipeline to ingest, embed, cluster, and label adversarial prompts (the kind used to try to "jailbreak" AI chatbots) against it, across five public red-teaming datasets, to find where public jailbreak research does and doesn't have coverage.

![Python 3.14](https://img.shields.io/badge/python-3.14-blue)
![uv](https://img.shields.io/badge/deps-uv-orange)
![License: MIT](https://img.shields.io/badge/license-MIT-green)

## What This Found

- **91% of the primitive × behavior coverage grid is empty.**
Out of 247 possible (attack technique) × (attacker objective) combinations, only 22 arevbacked by an actual cluster of real prompts. See [Coverage Analysis](#6-see-the-coverage-gaps) below.
- **The corpus is dominated by "meta-attacks."**
`content_policy_circumvention`(prompts whose only goal is unlocking the model, not doing anything specific once unlocked) accounts for the single largest behavior group. The datasets studied know a lot about jailbreak framing and comparatively little about what an attacker does *after* the jailbreak succeeds.
- **Emotional-manipulation attacks are almost invisible in academic datasets.**
  Only 2 of 76 clusters use emotional/relational framing as the attack technique — a real-world pattern (building parasocial trust with an AI to lower its guard) that harm-focused academic corpora were never designed to capture. Full writeup: [`docs/sparse-areas.md`](docs/sparse-areas.md).

These numbers reflect the current 76-cluster registry (`src/registry/candidates/cluster_assignments.yaml`). Some of the narrative docs below (`docs/sparse-areas.md`, `docs/week5-notes.md`) were written against an earlier 69-cluster version and haven't been regenerated yet — noted
in [Known Issues](#known-issues).

## Requirements

- Python 3.14
- [uv](https://docs.astral.sh/uv/) — used to install everything

## Quick Start

```bash
git clone https://github.com/rishithapamu/ai-security.git
cd ai-security
uv sync
```

That installs everything. From here, either run the whole pipeline in one go (see [note below](#a-note-on-make-run)), or go step-by-step:

### 1. Collect the data

```bash
PYTHONPATH=. uv run python cli.py ingest all
```

Downloads all five datasets and puts them into one consistent format (`data/processed/combined.parquet`), so the rest of the pipeline doesn't need to care where a prompt originally came from.

### 2. Turn prompts into numbers (embedding)

```bash
PYTHONPATH=. uv run python cli.py embed
```

Each prompt gets converted into a vector that represents its meaning, so prompts with similar meaning end up with similar vectors. This is what makes grouping (clustering) possible.

### 3. Remove near-duplicate prompts

```bash
make dedup-run
```

Collapses near-identical prompts (546 near-duplicate pairs were found at a 0.95 cosine-similarity threshold — see
[`docs/dedup-findings.md`](docs/dedup-findings.md)) into one representative record per group, writing `data/processed/deduped.parquet`. **This step is required, not optional** — `cluster.py` reads `deduped.parquet` directly and will error if it doesn't exist yet.

If you just want to *see* duplicate pairs without merging them, `make dedup` runs the read-only detection step and prints examples to the terminal.

### 4. Group similar prompts together

```bash
make cluster
```

Groups prompts by similarity so related attacks end up in the same bucket (HDBSCAN over a UMAP-reduced embedding space). To try different grouping settings:

```bash
make tune
```

### 5. Label each group

Each cluster gets tagged by hand with two labels: **how** the attack works (its technique, the *primitive*) and **what** the attacker is trying to achieve (its goal, the *behavior*). Why two separate axes instead of one — see [ADR 003](docs/decisions/003-registry-mental-model.md). Labels live in `src/registry/candidates/cluster_assignments.yaml`. Once filled in:

```bash
PYTHONPATH=. uv run python src/registry/label_attacks.py
```

### 6. See the coverage gaps

```bash
make coverage
```

Builds a chart showing every combination of technique × goal, and how many examples exist for each — including the combinations with zero. This is what produced the 91%-empty finding above.

### 7. Search for similar prompts

```bash
PYTHONPATH=. uv run python cli.py search "your prompt here"
```

Type in any prompt and get back the most similar ones already in the corpus.

### 8. Explore everything in the dashboard

```bash
make dashboard
```

Opens a Streamlit app (`src/app/`) with four pages: corpus overview, a per-cluster explorer with a UMAP scatter plot, an interactive coverage heatmap you can click into, and a live semantic search page.

#### A note on `make run`

`make run` exists and is meant to chain the whole pipeline in one command. As of this commit it does **not** call `make dedup-run` before `make cluster` — since `cluster.py` now requires `deduped.parquet` to exist, a fresh `make run` will currently fail partway through. Until the Makefile is updated, run step 3 (`make dedup-run`) manually before step 4, or before calling `make run`.

## What's in Here

```
cli.py           # the main commands: ingest, embed, search
src/
  ingest/         # loads each dataset and converts it to one shared format
  embed/          # turns prompts into numbers, finds & merges duplicate prompts
  cluster/        # groups similar prompts together
  registry/       # the technique/goal labels for each group
  analytics/      # builds the coverage chart and novelty scores
  app/            # Streamlit dashboard (overview, clusters, coverage, search)
docs/
  decisions/      # short write-ups explaining why certain choices were made
data/             # the datasets and results (not tracked in git)
reports/          # the coverage chart and novelty outputs (not tracked in git)
```

## Why Things Were Built This Way

Short write-ups explaining specific choices (like why prompts are labeled with two separate categories instead of one, or why a particular grouping setting was chosen over a "better-scoring" one) live here:

- [Why this dataset was chosen first](docs/decisions/001-dataset-selection.md)
- [How prompts are normalized](docs/decisions/002-schema-design.md)
- [How groups get labeled — primitive vs. behavior](docs/decisions/003-registry-mental-model.md)
- [What "coverage" means here](docs/decisions/005-coverage-dimension.md)

## Known Issues

Full list in [`docs/known-issues.md`](docs/known-issues.md). Highlights:

- `make run` doesn't yet call `dedup-run` before `cluster` (see note above) —needs a Makefile fix.
- Deduplication is built (`src/embed/dedup_merge.py`) and wired into `cluster.py`, but whether it has actually been run as part of the production pipeline that produced the current 76-cluster registry is **unconfirmed** — see known-issues #13.
- Two of the five datasets (AdvBench, In-The-Wild) don't ship their own attack-category labels, which limits supervised evaluation of cluster
  quality — see known-issues #6.
- About a quarter of prompts historically fell into no cluster ("noise") and are excluded from the headline coverage numbers; this should be re-verified against the current 76-cluster run.

## Settings

Code style/formatting rules live in `pyproject.toml`. To check your code automatically before every commit:

```bash
uv run pre-commit install
```

## Tests

```bash
uv run pytest
```

## License

MIT
