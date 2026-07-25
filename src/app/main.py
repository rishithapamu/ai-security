"""
main.py — Entry point for the AI Security Workbench dashboard.

Run with:
    PYTHONPATH=. uv run streamlit run src/app/main.py
"""

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yaml

from src.app.filters import (
    PALETTE,
    inject_styles,
    render_sidebar,
    section_header,
)

st.set_page_config(
    page_title="AI Security Workbench",
    page_icon="🔐",
    layout="wide",
)
inject_styles()


# ─────────────────────────────────────────────────────────────────────────────
# FIX 3: Don't unpack PLOTLY_TEMPLATE as **kwargs — that conflicts with
# any keyword argument you also pass explicitly (e.g. xaxis_title, yaxis_title).
# Instead, define a helper that sets common layout properties directly.
# ─────────────────────────────────────────────────────────────────────────────
def dark_layout(**extra) -> dict:
    """
    Return a dict of Plotly layout properties for the dark theme.
    Pass any additional overrides as keyword arguments — they are merged in
    and take precedence over the defaults.
    """
    base = dict(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#1A1D2E",
        font=dict(color="#E2E8F0", family="Inter, sans-serif"),
        xaxis=dict(gridcolor="#2E3250", linecolor="#2E3250"),
        yaxis=dict(gridcolor="#2E3250", linecolor="#2E3250"),
        margin=dict(t=10, b=10, l=0, r=0),
    )
    base.update(extra)  # merge caller overrides — never duplicates a key
    return base


PATHS = {
    "clusters": Path("data/clusters/clusters.parquet"),
    "assignments": Path("src/registry/candidates/cluster_assignments.yaml"),
    "primitives": Path("src/registry/candidates/primitives.yaml"),
    "behaviors": Path("src/registry/candidates/behaviors.yaml"),
}


@st.cache_data
def load_clusters() -> pd.DataFrame | None:
    if not PATHS["clusters"].exists():
        return None
    return pd.read_parquet(PATHS["clusters"])


@st.cache_data
def load_assignments() -> dict | None:
    if not PATHS["assignments"].exists():
        return None
    with open(PATHS["assignments"]) as f:
        raw = yaml.safe_load(f)
    return {int(k): v for k, v in raw["cluster_assignments"].items()}


@st.cache_data
def load_primitive_count() -> int:
    """Read primitive count from primitives.yaml — the full taxonomy definition."""
    if not PATHS["primitives"].exists():
        return 0
    with open(PATHS["primitives"]) as f:
        data = yaml.safe_load(f)
    return len(data.get("primitives", {}))


@st.cache_data
def load_behavior_count() -> int:
    """Read behavior count from behaviors.yaml — the full taxonomy definition."""
    if not PATHS["behaviors"].exists():
        return 0
    with open(PATHS["behaviors"]) as f:
        data = yaml.safe_load(f)
    # behaviors.yaml has top-level keys that are behavior names
    # exclude the 'notes' key which is metadata not a behavior
    return len([k for k in data.keys() if k != "notes"])


if "data_loaded" not in st.session_state:
    st.session_state["clusters"] = load_clusters()
    st.session_state["assignments"] = load_assignments()
    st.session_state["n_primitives"] = load_primitive_count()
    st.session_state["n_behaviors"] = load_behavior_count()
    st.session_state["data_loaded"] = True

clusters = st.session_state["clusters"]
assignments = st.session_state["assignments"]

selected_sources = render_sidebar(clusters)

# ─────────────────────────────────────────────────────────────────────────────
# Page header
# ─────────────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div style="margin-bottom:1.5rem;">
        <div style="font-size:1.9rem;
            font-weight:800;
            color:#E2E8F0;
            letter-spacing:-0.5px;">
            🔐 AI Security Workbench
        </div>
        <div style="font-size:13px;color:#64748B;margin-top:4px;">
            Adversarial prompt analysis
            across 5 public red-teaming datasets &nbsp;·&nbsp;
            <a
            href="https://github.com/rishithapamu/ai-security"
            target="_blank">GitHub ↗</a>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

if clusters is None:
    st.error(
        "⚠️ `data/clusters/clusters.parquet` not found."
        " Run the clustering pipeline first."
    )
    st.stop()

filtered = (
    clusters[clusters["source"].isin(selected_sources)]
    if selected_sources
    else clusters
)

