from uuid import UUID

from packages.domain.contracts import Claim, ClaimEvidence, Person
from packages.domain.enums import (
    EpistemicStatus,
    EvidenceStance,
    IdentityStatus,
    PublicationStatus,
)
from packages.rendering.profile_projection import SECTION_DEFINITIONS, build_profile_projection

PERSON_ID = UUID("00000000-0000-0000-0000-000000000099")
CLAIM_ID = UUID("30000000-0000-0000-0000-000000000099")
EVIDENCE_ID = UUID("40000000-0000-0000-0000-000000000099")
SOURCE_ID = UUID("20000000-0000-0000-0000-000000000099")


def person() -> Person:
    return Person(
        id=PERSON_ID,
        canonical_name="김프로필",
        identity_status=IdentityStatus.RESOLVED,
    )


def nomination_claim() -> Claim:
    return Claim(
        id=CLAIM_ID,
        person_id=PERSON_ID,
        proposition="김프로필은 위원장 후보자로 지명됐다.",
        subject="김프로필",
        predicate="NOMINATED_AS",
        object_text="위원장 후보자",
        qualifiers={"date": "2026-08-30"},
        epistemic_status=EpistemicStatus.FACT,
        publication_status=PublicationStatus.PUBLISHED,
        asserted_as_true=True,
    )


def nomination_evidence() -> ClaimEvidence:
    return ClaimEvidence(
        id=EVIDENCE_ID,
        claim_id=CLAIM_ID,
        source_id=SOURCE_ID,
        stance=EvidenceStance.SUPPORT,
        excerpt="projection must not copy this excerpt",
    )


def section(profile: dict, section_id: str) -> dict:
    return next(item for item in profile["sections"] if item["id"] == section_id)


def test_profile_projection_has_stable_twelve_section_contract() -> None:
    claim = nomination_claim()
    evidence = nomination_evidence()
    profile = build_profile_projection(
        person(),
        [claim],
        {claim.id: [evidence]},
        [],
        [],
    )

    assert profile["section_order"] == [item[0] for item in SECTION_DEFINITIONS]
    assert len(profile["sections"]) == 12
    assert profile["semantics"] == "DERIVED_READ_MODEL_FROM_CANONICAL_EVIDENCE"


def test_nomination_populates_summary_and_timeline_but_not_current_power() -> None:
    claim = nomination_claim()
    evidence = nomination_evidence()
    profile = build_profile_projection(
        person(),
        [claim],
        {claim.id: [evidence]},
        [],
        [],
    )

    summary = section(profile, "summary")
    timeline = section(profile, "career_timeline")
    power = section(profile, "current_power_tasks")

    assert summary["status"] == "AVAILABLE"
    assert timeline["status"] == "AVAILABLE"
    assert summary["entries"][0]["details"]["predicate"] == "NOMINATED_AS"
    assert summary["entries"][0]["claim_id"] == str(CLAIM_ID)
    assert summary["entries"][0]["evidence_ids"] == [str(EVIDENCE_ID)]
    assert summary["entries"][0]["source_ids"] == [str(SOURCE_ID)]
    assert power["status"] == "UNKNOWN"
    assert power["entries"] == []


def test_projection_never_copies_evidence_excerpt() -> None:
    claim = nomination_claim()
    evidence = nomination_evidence()
    profile = build_profile_projection(
        person(),
        [claim],
        {claim.id: [evidence]},
        [],
        [],
    )

    assert "projection must not copy this excerpt" not in str(profile)


def test_typed_relationship_is_stakeholder_but_co_mention_only_is_not() -> None:
    claim = nomination_claim()
    evidence = nomination_evidence()
    relationships = [
        {
            "id": "rel-appointment",
            "person_id": str(PERSON_ID),
            "related_organization_id": "org-1",
            "related_person_id": None,
            "relationship_type": "appointed leadership",
            "strength": "STRONG",
            "evidence": [
                {
                    "claim_evidence_id": str(EVIDENCE_ID),
                    "evidence_type": "APPOINTMENT",
                }
            ],
        },
        {
            "id": "rel-comention",
            "person_id": str(PERSON_ID),
            "related_person_id": "person-2",
            "related_organization_id": None,
            "relationship_type": "same announcement co-mention",
            "strength": "WEAK",
            "evidence": [
                {
                    "claim_evidence_id": str(EVIDENCE_ID),
                    "evidence_type": "CO_MENTION",
                }
            ],
        },
    ]
    profile = build_profile_projection(
        person(),
        [claim],
        {claim.id: [evidence]},
        relationships,
        [],
    )

    stakeholders = section(profile, "stakeholders")
    assert stakeholders["status"] == "AVAILABLE"
    assert [item["id"] for item in stakeholders["entries"]] == [
        "relationship:rel-appointment"
    ]
    assert stakeholders["entries"][0]["source_ids"] == [str(SOURCE_ID)]


def test_decision_episode_is_projected_without_creating_repeated_pattern() -> None:
    claim = nomination_claim()
    evidence = nomination_evidence()
    profile = build_profile_projection(
        person(),
        [claim],
        {claim.id: [evidence]},
        [],
        [
            {
                "id": "episode-1",
                "person_id": str(PERSON_ID),
                "description": "Public decision episode",
                "action": "acted",
                "target": "policy",
                "outcome": "published",
                "source_ids": [str(SOURCE_ID)],
                "independent_origin_ids": ["origin-1"],
            }
        ],
    )

    episodes = section(profile, "decision_episodes")
    patterns = section(profile, "repeated_patterns")
    assert episodes["status"] == "AVAILABLE"
    assert episodes["entries"][0]["source_ids"] == [str(SOURCE_ID)]
    assert patterns["status"] == "UNKNOWN"
    assert patterns["entries"] == []


def test_limitations_surface_unknown_sections_instead_of_filling_them() -> None:
    claim = nomination_claim()
    evidence = nomination_evidence()
    profile = build_profile_projection(
        person(),
        [claim],
        {claim.id: [evidence]},
        [],
        [],
    )

    limitations = section(profile, "limitations")
    limited_sections = {
        item["details"].get("section_id")
        for item in limitations["entries"]
        if item["kind"] == "LIMITATION"
    }
    assert "current_power_tasks" in limited_sections
    assert "forecast" in limited_sections
    assert "hearing_questions" in limited_sections
    assert profile["coverage"]["unknown"] > 0
