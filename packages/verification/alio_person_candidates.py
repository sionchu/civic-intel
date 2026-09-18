from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from uuid import UUID

from packages.domain.contracts import Claim, ClaimEvidence, Organization, Person
from packages.domain.enums import IdentityDecisionClass, IdentityStatus, PublicationStatus
from packages.persistence import SqlAlchemyRepository
from packages.rendering.alio_organization_content import (
    ALIO_EXECUTIVE_PREDICATE,
    ALIO_EXECUTIVE_SCOPE,
    ALIO_EXECUTIVE_SEMANTIC_SCOPE,
    ALIO_EXECUTIVE_SOURCE_CONTRACT,
)

from .cross_lane_identity import resolve_cross_lane_identity
from .identity import IdentityCandidate

DISCOVERY_REASON = "EXACT_CANONICAL_NAME_OVERLAP_DISCOVERY_ONLY"


class AlioCandidatePipelineError(ValueError):
    pass


@dataclass(frozen=True)
class CrossLaneCandidatePair:
    alio_organization_id: UUID
    alio_claim_id: UUID
    alio_evidence_ids: tuple[UUID, ...]
    executive_name: str
    position_text: str | None
    organization_name: str
    alio_apba_id: str | None
    term_start: str | None
    term_end: str | None
    person_id: UUID
    person_name: str
    person_birth_date: date | None
    discovery_reason: str
    identity_status: IdentityStatus
    decision_class: IdentityDecisionClass
    identity_reasons: tuple[str, ...]

    @property
    def candidate_key(self) -> tuple[UUID, UUID]:
        return self.alio_claim_id, self.person_id

    def to_dict(self) -> dict[str, object]:
        return {
            "executive_name": self.executive_name,
            "organization_id": str(self.alio_organization_id),
            "organization_name": self.organization_name,
            "position_text": self.position_text,
            "term_start": self.term_start,
            "term_end": self.term_end,
            "alio_claim_id": str(self.alio_claim_id),
            "alio_evidence_ids": [str(item) for item in self.alio_evidence_ids],
            "alio_apba_id": self.alio_apba_id,
            "person_id": str(self.person_id),
            "person_name": self.person_name,
            "person_birth_date": (
                self.person_birth_date.isoformat() if self.person_birth_date else None
            ),
            "discovery_reason": self.discovery_reason,
            "identity_status": self.identity_status.value,
            "decision_class": self.decision_class.value,
            "identity_reasons": list(self.identity_reasons),
        }


@dataclass(frozen=True)
class AlioCandidateGeneration:
    alio_executive_claims_considered: int
    public_people_considered: int
    candidates: tuple[CrossLaneCandidatePair, ...]

    def to_dict(self) -> dict[str, object]:
        resolved = sum(item.identity_status == IdentityStatus.RESOLVED for item in self.candidates)
        review = sum(item.identity_status == IdentityStatus.REVIEW for item in self.candidates)
        unresolved = sum(item.identity_status == IdentityStatus.UNRESOLVED for item in self.candidates)
        return {
            "status": "REVIEW_ONLY",
            "alio_executive_claims_considered": self.alio_executive_claims_considered,
            "public_people_considered": self.public_people_considered,
            "candidate_pairs": len(self.candidates),
            "resolved_pairs": resolved,
            "review_pairs": review,
            "unresolved_pairs": unresolved,
            "candidates": [item.to_dict() for item in self.candidates],
        }


def _normalized_name(value: str) -> str:
    return value.strip().casefold()


def _optional_qualifier(qualifiers: dict[str, str], key: str) -> str | None:
    value = qualifiers.get(key)
    if not isinstance(value, str):
        return None
    value = value.strip()
    return value or None


