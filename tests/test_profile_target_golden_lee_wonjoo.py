import json
from pathlib import Path
from typing import Any

from packages.domain.enums import (
    CrossLaneIdentityEvidenceType,
    IdentityStatus,
)
from packages.verification.cross_lane_identity import CrossLaneIdentityEvidence
from packages.verification.identity import IdentityCandidate
from packages.verification.profile_target import (
    ProfileTargetLink,
    ProfileTargetObservation,
    build_profile_research_target,
)

GOLDEN_SET = Path(__file__).parent / "golden" / "fixtures" / "golden_set_001.json"
CASE = Path(__file__).parent / "golden" / "fixtures" / "profile_target_lee_wonjoo_001.json"
SOURCE_REF = "https://www.president.go.kr/briefings/qGTHgnQ8"


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def observation(case: dict[str, Any], key: str) -> ProfileTargetObservation:
    observations = case["observations"]
    assert isinstance(observations, dict)
    row = observations[key]
    assert isinstance(row, dict)
    organization = row.get("organization")

    return ProfileTargetObservation(
        lane=str(row["lane"]),
        candidate=IdentityCandidate(
            canonical_name=str(case["canonical_name"]),
            office=str(row["office"]),
            organization=None if organization is None else str(organization),
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


def test_case_reuses_existing_golden_set_001_person_and_source_ref() -> None:
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
    assert matching[0]["canonical_name"] == "이원주"
    assert case["canonical_name"] == "이원주"

    source = case["sources"]["presidential_designation"]
    assert source["url"] == SOURCE_REF
    assert source["publisher"] == "대한민국 청와대"


def test_official_career_continuity_builds_research_only_profile_target() -> None:
    case = load_json(CASE)
    civil_service = observation(case, "civil_service")
    presidential_adviser = observation(case, "presidential_adviser")

    target = build_profile_research_target(
        civil_service,
        (ProfileTargetLink(presidential_adviser, continuity_evidence(case)),),
    )

    assert target.canonical_name == "이원주"
    assert target.source_lanes == ("CIVIL_SERVICE", "PRESIDENTIAL_OFFICE")
    assert target.source_refs == (SOURCE_REF,)
    assert target.linked[0].decision.status == IdentityStatus.RESOLVED
    assert target.linked[0].decision.decision_class.value == "OFFICIAL_CAREER_CONTINUITY"
    assert target.linked[0].observation.candidate.organization is None

    payload = target.to_dict()
    assert payload["identity_status"] == "RESOLVED"
    assert payload["linked_observations"][0]["identity"]["decision_scope"] == (
        "RESEARCH_IDENTITY_ONLY"
    )
    assert payload["linked_observations"][0]["identity"]["evidence_source_refs"] == [
        SOURCE_REF
    ]
    assert "publishable FACT" in str(payload["semantics"])


def test_designation_semantics_are_not_silently_promoted_to_appointment() -> None:
    case = load_json(CASE)
    adviser = observation(case, "presidential_adviser")

    assert "presidential_personnel_action:DESIGNATED" in adviser.candidate.career_anchors
    assert "presidential_personnel_action:APPOINTED" not in adviser.candidate.career_anchors
