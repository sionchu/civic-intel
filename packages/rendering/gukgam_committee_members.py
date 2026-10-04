from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from uuid import UUID

from packages.domain.contracts import Claim, ClaimEvidence, Person, Source, SourcePolicy
from packages.domain.enums import EpistemicStatus, IdentityStatus, PublicationStatus
from packages.rendering.governance_ontology import split_assembly_committee_names
from packages.rendering.gukgam_organization_claim import GukgamAuditTargetProjection
from packages.verification.assembly_base_profile import (
    ASSEMBLY_BASE_PROFILE_SOURCE_CONTRACT,
)
from packages.verification.claims import validate_claim_publication

GUKGAM_COMMITTEE_MEMBERS_SEMANTICS = "PUBLIC_CLAIM_BACKED_GUKGAM_COMMITTEE_MEMBERS_V1"
GUKGAM_COMMITTEE_MEMBERS_COVERAGE = "BOUNDED_INCOMPLETE_PUBLISHED_CLAIMS_ONLY"
GUKGAM_COMMITTEE_ROSTER_SEMANTICS = "MEMBER_ROSTER_SNAPSHOT_NOT_AUDIT_DAY_ATTENDANCE"

_COMMITTEE_PREDICATE = "ASSEMBLY_COMMITTEES"
_PARTY_PREDICATE = "ASSEMBLY_PARTY"
_PARTY_FIELD = {_COMMITTEE_PREDICATE: "committees", _PARTY_PREDICATE: "party"}
# The only Claim predicates the projection reads; callers may narrow their Claim read to these.
GUKGAM_COMMITTEE_ROSTER_PREDICATES = (_COMMITTEE_PREDICATE, _PARTY_PREDICATE)


_LIMITATIONS = (
    (
        "Members come from published current-roster committee Claims of public RESOLVED "
        "People; the roster is a member-roster snapshot, not audit-day attendance."
    ),
    "Committee membership does not mean the member questioned any audited institution.",
    (
        "Only committee names used by published Gukgam target Claims are listed, matched "
        "by exact official name; former or renamed committee names are not merged."
    ),
    "Coverage is bounded and incomplete; a missing member is not evidence of non-membership.",
)


class GukgamCommitteeMembersError(ValueError):
    pass


@dataclass(frozen=True)
class GukgamCommitteeMember:
    person_id: UUID
    canonical_name: str
    party: str | None
    party_claim_id: UUID | None
    claim_id: UUID
    epistemic_status: str
    evidence_ids: tuple[UUID, ...]
    source_ids: tuple[UUID, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "person": {"id": str(self.person_id), "name": self.canonical_name},
            "party": self.party,
            "party_claim_id": str(self.party_claim_id) if self.party_claim_id else None,
            "claim_id": str(self.claim_id),
            "epistemic_status": self.epistemic_status,
            "evidence_ids": [str(item) for item in self.evidence_ids],
            "source_ids": [str(item) for item in self.source_ids],
        }


@dataclass(frozen=True)
class GukgamCommitteeMembers:
    committee_name: str
    target_count: int
    members: tuple[GukgamCommitteeMember, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "committee_name": self.committee_name,
            "target_count": self.target_count,
            "member_count": len(self.members),
            "members": [member.to_dict() for member in self.members],
        }


@dataclass(frozen=True)
class GukgamCommitteeMembersProjection:
    year: int
    committees: tuple[GukgamCommitteeMembers, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "semantics": GUKGAM_COMMITTEE_MEMBERS_SEMANTICS,
            "coverage": GUKGAM_COMMITTEE_MEMBERS_COVERAGE,
            "roster_semantics": GUKGAM_COMMITTEE_ROSTER_SEMANTICS,
            "year": self.year,
            "committee_count": len(self.committees),
            "committees": [item.to_dict() for item in self.committees],
            "limitations": list(_LIMITATIONS),
        }


