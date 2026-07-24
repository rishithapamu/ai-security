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
# Plotly dark template — applied to every chart on this page
# Matches the dark background from config.toml so charts don't have
# a jarring white background in an otherwise dark UI
# ─────────────────────────────────────────────────────────────────────────────
PLOTLY_TEMPLATE = dict(
    layout=go.Layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#1E2130",
        font=dict(color="#E2E8F0", family="Inter, sans-serif"),
        xaxis=dict(gridcolor="#2E3250", linecolor="#2E3250"),
        yaxis=dict(gridcolor="#2E3250", linecolor="#2E3250"),
        colorway=[
            PALETTE["blue"],
            PALETTE["purple"],
            PALETTE["green"],
            PALETTE["amber"],
            PALETTE["red"],
            PALETTE["teal"],
        ],
    )
)

PATHS = {
    "clusters": Path("data/clusters/clusters.parquet"),
    "labels": Path("data/clusters/cluster_labels.csv"),
    "assignments": Path("src/registry/candidates/cluster_assignments.yaml"),
    "labeled": Path("data/attacks_labeled.parquet"),
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


if "data_loaded" not in st.session_state:
    st.session_state["clusters"] = load_clusters()
    st.session_state["assignments"] = load_assignments()
    st.session_state["data_loaded"] = True

clusters = st.session_state["clusters"]
assignments = st.session_state["assignments"]

selected_sources = render_sidebar(clusters)

# ─────────────────────────────────────────────────────────────────────────────
# Page header
# ─────────────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div style="margin-bottom: 1.5rem;">
        <div style="font-size:2rem; font-weight:800; color:#E2E8F0;
                    letter-spacing:-0.5px; line-height:1.2;">
            🔐 AI Security Workbench
        </div>
        <div style="font-size:14px; color:#64748B; margin-top:4px;">
            Adversarial prompt analysis across 5 public red-teaming datasets
            &nbsp;·&nbsp;
            <a href="https://github.com/rishithapamu/ai-security" target="_blank">
                GitHub ↗
            </a>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

if clusters is None:
    st.error(
        "⚠️ `data/clusters/clusters.parquet` not found. "
        "Run the clustering pipeline first."
    )
    st.stop()

filtered = (
    clusters[clusters["source"].isin(selected_sources)]
    if selected_sources
    else clusters
)

# ─────────────────────────────────────────────────────────────────────────────
# KPI row
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
    primitives = {v["primitive"] for v in assignments.values()}
    behaviors = {v["behavior"] for v in assignments.values()}
    total_cells = len(primitives) * len(behaviors)
    covered = len({(v["primitive"], v["behavior"]) for v in assignments.values()})
    coverage_pct = round(covered / total_cells * 100, 1)
else:
    coverage_pct = 0

c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("Total Prompts", f"{n_total:,}")
c2.metric("Clusters", n_clusters)
c3.metric("Clustered", f"{n_clustered:,}")
c4.metric("Noise Points", f"{n_noise:,}", f"{noise_pct}%")
c5.metric("Sources", n_sources)
c6.metric("Matrix Coverage", f"{coverage_pct}%")

st.markdown("<br>", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# Charts row
# ─────────────────────────────────────────────────────────────────────────────
left, right = st.columns(2)

with left:
    section_header("Prompts by Source", "Distribution across datasets")
    source_counts = filtered["source"].value_counts().reset_index()
    source_counts.columns = ["source", "count"]
    source_colours = [
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
            marker_color=source_colours,
            marker_line_width=0,
        )
    )
    fig.update_layout(
        **PLOTLY_TEMPLATE["layout"].to_plotly_json(),
        height=260,
        margin=dict(t=10, b=0, l=0, r=0),
        showlegend=False,
        bargap=0.3,
    )
    st.plotly_chart(fig, width="stretch")

with right:
    section_header("Cluster Size Distribution", "How many prompts per cluster")
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
        **PLOTLY_TEMPLATE["layout"].to_plotly_json(),
        height=260,
        margin=dict(t=10, b=0, l=0, r=0),
        xaxis_title="Cluster size",
        yaxis_title="# clusters",
    )
    st.plotly_chart(fig2, width="stretch")

# ─────────────────────────────────────────────────────────────────────────────
# Attack categories
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
section_header("Attack Categories", "Top 15 categories across filtered corpus")

