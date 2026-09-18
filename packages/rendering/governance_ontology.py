from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum
from typing import Iterable
from uuid import UUID

from packages.domain.enums import EpistemicStatus, PublicationStatus


class OntologyNodeKind(StrEnum):
    PERSON = "PERSON"
    ORGANIZATION = "ORGANIZATION"
    EDUCATIONAL_INSTITUTION = "EDUCATIONAL_INSTITUTION"
    COMPANY = "COMPANY"
    COMMITTEE = "COMMITTEE"
    OFFICE = "OFFICE"
    HEARING = "HEARING"
    ISSUE = "ISSUE"


class OntologyRelationType(StrEnum):
    HELD_ROLE = "HELD_ROLE"
    WORKED_AT = "WORKED_AT"
    STUDIED_AT = "STUDIED_AT"
    SERVED_ON = "SERVED_ON"
    DIRECTOR_OF = "DIRECTOR_OF"
    APPOINTED_TO = "APPOINTED_TO"
    APPEARED_AT = "APPEARED_AT"
    QUESTIONED = "QUESTIONED"
    AUDITED_BY = "AUDITED_BY"


@dataclass(frozen=True)
class OntologyNode:
    id: str
    kind: OntologyNodeKind
    label: str
    canonical_id: UUID | None = None
    source_key: str | None = None

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ValueError("ontology node id is required")
        if not self.label.strip():
            raise ValueError("ontology node label is required")
        if self.kind in {OntologyNodeKind.PERSON, OntologyNodeKind.ORGANIZATION}:
            if self.canonical_id is None:
                raise ValueError("public Person/Organization ontology nodes require canonical_id")


@dataclass(frozen=True)
class OntologyEdge:
    id: str
    source_node_id: str
    target_node_id: str
    relation_type: OntologyRelationType
    epistemic_status: EpistemicStatus
    publication_status: PublicationStatus
    claim_ids: tuple[UUID, ...]
    evidence_ids: tuple[UUID, ...]
    source_ids: tuple[UUID, ...]
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    as_of: date | None = None
    note: str | None = None

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ValueError("ontology edge id is required")
        if self.source_node_id == self.target_node_id:
            raise ValueError("ontology edge cannot be a self-loop")
        if self.publication_status != PublicationStatus.PUBLISHED:
            raise ValueError("public ontology edges must be PUBLISHED")
        if self.epistemic_status not in {EpistemicStatus.FACT, EpistemicStatus.CLAIM}:
            raise ValueError("public ontology edges require FACT or CLAIM status")
        if not self.claim_ids or not self.evidence_ids or not self.source_ids:
            raise ValueError("public ontology edges require Claim, Evidence, and Source provenance")
        if len(set(self.claim_ids)) != len(self.claim_ids):
            raise ValueError("ontology edge claim_ids must be unique")
        if len(set(self.evidence_ids)) != len(self.evidence_ids):
            raise ValueError("ontology edge evidence_ids must be unique")
        if len(set(self.source_ids)) != len(self.source_ids):
            raise ValueError("ontology edge source_ids must be unique")
        if self.valid_from is not None and self.valid_to is not None:
            if self.valid_to < self.valid_from:
                raise ValueError("ontology edge valid_to precedes valid_from")


@dataclass(frozen=True)
class OntologyGraph:
    nodes: tuple[OntologyNode, ...]
    edges: tuple[OntologyEdge, ...]

    def __post_init__(self) -> None:
        node_ids = [node.id for node in self.nodes]
        if len(set(node_ids)) != len(node_ids):
            raise ValueError("ontology graph node ids must be unique")
        edge_ids = [edge.id for edge in self.edges]
        if len(set(edge_ids)) != len(edge_ids):
            raise ValueError("ontology graph edge ids must be unique")
        known_nodes = set(node_ids)
        for edge in self.edges:
            if edge.source_node_id not in known_nodes or edge.target_node_id not in known_nodes:
                raise ValueError("ontology edge endpoint is missing from graph")


@dataclass(frozen=True)
class OntologyPathStep:
    edge: OntologyEdge
    from_node_id: str
    to_node_id: str
    traversed_forward: bool


@dataclass(frozen=True)
class OntologyPath:
    from_node_id: str
    to_node_id: str
    steps: tuple[OntologyPathStep, ...]

    @property
    def hops(self) -> int:
        return len(self.steps)


def shortest_connection_paths(
    graph: OntologyGraph,
    from_node_id: str,
    to_node_id: str,
    *,
    max_hops: int = 3,
    max_paths: int = 5,
    relation_types: Iterable[OntologyRelationType] | None = None,
) -> tuple[OntologyPath, ...]:
    """Return deterministic bounded shortest paths over publishable ontology edges.

    Edges retain their semantic direction, but exploration is bidirectional so paths such as
    Person -> School <- Person remain discoverable. Each returned step records whether traversal
    followed the stored edge direction.
    """

    if not 1 <= max_hops <= 3:
        raise ValueError("max_hops must be between 1 and 3")
    if not 1 <= max_paths <= 5:
        raise ValueError("max_paths must be between 1 and 5")
    if from_node_id == to_node_id:
        raise ValueError("connection path requires two distinct nodes")

    node_ids = {node.id for node in graph.nodes}
    if from_node_id not in node_ids or to_node_id not in node_ids:
        raise ValueError("connection path endpoint is missing from graph")

    allowed_relations = set(relation_types) if relation_types is not None else None
    adjacency: dict[str, list[tuple[str, OntologyEdge, bool]]] = {}
    for edge in graph.edges:
        if allowed_relations is not None and edge.relation_type not in allowed_relations:
            continue
        adjacency.setdefault(edge.source_node_id, []).append(
            (edge.target_node_id, edge, True)
        )
        adjacency.setdefault(edge.target_node_id, []).append(
            (edge.source_node_id, edge, False)
        )

    for neighbors in adjacency.values():
        neighbors.sort(
            key=lambda item: (
                item[1].relation_type.value,
                item[1].id,
                item[0],
            )
        )

    queue: deque[tuple[str, tuple[OntologyPathStep, ...], frozenset[str]]] = deque(
        [(from_node_id, (), frozenset({from_node_id}))]
    )
    found: list[OntologyPath] = []
    shortest_hops: int | None = None

    while queue and len(found) < max_paths:
        current_node, steps, seen = queue.popleft()
        if shortest_hops is not None and len(steps) >= shortest_hops:
            continue
        if len(steps) >= max_hops:
            continue

        for next_node, edge, traversed_forward in adjacency.get(current_node, ()):
            if next_node in seen:
                continue
            next_steps = steps + (
                OntologyPathStep(
                    edge=edge,
                    from_node_id=current_node,
                    to_node_id=next_node,
                    traversed_forward=traversed_forward,
                ),
            )
            if next_node == to_node_id:
                if shortest_hops is None:
                    shortest_hops = len(next_steps)
                if len(next_steps) == shortest_hops:
                    found.append(
                        OntologyPath(
                            from_node_id=from_node_id,
                            to_node_id=to_node_id,
                            steps=next_steps,
                        )
                    )
                    if len(found) >= max_paths:
                        break
                continue

            if shortest_hops is None or len(next_steps) < shortest_hops:
                queue.append((next_node, next_steps, seen | {next_node}))

    return tuple(found)
