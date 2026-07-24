"""
filters.py — Shared styles, colours, and sidebar for the dashboard.

The CSS defined in GLOBAL_CSS is injected on every page via inject_styles().
It defines:
  - CSS custom properties (variables) for the colour palette
  - Card component styles
  - Badge styles
  - Hyperlink styles
  - Metric box overrides to match the dark theme
  - Scrollbar styling

Why CSS variables?
    Defined once at :root, usable everywhere as var(--name).
    Change a colour in one place, it updates across all components.
    Without variables you'd have the same hex code repeated 40 times.
"""

import pandas as pd
import streamlit as st

# ─────────────────────────────────────────────────────────────────────────────
# Colour palette
# Used both in CSS variables and in Python (for plotly traces, badges)
# Defining them in Python means a single source of truth — the CSS reads from
# the variables, the Python code reads from this dict.
# ─────────────────────────────────────────────────────────────────────────────
PALETTE = {
    "blue": "#93C5FD",  # pastel blue
    "green": "#86EFAC",  # pastel green
    "purple": "#C084FC",  # pastel purple
    "amber": "#FCD34D",  # pastel amber
    "red": "#FCA5A5",  # pastel red
    "teal": "#5EEAD4",  # pastel teal
    "card": "#1E2130",  # card background
    "border": "#2E3250",  # card border
    "muted": "#64748B",  # muted/secondary text
}

SOURCE_COLOURS: dict[str, str] = {
    "jailbreakbench": PALETTE["blue"],
    "advbench": PALETTE["purple"],
    "harmbench": PALETTE["red"],
    "donotanswer": PALETTE["green"],
    "inthewild": PALETTE["amber"],
}

