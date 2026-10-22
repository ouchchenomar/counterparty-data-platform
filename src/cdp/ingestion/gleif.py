"""Ingestion incrémentale des enregistrements LEI depuis l'API publique GLEIF.

- Les enregistrements sont écrits tels quels (JSON Lines) dans la zone d'atterrissage :
  data/raw/gleif/ingest_date=AAAA-MM-JJ/lei_records_<pays>_<HHMMSS>.jsonl
- Un filigrane (watermark) mémorise la dernière date de mise à jour vue par pays.
  Le run suivant repart de ce filigrane moins LOOKBACK : le chevauchement est voulu,
  les doublons sont éliminés dans dbt (stg_gleif__lei_records). Voir docs/adr/0002.
"""

import argparse
import json
import logging
from collections.abc import Iterable, Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from cdp import config

API_URL = "https://api.gleif.org/api/v1/lei-records"
PAGE_SIZE = 200  # maximum accepté par l'API GLEIF
LOOKBACK = timedelta(days=1)
WATERMARK_FILE = "gleif_watermark.json"

log = logging.getLogger(__name__)


def build_session() -> requests.Session:
    retry = Retry(
        total=5,
        backoff_factor=1,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
    )
    session = requests.Session()
    session.headers["Accept"] = "application/vnd.api+json"
    session.mount("https://", HTTPAdapter(max_retries=retry))
    return session


def fetch_lei_records(
    session: requests.Session,
    country: str,
    updated_since: str | None = None,
    page_size: int = PAGE_SIZE,
    timeout: int = 30,
) -> Iterator[dict]:
    """Parcourt toutes les pages de résultats pour un pays donné."""
    params: dict[str, str | int] = {
        "filter[entity.legalAddress.country]": country,
        "page[size]": page_size,
        "page[number]": 1,
    }
    if updated_since:
        params["filter[registration.lastUpdateDate]"] = f">{updated_since}"

    while True:
        response = session.get(API_URL, params=params, timeout=timeout)
        response.raise_for_status()
        body = response.json()
        yield from body["data"]

        pagination = body["meta"]["pagination"]
        log.info("Page %s/%s", pagination["currentPage"], pagination["lastPage"])
        if pagination["currentPage"] >= pagination["lastPage"]:
            break
        params["page[number]"] = int(params["page[number]"]) + 1


def write_jsonl(records: Iterable[dict], landing_dir: Path, country: str) -> tuple[Path, int]:
    now = datetime.now(UTC)
    out_dir = landing_dir / f"ingest_date={now:%Y-%m-%d}"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"lei_records_{country}_{now:%H%M%S}.jsonl"

    count = 0
    with out_file.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
            count += 1
    return out_file, count


def max_last_update(records: Iterable[dict]) -> str | None:
    dates = [r["attributes"]["registration"]["lastUpdateDate"] for r in records]
    return max(dates) if dates else None


def read_watermark(state_dir: Path, country: str) -> str | None:
    path = state_dir / WATERMARK_FILE
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8")).get(country)


def write_watermark(state_dir: Path, country: str, value: str) -> None:
    path = state_dir / WATERMARK_FILE
    state = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    state[country] = value
    state_dir.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2), encoding="utf-8")


def run(
    country: str = config.DEFAULT_COUNTRY,
    full_refresh: bool = False,
    from_sample: bool = False,
    landing_dir: Path = config.RAW_GLEIF_DIR,
    state_dir: Path = config.STATE_DIR,
    sample_file: Path = config.SAMPLE_GLEIF_FILE,
    session: requests.Session | None = None,
) -> dict:
    """Ingère les LEI d'un pays. `from_sample` rejoue l'échantillon local (CI, hors ligne)."""
    if from_sample:
        lines = sample_file.read_text(encoding="utf-8").splitlines()
        records = [json.loads(line) for line in lines if line.strip()]
        out_file, count = write_jsonl(records, landing_dir, country)
        return {"mode": "sample", "records": count, "file": str(out_file)}

    watermark = None if full_refresh else read_watermark(state_dir, country)
    updated_since = None
    if watermark:
        updated_since = (datetime.fromisoformat(watermark) - LOOKBACK).date().isoformat()

    records = list(fetch_lei_records(session or build_session(), country, updated_since))
    if not records:
        log.info("Aucun enregistrement modifié depuis %s", updated_since)
        return {"mode": "incremental", "records": 0, "file": None}

    out_file, count = write_jsonl(records, landing_dir, country)
    # Le chevauchement peut ramener des dates antérieures : le filigrane ne recule jamais.
    new_watermark = max(d for d in (watermark, max_last_update(records)) if d)
    write_watermark(state_dir, country, new_watermark)

    mode = "full" if updated_since is None else "incremental"
    return {"mode": mode, "records": count, "file": str(out_file), "watermark": new_watermark}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--country", default=config.DEFAULT_COUNTRY)
    parser.add_argument("--full-refresh", action="store_true", help="ignore le filigrane")
    parser.add_argument("--from-sample", action="store_true", help="rejoue l'échantillon local")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    summary = run(args.country, args.full_refresh, args.from_sample)
    log.info("Ingestion terminée : %s", summary)


if __name__ == "__main__":
    main()
