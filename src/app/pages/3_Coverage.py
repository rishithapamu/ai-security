"""
3_Coverage.py — Coverage Analysis page.
"""

import json
from collections import defaultdict

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.app.filters import (
    PALETTE,
    inject_styles,
    prompt_card,
    render_sidebar,
    section_header,
)

st.set_page_config(page_title="Coverage Analysis", layout="wide")
inject_styles()

if "data_loaded" not in st.session_state:
    st.warning("Please navigate to the home page first.")
    st.stop()

assignments = st.session_state["assignments"]
clusters = st.session_state["clusters"]

if assignments is None:
    st.error("`cluster_assignments.yaml` not found.")
    st.stop()

selected_sources = render_sidebar(clusters)


@st.cache_data
def build_matrix(assignments_json: str) -> pd.DataFrame:
    d = json.loads(assignments_json)
    counts = defaultdict(lambda: defaultdict(int))
    for v in d.values():
        counts[v["primitive"]][v["behavior"]] += 1
    df = pd.DataFrame(counts).T.fillna(0).astype(int)
    return df.sort_index().sort_index(axis=1)


matrix = build_matrix(json.dumps({str(k): v for k, v in assignments.items()}))

pair_to_clusters: dict[tuple[str, str], list[int]] = defaultdict(list)
for cid, v in assignments.items():
    pair_to_clusters[(v["primitive"], v["behavior"])].append(int(cid))

flat = matrix.stack()
total_cells = len(flat)
covered = int((flat > 0).sum())
zero_cells = int((flat == 0).sum())

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown(
    '<div style="font-size:1.8rem; font-weight:800; color:#E2E8F0; '
    'margin-bottom:0.25rem;">📊 Coverage Analysis</div>'
    '<div style="font-size:13px; color:#64748B; margin-bottom:1.5rem;">'
    "Primitive × Behavior matrix — which attack-technique / harm-objective "
    "combinations exist in the dataset, and which are blind spots."
    "</div>",
    unsafe_allow_html=True,
)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Primitives", len(matrix))
c2.metric("Behaviors", len(matrix.columns))
c3.metric(
    "Covered Cells",
    f"{covered}/{total_cells}",
    f"{round(covered / total_cells * 100, 1)}%",
)
c4.metric("Gap Cells (zeros)", zero_cells)

st.markdown("<br>", unsafe_allow_html=True)
section_header(
    "Primitive × Behavior Heatmap",
    "Click any cell to drill into its prompts · white = zero clusters = blind spot",
)

# ── Heatmap ───────────────────────────────────────────────────────────────────
# Custom colorscale: dark background for zeros, pastel blue for coverage
# This integrates with the dark theme — a standard "Blues" scale has a
# white zero which looks jarring on a dark page.
colorscale = [
    [0.0, "#1A1D2E"],  # zero cells — same as card background (near invisible)
    [0.01, "#1E3A5F"],  # low coverage — dark blue
    [0.5, "#2563EB"],  # medium — mid blue
    [1.0, "#93C5FD"],  # high — pastel blue
]

fig = px.imshow(
    matrix,
    labels=dict(x="Behavior", y="Primitive", color="Clusters"),
    color_continuous_scale=colorscale,
    text_auto=True,
    aspect="auto",
    zmin=0,
)
fig.update_xaxes(tickangle=40, side="bottom", tickfont=dict(size=11, color="#94A3B8"))
fig.update_yaxes(tickfont=dict(size=11, color="#94A3B8"))
fig.update_traces(
    textfont=dict(color="#E2E8F0", size=12),
    # Cells with value 0 get lighter text so "0" is readable on dark bg
)
# ── Heatmap ───────────────────────────────────────────────────────────────────
# Custom colorscale: dark background for zeros, pastel blue for coverage
# This integrates with the dark theme — a standard "Blues" scale has a
# white zero which looks jarring on a dark page.
colorscale = [
    [0.0, "#1A1D2E"],  # zero cells — same as card background (near invisible)
    [0.01, "#1E3A5F"],  # low coverage — dark blue
    [0.5, "#2563EB"],  # medium — mid blue
    [1.0, "#93C5FD"],  # high — pastel blue
]

FIG_WIDTH = 1100
FIG_HEIGHT = max(440, len(matrix) * 54)
MARGIN = dict(l=260, b=200, t=20, r=40)

fig = px.imshow(
    matrix,
    labels=dict(x="Behavior", y="Primitive", color="Clusters"),
    color_continuous_scale=colorscale,
    text_auto=True,
    aspect="auto",
    zmin=0,
)
fig.update_xaxes(tickangle=40, side="bottom", tickfont=dict(size=11, color="#94A3B8"))
fig.update_yaxes(tickfont=dict(size=11, color="#94A3B8"))
fig.update_traces(
    textfont=dict(color="#E2E8F0", size=12),
    # Cells with value 0 get lighter text so "0" is readable on dark bg
)

# NOTE: st.plotly_chart's native on_select="rerun" never fires for Heatmap /
# px.imshow traces — Plotly only emits its "selected" event (which Streamlit's
# on_select listens for) on scatter-like traces, and Heatmap isn't one of them.
# streamlit-plotly-events was tried as a fix but bundles an old plotly.js that
# breaks the custom colorscale, text_auto counts, and category axis labels.
#
# Fix: keep the heatmap trace exactly as-is for visuals, and add a fully
# transparent Scatter trace on top with one marker per grid cell. Scatter *is*
# a selectable trace type, so clicks land on this invisible layer and native
# on_select="rerun" + event.selection.points works correctly.
behaviors_grid = [b for _p in matrix.index for b in matrix.columns]
primitives_grid = [p for p in matrix.index for _b in matrix.columns]