def _current_published(claim: Claim) -> bool:
    return (
        claim.publication_status == PublicationStatus.PUBLISHED
        and claim.epistemic_status in {EpistemicStatus.FACT, EpistemicStatus.CLAIM}
        and claim.superseded_at is None
        and claim.organization_id is None
        and bool(claim.object_text.strip())
    )


def _require_roster_contract(claim: Claim) -> None:
    if (
        claim.qualifiers.get("source_contract") != ASSEMBLY_BASE_PROFILE_SOURCE_CONTRACT
        or claim.qualifiers.get("field_name") != _PARTY_FIELD[claim.predicate]
    ):
        raise GukgamCommitteeMembersError(
            f"Assembly roster Claim has invalid source contract: {claim.id}"
        )


def _latest(claims: Sequence[Claim]) -> Claim:
    return max(claims, key=lambda item: (item.valid_from, item.recorded_at, str(item.id)))


def build_gukgam_committee_members_projection(
    targets: GukgamAuditTargetProjection,
    people: Sequence[Person],
    contexts: Mapping[
        UUID,
        tuple[Sequence[Claim], Mapping[UUID, Sequence[ClaimEvidence]]],
    ],
    *,
    sources: Mapping[UUID, Source],
    policies: Mapping[UUID, SourcePolicy],
) -> GukgamCommitteeMembersProjection:
    """List public Assembly members of the committees named by published Gukgam targets."""

    target_counts: dict[str, int] = {}
    for item in targets.items:
        target_counts[item.committee_name] = target_counts.get(item.committee_name, 0) + 1

    members_by_committee: dict[str, list[GukgamCommitteeMember]] = {
        name: [] for name in target_counts
    }

    source_map = dict(sources)
    policy_map = dict(policies)
    for person in people:
        if person.identity_status != IdentityStatus.RESOLVED or person.superseded_at is not None:
            continue
        claims, evidence_by_claim = contexts.get(person.id, ((), {}))
        publishable: dict[str, list[Claim]] = {_COMMITTEE_PREDICATE: [], _PARTY_PREDICATE: []}
        for claim in claims:
            if (
                claim.person_id != person.id
                or claim.predicate not in publishable
                or not _current_published(claim)
            ):
                continue
            evidence = list(evidence_by_claim.get(claim.id, ()))
            gate = validate_claim_publication(
                claim, person, evidence, source_map, policy_map
            )
            if not gate.publishable:
                continue
            if not evidence or any(item.claim_id != claim.id for item in evidence):
                raise GukgamCommitteeMembersError(
                    f"Assembly roster Claim evidence is invalid: {claim.id}"
                )
            _require_roster_contract(claim)
            publishable[claim.predicate].append(claim)

        if not publishable[_COMMITTEE_PREDICATE]:
            continue
        committee_claim = _latest(publishable[_COMMITTEE_PREDICATE])
        party_claim = (
            _latest(publishable[_PARTY_PREDICATE]) if publishable[_PARTY_PREDICATE] else None
        )
        evidence = list(evidence_by_claim.get(committee_claim.id, ()))
        names = split_assembly_committee_names(committee_claim.object_text)
        for name in names:
            if name not in members_by_committee:
                continue
            members_by_committee[name].append(
                GukgamCommitteeMember(
                    person_id=person.id,
                    canonical_name=person.canonical_name,
                    party=party_claim.object_text.strip() if party_claim else None,
                    party_claim_id=party_claim.id if party_claim else None,
                    claim_id=committee_claim.id,
                    epistemic_status=committee_claim.epistemic_status.value,
                    evidence_ids=tuple(sorted({item.id for item in evidence}, key=str)),
                    source_ids=tuple(sorted({item.source_id for item in evidence}, key=str)),
                )
            )

    committees = tuple(
        GukgamCommitteeMembers(
            committee_name=name,
            target_count=target_counts[name],
            members=tuple(
                sorted(
                    members_by_committee[name],
                    key=lambda member: (member.canonical_name, str(member.person_id)),
                )
            ),
        )
        for name in sorted(target_counts)
    )
    return GukgamCommitteeMembersProjection(year=targets.year, committees=committees)
