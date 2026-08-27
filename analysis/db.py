"""Shared helpers for connecting to cell_counts.db from the analysis scripts."""
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "cell_counts.db"
OUTPUT_DIR = ROOT / "output"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def get_connection() -> sqlite3.Connection:
    if not DB_PATH.exists():
        # cell_counts.db is derived data and isn't committed to git, so on a
        # fresh checkout (e.g. Streamlit Community Cloud, which only clones
        # the repo and never runs `python load_data.py`) it won't exist yet.
        # Build it on first use rather than failing.
        import load_data

        load_data.main()
    # check_same_thread=False: dashboard/app.py caches this connection with
    # st.cache_resource and reuses it across calls that Streamlit may run on
    # a different thread. We only ever read here, so sharing the connection
    # across threads is safe.
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def ensure_output_dir() -> Path:
    OUTPUT_DIR.mkdir(exist_ok=True)
    return OUTPUT_DIR
