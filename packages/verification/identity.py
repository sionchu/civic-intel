from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from packages.domain.enums import IdentityStatus


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
    score: int
    reasons: tuple[str, ...]


def resolve_identity(observed: IdentityCandidate, candidate: IdentityCandidate) -> IdentityDecision:
    reasons: list[str] = []
    names_a = {observed.canonical_name.casefold(), *(x.casefold() for x in observed.aliases)}
    names_b = {candidate.canonical_name.casefold(), *(x.casefold() for x in candidate.aliases)}
    if not names_a & names_b:
        return IdentityDecision(IdentityStatus.UNRESOLVED, -100, ("name_conflict",))
    score = 35
    reasons.append("name_match")
    if observed.birth_date and candidate.birth_date:
        if observed.birth_date != candidate.birth_date:
            return IdentityDecision(IdentityStatus.REVIEW, -100, ("birth_date_conflict",))
        score += 40
        reasons.append("birth_date_match")
    for label, left, right, weight in (
        ("office", observed.office, candidate.office, 20),
        ("organization", observed.organization, candidate.organization, 15),
    ):
        if left and right:
            if left.casefold() == right.casefold():
                score += weight
                reasons.append(f"{label}_match")
            else:
                score -= weight
                reasons.append(f"{label}_conflict")
    overlap = {x.casefold() for x in observed.career_anchors} & {
        x.casefold() for x in candidate.career_anchors
    }
    score += min(len(overlap), 2) * 10
    if overlap:
        reasons.append("career_anchor_match")
    status = (
        IdentityStatus.RESOLVED
        if score >= 70
        else IdentityStatus.REVIEW
        if score >= 20
        else IdentityStatus.UNRESOLVED
    )
    return IdentityDecision(status, score, tuple(reasons))
