# Known Issues

Ranked roughly by severity/impact. Each entry states what's wrong, why it matters,
and current status. This is a living doc — update status as issues are fixed.

---

## 1. Hardcoded absolute paths break portability (partially fixed)

`analysis.py`, `noise-analysis.py`, and `cli.py` all hardcode
`/Users/rishithapamu/Desktop/internship_project/ai-sec-workbench/...` instead of using
the `input`/`out` arguments the CLI already accepts. This means:
- The pipeline only runs on one machine.
- CLI flags like `--input` are silently ignored — they *look* configurable but aren't.

`cluster.py`'s `load_corpus` had this same bug and was fixed to actually use its
`input_dir` argument. The fix was not propagated to the other files that have the
identical pattern.

**Status:** Fixed in `cluster.py` only. Still present in `analysis.py`, `noise-analysis.py`, `cli.py`.

---

## 2. `dedup.py` silently ignores its own `--embeddings` CLI argument

`main()` correctly builds the FAISS index from the `--embeddings` path passed in, but
`find_duplicate_pairs()` reloads the raw embedding vectors used to query that index from
a hardcoded literal path (`data/embeddings/embeddings.npy`). If a non-default embeddings
directory is ever passed, the index and the query vectors would come from different
files — producing incorrect similarity scores with no error or warning.

**Status:** Not fixed. Higher risk than issue #1 because it can produce silently wrong
results rather than just breaking portability.

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

## 7. Novelty scores are dominated by measurement artifacts, not genuine novelty

Of the top 20 highest novelty-score prompts (see `novelty-inspection.md`), 7 were
encoding/formatting artifacts (Morse code, Unicode small-caps) that the embedding model
simply can't parse semantically, and 5 were benign Do-Not-Answer prompts that score high
only because they don't resemble any *harmful* cluster centroid. Only 2 of 20 were
genuinely novel attack patterns.

**Why it matters:** raw novelty score, used naively (e.g. to prioritize what to review or
collect more of), would waste review time on artifacts rather than real gaps.

**Recommended filters before reuse** (documented, not yet wired into `novelty.py` as code):
1. Exclude noise points (`cluster == -1`).
2. Exclude Do-Not-Answer benign prompts.
3. Exclude non-English prompts.

**Status:** Filters recommended in docs; unclear whether implemented as code in
`src/analytics/novelty.py` — verify before claiming this is automated.

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

## 10. Dedup recommendation not confirmed as applied before clustering

`dedup-findings.md` recommends deduplicating before clustering (546 near-duplicate pairs
found, 32 cross-source). `cluster.py`'s `main()` clusters the full combined corpus
directly, with no visible dedup/filter step in between ingestion and clustering.

**Why it matters:** if duplicates weren't actually dropped, some cluster density/sizes
may be partly inflated by near-identical repeated prompts (especially AdvBench's
templated variations — "Develop" vs "Outline" etc.) rather than reflecting genuinely
independent examples of an attack pattern.

**Status:** Unverified — needs a direct check of the actual ingestion→clustering pipeline
before making a claim either way in the viva. Don't guess on this one live.

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

*Last updated: this session, based on direct repo inspection — not carried over from
prior assumptions.*
