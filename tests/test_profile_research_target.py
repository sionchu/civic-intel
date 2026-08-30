import json
from datetime import date

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


def corporate_observation(*, birth_date: date | None = None) -> ProfileTargetObservation:
    return ProfileTargetObservation(
        lane="CORPORATE_OFFICIAL_PROFILE",
        candidate=IdentityCandidate(
            canonical_name="김AI",
            birth_date=birth_date,
            office="AI센터장",
            organization="테스트클라우드",
            career_anchors=("company_profile:testcloud-kimai",),
        ),
        source_refs=("company-official-profile-kimai", "shared-public-source"),
        discovery_reasons=("PRIVATE_SECTOR_SENIOR_TALENT",),
        appointment_target_slugs=("ai-policy-senior-role",),
    )


def presidential_observation(*, birth_date: date | None = None) -> ProfileTargetObservation:
    return ProfileTargetObservation(
        lane="PRESIDENTIAL_PERSONNEL",
        candidate=IdentityCandidate(
            canonical_name="김AI",
            birth_date=birth_date,
            office="AI정책수석비서관",
            organization="대통령비서실",
            career_anchors=("presidential_personnel:test-kimai",),
        ),
        source_refs=("presidential-briefing-kimai", "shared-public-source"),
        discovery_reasons=("PRESIDENTIAL_APPOINTMENT",),
        appointment_target_slugs=("ai-policy-senior-role", "national-ai-commission-vice-chair"),
    )


def continuity_evidence() -> tuple[CrossLaneIdentityEvidence, ...]:
    return (
        CrossLaneIdentityEvidence(
            evidence_type=CrossLaneIdentityEvidenceType.OFFICIAL_CAREER_CONTINUITY,
            source_ref="presidential-briefing-kimai",
            from_role="테스트클라우드 AI센터장",
            to_role="대통령비서실 AI정책수석비서관",
        ),
    )


def test_resolved_corporate_to_presidential_observations_build_one_target() -> None:
    primary = corporate_observation()
    linked = presidential_observation()

    target = build_profile_research_target(
        primary,
        (ProfileTargetLink(linked, continuity_evidence()),),
    )

    assert target.canonical_name == "김AI"
    assert target.source_lanes == ("CORPORATE_OFFICIAL_PROFILE", "PRESIDENTIAL_PERSONNEL")
    assert target.discovery_reasons == (
        "PRIVATE_SECTOR_SENIOR_TALENT",
        "PRESIDENTIAL_APPOINTMENT",
    )
    assert target.appointment_target_slugs == (
        "ai-policy-senior-role",
        "national-ai-commission-vice-chair",
    )
    assert target.linked[0].decision.status.value == "RESOLVED"
    assert target.linked[0].observation.candidate.organization == "대통령비서실"


def test_same_name_without_bridge_evidence_cannot_enter_profile_target() -> None:
    with pytest.raises(ProfileTargetBuildError, match="RESOLVED"):
        build_profile_research_target(
            corporate_observation(),
            (ProfileTargetLink(presidential_observation(), ()),),
        )


def test_birth_date_conflict_cannot_be_overridden_by_continuity_evidence() -> None:
    primary = corporate_observation(birth_date=date(1980, 1, 1))
    linked = presidential_observation(birth_date=date(1981, 1, 1))

    with pytest.raises(ProfileTargetBuildError, match="RESOLVED"):
        build_profile_research_target(
            primary,
            (ProfileTargetLink(linked, continuity_evidence()),),
        )


def test_aggregate_source_refs_are_deduplicated_but_observation_provenance_remains() -> None:
    target = build_profile_research_target(
        corporate_observation(),
        (ProfileTargetLink(presidential_observation(), continuity_evidence()),),
    )
    payload = target.to_dict()

    assert target.source_refs == (
        "company-official-profile-kimai",
        "shared-public-source",
        "presidential-briefing-kimai",
    )
    assert payload["primary"]["source_refs"] == [
        "company-official-profile-kimai",
        "shared-public-source",
    ]
    assert payload["linked_observations"][0]["observation"]["source_refs"] == [
        "presidential-briefing-kimai",
        "shared-public-source",
    ]
    assert payload["linked_observations"][0]["identity"]["evidence_source_refs"] == [
        "presidential-briefing-kimai"
    ]


def test_profile_target_has_no_appointment_probability_or_political_inference_fields() -> None:
    target = build_profile_research_target(
        corporate_observation(),
        (ProfileTargetLink(presidential_observation(), continuity_evidence()),),
    )
    rendered = json.dumps(target.to_dict(), ensure_ascii=False, sort_keys=True).casefold()

    assert "candidate_probability" not in rendered
    assert "appointment_probability" not in rendered
    assert "faction" not in rendered
    assert "loyalty" not in rendered
    assert "influence_score" not in rendered


def test_observation_requires_source_provenance() -> None:
    with pytest.raises(ValueError, match="source_refs"):
        ProfileTargetObservation(
            lane="CORPORATE",
            candidate=IdentityCandidate(canonical_name="김AI"),
            source_refs=(),
        )
