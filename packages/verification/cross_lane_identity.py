from __future__ import annotations

from dataclasses import dataclass

from packages.domain.enums import (
    CrossLaneIdentityEvidenceType,
    IdentityDecisionClass,
    IdentityStatus,
)

from .identity import IdentityCandidate


@dataclass(frozen=True)
class CrossLaneIdentityEvidence:
    evidence_type: CrossLaneIdentityEvidenceType
    source_ref: str
    namespace: str | None = None
    left_value: str | None = None
    right_value: str | None = None
    from_role: str | None = None
    to_role: str | None = None

    def __post_init__(self) -> None:
        if not self.source_ref.strip():
            raise ValueError("cross-lane identity evidence requires source_ref")
        if self.evidence_type == CrossLaneIdentityEvidenceType.EXTERNAL_ID and (
            not self.namespace or not self.left_value or not self.right_value
        ):
            raise ValueError("EXTERNAL_ID evidence requires namespace and both values")
        if self.evidence_type in {
            CrossLaneIdentityEvidenceType.OFFICIAL_CAREER_CONTINUITY,
            CrossLaneIdentityEvidenceType.OFFICIAL_BIOGRAPHY_CONTINUITY,
        } and (not self.from_role or not self.to_role):
            raise ValueError("continuity evidence requires from_role and to_role")


@dataclass(frozen=True)
class CrossLaneIdentityDecision:
    status: IdentityStatus
    decision_class: IdentityDecisionClass
    reasons: tuple[str, ...]
    evidence_types: tuple[CrossLaneIdentityEvidenceType, ...]


def _names(candidate: IdentityCandidate) -> set[str]:
    return {
        candidate.canonical_name.casefold(),
        *(alias.casefold() for alias in candidate.aliases),
    }


def _validate_evidence(
    left: IdentityCandidate,
    right: IdentityCandidate,
    evidence: CrossLaneIdentityEvidence,
) -> None:
    if evidence.evidence_type == CrossLaneIdentityEvidenceType.EXACT_BIRTH_DATE:
        if not left.birth_date or not right.birth_date:
            raise ValueError("EXACT_BIRTH_DATE evidence requires both candidate birth dates")
        if left.birth_date != right.birth_date:
            raise ValueError("EXACT_BIRTH_DATE evidence conflicts with candidate birth dates")
        return

    if evidence.evidence_type == CrossLaneIdentityEvidenceType.EXTERNAL_ID:
        assert evidence.left_value is not None and evidence.right_value is not None
        if evidence.left_value.strip().casefold() != evidence.right_value.strip().casefold():
            raise ValueError("EXTERNAL_ID evidence values do not match")
        return

    if evidence.evidence_type in {
        CrossLaneIdentityEvidenceType.OFFICIAL_CAREER_CONTINUITY,
        CrossLaneIdentityEvidenceType.OFFICIAL_BIOGRAPHY_CONTINUITY,
    }:
        return

    raise ValueError(f"unsupported cross-lane evidence type: {evidence.evidence_type}")


def resolve_cross_lane_identity(
    left: IdentityCandidate,
    right: IdentityCandidate,
    evidence: tuple[CrossLaneIdentityEvidence, ...] = (),
) -> CrossLaneIdentityDecision:
    """Resolve career-transition identity without treating role changes as identity conflicts.

    Cross-lane resolution is intentionally stricter than a name match. Different offices and
    organizations are neutral because career movement is the object being modeled.
    """

    if not (_names(left) & _names(right)):
        return CrossLaneIdentityDecision(
            IdentityStatus.UNRESOLVED,
            IdentityDecisionClass.NAME_CONFLICT,
            ("name_conflict",),
            (),
        )

    if left.birth_date and right.birth_date and left.birth_date != right.birth_date:
        return CrossLaneIdentityDecision(
            IdentityStatus.UNRESOLVED,
            IdentityDecisionClass.BIRTH_DATE_CONFLICT,
            ("birth_date_conflict",),
            (),
        )

    reasons = ["name_match"]
    accepted_types: list[CrossLaneIdentityEvidenceType] = []
    unique_types: set[CrossLaneIdentityEvidenceType] = set()

    for item in evidence:
        _validate_evidence(left, right, item)
        accepted_types.append(item.evidence_type)
        if item.evidence_type not in unique_types:
            unique_types.add(item.evidence_type)
            reasons.append(item.evidence_type.value.casefold())

    if not evidence:
        reasons.append("cross_lane_bridge_evidence_missing")
        return CrossLaneIdentityDecision(
            IdentityStatus.REVIEW,
            IdentityDecisionClass.CONTEXT_REVIEW,
            tuple(reasons),
            (),
        )

    precedence = (
        (
            CrossLaneIdentityEvidenceType.EXTERNAL_ID,
            IdentityDecisionClass.EXTERNAL_ID,
        ),
        (
            CrossLaneIdentityEvidenceType.EXACT_BIRTH_DATE,
            IdentityDecisionClass.EXACT_BIRTH_DATE,
        ),
        (
            CrossLaneIdentityEvidenceType.OFFICIAL_BIOGRAPHY_CONTINUITY,
            IdentityDecisionClass.OFFICIAL_BIOGRAPHY_CONTINUITY,
        ),
        (
            CrossLaneIdentityEvidenceType.OFFICIAL_CAREER_CONTINUITY,
            IdentityDecisionClass.OFFICIAL_CAREER_CONTINUITY,
        ),
    )
    decision_class = next(
        decision for evidence_type, decision in precedence if evidence_type in unique_types
    )
    return CrossLaneIdentityDecision(
        IdentityStatus.RESOLVED,
        decision_class,
        tuple(reasons),
        tuple(accepted_types),
    )
