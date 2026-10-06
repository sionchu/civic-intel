"""Registry bindings for biography text: exact, unique, precedence-ordered or not at all."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from packages.domain.contracts import Claim, ClaimEvidence
from packages.domain.enums import EpistemicStatus, EvidenceStance, PublicationStatus
from packages.rendering.relationship_bindings import (
    RegistryEntity,
    campaign_key,
    registry_from_rows,
    transition_key,
    university_key,
)
from packages.rendering.relationship_projection import (
    AffiliationContext,
    Binding,
    RelationStatus,
    career_transitions,
    derive_pair,
    extract_affiliation,
)

ORG = uuid4()
REGISTRY = registry_from_rows([
    ("한국전력공사", RegistryEntity(f"organization:{ORG}", "PUBLIC_INSTITUTION", "한국전력공사",
                                 "CANONICAL_ORGANIZATION", ORG), 0),
    ("한국전력공사", RegistryEntity("mois_org:B551000", "PUBLIC_INSTITUTION", "한국전력공사",
                                 "EXACT_REGISTRY_NAME"), 2),
    ("삼성전자", RegistryEntity("opendart_corp:00126380", "COMPANY", "삼성전자", "EXACT_REGISTRY_NAME"), 1),
    ("기획재정부", RegistryEntity("mois_org:1051000", "GOVERNMENT_BODY", "기획재정부", "EXACT_REGISTRY_NAME"), 2),
    ("서울대학교", RegistryEntity("mois_org:U0001", "UNIVERSITY", "서울대학교", "EXACT_REGISTRY_NAME"), 2),
    ("중앙고등학교", RegistryEntity("mois_org:H1", "GOVERNMENT_BODY", "중앙고등학교", "EXACT_REGISTRY_NAME"), 2),
    ("중앙고등학교", RegistryEntity("mois_org:H2", "GOVERNMENT_BODY", "중앙고등학교", "EXACT_REGISTRY_NAME"), 2),
])
CONTEXT = AffiliationContext(registry=REGISTRY)


def bio(person: UUID, predicate: str, **qualifiers: str):
    claim = Claim(
        person_id=person, proposition="p.", subject="s", predicate=predicate, object_text="x",
        qualifiers={"source_contract": "assembly_member_profile_biography", **qualifiers},
        epistemic_status=EpistemicStatus.CLAIM, publication_status=PublicationStatus.PUBLISHED,
        valid_from=datetime(2026, 10, 7, tzinfo=UTC),
    )
    evidence = [ClaimEvidence(claim_id=claim.id, source_id=uuid4(), stance=EvidenceStance.SUPPORT)]
    return extract_affiliation(claim, evidence, CONTEXT)


def career(person: UUID, text: str, category: str = "BUSINESS", **extra: str):
    return bio(person, "ASSEMBLY_BIOGRAPHY_CAREER", organization_text=text, line_text=text,
               career_category=category, **extra)


def test_registry_precedence_and_ambiguity() -> None:
    assert REGISTRY.bind("한국전력공사 기획처").key == f"organization:{ORG}"
    assert REGISTRY.bind("삼성전자㈜ 반도체사업부").key == "opendart_corp:00126380"
    assert REGISTRY.bind("중앙고등학교 동문회") is None  # two registry entities: ambiguous
    assert REGISTRY.bind("어느 민간 연구소") is None


def test_biography_career_binds_to_the_same_node_as_disclosures() -> None:
    a, b = uuid4(), uuid4()
    left = career(a, "한국전력공사 기획처장", "PUBLIC_SERVICE")
    assert left.via.key == f"organization:{ORG}" and left.via.binding == Binding.CANONICAL_ORGANIZATION
    company = career(b, "삼성전자 상무", "BUSINESS")
    other = career(a, "삼성전자 부장", "BUSINESS")
    relation = derive_pair(company, other)
    assert relation.status == RelationStatus.DERIVED and relation.relation_type == "SAME_EMPLOYER"


def test_university_binds_by_official_name_or_reviewed_alias_only() -> None:
    a, b, c, d = uuid4(), uuid4(), uuid4(), uuid4()
    full = bio(a, "ASSEMBLY_BIOGRAPHY_EDUCATION", institution_name="서울대학교", institution_level="UNIVERSITY")
    short = bio(b, "ASSEMBLY_BIOGRAPHY_EDUCATION", institution_name="서울대", institution_level="UNIVERSITY")
    foreign = bio(c, "ASSEMBLY_BIOGRAPHY_EDUCATION", institution_name="서울대학교",
                  institution_level="UNIVERSITY", country_text="미국")
    high = bio(d, "ASSEMBLY_BIOGRAPHY_EDUCATION", institution_name="중앙고등학교", institution_level="HIGH_SCHOOL")
    assert full.via.key == short.via.key == "mois_org:U0001"
    assert derive_pair(full, short).relation_type == "SAME_UNIVERSITY"
    assert foreign.via.binding == Binding.SOURCE_TEXT_UNBOUND
    assert high.via.binding == Binding.SOURCE_TEXT_UNBOUND
    assert university_key("한국외대", "UNIVERSITY", None) == "한국외국어대학교"
    assert university_key("어느대", "UNIVERSITY", None) is None


def test_campaign_and_transition_bind_on_election_and_party() -> None:
    assert campaign_key("제20대 대통령선거 더불어민주당 중앙선대위 정책본부장")[0] == "campaign:20220309:더불어민주당"
    assert campaign_key("제8회전국동시지방선거 국민의힘 중앙선대위 조직본부장")[0] == "campaign:20220601:국민의힘"
    assert campaign_key("이재명 대선 경선캠프 법률지원단장") is None  # no election ordinal
    assert campaign_key("제20대 대통령선거 중앙선대위") is None  # no party
    assert transition_key("제20대 대통령직 인수위원회 자문위원")[0] == "transition:20220309"
    assert transition_key("경기도지사직 인수위원회 자문위원") is None
    a, b = uuid4(), uuid4()
    left = career(a, "제20대 대통령선거 국민의힘 선거대책위원회", "CAMPAIGN")
    right = career(b, "제20대 대선 국민의힘 중앙선대위", "CAMPAIGN")
    relation = derive_pair(left, right)
    assert relation.relation_type == "SAME_CAMPAIGN" and relation.status == RelationStatus.DERIVED


def test_revolving_door_needs_strictly_ordered_stated_periods() -> None:
    person = uuid4()
    government = career(person, "기획재정부 국장", "PUBLIC_SERVICE",
                        period_start="2010-01-01", period_start_precision="YEAR",
                        period_end="2015-03-01", period_end_precision="MONTH")
    company = career(person, "삼성전자 사외이사", "BUSINESS",
                     period_start="2016-04-01", period_start_precision="MONTH")
    undated = career(person, "한국전력공사 이사", "PUBLIC_SERVICE")
    moves = career_transitions([government, company, undated])
    assert [item["transition_type"] for item in moves] == ["GOVERNMENT_TO_BUSINESS"]
    assert moves[0]["status"] == "DERIVED" and len(moves[0]["source_claim_ids"]) == 2
    same_month = career(person, "삼성전자 고문", "BUSINESS",
                        period_start="2015-03-01", period_start_precision="MONTH")
    assert career_transitions([government, same_month]) == []
