# Teiko Cell Count Analysis

This repository contains my solution to the Teiko Bio take-home assessment. It builds a SQLite database from `cell-count.csv` and answers the four analysis questions (Parts 1-4), plus an interactive dashboard to view the results.

## How to run

```bash
make setup      # installs dependencies from requirements.txt
make pipeline   # initializes the database, loads the CSV, runs Parts 2-4
make dashboard  # starts the Streamlit dashboard
```

`make dashboard` runs a Streamlit server on port 8501. In GitHub Codespaces this triggers a port forward and a popup with a link to open it in the browser. Locally, it's at `http://localhost:8501`.

**Dashboard link:** _fill in after running `make dashboard` in Codespaces_

## Repository structure

```
cell-count.csv               raw input data
load_data.py                 Part 1 - builds cell_counts.db
analysis/
  db.py                      shared DB connection helper
  part2_frequencies.py       Part 2 - per-sample population frequencies
  part3_stats.py             Part 3 - responder vs non-responder analysis
  part4_subset.py            Part 4 - baseline subset + bonus question
dashboard/
  app.py                     Streamlit dashboard
output/                      generated CSVs and plots
Makefile
requirements.txt
```

I split Parts 2-4 into separate scripts under `analysis/` rather than one large script, mainly so each part could be run and tested independently, and so the dashboard could import the same functions instead of duplicating the query/stats logic. If the analysis logic lived only in the dashboard, or only in standalone scripts, the two would eventually drift out of sync with each other.

## Part 1 - Database schema

The CSV has one row per sample, but that single row actually mixes together three different levels of information: which project a subject belongs to, attributes of the subject (condition, sex, age, treatment, response), and attributes of the individual sample (type, timepoint, cell counts). I split this into four tables:

```
projects(project_id PK)

subjects(subject_id PK, project_id FK, condition, sex, age, treatment, response)

samples(sample_id PK, subject_id FK, sample_type, time_from_treatment_start)

cell_counts(sample_id FK, population, count, PK(sample_id, population))
```

`projects` ends up with just one column since the CSV doesn't give any other project-level attributes, but I kept it as its own table anyway so that `project_id` is enforced through a foreign key rather than being a free-text field on `subjects`.

The choice I spent the most time on was `cell_counts`. The CSV has five separate columns for the five populations (`b_cell`, `cd8_t_cell`, `cd4_t_cell`, `nk_cell`, `monocyte`). I could have kept that as five columns in the table, but instead went with a long format: one row per sample per population, with a `population` column holding the name and a `count` column holding the value. This means each sample turns into five rows in `cell_counts` instead of one row with five columns.

I went with the long format for two reasons. First, several of the questions in Parts 2 and 3 ask for something "per population," which in this layout is a `GROUP BY population`, rather than five separate calculations, one per hardcoded column. Second, it scales better if more populations get added later - a sixth population is just new rows, not a schema change and not new columns to add to every query. The tradeoff is that `cell_counts` has 52,500 rows instead of 10,500, and most queries need a join back to `samples`/`subjects` for anything beyond the raw counts.

For a larger deployment (hundreds of projects, much higher sample volume), I'd expect this schema to hold up reasonably well as-is, since the row counts scale in the tables that are supposed to grow (subjects, samples, cell_counts) rather than in the number of columns. The main change I'd expect at that scale is moving off SQLite to something like Postgres for concurrent access, with the same table structure and indexes carried over. New types of analysis mostly turn into new SQL queries over the existing tables rather than new tables - Parts 3 and 4 below are both just different `WHERE`/`JOIN` combinations over the same four tables.

## Part 2 - Frequency table

`analysis/part2_frequencies.py` computes, for each sample, the total cell count (sum across all five populations) and then each population's share of that total as a percentage. Output goes to `output/frequencies.csv`, with one row per sample per population as specified.

## Part 3 - Responders vs non-responders

`analysis/part3_stats.py` filters to melanoma patients on miraclib, PBMC samples only, and compares the relative frequency of each population between responders and non-responders.

For the statistical test I used the Mann-Whitney U test rather than a t-test, since it doesn't require assuming the percentages are normally distributed within each group, which isn't something I wanted to assume without checking. Results are written to `output/responder_vs_nonresponder_stats.csv`, and a boxplot per population to `output/responder_vs_nonresponder_boxplot.png` (also viewable per-population in the dashboard).

Of the five populations, only `cd4_t_cell` comes out statistically significant (p ≈ 0.013), with responders showing a slightly higher CD4 T-cell percentage on average (about 30.5% vs 29.9%). The other four populations (b_cell, cd8_t_cell, nk_cell, monocyte) don't show a significant difference at p < 0.05.

## Part 4 - Subset analysis

`analysis/part4_subset.py` covers two related but different questions, which is worth calling out because the filters aren't the same:

1. Melanoma, PBMC, miraclib, baseline samples (`time_from_treatment_start = 0`). Among these, it breaks down sample counts by project, and subject counts by response and by sex.
2. The bonus question, which uses a different filter: melanoma and male, but *not* restricted to PBMC or miraclib - all sample types and treatments are included - restricted to responders at time 0, and asking for the raw average `b_cell` count rather than a percentage.

Results for the baseline subset are in `output/part4_summary_by_*.csv`, and the bonus answer is in `output/part4_answer.txt`.

**Bonus answer: 10206.15**

## Dashboard

`dashboard/app.py` is a Streamlit app with one tab per part (2, 3, 4). It imports the same functions used by the analysis scripts rather than reading only the exported CSVs, so it reflects the current state of the database if it's rebuilt. Part 2's table can be filtered by sample or population, Part 3 lets you pick a population to view its boxplot alongside the full stats table, and Part 4 shows the baseline breakdowns and the bonus-question answer.

## Notes

While building this, I ran into an import error caused by naming one of the analysis scripts with a hyphen (`part2-frequencies.py`) instead of an underscore - Python won't import a module whose name isn't a valid identifier, so the filename had to change before `part3_stats.py` could import from it. Worth knowing about if anyone reorganizes these files later.
