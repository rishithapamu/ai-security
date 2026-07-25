"""
filters.py — Shared styles, colours, and sidebar for the dashboard.
"""

import pandas as pd
import streamlit as st

PALETTE = {
    "blue": "#93C5FD",
    "green": "#86EFAC",
    "purple": "#C084FC",
    "amber": "#FCD34D",
    "red": "#FCA5A5",
    "teal": "#5EEAD4",
    "card": "#1E2130",
    "border": "#2E3250",
    "muted": "#64748B",
}

SOURCE_COLOURS: dict[str, str] = {
    "jailbreakbench": PALETTE["blue"],
    "advbench": PALETTE["purple"],
    "harmbench": PALETTE["red"],
    "donotanswer": PALETTE["green"],
    "inthewild": PALETTE["amber"],
}

GLOBAL_CSS = f"""
<style>
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

html, body, [class*="css"] {{
    font-family: 'Inter', 'Segoe UI', system-ui, sans-serif;
}}

/* FIX 1: increase top padding so page title isn't cut off by Streamlit's header bar */
.block-container {{
    padding-top: 2.5rem !important;
    padding-bottom: 3rem !important;
    max-width: 100% !important;
}}

/* FIX 4: section card — wraps each content section in a subtle container */
.section-card {{
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 20px 24px;
    margin-bottom: 16px;
}}

.prompt-card {{
    background: #16192A;
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
.section-header {{
    border-left: 3px solid var(--accent-blue);
    padding-left: 10px;
    margin-bottom: 1rem;
}}
.section-header h3 {{
    margin: 0;
    font-size: 1rem;
    color: var(--text);
    font-weight: 600;
}}
.section-header p {{
    margin: 2px 0 0 0;
    font-size: 12px;
    color: var(--muted);
}}

[data-testid="metric-container"] {{
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 14px 18px;
}}
[data-testid="stMetricLabel"] {{
    font-size: 11px !important;
    color: var(--text-dim) !important;
    text-transform: uppercase;
    letter-spacing: 0.06em;
}}
[data-testid="stMetricValue"] {{
    font-size: 1.5rem !important;
    font-weight: 700 !important;
    color: var(--text) !important;
}}

a, a:visited {{ color: var(--accent-blue); text-decoration: none; }}
a:hover      {{ color: var(--accent-purple); text-decoration: underline; }}

[data-testid="stSidebar"] {{ border-right: 1px solid var(--border); }}

hr {{ border-color: var(--border) !important; margin: 1.2rem 0 !important; }}

::-webkit-scrollbar       {{ width: 5px; height: 5px; }}
::-webkit-scrollbar-track {{ background: transparent; }}
::-webkit-scrollbar-thumb {{ background: var(--border); border-radius: 3px; }}

[data-testid="stAlert"] {{ border-radius: 8px; border-left-width: 3px; }}
</style>
"""


def inject_styles() -> None:
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)


def badge(text: str, colour: str = "grey") -> str:
    return f'<span class="badge badge-{colour}">{text}</span>'


def source_badge(source: str) -> str:
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
    prompt_escaped = (
        prompt.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    )

    rank_html = ""
    if rank is not None and score is not None:
        bar_colour = (
            "#86EFAC" if score >= 0.85 else "#FCD34D" if score >= 0.70 else "#64748B"
        )
        rank_html = f""" <div style="display:flex;
            align-items:center; gap:10px;margin-bottom:8px;">
            <span style="background:#16192A;border:1px solid #2E3250;color:#E2E8F0;
                         width:26px;height:26px;border-radius:50%;display:inline-flex;
                         align-items:center;justify-content:center;font-size:11px;
                         font-weight:700;flex-shrink:0;">#{rank}</span>
            <div style="flex:1;">
                <div style="height:4px;
                    background:#2E3250;
                    border-radius:2px;
                    overflow:hidden;">
                    <div style="height:100%;
                    width:{score * 100:.1f}%;
                    background:{bar_colour};
                    border-radius:2px;"></div>
                </div>
                <span style="font-size:10px;
                    color:#64748B;">similarity {score:.4f}</span>
            </div>
        </div>"""

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

    return f""" <div class="prompt-card">
    {rank_html}
    <div class="badge-row">{badges}</div>
    <div class="prompt-text">{prompt_escaped}</div>
    </div>"""


def section_header(title: str, subtitle: str = "") -> None:
    sub_html = f"<p>{subtitle}</p>" if subtitle else ""
    st.markdown(
        f'<div class="section-header"><h3>{title}</h3>{sub_html}</div>',
        unsafe_allow_html=True,
    )


def section_card_start() -> None:
    """Open a section card div. Must be paired with section_card_end()."""
    st.markdown('<div class="section-card">', unsafe_allow_html=True)


def section_card_end() -> None:
    """Close a section card div."""
    st.markdown("</div>", unsafe_allow_html=True)


def render_sidebar(clusters: pd.DataFrame | None) -> list[str]:
    """
    Render sidebar with source filter and external links only.

    FIX 2: removed the custom nav card links — they used <a href="..."> which
    triggers a full page reload and breaks session_state. Streamlit already
    generates working navigation from the pages/ directory automatically.
    The sidebar should only contain things Streamlit can't do itself:
    the source filter and external resource links.
    """
    with st.sidebar:
        st.markdown(
            """
            <div style="padding:8px 0 16px 0;">
                <div style="font-size:19px;font-weight:800;color:#93C5FD;
                            letter-spacing:-0.5px;">🔐 AI Sec Workbench</div>
                <div style="font-size:11px;color:#64748B;margin-top:2px;">
                    Adversarial prompt analysis
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("---")

        # Source filter
        if clusters is not None:
            st.markdown(
                '<div style="font-size:11px;font-weight:700;color:#64748B;'
                "text-transform:uppercase;letter-spacing:0.08em;"
                'margin-bottom:6px;">Source Filter</div>',
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
                    f'<div style="font-size:12px;color:#94A3B8;margin:3px 0;">'
                    f'<span style="color:{c};">{dot}</span> {src}</div>'
                )
            st.markdown(legend_html, unsafe_allow_html=True)
        else:
            selected = []

        st.markdown("---")

        # External links only — no internal nav links
        st.markdown(
            """
            <div style="font-size:11px;font-weight:700;color:#64748B;
                        text-transform:uppercase;letter-spacing:0.08em;
                        margin-bottom:8px;">Datasets</div>
            <div style="font-size:13px;line-height:2.1;">
                <a
                    href="https://github.com/rishithapamu/ai-security"
                    target="_blank"
                >📁 GitHub repo</a><br>

                <a
                    href="https://huggingface.co/datasets/JailbreakBench/JBB-Behaviors"
                    target="_blank"
                >🤗 JailbreakBench</a><br>

                <a
                    href="https://huggingface.co/datasets/AlignmentResearch/AdvBench"
                    target="_blank"
                >🤗 AdvBench</a><br >

                <a
                    href="https://huggingface.co/datasets/swiss-ai/harmbench"
                    target="_blank"
                >🤗 HarmBench</a><br>

                <a
                    href="https://huggingface.co/datasets/LibrAI/do-not-answer"
                    target="_blank"
                >🤗 DoNotAnswer</a><br>

                <a
                    href="https://huggingface.co/datasets/TrustAIRLab/in-the-wild-jailbreak-prompts"
                    target="_blank"
                >🤗 InTheWild</a>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("---")
        st.markdown(
            '<div style="font-size:11px;color:#475569;text-align:center;">'
            "ai-sec-workbench · Week 8</div>",
            unsafe_allow_html=True,
        )

    return selected if clusters is not None else []