# ─────────────────────────────────────────────────────────────────────────────
# Global CSS
# Injected once per page via inject_styles().
# Uses :root variables so colours are defined once and referenced everywhere.
# ─────────────────────────────────────────────────────────────────────────────
GLOBAL_CSS = f"""
<style>
/* ── Colour variables ───────────────────────────────────────────── */
:root {{
    --accent-blue:   {PALETTE["blue"]};
    --accent-green:  {PALETTE["green"]};
    --accent-purple: {PALETTE["purple"]};
    --accent-amber:  {PALETTE["amber"]};
    --accent-red:    {PALETTE["red"]};
    --accent-teal:   {PALETTE["teal"]};
    --card-bg:       {PALETTE["card"]};
    --border:        {PALETTE["border"]};
    --muted:         {PALETTE["muted"]};
    --text:          #E2E8F0;
    --text-dim:      #94A3B8;
}}

/* ── Page-level typography ──────────────────────────────────────── */
html, body, [class*="css"] {{
    font-family: 'Inter', 'Segoe UI', system-ui, sans-serif;
}}

/* ── Remove Streamlit's default top padding ─────────────────────── */
.block-container {{
    padding-top: 1.5rem !important;
    padding-bottom: 2rem !important;
}}

/* ── Prompt card ────────────────────────────────────────────────── */
/* Used on Clusters, Coverage, and Search pages */
.prompt-card {{
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-left: 3px solid var(--accent-blue);
    border-radius: 8px;
    padding: 14px 16px;
    margin-bottom: 10px;
    font-family: inherit;
    transition: border-left-color 0.15s ease;
}}
.prompt-card:hover {{
    border-left-color: var(--accent-purple);
}}
.prompt-card .prompt-text {{
    font-size: 13.5px;
    line-height: 1.65;
    color: var(--text);
    white-space: pre-wrap;
    word-break: break-word;
    margin-top: 8px;
}}
.prompt-card .badge-row {{
    display: flex;
    flex-wrap: wrap;
    gap: 5px;
    margin-bottom: 4px;
}}

/* ── Badges ─────────────────────────────────────────────────────── */
.badge {{
    display: inline-block;
    padding: 2px 9px;
    border-radius: 20px;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.02em;
}}
.badge-blue {{
    background: rgba(147,197,253,0.15);
    color: var(--accent-blue);
    border: 1px solid rgba(147,197,253,0.3);
}}
.badge-green {{
    background: rgba(134,239,172,0.15);
    color: var(--accent-green);
    border: 1px solid rgba(134,239,172,0.3);
}}
.badge-purple {{
    background: rgba(192,132,252,0.15);
    color: var(--accent-purple);
    border: 1px solid rgba(192,132,252,0.3);
}}
.badge-amber {{
    background: rgba(252,211,77,0.15);
    color: var(--accent-amber);
    border: 1px solid rgba(252,211,77,0.3);
}}
.badge-red {{
    background: rgba(252,165,165,0.15);
    color: var(--accent-red);
    border: 1px solid rgba(252,165,165,0.3);
}}
.badge-teal {{
    background: rgba(94,234,212,0.15);
    color: var(--accent-teal);
    border: 1px solid rgba(94,234,212,0.3);
}}
.badge-grey {{
    background: rgba(100,116,139,0.15);
    color: var(--text-dim);
    border: 1px solid rgba(100,116,139,0.3);
}}
/* ── Section header with accent bar ─────────────────────────────── */
.section-header {{
    border-left: 3px solid var(--accent-blue);
    padding-left: 10px;
    margin-bottom: 1rem;
    margin-top: 0.5rem;
}}
.section-header h3 {{
    margin: 0;
    font-size: 1.1rem;
    color: var(--text);
    font-weight: 600;
}}
.section-header p {{
    margin: 2px 0 0 0;
    font-size: 12px;
    color: var(--muted);
}}

/* ── KPI metric cards ───────────────────────────────────────────── */
/* Overrides Streamlit's default metric to match dark theme */
[data-testid="metric-container"] {{
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 14px 18px;
}}
[data-testid="stMetricLabel"] {{
    font-size: 12px !important;
    color: var(--text-dim) !important;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}}
[data-testid="stMetricValue"] {{
    font-size: 1.6rem !important;
    font-weight: 700 !important;
    color: var(--text) !important;
}}
[data-testid="stMetricDelta"] {{
    font-size: 12px !important;
}}

/* ── Hyperlinks ──────────────────────────────────────────────────── */
a, a:visited {{
    color: var(--accent-blue);
    text-decoration: none;
}}
a:hover {{
    color: var(--accent-purple);
    text-decoration: underline;
}}

/* ── Sidebar ─────────────────────────────────────────────────────── */
[data-testid="stSidebar"] {{
    border-right: 1px solid var(--border);
}}
[data-testid="stSidebar"] .stMarkdown a {{
    color: var(--accent-blue);
}}

/* ── Divider ─────────────────────────────────────────────────────── */
hr {{
    border-color: var(--border) !important;
    margin: 1rem 0 !important;
}}

/* ── Scrollbar (webkit) ──────────────────────────────────────────── */
::-webkit-scrollbar {{ width: 6px; height: 6px; }}
::-webkit-scrollbar-track {{ background: transparent; }}
::-webkit-scrollbar-thumb {{ background: var(--border); border-radius: 3px; }}
::-webkit-scrollbar-thumb:hover {{ background: var(--muted); }}

/* ── Info / warning / error boxes ───────────────────────────────── */
[data-testid="stAlert"] {{
    border-radius: 8px;
    border-left-width: 3px;
}}

/* ── Navigation link cards ───────────────────────────────────────── */
.nav-card {{
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 16px 18px;
    margin-bottom: 8px;
    transition: border-color 0.15s, background 0.15s;
}}
.nav-card:hover {{
    border-color: var(--accent-blue);
    background: rgba(147,197,253,0.05);
}}
.nav-card a {{
    font-size: 15px;
    font-weight: 600;
    color: var(--accent-blue) !important;
    text-decoration: none !important;
}}
.nav-card .nav-desc {{
    font-size: 12px;
    color: var(--muted);
    margin-top: 3px;
}}
</style>
"""


def inject_styles() -> None:
    """
    Inject global CSS into the page.

    Call this at the top of every page, after set_page_config.
    Streamlit renders st.markdown output directly into the page HTML —
    the <style> block gets picked up by the browser's CSS engine and
    applies to everything on the page.

    WHY NOT PUT THIS IN config.toml?
        config.toml only controls Streamlit's built-in theme variables
        (colours, font). It cannot define custom CSS classes, component
        overrides, or animations. For those you need injected CSS.
    """
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)