# ─────────────────────────────────────────────────────────────────────────────
# KPI row — each metric is already wrapped in a card by the CSS
# ─────────────────────────────────────────────────────────────────────────────
n_total = len(filtered)
n_noise = (filtered["cluster"] == -1).sum()
n_clustered = n_total - n_noise
n_clusters = filtered["cluster"].nunique() - (
    1 if -1 in filtered["cluster"].values else 0
)
noise_pct = round(n_noise / n_total * 100, 1) if n_total else 0
n_sources = filtered["source"].nunique()

if assignments:
    # Use the full taxonomy counts from primitives.yaml and behaviors.yaml
    # not just the ones that happen to appear in cluster_assignments.yaml.
    # This gives the correct denominator: 19 primitives × N behaviors = total cells.
    n_primitives = st.session_state["n_primitives"] or len(
        {v["primitive"] for v in assignments.values()}
    )
    n_behaviors = st.session_state["n_behaviors"] or len(
        {v["behavior"] for v in assignments.values()}
    )
    total_cells = n_primitives * n_behaviors
    covered = len({(v["primitive"], v["behavior"]) for v in assignments.values()})
    coverage_pct = round(covered / total_cells * 100, 1) if total_cells else 0
else:
    n_primitives = st.session_state.get("n_primitives", 0)
    n_behaviors = st.session_state.get("n_behaviors", 0)
    coverage_pct = 0

c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("Total Prompts", f"{n_total:,}")
c2.metric("Clusters", n_clusters)
c3.metric("Primitives", n_primitives)
c4.metric("Behaviors", n_behaviors)
c5.metric("Noise Points", f"{n_noise:,}", f"{noise_pct}%")
c6.metric("Matrix Coverage", f"{coverage_pct}%")

st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# FIX 4: wrap each section in a card div for visual separation
# ─────────────────────────────────────────────────────────────────────────────

# ── Charts row ────────────────────────────────────────────────────────────────
st.markdown('<div class="section-card">', unsafe_allow_html=True)
section_header("Corpus Overview", "Source distribution and cluster size breakdown")

left, right = st.columns(2)

with left:
    source_counts = filtered["source"].value_counts().reset_index()
    source_counts.columns = ["source", "count"]
    bar_colours = [
        {
            "jailbreakbench": PALETTE["blue"],
            "advbench": PALETTE["purple"],
            "harmbench": PALETTE["red"],
            "donotanswer": PALETTE["green"],
            "inthewild": PALETTE["amber"],
        }.get(s, PALETTE["muted"])
        for s in source_counts["source"]
    ]
    fig = go.Figure(
        go.Bar(
            x=source_counts["source"],
            y=source_counts["count"],
            marker_color=bar_colours,
            marker_line_width=0,
        )
    )
    fig.update_layout(
        **dark_layout(
            height=240,
            showlegend=False,
            bargap=0.3,
            xaxis_title="Dataset",
            yaxis_title="Prompts",
        )
    )
    st.plotly_chart(fig, width="stretch")

with right:
    clustered_only = filtered[filtered["cluster"] != -1]
    sizes = clustered_only["cluster"].value_counts().reset_index()
    sizes.columns = ["cluster", "size"]
    fig2 = go.Figure(
        go.Histogram(
            x=sizes["size"],
            nbinsx=20,
            marker_color=PALETTE["blue"],
            marker_line_width=0,
            opacity=0.85,
        )
    )
    fig2.update_layout(
        **dark_layout(
            height=240,
            xaxis_title="Cluster size (# prompts)",
            yaxis_title="# clusters",
        )
    )
    st.plotly_chart(fig2, width="stretch")

st.markdown("</div>", unsafe_allow_html=True)

# ── Attack categories ─────────────────────────────────────────────────────────
st.markdown('<div class="section-card">', unsafe_allow_html=True)
section_header(
    "Attack Categories",
    "Top 15 across filtered corpus"
    " (jailbreakbench, harmbench, donotanswer only"
    " AdvBench and InTheWild have no labels)",
)

