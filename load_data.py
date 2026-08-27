"""
Initializes the SQLite database (cell_counts.db) and loads cell-count.csv into it.

Run directly:
    python load_data.py
"""
import csv
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CSV_PATH = ROOT / "cell-count.csv"
DB_PATH = ROOT / "cell_counts.db"

POPULATIONS = ["b_cell", "cd8_t_cell", "cd4_t_cell", "nk_cell", "monocyte"]

SCHEMA = """
CREATE TABLE IF NOT EXISTS projects (
    project_id  TEXT PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS subjects (
    subject_id  TEXT PRIMARY KEY,
    project_id  TEXT NOT NULL REFERENCES projects(project_id),
    condition   TEXT NOT NULL,
    sex         TEXT NOT NULL,
    age         INTEGER,
    treatment   TEXT NOT NULL,
    response    TEXT
);

CREATE TABLE IF NOT EXISTS samples (
    sample_id                  TEXT PRIMARY KEY,
    subject_id                 TEXT NOT NULL REFERENCES subjects(subject_id),
    sample_type                TEXT NOT NULL,
    time_from_treatment_start  REAL
);

CREATE TABLE IF NOT EXISTS cell_counts (
    sample_id   TEXT NOT NULL REFERENCES samples(sample_id),
    population  TEXT NOT NULL,
    count       INTEGER NOT NULL,
    PRIMARY KEY (sample_id, population)
);

CREATE INDEX IF NOT EXISTS idx_subjects_project   ON subjects(project_id);
CREATE INDEX IF NOT EXISTS idx_samples_subject     ON samples(subject_id);
CREATE INDEX IF NOT EXISTS idx_cellcounts_sample   ON cell_counts(sample_id);
CREATE INDEX IF NOT EXISTS idx_cellcounts_pop      ON cell_counts(population);
"""


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)


def load_csv(conn: sqlite3.Connection, csv_path: Path) -> None:
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    projects = {r["project"] for r in rows}
    conn.executemany(
        "INSERT OR IGNORE INTO projects (project_id) VALUES (?)",
        [(p,) for p in projects],
    )

    subjects_seen = {}
    for r in rows:
        subjects_seen[r["subject"]] = (
            r["subject"],
            r["project"],
            r["condition"],
            r["sex"],
            int(r["age"]) if r["age"] else None,
            r["treatment"],
            r["response"] or None,
        )
    conn.executemany(
        """INSERT OR IGNORE INTO subjects
           (subject_id, project_id, condition, sex, age, treatment, response)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        list(subjects_seen.values()),
    )

    conn.executemany(
        """INSERT OR IGNORE INTO samples
           (sample_id, subject_id, sample_type, time_from_treatment_start)
           VALUES (?, ?, ?, ?)""",
        [
            (
                r["sample"],
                r["subject"],
                r["sample_type"],
                float(r["time_from_treatment_start"]) if r["time_from_treatment_start"] != "" else None,
            )
            for r in rows
        ],
    )

    cell_count_rows = []
    for r in rows:
        for pop in POPULATIONS:
            cell_count_rows.append((r["sample"], pop, int(r[pop])))
    conn.executemany(
        "INSERT OR IGNORE INTO cell_counts (sample_id, population, count) VALUES (?, ?, ?)",
        cell_count_rows,
    )

    conn.commit()


def main() -> None:
    if not CSV_PATH.exists():
        raise FileNotFoundError(f"Expected input file not found: {CSV_PATH}")

    if DB_PATH.exists():
        DB_PATH.unlink()

    conn = sqlite3.connect(DB_PATH)
    try:
        init_db(conn)
        load_csv(conn, CSV_PATH)
        n_samples = conn.execute("SELECT COUNT(*) FROM samples").fetchone()[0]
        n_subjects = conn.execute("SELECT COUNT(*) FROM subjects").fetchone()[0]
        n_counts = conn.execute("SELECT COUNT(*) FROM cell_counts").fetchone()[0]
        print(f"Loaded {n_subjects} subjects, {n_samples} samples, {n_counts} cell-count rows into {DB_PATH.name}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
