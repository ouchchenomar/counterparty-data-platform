import json

from cdp.ingestion import gleif


class FakeResponse:
    def __init__(self, body: dict):
        self._body = body

    def raise_for_status(self) -> None:
        pass

    def json(self) -> dict:
        return self._body


class FakeSession:
    """Simule l'API GLEIF : renvoie les pages fournies et mémorise les paramètres reçus."""

    def __init__(self, pages: list[list[dict]]):
        self.pages = pages
        self.calls: list[dict] = []

    def get(self, url, params, timeout):
        self.calls.append(dict(params))
        number = params["page[number]"]
        body = {
            "data": self.pages[number - 1],
            "meta": {"pagination": {"currentPage": number, "lastPage": len(self.pages)}},
        }
        return FakeResponse(body)


def test_fetch_reads_every_page(sample_records):
    session = FakeSession([sample_records[:2], sample_records[2:3]])
    records = list(gleif.fetch_lei_records(session, "MA"))
    assert len(records) == 3
    assert [call["page[number]"] for call in session.calls] == [1, 2]


def test_incremental_filter_is_sent(sample_records):
    session = FakeSession([sample_records[:1]])
    list(gleif.fetch_lei_records(session, "MA", updated_since="2026-10-01"))
    assert session.calls[0]["filter[registration.lastUpdateDate]"] == ">2026-10-01"


def test_run_writes_jsonl_and_watermark(tmp_path, sample_records):
    session = FakeSession([sample_records[:5]])
    summary = gleif.run(
        country="MA", landing_dir=tmp_path / "raw", state_dir=tmp_path / "state", session=session
    )

    assert summary["records"] == 5
    written = (tmp_path / "raw").rglob("*.jsonl")
    lines = next(written).read_text(encoding="utf-8").splitlines()
    assert json.loads(lines[0])["attributes"]["lei"] == sample_records[0]["attributes"]["lei"]
    assert gleif.read_watermark(tmp_path / "state", "MA") == gleif.max_last_update(
        sample_records[:5]
    )


def test_second_run_uses_watermark_with_lookback(tmp_path, sample_records):
    gleif.write_watermark(tmp_path, "MA", "2026-10-10T08:00:00Z")
    session = FakeSession([[]])
    summary = gleif.run(
        country="MA", landing_dir=tmp_path / "raw", state_dir=tmp_path, session=session
    )

    assert summary["records"] == 0
    assert session.calls[0]["filter[registration.lastUpdateDate]"] == ">2026-10-09"
