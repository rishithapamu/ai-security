"""
2_Clusters.py — Cluster Explorer page.
"""

from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.app.filters import (
    PALETTE,
    inject_styles,
    prompt_card,
    render_sidebar,
    section_header,
)

st.set_page_config(page_title="Cluster Explorer", layout="wide")
inject_styles()

if "data_loaded" not in st.session_state:
    st.warning("Please navigate to the home page first.")
    st.stop()

clusters = st.session_state["clusters"]
labels_df = st.session_state.get("cluster_labels")
assignments = st.session_state["assignments"]

if clusters is None:
    st.error("Cluster data not available.")
    st.stop()

selected_sources = render_sidebar(clusters)

EMBEDDINGS_DIR = Path("data/embeddings")


def build_label_map(labels_df, assignments, cluster_ids):
    csv_map = {}
    if labels_df is not None:
        num_col = next(
            (c for c in labels_df.columns if c.lower() in ("number", "cluster", "id")),
            None,
        )
        desc_col = next(
            (
                c
                for c in labels_df.columns
                if "description" in c.lower() or "label" in c.lower()
            ),
            None,
        )
        if num_col and desc_col:
            csv_map = dict(
                zip(labels_df[num_col].astype(int), labels_df[desc_col].astype(str))
            )
    assign_map = {}
    if assignments:
        for cid, v in assignments.items():
            assign_map[int(cid)] = f"{v['primitive']} / {v['behavior']}"
    result = {}
    for cid in cluster_ids:
        if cid in csv_map:
            result[cid] = f"Cluster {cid} — {csv_map[cid]}"
        elif cid in assign_map:
            result[cid] = f"Cluster {cid} — {assign_map[cid]}"
        else:
            result[cid] = f"Cluster {cid}"
    return result


@st.cache_data(show_spinner="Computing 2D UMAP layout (first load only)…")
def compute_umap_2d() -> pd.DataFrame | None:
    emb_path = EMBEDDINGS_DIR / "embeddings.npy"
    ids_path = EMBEDDINGS_DIR / "ids.npy"
    if not emb_path.exists() or not ids_path.exists():
        return None
    import umap

    emb = np.load(emb_path).astype("float32")
    ids = np.load(ids_path, allow_pickle=True).tolist()
    reducer = umap.UMAP(n_components=2, n_neighbors=15, min_dist=0.1, random_state=42)
    coords = reducer.fit_transform(emb)
    return pd.DataFrame({"id": ids, "x": coords[:, 0], "y": coords[:, 1]})


if "clusters_with_umap" not in st.session_state:
    coords_df = compute_umap_2d()
    st.session_state["clusters_with_umap"] = (
        clusters.merge(coords_df, on="id", how="left")
        if coords_df is not None
        else None
    )

df = st.session_state["clusters_with_umap"]
umap_available = df is not None and "x" in df.columns and df["x"].notna().any()

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown(
    '<div style="font-size:1.8rem; font-weight:800; color:#E2E8F0; '
    'margin-bottom:0.25rem;">🔍 Cluster Explorer</div>'
    '<div style="font-size:13px; color:#64748B; margin-bottom:1.5rem;">'
    "Select a cluster to explore its prompts, UMAP position, and attack breakdown."
    "</div>",
    unsafe_allow_html=True,
)

# ── Cluster selector ──────────────────────────────────────────────────────────
all_cluster_ids = sorted(c for c in clusters["cluster"].unique() if c != -1)
label_map = build_label_map(labels_df, assignments, all_cluster_ids)
options = [label_map[cid] for cid in all_cluster_ids]
option_to_id = {v: k for k, v in label_map.items()}

selected_option = st.selectbox("Select cluster", options=options, index=0)
selected_cluster_id = option_to_id[selected_option]

st.divider()

base_df = df if umap_available else clusters
cluster_df = base_df[
    (base_df["cluster"] == selected_cluster_id)
    & (base_df["source"].isin(selected_sources))
].copy()

this_assignment = (assignments or {}).get(selected_cluster_id, {})
this_primitive = this_assignment.get("primitive", "—")
this_behavior = this_assignment.get("behavior", "—")

# ── Cluster metadata KPIs ─────────────────────────────────────────────────────
m1, m2, m3, m4 = st.columns(4)
m1.metric("Cluster ID", selected_cluster_id)
m2.metric("Prompts (filtered)", len(cluster_df))
m3.metric("Primitive", this_primitive)
m4.metric("Behavior", this_behavior)

