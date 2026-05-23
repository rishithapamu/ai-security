# 001 — Dataset Selection for Initial Ingestion

## Status
Accepted

## Context
The workbench needs a dataset of adversarial prompts to test LLM defenses against. Several public datasets exist, each with different sizes, label schemas, and collection methods. Picking the wrong one first could mean building an ingestion pipeline around a dataset that is too limited, too noisy, or poorly labeled to support meaningful research. This decision records which dataset we chose to ingest first and why.

## Datasets Considered

### AdvBench
- **Source:** University of Chicago, 2023
- **Size:** 1,096 prompts (520 harmful behaviors, 576 harmful strings)
- **License:** MIT
- **Label schema:** No label schema — unlabeled prompts split into harmful behaviors and harmful strings. Success or failure of an attack is left to the user to evaluate.
- **Quality notes:** One of the earliest datasets of its kind, but lack of labels makes systematic evaluation difficult.

### HarmBench
- **Source:** Center for AI Safety, 2024
- **Size:** 400+ behaviors across 7 attack methods
- **License:** MIT
- **Label schema:** Each prompt is labeled on two dimensions — semantic (topic: cybercrime, weapons, misinformation etc.) and functional (attack type: standard, contextual, multimodal, copyright).
- **Quality notes:** Richest label schema of all datasets considered, purpose-built for benchmarking attack methods against defenses.

### JailbreakBench
- **Source:** Independent researchers, 2024
- **Size:** 200 prompts (100 harmful, 100 benign)
- **License:** MIT
- **Label schema:** Each prompt is labeled with a goal, target behavior, category (10 behavior categories) and source dataset.
- **Quality notes:** Only dataset to include benign prompts, which allows evaluation of false positive rates — whether defenses over-refuse safe prompts.

### Do-Not-Answer
- **Source:** Independent researchers, 2023
- **Size:** 939 questions, 5,634 responses
- **License:** Apache 2.0
- **Label schema:** Prompts are labeled by harm category (Information Hazards, Malicious Uses, Discrimination etc.) and responses are labeled by expected response type (cannot assist, refute opinion, discuss dual perspectives etc.).
- **Quality notes:** Only dataset that labels both the prompt and the expected model response, making it useful for evaluating response quality not just refusal rates.

### In-The-Wild (DAN)
- **Source:** Collected from Reddit, Discord and open source datasets, 2023
- **Size:** 6,387 prompts (666 confirmed jailbreaks)
- **License:** MIT
- **Label schema:** Each prompt is labeled with platform, source, whether it is a confirmed jailbreak, timestamp, and community metadata. No behavior or harm categories.
- **Quality notes:** Only dataset with real-world prompts used by actual users, but noisy and inconsistently labeled compared to academic datasets.

## Comparison

| Dataset | Size | Labels | Real-world | Benign prompts | License |

| AdvBench | 1,096 | None | No | No | MIT |
| HarmBench | 400+ | Rich | No | No | MIT |
| JailbreakBench | 200 | Medium | No | Yes | MIT |
| Do-Not-Answer | 939 | Rich | No | No | Apache 2.0 |
| In-The-Wild | 6,387 | Minimal | Yes | No | MIT |


## Decision
We will ingest JailbreakBench first. It contains prompts from AdvBench and HarmBench as well as original prompts, meaning we get coverage of the major academic datasets without having to ingest them separately. The dataset is small enough to work with quickly but large enough to cover a good variety of behavior categories.

In-the-Wild would be the second choice given its real-world prompts that have been proven to work, but the data is messy inconsistent, and some prompts may not be proper jailbreaks at all. The remaining datasets are either too large, too narrow, or already represented within JailbreakBench.

## Consequences
The ingestion pipeline will be built and tested against JailbreakBench first, meaning the normalized AttackRecord schema must accommodate its structure. All subsequent datasets will be mapped to the same schema, so no single dataset's structure dominates. By starting with an academic dataset we are giving up real-world realism early on — prompts that actual users have proven work in practice. In-the-Wild will be ingested second to address this gap.
