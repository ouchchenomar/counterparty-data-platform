import pytest

from cdp.quality.lei import compute_check_digits, is_valid_lei


def test_real_gleif_leis_are_valid(sample_records):
    assert all(is_valid_lei(r["attributes"]["lei"]) for r in sample_records)


def test_wrong_check_digits_are_rejected(sample_records):
    lei = sample_records[0]["attributes"]["lei"]
    wrong = f"{lei[:-2]}{(int(lei[-2:]) + 1) % 100:02d}"
    assert not is_valid_lei(wrong)


@pytest.mark.parametrize(
    "value", [None, "", "TOO_SHORT", "984500572E7EEKADB78A", "984500572e7eekadb784"]
)
def test_malformed_values_are_rejected(value):
    assert not is_valid_lei(value)


def test_compute_check_digits_round_trip(sample_records):
    lei = sample_records[0]["attributes"]["lei"]
    assert compute_check_digits(lei[:18]) == lei[-2:]


def test_compute_check_digits_rejects_bad_base():
    with pytest.raises(ValueError):
        compute_check_digits("abc")
