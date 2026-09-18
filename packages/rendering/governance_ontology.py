from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from uuid import UUID

from packages.domain.contracts import Claim, ClaimEvidence, Person
from packages.domain.enums import IdentityStatus, PublicationStatus


class GovernanceOntologyError(ValueError):
    pass


@dataclass(frozen=True)
class OntologyNode:
    id: str
    kind: str
    label: str
    canonical_id: UUID | None = None
    claim_ids: tuple[UUID, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "kind": self.kind,
            "label": self.label,
            "canonical_id": str(self.canonical_id) if self.canonical_id else None,
            "claim_ids": [str(item) for item in self.claim_ids],
        }


@dataclass(frozen=True)
class OntologyEdge:
    id: str
    source: str
    target: str
    relation_type: str
    label: str
    claim_id: UUID
    evidence_ids: tuple[UUID, ...]
    source_ids: tuple[UUID, ...]
    epistemic_status: str
    publication_status: str
    valid_from: str | None
    valid_to: str | None

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "source": self.source,
            "target": self.target,
            "relation_type": self.relation_type,
            "label": self.label,
            "claim_id": str(self.claim_id),
            "evidence_ids": [str(item) for item in self.evidence_ids],
            "source_ids": [str(item) for item in self.source_ids],
            "epistemic_status": self.epistemic_status,
            "publication_status": self.publication_status,
            "valid_from": self.valid_from,
            "valid_to": self.valid_to,
        }


@dataclass(frozen=True)
class OntologyGraph:
    center_node_id: str
    nodes: tuple[OntologyNode, ...]
    edges: tuple[OntologyEdge, ...]
    semantics: str = "READ_ONLY_PROJECTION_FROM_CANONICAL_CLAIM_EVIDENCE"

    def to_dict(self) -> dict[str, object]:
        return {
            "center_node_id": self.center_node_id,
            "nodes": [item.to_dict() for item in self.nodes],
            "edges": [item.to_dict() for item in self.edges],
            "semantics": self.semantics,
            "limitations": [
                "Only source-backed published relations explicitly mapped by the ontology projection are shown.",
                "A displayed path or shared institution does not establish friendship, influence, or motive.",
            ],
        }


_RELATION_MAPPING: dict[str, tuple[str, str]] = {
    "NOMINATED_AS": ("HELD_ROLE", "OFFICE"),
    "DESIGNATED_AS": ("HELD_ROLE", "OFFICE"),
    "APPOINTED_AS": ("HELD_ROLE", "OFFICE"),
    "ELECTED_AS": ("HELD_ROLE", "OFFICE"),
    "CURRENT_OFFICE": ("HELD_ROLE", "OFFICE"),
    "HOLDS_OFFICE": ("HELD_ROLE", "OFFICE"),
    "SERVED_AS": ("HELD_ROLE", "OFFICE"),
    "HELD_ROLE": ("HELD_ROLE", "OFFICE"),
    "WORKED_AS": ("HELD_ROLE", "OFFICE"),
    "APPOINTED_TO": ("APPOINTED_TO", "OFFICE"),
    "WORKED_AT": ("WORKED_AT", "ORGANIZATION"),
    "STUDIED_AT": ("STUDIED_AT", "EDUCATIONAL_INSTITUTION"),
    "SERVED_ON": ("SERVED_ON", "COMMITTEE"),
    "ASSEMBLY_COMMITTEES": ("SERVED_ON", "COMMITTEE"),
    "DIRECTOR_OF": ("DIRECTOR_OF", "COMPANY"),
    "APPEARED_AT": ("APPEARED_AT", "HEARING"),
}


def _iso(value) -> str | None:
    return value.isoformat() if value is not None else None


def _ordered_unique(values: Sequence[UUID]) -> tuple[UUID, ...]:
    return tuple(dict.fromkeys(values))


def build_person_governance_ontology(
    person: Person,
    claims: Sequence[Claim],
    evidence_by_claim: Mapping[UUID, Sequence[ClaimEvidence]],
) -> OntologyGraph:
    """Project one public Person into a small evidence-backed ontology graph.

    The projection is deliberately read-only. Non-canonical target nodes are scoped to the
    supporting Claim and are not reusable identity records.
    """

    if person.identity_status != IdentityStatus.RESOLVED or person.superseded_at is not None:
        raise GovernanceOntologyError("ontology projection requires a current RESOLVED Person")

    center = OntologyNode(
        id=f"person:{person.id}",
        kind="PERSON",
        label=person.canonical_name,
        canonical_id=person.id,
    )
    nodes: list[OntologyNode] = [center]
    edges: list[OntologyEdge] = []

    eligible_claims = sorted(
        (
            claim
            for claim in claims
            if claim.person_id == person.id
            and claim.organization_id is None
            and claim.publication_status == PublicationStatus.PUBLISHED
            and claim.superseded_at is None
            and claim.predicate in _RELATION_MAPPING
            and claim.object_text.strip()
        ),
        key=lambda item: (item.valid_from, str(item.id)),
    )

    for claim in eligible_claims:
        evidence = tuple(evidence_by_claim.get(claim.id, ()))
        if not evidence:
            raise GovernanceOntologyError(
                f"ontology relation Claim lacks ClaimEvidence: {claim.id}"
            )
        if any(item.claim_id != claim.id for item in evidence):
            raise GovernanceOntologyError(
                f"ontology relation evidence points to a different Claim: {claim.id}"
            )

        relation_type, target_kind = _RELATION_MAPPING[claim.predicate]
        target_id = f"{target_kind.casefold()}:{claim.id}"
        nodes.append(
            OntologyNode(
                id=target_id,
                kind=target_kind,
                label=claim.object_text.strip(),
                claim_ids=(claim.id,),
            )
        )
        edges.append(
            OntologyEdge(
                id=f"edge:{claim.id}",
                source=center.id,
                target=target_id,
                relation_type=relation_type,
                label=claim.predicate,
                claim_id=claim.id,
                evidence_ids=tuple(item.id for item in evidence),
                source_ids=_ordered_unique(tuple(item.source_id for item in evidence)),
                epistemic_status=claim.epistemic_status.value,
                publication_status=claim.publication_status.value,
                valid_from=_iso(claim.valid_from),
                valid_to=_iso(claim.valid_to),
            )
        )

    return OntologyGraph(
        center_node_id=center.id,
        nodes=tuple(nodes),
        edges=tuple(edges),
    )
