from uuid import UUID

import pytest

from packages.domain.contracts import Claim, ClaimEvidence, Person
from packages.domain.enums import (
    EpistemicStatus,
    EvidenceStance,
    IdentityStatus,
    PublicationStatus,
)
from packages.rendering.governance_ontology import (
    GovernanceOntologyError,
    build_person_governance_ontology,
)

PERSON_ID = UUID("00000000-0000-0000-0000-000000000501")
CLAIM_ID = UUID("30000000-0000-0000-0000-000000000501")
EVIDENCE_ID = UUID("40000000-0000-0000-0000-000000000501")
SOURCE_ID = UUID("20000000-0000-0000-0000-000000000501")


def person(*, status: IdentityStatus = IdentityStatus.RESOLVED) -> Person:
    return Person(
        id=PERSON_ID,
        canonical_name="김온톨로지",
        identity_status=status,
    )


def role_claim(*, predicate: str = "HELD_ROLE") -> Claim:
    return Claim(
        id=CLAIM_ID,
        person_id=PERSON_ID,
        proposition="김온톨로지는 테스트기관 위원장으로 재직한다.",
        subject="김온톨로지",
        predicate=predicate,
        object_text="테스트기관 위원장",
        epistemic_status=EpistemicStatus.FACT,
        publication_status=PublicationStatus.PUBLISHED,
        asserted_as_true=True,
    )


def evidence() -> ClaimEvidence:
    return ClaimEvidence(
        id=EVIDENCE_ID,
        claim_id=CLAIM_ID,
        source_id=SOURCE_ID,
        stance=EvidenceStance.SUPPORT,
        excerpt="projection must never copy this excerpt",
    )


def test_person_role_projects_to_evidence_backed_ontology_edge() -> None:
    claim = role_claim()
    graph = build_person_governance_ontology(
        person(),
        [claim],
        {claim.id: [evidence()]},
    )
    payload = graph.to_dict()

    assert payload["center_node_id"] == f"person:{PERSON_ID}"
    assert payload["semantics"] == "READ_ONLY_PROJECTION_FROM_CANONICAL_CLAIM_EVIDENCE"
    assert payload["nodes"][0] == {
        "id": f"person:{PERSON_ID}",
        "kind": "PERSON",
        "label": "김온톨로지",
        "canonical_id": str(PERSON_ID),
        "claim_ids": [],
    }
    assert payload["nodes"][1]["kind"] == "OFFICE"
    assert payload["nodes"][1]["label"] == "테스트기관 위원장"

    edge = payload["edges"][0]
    assert edge["relation_type"] == "HELD_ROLE"
    assert edge["claim_id"] == str(CLAIM_ID)
    assert edge["evidence_ids"] == [str(EVIDENCE_ID)]
    assert edge["source_ids"] == [str(SOURCE_ID)]
    assert edge["epistemic_status"] == "FACT"
    assert "projection must never copy this excerpt" not in str(payload)


@pytest.mark.parametrize("predicate", ["ASSEMBLY_PARTY", "ASSEMBLY_COMMITTEES"])
def test_unmapped_or_aggregate_claim_is_not_invented_as_relation(predicate: str) -> None:
    claim = role_claim(predicate=predicate)

    graph = build_person_governance_ontology(
        person(),
        [claim],
        {claim.id: [evidence()]},
    )

    assert len(graph.nodes) == 1
    assert graph.edges == ()


def test_mapped_relation_without_evidence_fails_closed() -> None:
    claim = role_claim()

    with pytest.raises(GovernanceOntologyError, match="lacks ClaimEvidence"):
        build_person_governance_ontology(person(), [claim], {})


def test_ontology_projection_requires_resolved_person() -> None:
    with pytest.raises(GovernanceOntologyError, match="current RESOLVED"):
        build_person_governance_ontology(
            person(status=IdentityStatus.REVIEW),
            [],
            {},
        )
