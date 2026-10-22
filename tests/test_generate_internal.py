from collections import Counter

from cdp.quality.lei import is_valid_lei
from cdp.synthetic.generate_internal import ANOMALY_TYPES, generate


def test_generation_is_deterministic(sample_records):
    assert generate(sample_records, seed=7) == generate(sample_records, seed=7)


def test_every_anomaly_type_is_injected(sample_records):
    _, truth = generate(sample_records)
    types = Counter(t["anomaly_type"] for t in truth)
    assert set(types) == {*ANOMALY_TYPES, "duplicate_record"}


def test_truth_points_to_existing_rows_once(sample_records):
    rows, truth = generate(sample_records)
    ids = {row["counterparty_id"] for row in rows}
    truth_ids = [t["counterparty_id"] for t in truth]
    assert set(truth_ids) <= ids
    assert len(truth_ids) == len(set(truth_ids)), "une seule anomalie par fiche"


def test_lei_anomalies_behave_as_labelled(sample_records):
    rows, truth = generate(sample_records)
    by_id = {row["counterparty_id"]: row for row in rows}
    known = {r["attributes"]["lei"] for r in sample_records}

    for item in truth:
        lei = by_id[item["counterparty_id"]]["lei"]
        if item["anomaly_type"] == "invalid_lei_checksum":
            assert not is_valid_lei(lei)
        elif item["anomaly_type"] == "lei_not_found":
            assert is_valid_lei(lei) and lei not in known
        elif item["anomaly_type"] == "missing_lei":
            assert lei == ""
