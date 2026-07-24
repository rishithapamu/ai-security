"""1_Overview.py — Named sidebar entry for the home page."""

import streamlit as st

from src.app.filters import render_sidebar

st.set_page_config(page_title="Overview", layout="wide")

if "data_loaded" not in st.session_state:
    st.warning("Please start from the home page.")
    st.stop()

clusters = st.session_state["clusters"]
assignments = st.session_state["assignments"]
render_sidebar(clusters)

st.title("🔐 AI Security Workbench — Overview")
st.markdown("Use the sidebar to navigate. This page also accessible via the home URL.")

if clusters is None:
    st.error("Cluster data not available.")
    st.stop()

st.divider()

n_total = len(clusters)
n_noise = (clusters["cluster"] == -1).sum()
n_clustered = n_total - n_noise
n_clusters = clusters["cluster"].nunique() - (
    1 if -1 in clusters["cluster"].values else 0
)
n_sources = clusters["source"].nunique()

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Total Prompts", f"{n_total:,}")
c2.metric("Clusters", n_clusters)
c3.metric("Clustered", f"{n_clustered:,}")
c4.metric("Noise Points", f"{(clusters['cluster'] == -1).sum():,}")
c5.metric("Sources", n_sources)

st.divider()
st.subheader("Datasets")
st.markdown("""
| Dataset | Focus | Notes |
|---------|-------|-------|
| **jailbreakbench** | Academic benchmark | Includes benign prompts |
| **advbench** | Harmful behaviors | Overlaps with jailbreakbench |
| **harmbench** | Multi-method attacks | Richest label schema |
| **donotanswer** | Response labeling | Labels both prompt and expected response |
| **inthewild** | Real-world jailbreaks | Noisiest; proven to work against real models |
""")
