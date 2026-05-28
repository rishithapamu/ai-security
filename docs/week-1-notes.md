# Week 1 Notes

## What I built
Set up a professional Python repository with CI, linting, and pre-commit hooks. Researched five public adversarial prompt datasets, compared their label schemas and quality, and wrote an ADR recommending JailbreakBench as the first dataset to ingest. Designed a normalized Pydantic schema (AttackRecord) to represent prompts from any dataset consistently. Built an ingestion pipeline that downloads JailbreakBench from HuggingFace, validates every row, logs any rejections, and saves the output as a parquet file.

## What took time
Reading through the dataset papers carefully enough to understand and explain each one's label schema. The datasets are more different from each other than they first appear — each one makes different tradeoffs between size, label richness, and realism.

## What surprised me
The variety of jailbreak types. It initially seemed like a straightforward problem — just prompts that trick a model. But the datasets revealed how many different angles attackers take: roleplay, fictional framing, direct instruction override, real-world community-sourced tricks. It's a much richer attack surface than expected.

## Next week
Week 2 is focused on embeddings and semantic similarity — moving from "I have prompts" to "I can find similar prompts quickly."

- Day 6: Embed 1,000 prompts using sentence-transformers and check if nearest-neighbor pairs actually make sense
- Day 7: Batch embed the full corpus and cache embeddings so unchanged prompts never get re-embedded
- Day 8: Build a find_similar() function using FAISS for fast similarity search
- Day 9: Detect near-duplicate prompts across datasets — find clusters where cosine similarity is above 0.95
- Day 10: Build an interactive 2D UMAP plot where hovering shows the prompt text
