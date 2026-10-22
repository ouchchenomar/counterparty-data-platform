"""Point d'entrée unique du pipeline : ingest -> synthetic -> load -> dbt.

Exemples :
    python -m cdp.pipeline                      # tout le pipeline, API GLEIF en direct
    python -m cdp.pipeline --from-sample        # hors ligne, sur l'échantillon (CI)
    python -m cdp.pipeline --step dbt           # une seule étape (utilisé par Airflow)
"""

import argparse
import logging
import os

from cdp import config, load_raw
from cdp.ingestion import gleif
from cdp.synthetic import generate_internal

STEPS = ("ingest", "synthetic", "load", "dbt")

log = logging.getLogger(__name__)


def run_dbt(command: str = "build") -> None:
    # Import local : dbt n'est nécessaire que pour cette étape.
    from dbt.cli.main import dbtRunner

    os.environ.setdefault("CDP_DUCKDB_PATH", str(config.DUCKDB_PATH))
    args = [command, "--project-dir", str(config.DBT_DIR), "--profiles-dir", str(config.DBT_DIR)]
    result = dbtRunner().invoke(args)
    if not result.success:
        raise RuntimeError(f"dbt {command} a échoué") from result.exception


def run_step(step: str, from_sample: bool = False, full_refresh: bool = False) -> None:
    log.info("Étape : %s", step)
    if step == "ingest":
        log.info("%s", gleif.run(full_refresh=full_refresh, from_sample=from_sample))
    elif step == "synthetic":
        log.info("%s", generate_internal.run())
    elif step == "load":
        log.info("%s", load_raw.run())
    elif step == "dbt":
        run_dbt()
    else:
        raise ValueError(f"Étape inconnue : {step}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Pipeline Counterparty Data Platform")
    parser.add_argument("--step", choices=(*STEPS, "all"), default="all")
    parser.add_argument("--from-sample", action="store_true")
    parser.add_argument("--full-refresh", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    for step in STEPS if args.step == "all" else (args.step,):
        run_step(step, args.from_sample, args.full_refresh)


if __name__ == "__main__":
    main()
