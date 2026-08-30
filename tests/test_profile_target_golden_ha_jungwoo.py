import json
from pathlib import Path
from typing import Any

import pytest

from packages.domain.enums import CrossLaneIdentityEvidenceType
from packages.verification.cross_lane_identity import CrossLaneIdentityEvidence
from packages.verification.identity import IdentityCandidate
from packages.verification.profile_target import (
    ProfileTargetBuildError,
    ProfileTargetLink,
    ProfileTargetObservation,
    build_profile_research_target,
)

GOLDEN_SET = Path(__file__).parent / "golden" / "fixtures" / "golden_set_001.json"
CASE = Path(__file__).parent / "golden" / "fixtures" / "profile_target_ha_jungwoo_001.json"


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def observation(case: dict[str, Any], key: str) -> ProfileTargetObservation:
    observations = case["observations"]
    assert isinstance(observations, dict)
    row = observations[key]
    assert isinstance(row, dict)

    return ProfileTargetObservation(
        lane=str(row["lane"]),
        candidate=IdentityCandidate(
            canonical_name=str(case["canonical_name"]),
            office=str(row["office"]),
            organization=str(row["organization"]),
            career_anchors=tuple(str(item) for item in row.get("career_anchors", [])),
        ),
        source_refs=tuple(str(item) for item in row["source_refs"]),
        discovery_reasons=tuple(str(item) for item in row.get("discovery_reasons", [])),
        appointment_target_slugs=tuple(
            str(item) for item in row.get("appointment_target_slugs", [])
        ),
    )


def continuity_evidence(case: dict[str, Any]) -> tuple[CrossLaneIdentityEvidence, ...]:
    links = case["resolved_links"]
    assert isinstance(links, list) and len(links) == 1
    row = links[0]
    assert isinstance(row, dict)
    return (
        CrossLaneIdentityEvidence(
            evidence_type=CrossLaneIdentityEvidenceType(str(row["evidence_type"])),
            source_ref=str(row["source_ref"]),
            from_role=str(row["from_role"]),
            to_role=str(row["to_role"]),
        ),
    )


def test_case_reuses_existing_golden_set_001_person() -> None:
    case = load_json(CASE)
    golden = load_json(GOLDEN_SET)
    people = golden["people"]
    assert isinstance(people, list)

    matching = [
        item
        for item in people
        if isinstance(item, dict) and item.get("id") == case["golden_set_person_id"]
    ]
    assert len(matching) == 1
    assert matching[0]["canonical_name"] == "하정우"
    assert case["canonical_name"] == "하정우"


def test_official_presidential_continuity_builds_resolved_profile_target() -> None:
    case = load_json(CASE)
    office = observation(case, "presidential_office")
    commission = observation(case, "presidential_commission")

    target = build_profile_research_target(
        office,
        (ProfileTargetLink(commission, continuity_evidence(case)),),
    )

    assert target.canonical_name == "하정우"
    assert target.source_lanes == ("PRESIDENTIAL_OFFICE", "PRESIDENTIAL_COMMISSION")
    assert target.source_refs == (
        "https://www.president.go.kr/briefings/sVNpSTtz",
        "https://www.president.go.kr/briefings/qGTHgnQ8",
    )
    assert target.linked[0].decision.status.value == "RESOLVED"
    assert target.appointment_target_slugs == ("national-ai-strategy-committee-vice-chair",)


def test_commission_role_preserves_nomination_not_completed_appointment() -> None:
    case = load_json(CASE)
    commission = observation(case, "presidential_commission")

    assert "presidential_personnel_action:NOMINATED" in commission.candidate.career_anchors
    assert "presidential_personnel_action:APPOINTED" not in commission.candidate.career_anchors


def test_naver_same_name_context_is_not_auto_merged_without_bridge_evidence() -> None:
    case = load_json(CASE)
    office = observation(case, "presidential_office")
    corporate = observation(case, "corporate_context")

    with pytest.raises(ProfileTargetBuildError, match="RESOLVED"):
        build_profile_research_target(
            office,
            (ProfileTargetLink(corporate, ()),),
        )


def test_unresolved_corporate_source_remains_outside_resolved_target_provenance() -> None:
    case = load_json(CASE)
    office = observation(case, "presidential_office")
    commission = observation(case, "presidential_commission")
    target = build_profile_research_target(
        office,
        (ProfileTargetLink(commission, continuity_evidence(case)),),
    )

    assert "https://www.navercorp.com/media/pressReleasesDetail?seq=31410" not in target.source_refs
    assert "CORPORATE_OFFICIAL_PROFILE" not in target.source_lanes


def test_real_golden_target_has_no_political_or_probability_scores() -> None:
    case = load_json(CASE)
    target = build_profile_research_target(
        observation(case, "presidential_office"),
        (
            ProfileTargetLink(
                observation(case, "presidential_commission"),
                continuity_evidence(case),
            ),
        ),
    )
    rendered = json.dumps(target.to_dict(), ensure_ascii=False, sort_keys=True).casefold()

    assert "candidate_probability" not in rendered
    assert "appointment_probability" not in rendered
    assert "faction" not in rendered
    assert "loyalty" not in rendered
    assert "influence_score" not in rendered