def badge(text: str, colour: str = "grey") -> str:
    """
    Return an HTML badge string.

    colour must be one of: blue, green, purple, amber, red, teal, grey
    Use this in any f-string that builds HTML cards.

    Example:
        html = ( f'<div>{badge("jailbreakbench", "blue")} '
        f'{badge("roleplay_jailbreak", "purple")}</div>'
        )
    """
    return f'<span class="badge badge-{colour}">{text}</span>'


def source_badge(source: str) -> str:
    """Return a coloured badge for a dataset source name."""
    colour_map = {
        "jailbreakbench": "blue",
        "advbench": "purple",
        "harmbench": "red",
        "donotanswer": "green",
        "inthewild": "amber",
    }
    return badge(source, colour_map.get(source, "grey"))


def prompt_card(
    prompt: str,
    source: str,
    category: str | None = None,
    cluster_id: int | None = None,
    primitive: str | None = None,
    behavior: str | None = None,
    rank: int | None = None,
    score: float | None = None,
) -> str:
    """
    Build an HTML prompt card string.

    Returns raw HTML — pass to st.markdown(..., unsafe_allow_html=True).

    All arguments except prompt and source are optional — the card renders
    only the badges it has data for, so it works on all three pages
    (Clusters, Coverage, Search) without modification.
    """
    prompt_escaped = (
        prompt.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    )

    # Rank + score bar (Search page only)
    rank_html = ""
    if rank is not None and score is not None:
        bar_colour = (
            "#86EFAC" if score >= 0.85 else "#FCD34D" if score >= 0.70 else "#64748B"
        )
        rank_html = f"""
        <div style="display:flex; align-items:center; gap:10px; margin-bottom:8px;">
            <span style="
                background:#1E2130; border:1px solid #2E3250;
                color:#E2E8F0; width:26px; height:26px;
                border-radius:50%; display:inline-flex; align-items:center;
                justify-content:center; font-size:11px; font-weight:700;
                flex-shrink:0;">#{rank}</span>
            <div style="flex:1;">
                <div
                    style="
                        height:4px;
                        background:#2E3250;
                        border-radius:2px;
                        overflow:hidden;">
                    <div
                        style="
                            height:100%;
                            width:{score * 100:.1f}%;
                            background:{bar_colour};
                            border-radius:2px; "
                    ></div>
                </div>
                <span style="font-size:10px; color:#64748B;">
                similarity {score:.4f}
                </span>
            </div>
        </div>"""

    # Badge row
    badges = source_badge(source)
    if category:
        badges += f" {badge(category, 'grey')}"
    if cluster_id is not None and cluster_id != -1:
        badges += f" {badge(f'cluster {cluster_id}', 'teal')}"
    elif cluster_id == -1:
        badges += f" {badge('noise', 'grey')}"
    if primitive:
        badges += f" {badge(primitive, 'purple')}"
    if behavior:
        badges += f" {badge(behavior, 'green')}"

    return f"""
    <div class="prompt-card">
        {rank_html}
        <div class="badge-row">{badges}</div>
        <div class="prompt-text">{prompt_escaped}</div>
    </div>"""


def section_header(title: str, subtitle: str = "") -> None:
    """Render a section header with a left accent bar."""
    sub_html = f"<p>{subtitle}</p>" if subtitle else ""
    st.markdown(
        f'<div class="section-header"><h3>{title}</h3>{sub_html}</div>',
        unsafe_allow_html=True,
    )


