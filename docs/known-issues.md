# Known Issues

Ranked roughly by severity/impact. Each entry states what's wrong, why it matters, and current status. This is a living doc — update status as issues are fixed.

---

## 1. Hardcoded absolute paths break portability (partially fixed)

`analysis.py`, `noise-analysis.py`, and `cli.py` all hardcode
`/Users/rishithapamu/Desktop/internship_project/ai-sec-workbench/...` instead of using
the `input`/`out` arguments the CLI already accepts. This means:
- The pipeline only runs on one machine.
- CLI flags like `--input` are silently ignored — they *look* configurable but aren't.

`cluster.py`'s `load_corpus` had this same bug and was fixed to actually use its`input_dir` argument. The fix was not propagated to the other files that have the identical pattern.

**Status:** Fixed in `cluster.py` only. Still present in `analysis.py`, `noise-analysis.py`, `cli.py`.

---

## 2. `dedup.py` silently ignores its own `--embeddings` CLI argument

`main()` correctly builds the FAISS index from the `--embeddings` path passed in, but `find_duplicate_pairs()` reloads the raw embedding vectors used to query that index from a hardcoded literal path (`data/embeddings/embeddings.npy`). If a non-default embeddings directory is ever passed, the index and the query vectors would come from different files — producing incorrect similarity scores with no error or warning.

**Status:** Not fixed. Higher risk than issue #1 because it can produce silently wrongresults rather than just breaking portability.

---

## 3. Dead code in `quality.py`'s `print_report` — output is missing data with no error

```python
print(f"\n{'─' * 80}")
print(f"CLUSTER {cluster_id}: {cluster_label}")
f"Total points: {total_in_cluster} | "
f"Weak members: {weak_count} ({weak_pct:.1f}%)"
print(f"{'─' * 80}")
```

The two f-strings in the middle are evaluated and discarded — never printed. The report
runs without error and looks nearly correct; it just never shows the point/weak-member
counts per cluster.

**Status:** Not fixed. Low effort to fix (wrap in `print(...)`), high value to mention
in viva as an example of a bug unit tests wouldn't catch.

---

## 4. Registry drift between candidate files and the single source of truth

Early candidate files (`cluster_to_primitive.yaml`, `primitives.yaml`, `behaviors.yaml`)
disagree with the consolidated `cluster_assignments.yaml` in places:
- Cluster 17/20: an early draft filed `harmful_advice` as if it were a *primitive*
  (technique); the final assignment correctly treats it as a *behavior* (objective).
- Cluster 29: candidate file says behavior `dangerous_materials`; final assignment says
  `criminal_assistance`.
- Cluster 40: candidate file says behavior `harassment`; final assignment says
  `cybercrime_enablement`.

**Why it matters:** this is exactly the risk that motivated consolidating everything
into `cluster_assignments.yaml` as the single source of truth — nothing errors when two
YAML files disagree, so any code that accidentally reads from a candidate file instead
of the consolidated one would silently use stale/wrong labels.

**Status:** Resolved for downstream code (only `cluster_assignments.yaml` is read by
`label_attacks.py` / `coverage_analysis.py`), but the candidate files themselves still
contain the contradictions and haven't been cleaned up or removed.

---

## 5. `severity` field is unpopulated for every record

Per ADR 002, none of the five source datasets provide severity ratings, so this field
defaults to `None` for all 3,464 records. It was scoped as "assign manually or via
classifier later" — that later hasn't happened yet.

**Why it matters:** blocks the `behavior × severity` coverage dimension proposed in
ADR 005, which is explicitly deferred pending this field.

**Status:** Open, scoped out of current phase intentionally (documented, not an oversight).

---

## 6. `attack_category` is inconsistent ground truth — cannot be used for supervised evaluation as-is

`attack_category` is null for 100% of AdvBench and In-The-Wild records, and even where
present (JailbreakBench, HarmBench, Do-Not-Answer), the three datasets use three
different, non-unified taxonomies.

**Why it matters:** this is the only candidate external ground truth for evaluating
cluster quality (using `cluster_assignments.yaml`'s own labels would be circular — see
issue in evaluation methodology). Its incompleteness and inconsistency means no clean
F1/precision/recall score against clustering is currently possible without first doing
taxonomy-unification work that hasn't been done.

**Status:** Open, documented limitation rather than a bug per se.

---

## 8. Sparse-cell interpretation required manual case-by-case judgment, not a general rule

