"""Charge la zone d'atterrissage dans le schéma `raw` de DuckDB (couche Bronze).

Les tables raw sont reconstruites à chaque run à partir des fichiers : les fichiers restent
la source de vérité, ce qui rend le chargement idempotent. Aucune transformation métier ici,
le parsing JSON et le nettoyage sont faits dans dbt.
"""

import logging
from pathlib import Path

import duckdb

from cdp import config
from cdp.synthetic.generate_internal import INTERNAL_FILE, TRUTH_FILE

log = logging.getLogger(__name__)


def _posix(path: Path) -> str:
    return path.as_posix().replace("'", "''")


def run(
    db_path: Path = config.DUCKDB_PATH,
    landing_dir: Path = config.RAW_GLEIF_DIR,
    synthetic_dir: Path = config.SYNTHETIC_DIR,
) -> dict[str, int]:
    if not any(landing_dir.rglob("*.jsonl")):
        raise FileNotFoundError(f"Aucun fichier GLEIF dans {landing_dir}")

    db_path.parent.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(str(db_path)) as con:
        con.execute("create schema if not exists raw")
        con.execute(f"""
            create or replace table raw.gleif_lei_records as
            select json as payload, filename as _source_file, current_timestamp as _loaded_at
            from read_json_objects('{_posix(landing_dir)}/**/*.jsonl',
                                   format = 'newline_delimited', filename = true)
        """)
        for table, file_name in [
            ("internal_counterparties", INTERNAL_FILE),
            ("anomalies_truth", TRUTH_FILE),
        ]:
            con.execute(f"""
                create or replace table raw.{table} as
                select *, filename as _source_file, current_timestamp as _loaded_at
                from read_csv('{_posix(synthetic_dir / file_name)}',
                              header = true, all_varchar = true, filename = true)
            """)

        counts = {
            table: con.execute(f"select count(*) from raw.{table}").fetchone()[0]
            for table in ("gleif_lei_records", "internal_counterparties", "anomalies_truth")
        }
    log.info("Tables raw chargées : %s", counts)
    return counts


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    run()
