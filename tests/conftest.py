import json

import pytest

from cdp import config


@pytest.fixture
def sample_records() -> list[dict]:
    lines = config.SAMPLE_GLEIF_FILE.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]
