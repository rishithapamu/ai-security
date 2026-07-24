import logging
from collections import defaultdict
from pathlib import Path

import pandas as pd
import plotly.express as px
import typer
import yaml

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)

app = typer.Typer()

# The full candidate vocabulary — every primitive/behavior category that was
# ever *defined*, whether or not it ended up being assigned to a cluster.
# Sourced from primitives.yaml / ADR 004. Keeping this list explicit (not
# derived from cluster_assignments.yaml) is the whole point: it lets zero-
# assignment categories still show up as empty rows/columns instead of
# vanishing.
ALL_PRIMITIVES = [
    "instruction_override",
    "roleplay_jailbreak",
    "prompt_manipulation",
    "content_extraction",
    "sensitive_information_extraction",
    "emotional_engagement",
    "misinformation_generation",
    "fraud_and_deception",
    "criminal_assistance",
    "cybercrime_enablement",
    "dangerous_materials_assistance",
    "self_harm_enablement",
    "harassment_enablement",
    "hateful_or_violent_content",
    "sexual_content_generation",
    "identity_and_privacy_abuse",
    "economic_manipulation",
    "reputational_manipulation",
    "content_policy_circumvention",
]

ALL_BEHAVIORS = [
    "criminal_assistance",
    "cybercrime_enablement",
    "fraud_and_deception",
    "misinformation_generation",
    "hateful_or_violent_content",
    "sexual_content_generation",
    "dangerous_materials_assistance",
    "self_harm_enablement",
    "harassment_enablement",
    "harmful_advice",
    "economic_manipulation",
    "reputational_manipulation",
    "content_policy_circumvention",
]


def load_assignments(path: Path) -> dict[int, dict]:
    """
    Load cluster_assignments.yaml.

    This is the single source of truth we built in Day 21 —
    each cluster has BOTH a primitive (technique) and a behavior (objective).
    Loading from here means primitive and behavior are genuinely different
    dimensions, not the same list mapped to itself.
    """
    with open(path) as f:
        raw = yaml.safe_load(f)
    return {int(k): v for k, v in raw["cluster_assignments"].items()}


def build_coverage_matrix(assignments: dict[int, dict]) -> pd.DataFrame:
    counts: dict = defaultdict(lambda: defaultdict(int))
    for cid, assignment in assignments.items():
        primitive = assignment["primitive"]
        behavior = assignment["behavior"]
        counts[primitive][behavior] += 1

    df = pd.DataFrame(counts).T

    # Reindex against the FULL vocabulary, not just what's present.
    # This is the fix: any primitive/behavior with zero clusters now gets
    # an explicit all-zero row/column instead of being dropped silently.
    df = df.reindex(index=ALL_PRIMITIVES, columns=ALL_BEHAVIORS, fill_value=0)
    df = df.fillna(0).astype(int).sort_index().sort_index(axis=1)
    return df


def save_heatmap(matrix: pd.DataFrame, out_path: Path) -> None:
    """
    Save an interactive plotly heatmap.

    Blues scale: zero=white (gap), dense=dark blue.
    text_auto=True: prints count inside each cell.
    tickangle=45: rotates behavior labels so they don't overlap.
    """
    fig = px.imshow(
        matrix,
        labels=dict(x="Behavior", y="Primitive", color="Clusters"),
        title="Coverage Matrix: Primitive x Behavior",
        color_continuous_scale="Blues",
        text_auto=True,
        aspect="auto",
    )
    fig.update_xaxes(tickangle=45)
    fig.update_layout(
        height=max(400, len(matrix) * 60),
        width=max(900, len(matrix.columns) * 90),
        margin=dict(l=250, b=200, t=60, r=40),
        title_font_size=16,
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(str(out_path))
    log.info("Saved heatmap → %s", out_path)


def print_summary(matrix: pd.DataFrame) -> None:
    """
    Print coverage stats to terminal.

    stack() converts the 2D matrix into a Series with MultiIndex:
        (primitive, behavior) → count
    Making it trivial to sort and find top/bottom cells.
    """
    flat = matrix.stack()
    total_cells = len(flat)
    covered_cells = (flat > 0).sum()
    zero_cells = (flat == 0).sum()

    print("\n=== COVERAGE SUMMARY ===")
    print(f"Primitives:         {len(matrix)}")
    print(f"Behaviors:          {len(matrix.columns)}")
    print(f"Total cells:        {total_cells}")
    print(f"Covered cells:      {covered_cells}  ({covered_cells / total_cells:.0%})")
    print(f"Zero cells (gaps):  {zero_cells}  ({zero_cells / total_cells:.0%})")

    print("\n--- TOP 3 DENSEST CELLS ---")
    for (primitive, behavior), count in (
        flat.sort_values(ascending=False).head(3).items()
    ):
        print(f"  {primitive} x {behavior}: {count} clusters")

    print("\n--- TOP 3 SPARSEST NON-ZERO CELLS ---")
    nonzero = flat[flat > 0]
    for (primitive, behavior), count in nonzero.sort_values().head(3).items():
        print(f"  {primitive} x {behavior}: {count} cluster(s)")

    print("\n--- ZERO CELLS (gaps) ---")
    gaps = [(p, b) for (p, b), v in flat.items() if v == 0]
    print(f"  {len(gaps)} combinations with zero coverage:")
    for p, b in gaps:
        print(f"    {p} x {b}")


@app.command()
def main(
    assignments: Path = typer.Option(
        "src/registry/candidates/cluster_assignments.yaml",
        help="Path to cluster_assignments.yaml",
    ),
    out: Path = typer.Option(
        Path("reports/"),
        help="Output directory",
    ),
) -> None:
    """Compute and visualize primitive x behavior coverage."""
    log.info("Loading assignments from %s", assignments)
    cluster_assignments = load_assignments(assignments)
    log.info("Loaded %d cluster assignments", len(cluster_assignments))

    matrix = build_coverage_matrix(cluster_assignments)
    log.info(
        "Coverage matrix: %d primitives x %d behaviors",
        len(matrix),
        len(matrix.columns),
    )

    csv_path = out / "coverage_primitive_x_behavior.csv"
    out.mkdir(parents=True, exist_ok=True)
    matrix.to_csv(csv_path)
    log.info("Saved raw counts → %s", csv_path)

    heatmap_path = out / "coverage_primitive_x_behavior.html"
    save_heatmap(matrix, heatmap_path)

    print_summary(matrix)


if __name__ == "__main__":
    app()
