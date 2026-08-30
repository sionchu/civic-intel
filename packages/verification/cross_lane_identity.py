from __future__ import annotations

from dataclasses import dataclass

from packages.domain.enums import CrossLaneIdentityEvidenceType, IdentityStatus

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
    score: int
    reasons: tuple[str, ...]
    evidence_types: tuple[CrossLaneIdentityEvidenceType, ...]


_EVIDENCE_WEIGHTS = {
    CrossLaneIdentityEvidenceType.EXACT_BIRTH_DATE: 50,
    CrossLaneIdentityEvidenceType.EXTERNAL_ID: 60,
    CrossLaneIdentityEvidenceType.OFFICIAL_CAREER_CONTINUITY: 40,
    CrossLaneIdentityEvidenceType.OFFICIAL_BIOGRAPHY_CONTINUITY: 40,
}


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
            -100,
            ("name_conflict",),
            (),
        )

    if left.birth_date and right.birth_date and left.birth_date != right.birth_date:
        return CrossLaneIdentityDecision(
            IdentityStatus.UNRESOLVED,
            -100,
            ("birth_date_conflict",),
            (),
        )

    score = 35
    reasons = ["name_match"]
    accepted_types: list[CrossLaneIdentityEvidenceType] = []
    scored_types: set[CrossLaneIdentityEvidenceType] = set()

    for item in evidence:
        _validate_evidence(left, right, item)
        accepted_types.append(item.evidence_type)
        if item.evidence_type not in scored_types:
            score += _EVIDENCE_WEIGHTS[item.evidence_type]
            scored_types.add(item.evidence_type)
            reasons.append(item.evidence_type.value.casefold())

    if not evidence:
        reasons.append("cross_lane_bridge_evidence_missing")

    status = IdentityStatus.RESOLVED if score >= 70 else IdentityStatus.REVIEW
    return CrossLaneIdentityDecision(
        status,
        score,
        tuple(reasons),
        tuple(accepted_types),
    )
