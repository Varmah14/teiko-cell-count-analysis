"""
Interactive dashboard for Bob's cell-count analysis (Parts 2-4).

Run:
    streamlit run dashboard/app.py
"""
import sys
from pathlib import Path

import pandas as pd
import streamlit as st
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from analysis.db import get_connection
from analysis.part2_frequencies import compute_frequencies
from analysis.part3_stats import POPULATIONS, get_melanoma_miraclib_pbmc_frequencies, run_stats
from analysis.part4_subset import BASELINE_QUERY

st.set_page_config(page_title="Teiko Cell Count Dashboard", layout="wide")


@st.cache_resource
def _connection():
    return get_connection()


@st.cache_data
def load_frequencies():
    return compute_frequencies(_connection())


@st.cache_data
def load_part3_subset():
    return get_melanoma_miraclib_pbmc_frequencies(_connection())


@st.cache_data
def load_baseline():
    return pd.read_sql_query(BASELINE_QUERY, _connection())


st.title("Teiko Bio — Cell Population Dashboard")
st.caption("Data: cell-count.csv | DB: cell_counts.db")

tab2, tab3, tab4 = st.tabs(
    ["Part 2 — Frequencies", "Part 3 — Responder vs Non-responder", "Part 4 — Subset Analysis"]
)

# ---------------------------------------------------------------- Part 2 ----
with tab2:
    st.header("Relative frequency of each cell population per sample")
    freq = load_frequencies()

    samples = sorted(freq["sample"].unique())
    populations = sorted(freq["population"].unique())
    col1, col2 = st.columns(2)
    sel_samples = col1.multiselect("Filter by sample", samples)
    sel_pops = col2.multiselect("Filter by population", populations)

    view = freq.copy()
    if sel_samples:
        view = view[view["sample"].isin(sel_samples)]
    if sel_pops:
        view = view[view["population"].isin(sel_pops)]

    st.dataframe(view, use_container_width=True, height=420)
    st.download_button(
        "Download full frequency table (CSV)",
        freq.to_csv(index=False),
        file_name="frequencies.csv",
    )

# ---------------------------------------------------------------- Part 3 ----
with tab3:
    st.header("Melanoma, miraclib, PBMC: responders vs non-responders")
    subset = load_part3_subset()
    stats_df = run_stats(subset)

    st.subheader("Boxplots by population")
    pop_choice = st.selectbox("Population", POPULATIONS, index=0)
    data = subset[subset["population"] == pop_choice]

    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(5, 5))
    groups = [
        data[data["response"] == "yes"]["percentage"],
        data[data["response"] == "no"]["percentage"],
    ]
    ax.boxplot(groups, tick_labels=["responder", "non-responder"], showmeans=True)
    ax.set_ylabel("relative frequency (%)")
    ax.set_title(pop_choice)
    st.pyplot(fig)

    st.subheader("All populations")
    st.image(str(Path(__file__).resolve().parent.parent / "output" / "responder_vs_nonresponder_boxplot.png"))

    st.subheader("Statistical test results (Mann-Whitney U)")
    st.dataframe(stats_df, use_container_width=True)

    sig = stats_df[stats_df["significant_p<0.05"]]
    if len(sig):
        st.success(f"Significant difference (p < 0.05): {', '.join(sig['population'])}")
    else:
        st.info("No population reached statistical significance at p < 0.05.")

# ---------------------------------------------------------------- Part 4 ----
with tab4:
    st.header("Melanoma, PBMC, miraclib, baseline (time = 0) samples")
    baseline = load_baseline()
    st.metric("Samples", len(baseline))

    subjects = baseline.drop_duplicates("subject_id")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.subheader("Samples per project")
        st.dataframe(baseline.groupby("project_id")["sample_id"].nunique().rename("n_samples"))
    with c2:
        st.subheader("Subjects by response")
        st.dataframe(subjects["response"].value_counts().rename_axis("response").rename("n_subjects"))
    with c3:
        st.subheader("Subjects by sex")
        st.dataframe(subjects["sex"].value_counts().rename_axis("sex").rename("n_subjects"))

    st.divider()
    st.subheader("Bonus question")
    st.write(
        "Considering melanoma males of all sample and treatment types, "
        "average number of B cells for responders at time = 0:"
    )
    conn = _connection()
    avg_b_cell = pd.read_sql_query(
        """
        SELECT AVG(cc.count) AS avg_b_cell
        FROM cell_counts cc
        JOIN samples sm ON sm.sample_id = cc.sample_id
        JOIN subjects su ON su.subject_id = sm.subject_id
        WHERE su.condition = 'melanoma'
          AND su.sex = 'M'
          AND su.response = 'yes'
          AND sm.time_from_treatment_start = 0
          AND cc.population = 'b_cell'
        """,
        conn,
    )["avg_b_cell"].iloc[0]
    st.metric("Average B cells", f"{avg_b_cell:.2f}")
