from datetime import UTC, datetime
from uuid import uuid4

import pytest

from packages.domain.enums import EpistemicStatus, PublicationStatus
from packages.rendering.governance_ontology import (
    OntologyEdge,
    OntologyGraph,
    OntologyNode,
    OntologyNodeKind,
    OntologyRelationType,
    shortest_connection_paths,
)


def _node(node_id: str, kind: OntologyNodeKind, label: str) -> OntologyNode:
    canonical_id = (
        uuid4()
        if kind in {OntologyNodeKind.PERSON, OntologyNodeKind.ORGANIZATION}
        else None
    )
    return OntologyNode(
        id=node_id,
        kind=kind,
        label=label,
        canonical_id=canonical_id,
        source_key=None if canonical_id is not None else node_id,
    )


def _edge(
    edge_id: str,
    source_node_id: str,
    target_node_id: str,
    relation_type: OntologyRelationType,
) -> OntologyEdge:
    return OntologyEdge(
        id=edge_id,
        source_node_id=source_node_id,
        target_node_id=target_node_id,
        relation_type=relation_type,
        epistemic_status=EpistemicStatus.FACT,
        publication_status=PublicationStatus.PUBLISHED,
        claim_ids=(uuid4(),),
        evidence_ids=(uuid4(),),
        source_ids=(uuid4(),),
        valid_from=datetime(2024, 1, 1, tzinfo=UTC),
    )


def test_public_edge_requires_full_provenance() -> None:
    with pytest.raises(ValueError, match="Claim, Evidence, and Source"):
        OntologyEdge(
            id="missing-provenance",
            source_node_id="person:a",
            target_node_id="organization:x",
            relation_type=OntologyRelationType.WORKED_AT,
            epistemic_status=EpistemicStatus.FACT,
            publication_status=PublicationStatus.PUBLISHED,
            claim_ids=(uuid4(),),
            evidence_ids=(),
            source_ids=(uuid4(),),
        )


def test_unknown_relation_cannot_become_public_graph_edge() -> None:
    with pytest.raises(ValueError, match="FACT or CLAIM"):
        OntologyEdge(
            id="unknown-relation",
            source_node_id="person:a",
            target_node_id="organization:x",
            relation_type=OntologyRelationType.WORKED_AT,
            epistemic_status=EpistemicStatus.UNKNOWN,
            publication_status=PublicationStatus.PUBLISHED,
            claim_ids=(uuid4(),),
            evidence_ids=(uuid4(),),
            source_ids=(uuid4(),),
        )


def test_shared_institution_path_preserves_edge_direction() -> None:
    graph = OntologyGraph(
        nodes=(
            _node("person:a", OntologyNodeKind.PERSON, "A"),
            _node("school:x", OntologyNodeKind.EDUCATIONAL_INSTITUTION, "X대학교"),
            _node("person:b", OntologyNodeKind.PERSON, "B"),
        ),
        edges=(
            _edge(
                "a-school",
                "person:a",
                "school:x",
                OntologyRelationType.STUDIED_AT,
            ),
            _edge(
                "b-school",
                "person:b",
                "school:x",
                OntologyRelationType.STUDIED_AT,
            ),
        ),
    )

    paths = shortest_connection_paths(graph, "person:a", "person:b")

    assert len(paths) == 1
    assert paths[0].hops == 2
    assert [step.edge.id for step in paths[0].steps] == ["a-school", "b-school"]
    assert [step.traversed_forward for step in paths[0].steps] == [True, False]


def test_relation_filter_is_exploration_only() -> None:
    graph = OntologyGraph(
        nodes=(
            _node("person:a", OntologyNodeKind.PERSON, "A"),
            _node("school:x", OntologyNodeKind.EDUCATIONAL_INSTITUTION, "X대학교"),
            _node("organization:y", OntologyNodeKind.ORGANIZATION, "Y기관"),
            _node("person:b", OntologyNodeKind.PERSON, "B"),
        ),
        edges=(
            _edge(
                "a-school",
                "person:a",
                "school:x",
                OntologyRelationType.STUDIED_AT,
            ),
            _edge(
                "b-school",
                "person:b",
                "school:x",
                OntologyRelationType.STUDIED_AT,
            ),
            _edge(
                "a-org",
                "person:a",
                "organization:y",
                OntologyRelationType.WORKED_AT,
            ),
            _edge(
                "b-org",
                "person:b",
                "organization:y",
                OntologyRelationType.WORKED_AT,
            ),
        ),
    )

    school_paths = shortest_connection_paths(
        graph,
        "person:a",
        "person:b",
        relation_types=(OntologyRelationType.STUDIED_AT,),
    )
    work_paths = shortest_connection_paths(
        graph,
        "person:a",
        "person:b",
        relation_types=(OntologyRelationType.WORKED_AT,),
    )

    assert [[step.edge.id for step in path.steps] for path in school_paths] == [
        ["a-school", "b-school"]
    ]
    assert [[step.edge.id for step in path.steps] for path in work_paths] == [
        ["a-org", "b-org"]
    ]


def test_path_search_is_bounded_and_returns_only_shortest_paths() -> None:
    nodes = [
        _node("person:a", OntologyNodeKind.PERSON, "A"),
        _node("person:b", OntologyNodeKind.PERSON, "B"),
    ]
    edges = []
    for index in range(6):
        school_id = f"school:{index}"
        nodes.append(
            _node(
                school_id,
                OntologyNodeKind.EDUCATIONAL_INSTITUTION,
                f"학교 {index}",
            )
        )
        edges.extend(
            (
                _edge(
                    f"a-{index}",
                    "person:a",
                    school_id,
                    OntologyRelationType.STUDIED_AT,
                ),
                _edge(
                    f"b-{index}",
                    "person:b",
                    school_id,
                    OntologyRelationType.STUDIED_AT,
                ),
            )
        )

    graph = OntologyGraph(nodes=tuple(nodes), edges=tuple(edges))
    paths = shortest_connection_paths(graph, "person:a", "person:b")

    assert len(paths) == 5
    assert {path.hops for path in paths} == {2}


@pytest.mark.parametrize("max_hops", [0, 4])
def test_path_search_rejects_unbounded_hop_requests(max_hops: int) -> None:
    graph = OntologyGraph(
        nodes=(
            _node("person:a", OntologyNodeKind.PERSON, "A"),
            _node("person:b", OntologyNodeKind.PERSON, "B"),
        ),
        edges=(),
    )

    with pytest.raises(ValueError, match="max_hops"):
        shortest_connection_paths(
            graph,
            "person:a",
            "person:b",
            max_hops=max_hops,
        )


def test_residence_is_not_an_ontology_relation_type() -> None:
    assert "RESIDES_AT" not in {item.value for item in OntologyRelationType}
    assert "LIVES_AT" not in {item.value for item in OntologyRelationType}
