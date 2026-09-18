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
REFUTE_EVIDENCE_ID = UUID("40000000-0000-0000-0000-000000000502")
SOURCE_ID = UUID("20000000-0000-0000-0000-000000000501")
REFUTE_SOURCE_ID = UUID("20000000-0000-0000-0000-000000000502")


def person(*, status: IdentityStatus = IdentityStatus.RESOLVED) -> Person:
    return Person(
        id=PERSON_ID,
        canonical_name="김온톨로지",
        identity_status=status,
    )


def role_claim(
    *,
    predicate: str = "HELD_ROLE",
    epistemic_status: EpistemicStatus = EpistemicStatus.FACT,
) -> Claim:
    return Claim(
        id=CLAIM_ID,
        person_id=PERSON_ID,
        proposition="김온톨로지는 테스트기관 위원장으로 재직한다.",
        subject="김온톨로지",
        predicate=predicate,
        object_text="테스트기관 위원장",
        epistemic_status=epistemic_status,
        publication_status=PublicationStatus.PUBLISHED,
        asserted_as_true=epistemic_status == EpistemicStatus.FACT,
        resolution_note=(
            "공개 관계로 단정할 수 있는 근거가 아직 없다."
            if epistemic_status == EpistemicStatus.UNKNOWN
            else None
        ),
    )


def evidence(
    *,
    evidence_id: UUID = EVIDENCE_ID,
    source_id: UUID = SOURCE_ID,
    stance: EvidenceStance = EvidenceStance.SUPPORT,
) -> ClaimEvidence:
    return ClaimEvidence(
        id=evidence_id,
        claim_id=CLAIM_ID,
        source_id=source_id,
        stance=stance,
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
    assert edge["source_conflict"] is False
    assert "projection must never copy this excerpt" not in str(payload)


@pytest.mark.parametrize(
    "predicate",
    [
        "ASSEMBLY_PARTY",
        "ASSEMBLY_COMMITTEES",
        "NOMINATED_AS",
        "DESIGNATED_AS",
        "APPOINTED_AS",
        "ELECTED_AS",
    ],
)
def test_unmapped_or_non_role_claim_is_not_invented_as_relation(predicate: str) -> None:
    claim = role_claim(predicate=predicate)

    graph = build_person_governance_ontology(
        person(),
        [claim],
        {claim.id: [evidence()]},
    )

    assert len(graph.nodes) == 1
    assert graph.edges == ()


def test_unknown_mapped_claim_does_not_become_public_relation() -> None:
    claim = role_claim(epistemic_status=EpistemicStatus.UNKNOWN)

    graph = build_person_governance_ontology(
        person(),
        [claim],
        {claim.id: [evidence()]},
    )

    assert len(graph.nodes) == 1
    assert graph.edges == ()


def test_source_conflict_is_preserved_on_relation_edge() -> None:
    claim = role_claim()

    graph = build_person_governance_ontology(
        person(),
        [claim],
        {
            claim.id: [
                evidence(),
                evidence(
                    evidence_id=REFUTE_EVIDENCE_ID,
                    source_id=REFUTE_SOURCE_ID,
                    stance=EvidenceStance.REFUTE,
                ),
            ]
        },
    )

    payload = graph.to_dict()
    assert payload["edges"][0]["source_conflict"] is True
    assert payload["edges"][0]["source_ids"] == [
        str(SOURCE_ID),
        str(REFUTE_SOURCE_ID),
    ]


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
