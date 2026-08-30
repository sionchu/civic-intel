from pathlib import Path

from packages.domain.enums import EpistemicStatus, EvidenceStance, PublicationStatus
from packages.verification.golden import load_golden_set
from packages.verification.quality import EXPECTED_ROSTER, evaluate_golden

FIXTURES = Path(__file__).parent / "fixtures"


def test_golden_set_001_is_real_and_executable() -> None:
    golden = load_golden_set(FIXTURES)
    report = evaluate_golden(FIXTURES)
    assert golden.id == "GOLDEN_SET_001"
    assert {item.person.canonical_name for item in golden.people} == EXPECTED_ROSTER
    assert report.passed, report.failures
    assert all(report.checks.values())
    assert report.metrics["published_facts"] == 10


def test_unknown_is_publicly_visible_without_becoming_fact() -> None:
    golden = load_golden_set(FIXTURES)
    unknown = next(
        item for item in golden.claims if item.epistemic_status == EpistemicStatus.UNKNOWN
    )
    assert unknown.publication_status == PublicationStatus.PUBLISHED
    assert unknown.asserted_as_true is False
    assert unknown.resolution_note


def test_conflicting_evidence_and_official_claim_semantics_are_preserved() -> None:
    golden = load_golden_set(FIXTURES)
    stances = {
        item.stance
        for item in golden.evidence
        if str(item.claim_id) == "30000000-0000-0000-0000-000000000013"
    }
    assert stances == {EvidenceStance.SUPPORT, EvidenceStance.REFUTE}
    official = next(
        item for item in golden.claims if item.qualifiers.get("speaker") == "대통령비서실"
    )
    assert official.epistemic_status == EpistemicStatus.CLAIM
    assert official.asserted_as_true is False
