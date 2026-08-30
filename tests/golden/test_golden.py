import json
from pathlib import Path

from packages.domain.enums import EpistemicStatus, EvidenceStance, SourceCollectionMode
from packages.verification.claims import validate_pattern
from packages.verification.quality import evaluate_golden


def scenarios():
    path = Path(__file__).parent / "fixtures" / "scenarios.json"
    return {item["name"]: item for item in json.loads(path.read_text(encoding="utf-8"))}


def test_golden_manifest_is_complete() -> None:
    report = evaluate_golden(Path(__file__).parent / "fixtures")
    assert report.passed
    assert report.people_count == 10


def test_epistemic_and_stance_values_are_preserved() -> None:
    data = scenarios()
    assert (
        EpistemicStatus(data["official_assertion_remains_claim"]["status"]) is EpistemicStatus.CLAIM
    )
    assert EpistemicStatus(data["unknown_first_class"]["status"]) is EpistemicStatus.UNKNOWN
    assert [EvidenceStance(x) for x in data["support_and_refute"]["stances"]] == [
        EvidenceStance.SUPPORT,
        EvidenceStance.REFUTE,
    ]


def test_pattern_and_policy_scenarios() -> None:
    data = scenarios()
    assert not validate_pattern([{"one"}]).publishable
    assert validate_pattern([{"one"}, {"two"}]).publishable
    assert (
        SourceCollectionMode(data["blocked_source_policy"]["mode"]) is SourceCollectionMode.BLOCKED
    )
    assert (
        SourceCollectionMode(data["discovery_only_source_policy"]["mode"])
        is SourceCollectionMode.DISCOVERY_ONLY
    )