if "attack_category" in filtered.columns and filtered["attack_category"].notna().any():
    cat_counts = (
        filtered["attack_category"].dropna().value_counts().head(15).reset_index()
    )
    cat_counts.columns = ["category", "count"]
    n = len(cat_counts)
    bar_colours_cat = [f"rgba(147,197,253,{0.9 - i * 0.04})" for i in range(n)]

    fig3 = go.Figure(
        go.Bar(
            x=cat_counts["count"],
            y=cat_counts["category"],
            orientation="h",
            marker_color=bar_colours_cat,
            marker_line_width=0,
        )
    )
    # FIX 3: pass xaxis_title and yaxis_title directly to dark_layout()
    # so they go into the same update_layout() call — no duplicate keys
    fig3.update_layout(
        **dark_layout(
            height=360,
            showlegend=False,
            yaxis=dict(categoryorder="total ascending", gridcolor="#2E3250"),
            xaxis_title="Prompts",
        )
    )
    st.plotly_chart(fig3, width="stretch")
else:
    st.info("No attack_category labels in filtered corpus.")

st.markdown("</div>", unsafe_allow_html=True)

# ── Dataset cards ─────────────────────────────────────────────────────────────
st.markdown('<div class="section-card">', unsafe_allow_html=True)
section_header("Datasets", "Sources ingested into this workbench")

cols = st.columns(5)
datasets = [
    (
        "JailbreakBench",
        "jailbreakbench",
        PALETTE["blue"],
        "https://huggingface.co/datasets/JailbreakBench/JBB-Behaviors",
        "Academic benchmark · includes benign prompts",
    ),
    (
        "AdvBench",
        "advbench",
        PALETTE["purple"],
        "https://huggingface.co/datasets/AlignmentResearch/AdvBench",
        "Harmful behaviors · no label schema",
    ),
    (
        "HarmBench",
        "harmbench",
        PALETTE["red"],
        "https://huggingface.co/datasets/swiss-ai/harmbench",
        "Richest label schema · semantic + functional",
    ),
    (
        "DoNotAnswer",
        "donotanswer",
        PALETTE["green"],
        "https://huggingface.co/datasets/LibrAI/do-not-answer",
        "Labels both prompt and expected response",
    ),
    (
        "InTheWild",
        "inthewild",
        PALETTE["amber"],
        "https://huggingface.co/datasets/TrustAIRLab/in-the-wild-jailbreak-prompts",
        "Real-world · proven jailbreaks · noisiest",
    ),
]
for col, (name, source, colour, url, desc) in zip(cols, datasets):
    n_src = len(clusters[clusters["source"] == source])
    col.markdown(
        f"""
        <div style="background:#16192A;border:1px solid #2E3250;
                    border-top:3px solid {colour};border-radius:8px;padding:14px;">
            <div style="font-size:13px;font-weight:700;">
                <a href="{url}"
                    target="_blank" style="color:{colour};
                    text-decoration:none;">
                    {name} ↗</a>
            </div>
            <div style="font-size:11px;
                color:#64748B;
                margin-top:6px;
                line-height:1.5;">{desc}</div>
            <div style="font-size:1.6rem;
                font-weight:800;
                color:{colour};
                margin-top:10px;">{n_src:,}</div>
            <div style="font-size:10px;
                color:#64748B;">prompts</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
st.markdown("</div>", unsafe_allow_html=True)

# ── ADR links ─────────────────────────────────────────────────────────────────
st.markdown('<div class="section-card">', unsafe_allow_html=True)
section_header("Architecture Decisions", "Design choices recorded as ADRs")

adrs = [
    ("001", "Dataset Selection", "docs/decisions/001-dataset-selection.md"),
    ("002", "Schema Design", "docs/decisions/002-schema-design.md"),
    ("003", "Registry Model", "docs/decisions/003-registry-mental-model.md"),
    ("004", "Registry Design", "docs/decisions/004-registry-design-notes.md"),
    ("005", "Coverage Dimensions", "docs/decisions/005-coverage-dimension.md"),
]
adr_html = '<div style="display:flex;flex-wrap:wrap;gap:8px;">'
for num, title, path in adrs:
    adr_html += (
        f'<a href="https://github.com/rishithapamu/ai-security/blob/main/{path}" '
        f'target="_blank" style="background:#16192A;border:1px solid #2E3250;'
        f"border-radius:6px;padding:8px 14px;font-size:12px;color:#93C5FD;"
        f'text-decoration:none;display:inline-block;">'
        f"ADR {num} — {title} ↗</a>"
    )
adr_html += "</div>"
st.markdown(adr_html, unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)