inner_width = FIG_WIDTH - MARGIN["l"] - MARGIN["r"]
inner_height = FIG_HEIGHT - MARGIN["t"] - MARGIN["b"]
marker_size = max(
    8, min(inner_width / len(matrix.columns), inner_height / len(matrix.index)) * 0.92
)

fig.add_trace(
    go.Scatter(
        x=behaviors_grid,
        y=primitives_grid,
        mode="markers",
        marker=dict(size=marker_size, symbol="square", opacity=0),
        showlegend=False,
        hoverinfo="skip",
        name="click_layer",
    )
)

fig.update_layout(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="#1A1D2E",
    width=FIG_WIDTH,
    height=FIG_HEIGHT,
    margin=MARGIN,
    coloraxis_showscale=False,
    font=dict(color="#E2E8F0", family="Inter, sans-serif"),
)

event = st.plotly_chart(
    fig,
    on_select="rerun",
    key="coverage_heatmap",
)

if event is not None:
    points = event.selection.points
    if points:
        point = points[0]
        primitive = point["y"]
        behavior = point["x"]
        st.session_state["coverage_selection"] = (
            primitive,
            behavior,
        )
# ── Drill-down ────────────────────────────────────────────────────────────────
st.divider()
selection: tuple[str, str] | None = st.session_state.get("coverage_selection")

if selection:
    sel_primitive, sel_behavior = selection
    sel_count = (
        int(matrix.loc[sel_primitive, sel_behavior])
        if (sel_primitive in matrix.index and sel_behavior in matrix.columns)
        else 0
    )

    col_a, col_b = st.columns([4, 1])
    with col_a:
        section_header(
            f"{sel_primitive}  ×  {sel_behavior}",
            f"{sel_count} cluster(s) map to this cell",
        )
    with col_b:
        if st.button("✕ Clear", type="secondary"):
            del st.session_state["coverage_selection"]
            st.rerun()

    if sel_count == 0:
        st.markdown(
            f"""
            <div style="background:#1E2130; border:1px solid #2E3250;
                        border-left:3px solid {PALETTE["red"]};
                        border-radius:8px; padding:16px 20px; margin:8px 0;">
                <div style="font-size:14px; font-weight:700; color:{PALETTE["red"]};
                            margin-bottom:6px;">⚠ Gap Cell — No Coverage</div>
                <div style="font-size:13px; color:#94A3B8; line-height:1.65;">
                    No cluster in the dataset maps to
                    <span style="color:{PALETTE["purple"]};
                    font-weight:600;">{sel_primitive}</span>
                    ×
                    <span style="color:{PALETTE["green"]};
                    font-weight:600;">{sel_behavior}</span>.
                    A model trained on this corpus has no examples
                    of this attack pattern —
                    it is a genuine blind spot in the research dataset.
                </div>
                <div style="font-size:12px; color:#64748B; margin-top:10px;">
                    <strong style="color:#94A3B8;">Augmentation candidate:</strong>
                    Prompts using <em>{sel_primitive}</em> technique to achieve
                    <em>{sel_behavior}</em> outcomes would fill this gap.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        cluster_ids = pair_to_clusters.get((sel_primitive, sel_behavior), [])

        if clusters is not None:
            cell_df = clusters[
                clusters["cluster"].isin(cluster_ids)
                & clusters["source"].isin(selected_sources)
            ].copy()

            m1, m2, m3 = st.columns(3)
            m1.metric("Prompts (filtered)", len(cell_df))
            m2.metric("Cluster IDs", ", ".join(str(c) for c in sorted(cluster_ids)))
            m3.metric("Sources", cell_df["source"].nunique())

            if not cell_df.empty:
                # Per-cluster summary
                cluster_summary = (
                    cell_df.groupby("cluster")
                    .agg(
                        prompts=("prompt", "count"),
                        sources=("source", lambda x: ", ".join(sorted(x.unique()))),
                        top_category=(
                            "attack_category",
                            lambda x: (
                                x.dropna().mode().iloc[0] if x.dropna().any() else "—"
                            ),
                        ),
                    )
                    .reset_index()
                )
                st.dataframe(cluster_summary, width="stretch", hide_index=True)

                section_header(
                    "Prompts", f"Showing {min(20, len(cell_df))} of {len(cell_df)}"
                )
                cards = ""
                for _, row in cell_df.head(20).iterrows():
                    cards += prompt_card(
                        prompt=str(row.get("prompt", "")),
                        source=str(row.get("source", "unknown")),
                        category=str(row.get("attack_category", "") or ""),
                        cluster_id=int(row.get("cluster", -1)),
                        primitive=sel_primitive,
                        behavior=sel_behavior,
                    )
                st.markdown(cards, unsafe_allow_html=True)
            else:
                st.info("No prompts match the current source filter.")
else:
    st.markdown(
        """
        <div style="background:#1A1D2E; border:1px solid #2E3250;
                    border-radius:8px; padding:20px; text-align:center;
                    color:#64748B; font-size:13px;">
            👆 Click any cell in the heatmap above to explore its prompts
        </div>
        """,
        unsafe_allow_html=True,
    )

# ── Gap table ─────────────────────────────────────────────────────────────────
st.divider()
section_header(
    "Gap Analysis", f"{zero_cells} primitive × behavior combinations with zero coverage"
)

gaps = [{"primitive": p, "behavior": b} for (p, b), v in flat.items() if v == 0]
if gaps:
    st.dataframe(
        pd.DataFrame(gaps).sort_values(["primitive", "behavior"]),
        width="stretch",
        hide_index=True,
        height=320,
    )
else:
    st.success("No gaps — all cells have at least one cluster.")
