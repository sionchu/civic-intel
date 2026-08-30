from pathlib import Path

from packages.domain.enums import EpistemicStatus, EvidenceStance, PublicationStatus
from packages.verification.golden import load_golden_set
from packages.verification.quality import EXPECTED_ROSTER, evaluate_golden

FIXTURES = Path(__file__).parent / "fixtures"
HA_JUNGWOO_ID = "00000000-0000-0000-0000-000000000009"


def test_golden_set_001_is_real_and_executable() -> None:
    golden = load_golden_set(FIXTURES)
    report = evaluate_golden(FIXTURES)
    assert golden.id == "GOLDEN_SET_001"
    assert {item.person.canonical_name for item in golden.people} == EXPECTED_ROSTER
    assert len(golden.people) == 10
    assert report.passed, report.failures
    assert all(report.checks.values())
    assert report.metrics["published_facts"] == 11


def test_profile_evidence_supplement_enriches_existing_person_only() -> None:
    golden = load_golden_set(FIXTURES)
    ha_claims = [item for item in golden.claims if str(item.person_id) == HA_JUNGWOO_ID]

    held_role = next(item for item in ha_claims if item.predicate == "HELD_ROLE")
    rationale = next(item for item in ha_claims if item.predicate == "APPOINTMENT_RATIONALE")

    assert held_role.epistemic_status == EpistemicStatus.FACT
    assert held_role.asserted_as_true is True
    assert held_role.qualifiers["date"] == "2026-01-27"
    assert rationale.epistemic_status == EpistemicStatus.CLAIM
    assert rationale.asserted_as_true is False
    assert rationale.qualifiers["speaker"] == "대통령비서실"
    assert golden.raw["profile_evidence_supplement"]["id"] == "GOLDEN_SET_001_PROFILE_EVIDENCE"


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
    official_claims = [
        item for item in golden.claims if item.qualifiers.get("speaker") == "대통령비서실"
    ]
    assert official_claims
    assert all(item.epistemic_status == EpistemicStatus.CLAIM for item in official_claims)
    assert all(item.asserted_as_true is False for item in official_claims)
