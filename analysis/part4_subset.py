import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from analysis.db import get_connection, ensure_output_dir

BASELINE_QUERY = """
SELECT
    sm.sample_id,
    sm.time_from_treatment_start,
    sm.sample_type,
    su.subject_id,
    su.project_id,
    su.condition,
    su.treatment,
    su.response,
    su.sex
FROM samples sm
JOIN subjects su ON su.subject_id = sm.subject_id
WHERE su.condition = 'melanoma'
  AND sm.sample_type = 'PBMC'
  AND su.treatment = 'miraclib'
  AND sm.time_from_treatment_start = 0
"""

BONUS_QUERY = """
SELECT AVG(cc.count) AS avg_b_cell
FROM cell_counts cc
JOIN samples sm ON sm.sample_id = cc.sample_id
JOIN subjects su ON su.subject_id = sm.subject_id
WHERE su.condition = 'melanoma'
  AND su.sex = 'M'
  AND su.response = 'yes'
  AND sm.time_from_treatment_start = 0
  AND cc.population = 'b_cell'
"""


def main() -> None:
    conn = get_connection()
    try:
        baseline = pd.read_sql_query(BASELINE_QUERY, conn)
        bonus = pd.read_sql_query(BONUS_QUERY, conn)
    finally:
        conn.close()

    out_dir = ensure_output_dir()

    baseline.to_csv(out_dir / "part4_baseline_samples.csv", index=False)

    by_project = baseline.groupby("project_id")["sample_id"].nunique().rename("n_samples").reset_index()
    by_project.to_csv(out_dir / "part4_summary_by_project.csv", index=False)

    subjects = baseline.drop_duplicates("subject_id")
    by_response = subjects["response"].value_counts().rename_axis("response").reset_index(name="n_subjects")
    by_response.to_csv(out_dir / "part4_summary_by_response.csv", index=False)

    by_sex = subjects["sex"].value_counts().rename_axis("sex").reset_index(name="n_subjects")
    by_sex.to_csv(out_dir / "part4_summary_by_sex.csv", index=False)

    avg_b_cell = round(float(bonus["avg_b_cell"].iloc[0]), 2)
    with open(out_dir / "part4_answer.txt", "w") as f:
        f.write(
            "Average b_cell count, melanoma males, all sample/treatment types, "
            f"responders at time_from_treatment_start=0: {avg_b_cell:.2f}\n"
        )

    print(f"Baseline melanoma/PBMC/miraclib samples: {len(baseline)}")
    print("\nSamples per project:\n", by_project.to_string(index=False))
    print("\nSubjects by response:\n", by_response.to_string(index=False))
    print("\nSubjects by sex:\n", by_sex.to_string(index=False))
    print(f"\nAverage b_cell count (melanoma males, responders, time=0, all types): {avg_b_cell:.2f}")


if __name__ == "__main__":
    main()
