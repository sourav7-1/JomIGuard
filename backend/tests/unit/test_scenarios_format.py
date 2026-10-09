"""Structure checks for tests/scenarios (the answer key). The rule engine does not exist yet."""

import json
import re
from pathlib import Path

import pytest
from pydantic import TypeAdapter

from app.schemas.extracted import ExtractedDocument

HERE = Path(__file__).parent
SCENARIOS = sorted(p for p in (HERE.parent / "scenarios").iterdir() if p.is_dir())
# repo: <root>/docs; Docker: /docs (read-only mount in docker-compose.yml)
FINDINGS_MD = (HERE.parents[2] / "docs/specs/findings.md").read_text(encoding="utf-8")
# rows of the "Codes" table: | `code` | group | severity | ...
CODES = dict(re.findall(r"^\| `(\w+)` \| \w+ \| (bad|warn) \|", FINDINGS_MD, re.MULTILINE))
EXPECTED_KEYS = {
    "title_bn",
    "description_bn",
    "expected_findings",
    "expected_risk",
    "needs_expert_check",
}
documents = TypeAdapter(ExtractedDocument)


def risk(severities: set[str]) -> str:
    return "high" if "bad" in severities else "medium" if "warn" in severities else "low"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_vocabulary_parsed():
    assert len(CODES) == 13
    assert len(SCENARIOS) >= 20


@pytest.mark.parametrize("case", SCENARIOS, ids=lambda p: p.name)
def test_scenario(case: Path):
    expected = load(case / "expected.json")
    assert set(expected) == EXPECTED_KEYS
    assert isinstance(expected["needs_expert_check"], bool)

    docs = sorted(p for p in case.glob("*.json") if p.name != "expected.json")
    assert docs, "no documents"
    for doc in docs:
        documents.validate_python(load(doc))

    findings = expected["expected_findings"]
    assert len({f["code"] for f in findings}) == len(findings), "duplicate code"
    for f in findings:
        assert f["code"] in CODES, f["code"]
        assert f["severity"] == CODES[f["code"]], f["code"]
        assert f["documents"], f["code"]
        for name in f["documents"]:
            assert (case / name).is_file(), name

    assert expected["expected_risk"] == risk({f["severity"] for f in findings})