def _load_published_alio_claims(
    repository: SqlAlchemyRepository,
) -> tuple[tuple[Organization, Claim, tuple[ClaimEvidence, ...]], ...]:
    organizations = tuple(repository.public_organizations())
    contexts = repository.published_organization_claim_contexts(
        item.id for item in organizations
    )
    claims: list[tuple[Organization, Claim, tuple[ClaimEvidence, ...]]] = []
    for organization in organizations:
        organization_claims, evidence_by_claim = contexts.get(organization.id, ((), {}))
        for claim in organization_claims:
            if (
                claim.organization_id != organization.id
                or claim.publication_status != PublicationStatus.PUBLISHED
                or claim.superseded_at is not None
                or claim.predicate != ALIO_EXECUTIVE_PREDICATE
                or claim.qualifiers.get("source_contract") != ALIO_EXECUTIVE_SOURCE_CONTRACT
                or claim.qualifiers.get("source_scope") != ALIO_EXECUTIVE_SCOPE
                or claim.qualifiers.get("semantic_scope") != ALIO_EXECUTIVE_SEMANTIC_SCOPE
            ):
                continue
            if _optional_qualifier(claim.qualifiers, "canonical_name") is None:
                continue
            evidence = tuple(
                sorted(evidence_by_claim.get(claim.id, ()), key=lambda item: str(item.id))
            )
            if not evidence:
                raise AlioCandidatePipelineError(
                    "published ALIO executive Claim lacks ClaimEvidence"
                )
            if len({item.id for item in evidence}) != len(evidence):
                raise AlioCandidatePipelineError(
                    "published ALIO executive Claim has duplicate ClaimEvidence"
                )
            claims.append((organization, claim, evidence))
    return tuple(
        sorted(
            claims,
            key=lambda item: (
                _optional_qualifier(item[1].qualifiers, "canonical_name") or "",
                item[0].name,
                str(item[1].id),
            ),
        )
    )


def generate_alio_cross_lane_candidates(
    repository: SqlAlchemyRepository,
) -> AlioCandidateGeneration:
    """Generate deterministic, non-persistent ALIO-to-Person review candidates."""

    repository.assert_ready()
    alio_claims = _load_published_alio_claims(repository)
    people = tuple(
        item
        for item in repository.public_people()
        if item.identity_status == IdentityStatus.RESOLVED and item.superseded_at is None
    )
    people_by_name: dict[str, list[Person]] = defaultdict(list)
    for person in people:
        normalized = _normalized_name(person.canonical_name)
        if normalized:
            people_by_name[normalized].append(person)

    by_key: dict[tuple[UUID, UUID], CrossLaneCandidatePair] = {}
    for organization, claim, evidence in alio_claims:
        executive_name = _optional_qualifier(claim.qualifiers, "canonical_name")
        assert executive_name is not None
        for person in people_by_name.get(_normalized_name(executive_name), ()):
            alio_candidate = IdentityCandidate(
                canonical_name=executive_name,
                birth_date=None,
                office=_optional_qualifier(claim.qualifiers, "position_text"),
                organization=organization.name,
            )
            person_candidate = IdentityCandidate(
                canonical_name=person.canonical_name,
                birth_date=person.birth_date,
                office=None,
                organization=None,
            )
            decision = resolve_cross_lane_identity(alio_candidate, person_candidate, evidence=())
            if not (
                decision.status == IdentityStatus.REVIEW
                and decision.decision_class == IdentityDecisionClass.CONTEXT_REVIEW
                and "cross_lane_bridge_evidence_missing" in decision.reasons
            ):
                raise AlioCandidatePipelineError(
                    "ALIO name-overlap candidate resolved without bridge evidence"
                )
            candidate = CrossLaneCandidatePair(
                alio_organization_id=organization.id,
                alio_claim_id=claim.id,
                alio_evidence_ids=tuple(item.id for item in evidence),
                executive_name=executive_name,
                position_text=_optional_qualifier(claim.qualifiers, "position_text"),
                organization_name=organization.name,
                alio_apba_id=_optional_qualifier(claim.qualifiers, "alio_apba_id"),
                term_start=_optional_qualifier(claim.qualifiers, "term_start"),
                term_end=_optional_qualifier(claim.qualifiers, "term_end"),
                person_id=person.id,
                person_name=person.canonical_name,
                person_birth_date=person.birth_date,
                discovery_reason=DISCOVERY_REASON,
                identity_status=decision.status,
                decision_class=decision.decision_class,
                identity_reasons=decision.reasons,
            )
            existing = by_key.get(candidate.candidate_key)
            if existing is not None:
                if existing != candidate:
                    raise AlioCandidatePipelineError(
                        "duplicate ALIO candidate key has conflicting values"
                    )
                continue
            by_key[candidate.candidate_key] = candidate

    ordered = tuple(
        sorted(
            by_key.values(),
            key=lambda item: (
                item.executive_name,
                item.organization_name,
                str(item.alio_claim_id),
                str(item.person_id),
            ),
        )
    )
    return AlioCandidateGeneration(
        alio_executive_claims_considered=len(alio_claims),
        public_people_considered=len(people),
        candidates=ordered,
    )
