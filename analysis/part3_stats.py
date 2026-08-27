import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from analysis.db import get_connection, ensure_output_dir
from analysis.part2_frequencies import compute_frequencies

POPULATIONS = ["b_cell", "cd8_t_cell", "cd4_t_cell", "nk_cell", "monocyte"]


def get_melanoma_miraclib_pbmc_frequencies(conn) -> pd.DataFrame:
    freq = compute_frequencies(conn)

    meta = pd.read_sql_query(
        """
        SELECT sm.sample_id AS sample, sm.sample_type, su.condition, su.treatment, su.response
        FROM samples sm
        JOIN subjects su ON su.subject_id = sm.subject_id
        """,
        conn,
    )

    merged = freq.merge(meta, on="sample")
    subset = merged[
        (merged["condition"] == "melanoma")
        & (merged["treatment"] == "miraclib")
        & (merged["sample_type"] == "PBMC")
        & (merged["response"].isin(["yes", "no"]))
    ].copy()
    return subset


def run_stats(subset: pd.DataFrame) -> pd.DataFrame:
    results = []
    for pop in POPULATIONS:
        resp = subset[(subset["population"] == pop) & (subset["response"] == "yes")]["percentage"]
        nonresp = subset[(subset["population"] == pop) & (subset["response"] == "no")]["percentage"]
        u_stat, p_val = stats.mannwhitneyu(resp, nonresp, alternative="two-sided")
        results.append(
            {
                "population": pop,
                "n_responders": len(resp),
                "n_non_responders": len(nonresp),
                "mean_responders_pct": round(resp.mean(), 3),
                "mean_non_responders_pct": round(nonresp.mean(), 3),
                "mannwhitney_u": round(u_stat, 3),
                "p_value": p_val,
                "significant_p<0.05": p_val < 0.05,
            }
        )
    return pd.DataFrame(results).sort_values("p_value").reset_index(drop=True)


def make_boxplot(subset: pd.DataFrame, out_path: Path) -> None:
    fig, axes = plt.subplots(1, len(POPULATIONS), figsize=(4 * len(POPULATIONS), 5), sharey=False)
    for ax, pop in zip(axes, POPULATIONS):
        data = subset[subset["population"] == pop]
        groups = [data[data["response"] == "yes"]["percentage"], data[data["response"] == "no"]["percentage"]]
        ax.boxplot(groups, tick_labels=["responder", "non-responder"], showmeans=True)
        ax.set_title(pop)
        ax.set_ylabel("relative frequency (%)")
    fig.suptitle("Melanoma, miraclib, PBMC: responders vs non-responders")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def main() -> None:
    conn = get_connection()
    try:
        subset = get_melanoma_miraclib_pbmc_frequencies(conn)
    finally:
        conn.close()

    out_dir = ensure_output_dir()

    stats_df = run_stats(subset)
    stats_path = out_dir / "responder_vs_nonresponder_stats.csv"
    stats_df.to_csv(stats_path, index=False)

    plot_path = out_dir / "responder_vs_nonresponder_boxplot.png"
    make_boxplot(subset, plot_path)

    print(f"Wrote {stats_path}")
    print(f"Wrote {plot_path}")
    print(stats_df.to_string(index=False))
    sig = stats_df[stats_df["significant_p<0.05"]]
    if len(sig):
        print("\nSignificant populations (p < 0.05):", ", ".join(sig["population"]))
    else:
        print("\nNo populations reached p < 0.05.")


if __name__ == "__main__":
    main()
