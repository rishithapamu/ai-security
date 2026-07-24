# 005 — Coverage Dimensions for Analytics

## Status
Accepted

## Context
The registry now maps 69 clusters to attack primitives and behaviors. Before buildingcoverage charts, we need to define what "coverage" means — which dimensions matter for research and why. Without this definition, a heatmap is just a pretty picture.

## Dimensions Selected

### 1. primitive × behavior (primary)
Rows: attack primitives (the *how* — technique used)
Columns: behaviors (the *what* — attacker objective)
Cell value: number of clusters mapping to that (primitive, behavior) pair

This is the most important dimension. It answers: for each combination of technique andobjective, how much evidence does the dataset contain? A zero cell means no cluster captures that combination — a blind spot.

### 2. primitive × source (secondary)
Rows: attack primitives
Columns: source datasets (jailbreakbench, advbench, harmbench, donotanswer, inthewild)
Cell value: number of clusters where that primitive appears in that source

This answers: are certain attack techniques only represented by one dataset? If `roleplay_jailbreak` only appears in `inthewild`, coverage of that technique is fragile and source-dependent.

### 3. behavior × severity (optional, pending severity labels)
Most clusters currently have severity = None (severity is assigned manually per ADR 002). This dimension will be revisited once severity labels are populated.

## What "dense" and "sparse" mean

Dense cell: 3+ clusters map to this (primitive, behavior) pair. The dataset has multipleindependent examples of this attack pattern — robust coverage.

Sparse cell: 0–1 clusters. Either the dataset has never seen this combination, or only one example exists. A red flag for research completeness.

## Why this matters
A model or defense system trained on this dataset will be blind to sparse combinations. If `emotional_engagement × self_harm_enablement` is empty, no training signal exists for prompts that use emotional manipulation to enable self-harm — a real and documented attack pattern.

## Consequences
Coverage charts will be computed for dimensions 1 and 2. Sparse cells will be flagged as candidates for dataset augmentation in Week 6.
