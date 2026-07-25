# ai-sec-workbench

 To identify adversarial prompts, the kind used to try to "jailbreak" AI chatbots.

![Python 3.14](https://img.shields.io/badge/python-3.14-blue)
![uv](https://img.shields.io/badge/deps-uv-orange)
![License: MIT](https://img.shields.io/badge/license-MIT-green)

## Requirements

- Python 3.14
- [uv](https://docs.astral.sh/uv/) — used to install everything

## Installation

```bash
git clone https://github.com/rishithapamu/ai-security.git
cd ai-security
uv sync
```

## How to Run It

make run should run all commands and open the web application. However, if you wish to go step-by-step:

### 1. Collect the data

```bash
PYTHONPATH=. uv run python cli.py ingest all
```

Downloads all five datasets and puts them into one consistent format, so the rest of the pipeline doesn't need to care where a prompt originally came from.

### 2. Turn prompts into numbers (embedding)

```bas
PYTHONPATH=. uv run python cli.py embed
```

Each prompt gets converted into a list of numbers that represents its meaning, so prompts with similar meaning end up with similar numbers. This is what makes the next step — grouping — possible.

### 3. Check for duplicates (optional, informational only)

```bash
make dedup
```

Flags prompts that are the same or nearly the same, including ones that show up in more than one dataset. This step reports duplicates but doesn't remove them yet — see Known Issues.

### 4. Group similar prompts together

```bash
make cluster
```

Groups prompts by similarity so related attacks end up in the same bucket. To try different grouping settings:

```bash
make tune
```

### 5. Label each group

Each group gets tagged by hand with two labels: **how** the attack works (its technique) and **what** the attacker is trying to achieve (its goal). This is done in `src/registry/candidates/cluster_assignments.yaml`. Once filled in:

```bash
PYTHONPATH=. uv run python src/registry/label_attacks.py
```

### 6. See the coverage gaps

```bash
make coverage
```

Builds a chart showing every combination of technique × goal, and how many examples exist for each — including the combinations with none at all.

### 7. Search for similar prompts

```bash
PYTHONPATH=. uv run python cli.py search "your prompt here"
```

Type in any prompt and get back the most similar ones already in the dataset.

## What's in Here

```
cli.py           # the main commands: ingest, embed, search
src/
  ingest/         # loads each dataset and converts it to one shared format
  embed/          # turns prompts into numbers, finds similar/duplicate prompts
  cluster/        # groups similar prompts together
  registry/       # the technique/goal labels for each group
  analytics/      # builds the coverage chart
docs/
  decisions/      # short write-ups explaining why certain choices were made
data/             # the datasets and results (not tracked in git)
reports/          # the final coverage chart (not tracked in git)
```

## Settings

Code style/formatting rules live in `pyproject.toml`. To check your code automatically before every commit:

```bash
uv run pre-commit install
```

## Tests

```bash
uv run pytest
```

## Why Things Were Built This Way

Short write-ups explaining specific choices (like why prompts are labeled with two separate categories instead of one, or why a particular grouping setting was chosen over a "better-scoring" one) live here:

- [Why this dataset was chosen first](docs/decisions/001-dataset-selection.md)
- [How prompts are normalized](docs/decisions/002-schema-design.md)
- [How groups get labeled](docs/decisions/003-registry-mental-model.md)
- [More on the labeling design](docs/decisions/004-registry-design-notes.md)
- [What "coverage" means here](docs/decisions/005-coversge-dimension.md)

## Known Issues

Full list in [`docs/known-issues.md`](docs/known-issues.md). The short version: duplicate prompts are detected but not yet removed before grouping; about a quarter of prompts don't fit cleanly into any group and are left out of the headline coverage numbers; two of the five datasets don't come with their own attack-category labels.

## License

MIT