The coverage matrix can't distinguish "this combination is genuinely rare in the real
world" from "this dataset never collected it." `sparse-areas.md` resolved this manually
for 5 cells (3 dataset gaps, 1 genuinely rare, 1 both) — but this required human judgment
per cell; there's no systematic/automated way to make this call for the other sparse
cells in the matrix.

**Status:** Open by nature of the problem — flagged as a methodology limitation, not
something with a code fix.

---

## 9. Primitive and behavior taxonomies share overlapping label names, blurring the orthogonality principle

`misinformation_generation` and `content_policy_circumvention` each appear as *both* a
primitive and a behavior label across the registry files, meaning the same word
sometimes describes technique and sometimes describes objective depending on context.

**Why it matters:** the entire registry design (ADR 003/004) depends on primitive and
behavior being genuinely orthogonal dimensions. Reusing the same label name across both
axes risks confusing anyone reading the registry about which axis a given cluster
assignment refers to.

**Status:** Open. Would require renaming one of the overlapping labels on one axis to
fully resolve.

---

## 11. Test coverage does not include the clustering/alignment logic

Existing tests (`test_hello.py`, `test_schema.py`, `test_search.py`) cover the schema and
FAISS search, but not the embedding↔corpus alignment logic in `cluster.py`/`quality.py`/
`novelty.py` — the exact code responsible for the misalignment bug class described in
issue #2's family (silent ID/positional mismatch).

**Status:** A `test_cluster.py` file has been added locally (uncommitted as of this
session) — verify its actual test coverage once committed and pushed.

---

## 12. Process risk: uncommitted work sat unpushed for an unknown period

A substantial chunk of work — the Streamlit dashboard (`src/app/`), generated reports,
`test_cluster.py`, and `cluster.py` fixes — existed only in the local working directory,
uncommitted, discovered only when checking `git status` directly. The commit was also
blocked by 30 unresolved `ruff` line-length (E501) violations in the new dashboard pages.

**Why it matters:** work that exists only locally isn't backed up, isn't visible to a
supervisor checking GitHub, and can't be verified as "done" by anyone but the person
looking directly at the laptop it's on.

**Status:** Commit currently blocked on ruff E501 fixes; not yet pushed to `origin/main`
as of this session.

---
## 13. Deduplication step built but not applied before clustering

**Severity:** Medium
**Status:** Open

### Description
`docs/dedup-findings.md` identified 546 near-duplicate prompt pairs (cosine similarity ≥ 0.95) across the combined corpus of 3,464 records, using `src/embed/dedup.py`. Of these, 32 pairs were cross-source duplicates between AdvBench and JailbreakBench (several scoring 1.000 — identical prompts), confirming that JailbreakBench was partially derived from AdvBench. The remaining 514 pairs were same-source duplicates, concentrated in AdvBench,differing only by minor wording ("Develop" vs "Outline", "Write" vs "Create"), consistent with LLM-generated synthetic variation.

A deduplication script (`src/embed/dedup_merge.py`) was written that collapses near-duplicate groups via union-find and selects one representative record per group, but this step has not yet been run as part of the production pipeline. All clustering, registry, and coverage analysis in this project (Weeks 4–8) was performed on the non-deduplicated corpus.

### Impact
Near-duplicate prompts inflate the density of whichever region of embedding
space they occupy. This means:
- Cluster sizes partially reflect copy-paste/synthetic repetition rather than
  distinct attack instances.
- Novelty scores for near-duplicate clusters are artificially suppressed
  (many neighbors, low apparent novelty) — the inverse of the
  encoding-artifact problem already noted in the novelty-scoring findings.
- Coverage counts in `cluster_assignments.yaml` (primitive × behavior matrix)
  may overweight primitive/behavior combinations that happen to contain
  heavily-duplicated source material, most notably `instruction_override`
  clusters sourced from AdvBench.

The effect on final conclusions (e.g. the 75%-empty coverage matrix, the
meta-attack dominance finding) is believed to be small, since duplicates
tend to reinforce existing dense cells rather than create new ones, but
this has not been empirically verified.

### Recommendation
Run the full pipeline in order — `ingest → embed → dedup-run → cluster →
tune → quality → noise-analysis → relabel → coverage` — and compare the
resulting cluster count, sizes, and coverage matrix against the current
(non-deduplicated) results. If the shift is material, re-label clusters
against the deduplicated run and update `cluster_assignments.yaml`
accordingly. If the shift is negligible, this can be closed as "verified
low-impact" without a full relabel.
