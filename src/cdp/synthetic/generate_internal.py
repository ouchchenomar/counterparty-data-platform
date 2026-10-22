"""Génère un extrait « interne » de contreparties à partir des enregistrements GLEIF.

L'extrait simule le fichier d'un système bancaire interne. Des anomalies y sont injectées
volontairement, une au plus par fiche, et consignées dans anomalies_truth.csv : cette
vérité terrain permet de mesurer le taux de détection des règles qualité (rpt_dq_detection).
"""

import argparse
import csv
import json
import logging
import random
import string
from datetime import date, timedelta
from pathlib import Path

from cdp import config
from cdp.quality.lei import compute_check_digits

INTERNAL_FILE = "internal_counterparties.csv"
TRUTH_FILE = "anomalies_truth.csv"
FIELDS = [
    "counterparty_id",
    "legal_name",
    "lei",
    "country_code",
    "city",
    "legal_form",
    "segment",
    "onboarding_date",
    "relationship_manager",
]

ANOMALY_TYPES = [
    "missing_mandatory_field",
    "missing_lei",
    "invalid_lei_checksum",
    "lei_not_found",
    "country_mismatch",
]
SEGMENTS = ["Corporate", "Institution financiere", "PME", "Assurance", "OPCVM"]
OTHER_COUNTRIES = ["FR", "ES", "SN", "CI", "AE", "GB"]

log = logging.getLogger(__name__)


def load_gleif_records(paths: list[Path]) -> list[dict]:
    """Charge les enregistrements GLEIF et garde la version la plus récente de chaque LEI."""
    latest: dict[str, dict] = {}
    for path in paths:
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            record = json.loads(line)
            lei = record["attributes"]["lei"]
            updated = record["attributes"]["registration"]["lastUpdateDate"]
            current = latest.get(lei)
            if current is None or updated > current["attributes"]["registration"]["lastUpdateDate"]:
                latest[lei] = record
    return [latest[lei] for lei in sorted(latest)]


def to_internal_row(record: dict, index: int, rng: random.Random) -> dict:
    entity = record["attributes"]["entity"]
    address = entity["legalAddress"]
    legal_form = entity["legalForm"]
    onboarding = date(2023, 1, 1) + timedelta(days=rng.randrange(0, 3 * 365))
    return {
        "counterparty_id": f"CP-{index:06d}",
        # Les saisies internes ne reprennent pas toujours la casse officielle : ce n'est
        # pas une anomalie, mais le golden record doit privilégier le nom GLEIF.
        "legal_name": entity["legalName"]["name"].title(),
        "lei": record["attributes"]["lei"],
        "country_code": address["country"],
        "city": (address["city"] or "").title(),
        "legal_form": legal_form["other"] or legal_form["id"] or "",
        "segment": rng.choice(SEGMENTS),
        "onboarding_date": onboarding.isoformat(),
        "relationship_manager": f"RM{rng.randint(1, 12):03d}",
    }


def _random_valid_lei(rng: random.Random, known: set[str]) -> str:
    while True:
        base = "9845" + "".join(rng.choices(string.ascii_uppercase + string.digits, k=14))
        lei = base + compute_check_digits(base)
        if lei not in known:
            return lei


def _break_checksum(lei: str) -> str:
    wrong = (int(lei[-2:]) + 1) % 100
    return f"{lei[:-2]}{wrong:02d}"


def inject_anomaly(row: dict, anomaly: str, rng: random.Random, known: set[str]) -> None:
    if anomaly == "missing_mandatory_field":
        row[rng.choice(["legal_name", "city"])] = ""
    elif anomaly == "missing_lei":
        row["lei"] = ""
    elif anomaly == "invalid_lei_checksum":
        row["lei"] = _break_checksum(row["lei"])
    elif anomaly == "lei_not_found":
        row["lei"] = _random_valid_lei(rng, known)
    elif anomaly == "country_mismatch":
        row["country_code"] = rng.choice(OTHER_COUNTRIES)
    else:
        raise ValueError(f"Anomalie inconnue : {anomaly}")


def make_duplicate(row: dict, index: int) -> dict:
    duplicate = dict(row)
    duplicate["counterparty_id"] = f"CP-{index:06d}"
    duplicate["legal_name"] = row["legal_name"].upper() + " "
    later = date.fromisoformat(row["onboarding_date"]) + timedelta(days=30)
    duplicate["onboarding_date"] = later.isoformat()
    return duplicate


def generate(
    records: list[dict], seed: int = 42, anomaly_rate: float = 0.25, duplicate_rate: float = 0.05
) -> tuple[list[dict], list[dict]]:
    """Retourne (fiches internes, vérité terrain des anomalies)."""
    rng = random.Random(seed)
    known = {r["attributes"]["lei"] for r in records}
    rows = [to_internal_row(record, i + 1, rng) for i, record in enumerate(records)]
    truth: list[dict] = []

    targets = rng.sample(range(len(rows)), k=round(len(rows) * anomaly_rate))
    for position, row_index in enumerate(targets):
        # Rotation sur les types pour que chacun soit représenté.
        anomaly = ANOMALY_TYPES[position % len(ANOMALY_TYPES)]
        row = rows[row_index]
        inject_anomaly(row, anomaly, rng, known)
        truth.append({"counterparty_id": row["counterparty_id"], "anomaly_type": anomaly})

    anomalous = set(targets)
    clean = [i for i in range(len(rows)) if i not in anomalous]
    n_duplicates = max(1, round(len(rows) * duplicate_rate))
    for source_index in rng.sample(clean, k=min(n_duplicates, len(clean))):
        duplicate = make_duplicate(rows[source_index], len(rows) + 1)
        rows.append(duplicate)
        truth.append(
            {"counterparty_id": duplicate["counterparty_id"], "anomaly_type": "duplicate_record"}
        )

    return rows, truth


def write_csv(rows: list[dict], path: Path, fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def run(
    landing_dir: Path = config.RAW_GLEIF_DIR,
    output_dir: Path = config.SYNTHETIC_DIR,
    seed: int = 42,
    overwrite: bool = False,
) -> dict:
    internal_path = output_dir / INTERNAL_FILE
    if internal_path.exists() and not overwrite:
        log.info("Extrait interne déjà présent : %s", internal_path)
        return {"generated": False, "file": str(internal_path)}

    paths = sorted(landing_dir.rglob("*.jsonl"))
    if not paths:
        raise FileNotFoundError(f"Aucun fichier GLEIF dans {landing_dir} : lancez l'ingestion.")

    rows, truth = generate(load_gleif_records(paths), seed=seed)
    write_csv(rows, internal_path, FIELDS)
    write_csv(truth, output_dir / TRUTH_FILE, ["counterparty_id", "anomaly_type"])
    return {
        "generated": True,
        "rows": len(rows),
        "anomalies": len(truth),
        "file": str(internal_path),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    log.info("Génération terminée : %s", run(seed=args.seed, overwrite=args.overwrite))


if __name__ == "__main__":
    main()
