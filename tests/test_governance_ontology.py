from uuid import UUID

import pytest

from packages.domain.contracts import Claim, ClaimEvidence, Organization, Person
from packages.domain.enums import (
    EpistemicStatus,
    EvidenceStance,
    IdentityStatus,
    PublicationStatus,
)
from packages.rendering.alio_organization_content import (
    ALIO_EXECUTIVE_PREDICATE,
    ALIO_EXECUTIVE_SOURCE_CONTRACT,
)
from packages.rendering.governance_ontology import (
    GovernanceOntologyError,
    build_organization_governance_ontology,
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


def organization() -> Organization:
    return Organization(
        id=UUID("10000000-0000-0000-0000-000000000501"),
        name="테스트공공기관",
    )


def executive_claim(
    claim_id: UUID,
    *,
    name: str = "김공개",
    position: str = "사장",
    source_contract: str = ALIO_EXECUTIVE_SOURCE_CONTRACT,
) -> Claim:
    item = organization()
    return Claim(
        id=claim_id,
        organization_id=item.id,
        proposition=f"{item.name}는 ALIO 임원현황에서 {position} 직위의 {name}을 공개한다.",
        subject=item.name,
        predicate=ALIO_EXECUTIVE_PREDICATE,
        object_text=f"{position} · {name}",
        qualifiers={
            "source_contract": source_contract,
            "provider_record_key": f"2026091900000000:{claim_id.int % 1000}",
            "canonical_name": name,
            "position_text": position,
        },
        epistemic_status=EpistemicStatus.FACT,
        publication_status=PublicationStatus.PUBLISHED,
        asserted_as_true=True,
    )


def executive_evidence(claim_id: UUID, *, suffix: int = 1) -> ClaimEvidence:
    return ClaimEvidence(
        id=UUID(f"40000000-0000-0000-0000-{suffix:012d}"),
        claim_id=claim_id,
        source_id=SOURCE_ID,
        stance=EvidenceStance.SUPPORT,
    )


def test_organization_executive_projects_source_listed_record_not_person() -> None:
    claim_id = UUID("30000000-0000-0000-0000-000000000601")
    claim = executive_claim(claim_id)
    graph = build_organization_governance_ontology(
        organization(),
        [claim],
        {claim.id: [executive_evidence(claim.id)]},
    )
    payload = graph.to_dict()

    assert payload["center_node_id"] == f"organization:{organization().id}"
    assert payload["nodes"][0]["kind"] == "ORGANIZATION"
    assert payload["nodes"][0]["canonical_id"] == str(organization().id)
    assert payload["nodes"][1]["kind"] == "SOURCE_LISTED_ROLE_HOLDER"
    assert payload["nodes"][1]["canonical_id"] is None
    assert payload["nodes"][1]["label"] == "사장 · 김공개"
    assert payload["edges"][0]["relation_type"] == "LISTS_EXECUTIVE"
    assert payload["edges"][0]["claim_id"] == str(claim.id)
    assert "not a canonical Person" in " ".join(payload["limitations"])


def test_organization_same_name_executive_claims_remain_distinct_records() -> None:
    first_id = UUID("30000000-0000-0000-0000-000000000611")
    second_id = UUID("30000000-0000-0000-0000-000000000612")
    first = executive_claim(first_id, name="동명이인", position="사장")
    second = executive_claim(second_id, name="동명이인", position="이사")

    graph = build_organization_governance_ontology(
        organization(),
        [first, second],
        {
            first.id: [executive_evidence(first.id, suffix=11)],
            second.id: [executive_evidence(second.id, suffix=12)],
        },
    )

    targets = [node for node in graph.nodes if node.kind == "SOURCE_LISTED_ROLE_HOLDER"]
    assert len(targets) == 2
    assert targets[0].id != targets[1].id
    assert all(node.canonical_id is None for node in targets)


def test_organization_ontology_ignores_classification_claim() -> None:
    item = organization()
    classification = Claim(
        id=UUID("30000000-0000-0000-0000-000000000621"),
        organization_id=item.id,
        proposition="기관 분류",
        subject=item.name,
        predicate="ALIO_INSTITUTION_CLASSIFICATION",
        object_text="공기업",
        epistemic_status=EpistemicStatus.FACT,
        publication_status=PublicationStatus.PUBLISHED,
        asserted_as_true=True,
    )

    graph = build_organization_governance_ontology(item, [classification], {})

    assert len(graph.nodes) == 1
    assert graph.edges == ()


def test_organization_ontology_fails_closed_on_missing_evidence_or_contract() -> None:
    claim_id = UUID("30000000-0000-0000-0000-000000000631")
    claim = executive_claim(claim_id)

    with pytest.raises(GovernanceOntologyError, match="lacks ClaimEvidence"):
        build_organization_governance_ontology(organization(), [claim], {})

    invalid = executive_claim(
        UUID("30000000-0000-0000-0000-000000000632"),
        source_contract="wrong-contract",
    )
    with pytest.raises(GovernanceOntologyError, match="invalid source contract"):
        build_organization_governance_ontology(
            organization(),
            [invalid],
            {invalid.id: [executive_evidence(invalid.id, suffix=32)]},
        )
