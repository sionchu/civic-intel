import json
from pathlib import Path

import pytest

from packages.verification.golden import GoldenSupplementError, load_golden_set

FIXTURES = Path(__file__).parent / "fixtures"
BASE_NAME = "golden_set_001.json"
SUPPLEMENT_NAME = "golden_set_001_profile_evidence.json"


def write_fixture_pair(target: Path, *, mutate) -> None:
    base = json.loads((FIXTURES / BASE_NAME).read_text(encoding="utf-8"))
    supplement = json.loads((FIXTURES / SUPPLEMENT_NAME).read_text(encoding="utf-8"))
    mutate(base, supplement)
    target.mkdir(parents=True, exist_ok=True)
    (target / BASE_NAME).write_text(json.dumps(base, ensure_ascii=False), encoding="utf-8")
    (target / SUPPLEMENT_NAME).write_text(
        json.dumps(supplement, ensure_ascii=False), encoding="utf-8"
    )


def test_duplicate_record_id_in_supplement_fails_closed(tmp_path: Path) -> None:
    def duplicate_claim_id(base: dict, supplement: dict) -> None:
        supplement["claims"][0]["id"] = base["claims"][0]["id"]

    write_fixture_pair(tmp_path, mutate=duplicate_claim_id)

    with pytest.raises(GoldenSupplementError, match="duplicate Golden record id"):
        load_golden_set(tmp_path)


def test_broken_supplement_reference_fails_closed(tmp_path: Path) -> None:
    def missing_policy(_: dict, supplement: dict) -> None:
        supplement["sources"][0]["policy_id"] = "10000000-0000-0000-0000-999999999999"

    write_fixture_pair(tmp_path, mutate=missing_policy)

    with pytest.raises(GoldenSupplementError, match="missing SourcePolicy"):
        load_golden_set(tmp_path)


def test_supplement_cannot_declare_people(tmp_path: Path) -> None:
    def add_person(_: dict, supplement: dict) -> None:
        supplement["people"] = [
            {
                "id": "00000000-0000-0000-0000-999999999999",
                "canonical_name": "금지된 추가 인물",
                "identity_status": "RESOLVED",
                "aliases": [],
                "identity_anchors": {},
            }
        ]

    write_fixture_pair(tmp_path, mutate=add_person)

    with pytest.raises(GoldenSupplementError, match="cannot declare Person"):
        load_golden_set(tmp_path)
