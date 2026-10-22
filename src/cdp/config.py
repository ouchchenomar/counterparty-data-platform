"""Chemins du projet, surchargeables par variables d'environnement (Docker, CI)."""

import os
from pathlib import Path

PROJECT_DIR = Path(os.environ.get("CDP_PROJECT_DIR", Path(__file__).resolve().parents[2]))

DATA_DIR = PROJECT_DIR / "data"
RAW_GLEIF_DIR = DATA_DIR / "raw" / "gleif"
SYNTHETIC_DIR = DATA_DIR / "synthetic"
STATE_DIR = DATA_DIR / "state"
SAMPLE_GLEIF_FILE = DATA_DIR / "sample" / "gleif_sample.jsonl"
DUCKDB_PATH = Path(os.environ.get("CDP_DUCKDB_PATH", DATA_DIR / "warehouse" / "cdp.duckdb"))

DBT_DIR = PROJECT_DIR / "dbt"

DEFAULT_COUNTRY = "MA"
