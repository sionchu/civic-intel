from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from packages.domain.enums import IdentityDecisionClass, IdentityStatus


@dataclass(frozen=True)
class IdentityCandidate:
    canonical_name: str
    aliases: tuple[str, ...] = ()
    birth_date: date | None = None
    office: str | None = None
    organization: str | None = None
    career_anchors: tuple[str, ...] = ()


@dataclass(frozen=True)
class IdentityDecision:
    status: IdentityStatus
    decision_class: IdentityDecisionClass
    reasons: tuple[str, ...]


def resolve_identity(observed: IdentityCandidate, candidate: IdentityCandidate) -> IdentityDecision:
    reasons: list[str] = []
    names_a = {observed.canonical_name.casefold(), *(x.casefold() for x in observed.aliases)}
    names_b = {candidate.canonical_name.casefold(), *(x.casefold() for x in candidate.aliases)}
    if not names_a & names_b:
        return IdentityDecision(
            IdentityStatus.UNRESOLVED,
            IdentityDecisionClass.NAME_CONFLICT,
            ("name_conflict",),
        )
    reasons.append("name_match")
    if observed.birth_date and candidate.birth_date:
        if observed.birth_date != candidate.birth_date:
            return IdentityDecision(
                IdentityStatus.UNRESOLVED,
                IdentityDecisionClass.BIRTH_DATE_CONFLICT,
                ("birth_date_conflict",),
            )
        reasons.append("birth_date_match")
        return IdentityDecision(
            IdentityStatus.RESOLVED,
            IdentityDecisionClass.EXACT_BIRTH_DATE,
            tuple(reasons),
        )

    context_matches: dict[str, bool] = {}
    for label, left, right in (
        ("office", observed.office, candidate.office),
        ("organization", observed.organization, candidate.organization),
    ):
        context_matches[label] = False
        if left and right:
            if left.casefold() == right.casefold():
                context_matches[label] = True
                reasons.append(f"{label}_match")
            else:
                reasons.append(f"{label}_conflict")
    overlap = {x.casefold() for x in observed.career_anchors} & {
        x.casefold() for x in candidate.career_anchors
    }
    if overlap:
        reasons.append("career_anchor_match")
    if context_matches["office"] and context_matches["organization"]:
        return IdentityDecision(
            IdentityStatus.RESOLVED,
            IdentityDecisionClass.SAME_STATE_CONTEXT,
            tuple(reasons),
        )
    if len(overlap) >= 2 and any(context_matches.values()):
        return IdentityDecision(
            IdentityStatus.RESOLVED,
            IdentityDecisionClass.SHARED_CAREER_ANCHORS,
            tuple(reasons),
        )
    reasons.append("deterministic_identity_evidence_insufficient")
    return IdentityDecision(
        IdentityStatus.REVIEW,
        IdentityDecisionClass.CONTEXT_REVIEW,
        tuple(reasons),
    )