if "attack_category" in filtered.columns:
    cat_counts = (
        filtered["attack_category"].dropna().value_counts().head(15).reset_index()
    )
    cat_counts.columns = ["category", "count"]

    # Colour bars by rank — gradient from blue to purple
    n = len(cat_counts)
    bar_colours = [f"rgba(147,197,253,{0.9 - i * 0.04})" for i in range(n)]

    fig3 = go.Figure(
        go.Bar(
            x=cat_counts["count"],
            y=cat_counts["category"],
            orientation="h",
            marker_color=bar_colours,
            marker_line_width=0,
        )
    )
    fig3.update_layout(
        **PLOTLY_TEMPLATE["layout"].to_plotly_json(),
        height=380,
        margin=dict(t=10, b=0, l=0, r=0),
        yaxis={"categoryorder": "total ascending"},
        showlegend=False,
        xaxis_title="Prompts",
    )
    st.plotly_chart(fig3, width="stretch")
else:
    st.info("No `attack_category` column in clusters.parquet.")

# ─────────────────────────────────────────────────────────────────────────────
# Dataset reference links
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
section_header("Datasets", "Sources ingested into this workbench")

cols = st.columns(5)
datasets = [
    (
        "JailbreakBench",
        "jailbreakbench",
        PALETTE["blue"],
        "https://huggingface.co/datasets/JailbreakBench/JBB-Behaviors",
        "200 prompts · academic benchmark · includes benign prompts",
    ),
    (
        "AdvBench",
        "advbench",
        PALETTE["purple"],
        "https://huggingface.co/datasets/AlignmentResearch/AdvBench",
        "520 prompts · harmful behaviors · no label schema",
    ),
    (
        "HarmBench",
        "harmbench",
        PALETTE["red"],
        "https://huggingface.co/datasets/swiss-ai/harmbench",
        "400 prompts · richest label schema · semantic + functional",
    ),
    (
        "DoNotAnswer",
        "donotanswer",
        PALETTE["green"],
        "https://huggingface.co/datasets/LibrAI/do-not-answer",
        "939 prompts · labels both prompt and expected response",
    ),
    (
        "InTheWild",
        "inthewild",
        PALETTE["amber"],
        "https://huggingface.co/datasets/TrustAIRLab/in-the-wild-jailbreak-prompts",
        "1,405 prompts · real-world · proven jailbreaks",
    ),
]

for col, (name, source, colour, url, desc) in zip(cols, datasets):
    n_src = len(clusters[clusters["source"] == source]) if clusters is not None else 0
    col.markdown(
        f"""
        <div style="background:#1E2130; border:1px solid #2E3250;
                    border-top: 3px solid {colour};
                    border-radius:8px; padding:14px;">
            <div style="font-size:13px; font-weight:700; color:#E2E8F0;">
                <a href="{url}" target="_blank"
                   style="color:{colour}; text-decoration:none;">{name} ↗</a>
            </div>
            <div style="font-size:11px; color:#64748B; margin-top:6px;
                        line-height:1.5;">{desc}</div>
            <div style="font-size:20px; font-weight:800; color:{colour};
                        margin-top:10px;">{n_src:,}</div>
            <div style="font-size:10px; color:#64748B;">prompts</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ─────────────────────────────────────────────────────────────────────────────
# ADR links
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
section_header("Architecture Decisions", "Design choices recorded as ADRs")

adrs = [
    ("001", "Dataset Selection", "docs/decisions/001-dataset-selection.md"),
    ("002", "Schema Design", "docs/decisions/002-schema-design.md"),
    ("003", "Registry Model", "docs/decisions/003-registry-mental-model.md"),
    ("004", "Registry Design", "docs/decisions/004-registry-design-notes.md"),
    ("005", "Coverage Dimensions", "docs/decisions/005-coverage-dimension.md"),
]

adr_html = '<div style="display:flex; flex-wrap:wrap; gap:8px;">'
for num, title, path in adrs:
    adr_html += f"""
    <a href="https://github.com/rishithapamu/ai-security/blob/main/{path}"
       target="_blank"
       style="background:#1E2130; border:1px solid #2E3250; border-radius:6px;
              padding:8px 14px; font-size:12px; color:#93C5FD;
              text-decoration:none; display:inline-block;">
        ADR {num} — {title} ↗
    </a>"""
adr_html += "</div>"
st.markdown(adr_html, unsafe_allow_html=True)
