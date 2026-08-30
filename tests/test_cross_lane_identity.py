from datetime import date

import pytest

from packages.domain.enums import (
    CrossLaneIdentityEvidenceType,
    IdentityDecisionClass,
    IdentityStatus,
)
from packages.verification.cross_lane_identity import (
    CrossLaneIdentityEvidence,
    resolve_cross_lane_identity,
)
from packages.verification.identity import IdentityCandidate


def candidate(
    *,
    name: str = "김인재",
    birth_date: date | None = None,
    office: str | None = None,
    organization: str | None = None,
) -> IdentityCandidate:
    return IdentityCandidate(
        canonical_name=name,
        birth_date=birth_date,
        office=office,
        organization=organization,
    )


def continuity_evidence() -> CrossLaneIdentityEvidence:
    return CrossLaneIdentityEvidence(
        evidence_type=CrossLaneIdentityEvidenceType.OFFICIAL_CAREER_CONTINUITY,
        source_ref="official-personnel-briefing-001",
        from_role="테스트기업 CTO",
        to_role="대통령비서실 수석비서관",
    )


def test_same_name_different_roles_without_bridge_evidence_stays_review() -> None:
    left = candidate(office="CTO", organization="테스트기업")
    right = candidate(office="수석비서관", organization="대통령비서실")

    decision = resolve_cross_lane_identity(left, right)

    assert decision.status == IdentityStatus.REVIEW
    assert decision.decision_class == IdentityDecisionClass.CONTEXT_REVIEW
    assert not hasattr(decision, "score")
    assert "cross_lane_bridge_evidence_missing" in decision.reasons
    assert "office_conflict" not in decision.reasons
    assert "organization_conflict" not in decision.reasons


def test_official_career_continuity_can_resolve_compatible_transition() -> None:
    left = candidate(office="CTO", organization="테스트기업")
    right = candidate(office="수석비서관", organization="대통령비서실")

    decision = resolve_cross_lane_identity(left, right, (continuity_evidence(),))

    assert decision.status == IdentityStatus.RESOLVED
    assert decision.decision_class == IdentityDecisionClass.OFFICIAL_CAREER_CONTINUITY
    assert decision.evidence_types == (
        CrossLaneIdentityEvidenceType.OFFICIAL_CAREER_CONTINUITY,
    )


def test_name_only_never_resolves_even_when_role_text_matches() -> None:
    left = candidate(office="위원", organization="테스트위원회")
    right = candidate(office="위원", organization="테스트위원회")

    assert resolve_cross_lane_identity(left, right).status == IdentityStatus.REVIEW


def test_hard_birth_date_conflict_fails_closed_even_with_continuity_source() -> None:
    left = candidate(
        birth_date=date(1970, 1, 1), office="CTO", organization="테스트기업"
    )
    right = candidate(
        birth_date=date(1980, 1, 1), office="수석비서관", organization="대통령비서실"
    )

    decision = resolve_cross_lane_identity(left, right, (continuity_evidence(),))

    assert decision.status == IdentityStatus.UNRESOLVED
    assert decision.decision_class == IdentityDecisionClass.BIRTH_DATE_CONFLICT
    assert decision.reasons == ("birth_date_conflict",)


def test_source_backed_exact_birth_date_resolves_when_dates_match() -> None:
    dob = date(1975, 4, 7)
    evidence = CrossLaneIdentityEvidence(
        evidence_type=CrossLaneIdentityEvidenceType.EXACT_BIRTH_DATE,
        source_ref="official-biography-001",
    )

    decision = resolve_cross_lane_identity(
        candidate(birth_date=dob, organization="민간기업"),
        candidate(birth_date=dob, organization="정부위원회"),
        (evidence,),
    )

    assert decision.status == IdentityStatus.RESOLVED
    assert decision.decision_class == IdentityDecisionClass.EXACT_BIRTH_DATE


def test_exact_birth_evidence_requires_both_candidate_dates() -> None:
    evidence = CrossLaneIdentityEvidence(
        evidence_type=CrossLaneIdentityEvidenceType.EXACT_BIRTH_DATE,
        source_ref="official-biography-001",
    )
    with pytest.raises(ValueError, match="requires both candidate birth dates"):
        resolve_cross_lane_identity(candidate(), candidate(birth_date=date(1975, 4, 7)), (evidence,))


def test_exact_external_id_match_can_resolve_cross_lane_identity() -> None:
    evidence = CrossLaneIdentityEvidence(
        evidence_type=CrossLaneIdentityEvidenceType.EXTERNAL_ID,
        source_ref="official-crosswalk-001",
        namespace="public-person-id",
        left_value="P-001",
        right_value="P-001",
    )

    decision = resolve_cross_lane_identity(
        candidate(organization="기관A"),
        candidate(organization="기관B"),
        (evidence,),
    )
    assert decision.status == IdentityStatus.RESOLVED
    assert decision.decision_class == IdentityDecisionClass.EXTERNAL_ID


def test_mismatched_external_id_evidence_is_rejected() -> None:
    evidence = CrossLaneIdentityEvidence(
        evidence_type=CrossLaneIdentityEvidenceType.EXTERNAL_ID,
        source_ref="official-crosswalk-001",
        namespace="public-person-id",
        left_value="P-001",
        right_value="P-002",
    )
    with pytest.raises(ValueError, match="values do not match"):
        resolve_cross_lane_identity(candidate(), candidate(), (evidence,))


def test_evidence_requires_source_and_continuity_roles() -> None:
    with pytest.raises(ValueError, match="requires source_ref"):
        CrossLaneIdentityEvidence(
            evidence_type=CrossLaneIdentityEvidenceType.OFFICIAL_CAREER_CONTINUITY,
            source_ref="",
            from_role="기업 CTO",
            to_role="정부 수석",
        )

    with pytest.raises(ValueError, match="requires from_role and to_role"):
        CrossLaneIdentityEvidence(
            evidence_type=CrossLaneIdentityEvidenceType.OFFICIAL_BIOGRAPHY_CONTINUITY,
            source_ref="official-bio",
        )


def test_duplicate_same_evidence_type_keeps_one_explicit_decision_class() -> None:
    first = continuity_evidence()
    second = CrossLaneIdentityEvidence(
        evidence_type=CrossLaneIdentityEvidenceType.OFFICIAL_CAREER_CONTINUITY,
        source_ref="official-personnel-briefing-002",
        from_role="테스트기업 CTO",
        to_role="대통령비서실 수석비서관",
    )

    decision = resolve_cross_lane_identity(candidate(), candidate(), (first, second))

    assert decision.status == IdentityStatus.RESOLVED
    assert decision.decision_class == IdentityDecisionClass.OFFICIAL_CAREER_CONTINUITY
    assert len(decision.evidence_types) == 2


def test_different_names_fail_before_cross_lane_evidence() -> None:
    decision = resolve_cross_lane_identity(
        candidate(name="김인재"), candidate(name="이인재"), (continuity_evidence(),)
    )
    assert decision.status == IdentityStatus.UNRESOLVED
    assert decision.decision_class == IdentityDecisionClass.NAME_CONFLICT
    assert decision.reasons == ("name_conflict",)


def test_cross_lane_evidence_taxonomy_has_no_proximity_or_political_signal() -> None:
    names = {item.name for item in CrossLaneIdentityEvidenceType}
    assert "CO_MENTION" not in names
    assert "PROXIMITY" not in names
    assert "FACTION" not in names
    assert "IDEOLOGY" not in names
