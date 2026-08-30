from __future__ import annotations

from dataclasses import dataclass, field

from packages.domain.contracts import (
    Claim,
    ClaimEvidence,
    Person,
    Source,
    SourcePolicy,
    SourceSnapshot,
)
from packages.domain.enums import IdentityStatus
from packages.verification.profile_target import ProfileResearchTarget


class ReviewedPersonImportError(ValueError):
    pass


@dataclass(frozen=True)
class ReviewedPersonBundle:
    person: Person
    profile_target: ProfileResearchTarget
    policies: tuple[SourcePolicy, ...] = field(default_factory=tuple)
    sources: tuple[Source, ...] = field(default_factory=tuple)
    snapshots: tuple[SourceSnapshot, ...] = field(default_factory=tuple)
    claims: tuple[Claim, ...] = field(default_factory=tuple)
    evidence: tuple[ClaimEvidence, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if self.person.identity_status != IdentityStatus.RESOLVED:
            raise ReviewedPersonImportError("reviewed person import requires RESOLVED Person identity")
        if self.person.canonical_name.casefold() != self.profile_target.canonical_name.casefold():
            raise ReviewedPersonImportError("Person canonical name must match ProfileResearchTarget")
        if any(link.decision.status != IdentityStatus.RESOLVED for link in self.profile_target.linked):
            raise ReviewedPersonImportError("ProfileResearchTarget contains non-RESOLVED link")
        if any(claim.person_id != self.person.id for claim in self.claims):
            raise ReviewedPersonImportError("all imported claims must reference the imported Person")

        declared = [
            self.person.id,
            *(item.id for item in self.policies),
            *(item.id for item in self.sources),
            *(item.id for item in self.snapshots),
            *(item.id for item in self.claims),
            *(item.id for item in self.evidence),
        ]
        if len(set(declared)) != len(declared):
            raise ReviewedPersonImportError("reviewed person bundle contains duplicate declared IDs")

        claim_ids = {item.id for item in self.claims}
        if any(item.claim_id not in claim_ids for item in self.evidence):
            raise ReviewedPersonImportError("bundle evidence must reference a claim declared in the bundle")