st.markdown("<br>", unsafe_allow_html=True)

# ── UMAP scatter ──────────────────────────────────────────────────────────────
if umap_available:
    section_header(
        "UMAP Embedding Space", "Orange = selected cluster · grey = everything else"
    )

    bg = base_df[base_df["cluster"] != -1]
    fg = cluster_df

    fig = go.Figure()

    # Background: all clusters, grey, no hover
    fig.add_trace(
        go.Scatter(
            x=bg["x"],
            y=bg["y"],
            mode="markers",
            marker=dict(size=3, color="#2E3250", opacity=0.6),
            name="Other clusters",
            hoverinfo="skip",
        )
    )

    # Foreground: selected cluster, pastel blue/orange highlight
    fig.add_trace(
        go.Scatter(
            x=fg["x"],
            y=fg["y"],
            mode="markers",
            marker=dict(
                size=9,
                color=PALETTE["amber"],
                opacity=0.95,
                line=dict(width=1, color="#0F1117"),
            ),
            name=selected_option,
            text=fg["source"].astype(str) + " · " + fg["prompt"].str[:120] + "…",
            hovertemplate="<b>%{text}</b><extra></extra>",
        )
    )

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#1A1D2E",
        height=420,
        margin=dict(t=10, b=10, l=0, r=0),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.01,
            xanchor="left",
            x=0,
            font=dict(color="#94A3B8", size=12),
            bgcolor="rgba(0,0,0,0)",
        ),
        xaxis=dict(
            showticklabels=False,
            title="UMAP-1",
            gridcolor="#2E3250",
            linecolor="#2E3250",
        ),
        yaxis=dict(
            showticklabels=False,
            title="UMAP-2",
            gridcolor="#2E3250",
            linecolor="#2E3250",
        ),
        font=dict(color="#E2E8F0"),
    )
    st.plotly_chart(fig, width="stretch")
    st.caption("2D UMAP compresses 384 dimensions — distances are approximate.")
else:
    st.warning("UMAP scatter unavailable — run `make embed` to generate embeddings.")

st.divider()

# ── Detail panel ──────────────────────────────────────────────────────────────
detail_left, detail_right = st.columns([3, 2])

with detail_left:
    n_max = max(3, len(cluster_df))
    n_show = (
        st.slider("Prompts to display", 3, min(30, n_max), min(10, n_max))
        if n_max > 3
        else n_max
    )
    section_header("Prompts", f"{len(cluster_df)} total · showing {n_show}")

    if cluster_df.empty:
        st.info("No prompts match the current source filter.")
    else:
        cards = ""
        for _, row in cluster_df.head(n_show).iterrows():
            cards += prompt_card(
                prompt=str(row.get("prompt", "")),
                source=str(row.get("source", "unknown")),
                category=str(row.get("attack_category", "") or ""),
                cluster_id=selected_cluster_id,
                primitive=this_primitive if this_primitive != "—" else None,
                behavior=this_behavior if this_behavior != "—" else None,
            )
        st.markdown(cards, unsafe_allow_html=True)

with detail_right:
    section_header("Attack Categories", "Distribution within this cluster")

    if (
        "attack_category" in cluster_df.columns
        and cluster_df["attack_category"].notna().any()
    ):
        cat_counts = cluster_df["attack_category"].dropna().value_counts().reset_index()
        cat_counts.columns = ["category", "count"]

        fig_cat = go.Figure(
            go.Bar(
                x=cat_counts["count"],
                y=cat_counts["category"],
                orientation="h",
                marker_color=PALETTE["purple"],
                marker_line_width=0,
                opacity=0.85,
            )
        )
        fig_cat.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="#1A1D2E",
            height=300,
            margin=dict(t=10, b=0, l=0, r=0),
            yaxis={"categoryorder": "total ascending"},
            showlegend=False,
            font=dict(color="#E2E8F0"),
            xaxis=dict(gridcolor="#2E3250"),
            yaxis2=dict(gridcolor="#2E3250"),
        )
        st.plotly_chart(fig_cat, width="stretch")
    else:
        st.info("No attack_category labels for this cluster.")

    section_header("Source Breakdown")
    src_counts = cluster_df["source"].value_counts().reset_index()
    src_counts.columns = ["source", "count"]
    st.dataframe(src_counts, width="stretch", hide_index=True)
