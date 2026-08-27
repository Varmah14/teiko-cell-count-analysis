import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from analysis.db import get_connection, ensure_output_dir


def compute_frequencies(conn) -> pd.DataFrame:
    df = pd.read_sql_query(
        """
        SELECT sample_id AS sample, population, count
        FROM cell_counts
        """,
        conn,
    )
    totals = df.groupby("sample")["count"].transform("sum")
    df["total_count"] = totals
    df["percentage"] = (df["count"] / df["total_count"] * 100).round(4)
    df = df[["sample", "total_count", "population", "count", "percentage"]]
    return df.sort_values(["sample", "population"]).reset_index(drop=True)


def main() -> None:
    conn = get_connection()
    try:
        df = compute_frequencies(conn)
    finally:
        conn.close()

    out_dir = ensure_output_dir()
    out_path = out_dir / "frequencies.csv"
    df.to_csv(out_path, index=False)
    print(f"Wrote {len(df)} rows to {out_path}")
    print(df.head(10).to_string(index=False))


if __name__ == "__main__":
    main()