def render_sidebar(clusters: pd.DataFrame | None) -> list[str]:
    """
    Render the global sidebar with source filter and navigation links.

    The key= parameter on st.multiselect ties the widget to
    session_state["global_sources"] automatically. Changing the selection
    on any page updates the shared key, so all pages see the same filter.
    """
    with st.sidebar:
        st.markdown(
            """
            <div style="padding: 8px 0 16px 0;">
                <div style="font-size:20px; font-weight:800; color:#93C5FD;
                            letter-spacing:-0.5px;">🔐 AI Sec Workbench</div>
                <div style="font-size:11px; color:#64748B; margin-top:2px;">
                    Adversarial prompt analysis
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("---")

        # ── Navigation links ─────────────────────────────────────────
        # Streamlit's multi-page navigation happens via the pages/ directory.
        # We can't programmatically navigate — but we can show styled links
        # that match Streamlit's own sidebar page links, giving users a
        # visual map of what's available and what each page does.
        st.markdown(
            """
            <div style="font-size:11px; font-weight:700; color:#64748B;
                        text-transform:uppercase; letter-spacing:0.08em;
                        margin-bottom:8px;">Navigation</div>

            <div class="nav-card">
                <a href="/" target="_self">🏠 Overview</a>
                <div class="nav-desc">Corpus stats, source breakdown</div>
            </div>
            <div class="nav-card">
                <a href="/2_Clusters" target="_self">🔍 Cluster Explorer</a>
                <div class="nav-desc">Browse clusters, read prompts</div>
            </div>
            <div class="nav-card">
                <a href="/3_Coverage" target="_self">📊 Coverage Analysis</a>
                <div class="nav-desc">Primitive × behavior heatmap</div>
            </div>
            <div class="nav-card">
                <a href="/4_Search" target="_self">🔎 Semantic Search</a>
                <div class="nav-desc">FAISS similarity search</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("---")

        # ── Source filter ─────────────────────────────────────────────
        if clusters is not None:
            st.markdown(
                '<div style="font-size:11px; font-weight:700; color:#64748B; '
                "text-transform:uppercase; letter-spacing:0.08em; "
                'margin-bottom:6px;">Source filter</div>',
                unsafe_allow_html=True,
            )
            all_sources = sorted(clusters["source"].unique().tolist())
            current = st.session_state.get("global_sources", all_sources)
            selected = st.multiselect(
                "Sources",
                options=all_sources,
                default=current,
                key="global_sources",
                label_visibility="collapsed",
            )

            # Source legend with colour dots
            colour_map = {
                "jailbreakbench": "#93C5FD",
                "advbench": "#C084FC",
                "harmbench": "#FCA5A5",
                "donotanswer": "#86EFAC",
                "inthewild": "#FCD34D",
            }
            legend_html = ""
            for src in all_sources:
                c = colour_map.get(src, "#64748B")
                dot = "●" if src in selected else "○"
                legend_html += (
                    f'<div style="font-size:12px; color:#94A3B8; '
                    f'margin:2px 0;">'
                    f'<span style="color:{c};">{dot}</span> {src}</div>'
                )
            st.markdown(legend_html, unsafe_allow_html=True)
        else:
            selected = []

        st.markdown("---")

        # ── External links ────────────────────────────────────────────
        st.markdown(
            """
            <div style="font-size:11px; font-weight:700; color:#64748B;
                        text-transform:uppercase; letter-spacing:0.08em;
                        margin-bottom:8px;">Resources</div>

            <div style="font-size:13px; line-height:2;">
                <a href="https://github.com/rishithapamu/ai-security"
                   target="_blank">
                    📁 GitHub repo
                </a><br>
                <a href="https://huggingface.co/datasets/JailbreakBench/JBB-Behaviors"
                   target="_blank">
                    🤗 JailbreakBench
                </a><br>
                <a href="https://huggingface.co/datasets/AlignmentResearch/AdvBench"
                   target="_blank">
                    🤗 AdvBench
                </a><br>
                <a href="https://huggingface.co/datasets/swiss-ai/harmbench"
                   target="_blank">
                    🤗 HarmBench
                </a><br>
                <a href="https://huggingface.co/datasets/LibrAI/do-not-answer"
                   target="_blank">
                    🤗 DoNotAnswer
                </a><br>
                <a href="https://huggingface.co/datasets/TrustAIRLab/in-the-wild-jailbreak-prompts"
                   target="_blank">
                    🤗 InTheWild
                </a>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("---")
        st.markdown(
            '<div style="font-size:11px; color:#475569; text-align:center;">'
            "ai-sec-workbench · Week 8</div>",
            unsafe_allow_html=True,
        )

    return selected if clusters is not None else []
