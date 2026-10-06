"""False-positive and traceability regressions for the deterministic relationship projection."""

from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import UUID, uuid4

from packages.domain.contracts import Claim, ClaimEvidence, Organization
from packages.domain.enums import EpistemicStatus, EvidenceStance, PublicationStatus
from packages.rendering.relationship_projection import (
    RULES,
    AffiliationContext,
    Overlap,
    RelationStatus,
    cosponsorship_pairs,
    derive_pair,
    extract_affiliation,
    relations_for_person,
    shortest_evidence_path,
    temporal_overlap,
)

SOURCE = uuid4()
WHEN = datetime(2026, 10, 6, 11, tzinfo=UTC)


def claim(person: UUID, predicate: str, qualifiers: dict[str, str], *, object_text: str = "x",
          status: EpistemicStatus = EpistemicStatus.FACT,
          publication: PublicationStatus = PublicationStatus.PUBLISHED) -> Claim:
    return Claim(
        person_id=person, proposition="p.", subject="s", predicate=predicate,
        object_text=object_text, qualifiers=qualifiers, epistemic_status=status,
        asserted_as_true=status == EpistemicStatus.FACT, publication_status=publication,
        valid_from=WHEN,
    )


def evidence(item: Claim, stance: EvidenceStance = EvidenceStance.SUPPORT) -> list[ClaimEvidence]:
    return [ClaimEvidence(claim_id=item.id, source_id=SOURCE, stance=stance)]


def member(person: UUID, code: str, name: str, *, role: str = "위원", run: str = "run:1"):
    item = claim(person, "ASSEMBLY_COMMITTEE_MEMBERSHIP", {
        "source_contract": "assembly_committee_member_list_membership",
        "committee_code": code, "committee_name": name, "committee_role": role,
    }, object_text=name)
    return item, AffiliationContext(capture_keys={item.id: (run,)})


def affiliation(item: Claim, context: AffiliationContext | None = None, stance=EvidenceStance.SUPPORT):
    return extract_affiliation(item, evidence(item, stance), context or AffiliationContext())


def dart(person: UUID, corp_code: str, corp_name: str, receipt: str, **extra: str):
    return affiliation(claim(person, "OPENDART_DISCLOSED_EXECUTIVE_ROLE", {
        "source_contract": "opendart_reviewed_executive_role", "corp_code": corp_code,
        "corp_name": corp_name, "receipt_no": receipt, "settlement_date": "2025-12-31",
        "position": "이사", "registered_status": "사외이사", **extra,
    }, status=EpistemicStatus.CLAIM))


def education(person: UUID, name: str, **extra: str):
    return affiliation(claim(person, "ASSEMBLY_BIOGRAPHY_EDUCATION", {
        "source_contract": "assembly_member_profile_biography", "institution_name": name, **extra,
    }, status=EpistemicStatus.CLAIM))


def test_same_committee_code_in_same_capture_is_derived_and_traceable() -> None:
    a, b = uuid4(), uuid4()
    (ca, xa), (cb, xb) = member(a, "9700005", "국회운영위원회"), member(b, "9700005", "국회운영위원회", role="간사")
    left, right = affiliation(ca, xa), affiliation(cb, xb)
    relation = derive_pair(left, right)
    assert relation is not None
    payload = relation.to_dict()
    assert payload["relation_type"] == "SAME_PARLIAMENTARY_COMMITTEE"
    assert payload["status"] == RelationStatus.DERIVED
    assert payload["temporal"]["overlap"] == Overlap.VERIFIED
    assert set(payload["source_claim_ids"]) == {str(ca.id), str(cb.id)}
    assert payload["evidence_ids"] and payload["rule_version"] == "1.0"
    assert "친분" in payload["interpretation_note"]


def test_committee_name_without_same_code_is_never_joined() -> None:
    a, b = uuid4(), uuid4()
    (ca, xa), (cb, xb) = member(a, "C1", "예산결산특별위원회"), member(b, "C2", "예산결산특별위원회")
    assert derive_pair(affiliation(ca, xa), affiliation(cb, xb)) is None


def test_overlap_is_unknown_without_shared_capture_or_known_periods() -> None:
    a, b = uuid4(), uuid4()
    (ca, _), (cb, _) = member(a, "C1", "정무위원회"), member(b, "C1", "정무위원회")
    relation = derive_pair(affiliation(ca), affiliation(cb))
    assert relation is not None and relation.overlap == Overlap.UNKNOWN


def test_same_person_and_name_twins_stay_distinct() -> None:
    a = uuid4()
    (ca, xa) = member(a, "C1", "정무위원회")
    (cb, xb) = member(a, "C1", "정무위원회")
    assert derive_pair(affiliation(ca, xa), affiliation(cb, xb)) is None
    twin_one, twin_two = uuid4(), uuid4()
    one = dart(twin_one, "001", "가회사", "R1")
    two = dart(twin_two, "002", "나회사", "R2")
    # Same displayed name never matters: only the via entity key can join two People.
    assert derive_pair(one, two) is None


def test_company_name_alias_and_group_do_not_join_without_same_corp_code() -> None:
    a, b, c = uuid4(), uuid4(), uuid4()
    samsung = dart(a, "00126380", "삼성전자", "R1")
    samsung_alias = dart(b, "99999999", "삼성전자㈜", "R2")
    group = dart(c, "00000001", "삼성그룹", "R3")
    assert derive_pair(samsung, samsung_alias) is None
    assert derive_pair(samsung, group) is None


def test_board_interlock_only_with_same_filing_otherwise_same_board() -> None:
    a, b, c = uuid4(), uuid4(), uuid4()
    first = dart(a, "00159218", "한전KPS", "R2026")
    same_filing = dart(b, "00159218", "한전KPS", "R2026")
    other_year = dart(c, "00159218", "한전KPS", "R2025")
    assert derive_pair(first, same_filing).relation_type == "BOARD_INTERLOCK"
    later = derive_pair(first, other_year)
    assert later.relation_type == "SAME_COMPANY_BOARD" and later.overlap == Overlap.UNKNOWN


def test_school_relations_are_candidates_never_default_or_friendship() -> None:
    a, b = uuid4(), uuid4()
    left = education(a, "서울대학교", department_text="법학과")
    right = education(b, "서울 대학교", department_text="법학과")
    relation = derive_pair(left, right)
    assert relation.status == RelationStatus.CANDIDATE
    assert relation.relation_type == "SAME_DEPARTMENT"
    assert relations_for_person(a, [left, right]) == []
    assert len(relations_for_person(a, [left, right], include_candidates=True)) == 1
    banned = {"FRIEND", "CLOSE", "INFLUENCE", "CRONY", "친분", "유착", "실세"}
    for rule in RULES:
        assert not any(word in rule.relation_type for word in banned)


def test_university_and_affiliated_high_school_are_different_entities() -> None:
    a, b = uuid4(), uuid4()
    assert derive_pair(education(a, "경북대학교"), education(b, "경북대학교 사범대학 부속고등학교")) is None


def test_education_overlap_needs_both_periods_and_is_conservative() -> None:
    a, b, c = uuid4(), uuid4(), uuid4()
    left = education(a, "고려대학교", period_start="1988-01-01", period_start_precision="YEAR",
                     period_end="1992-01-01", period_end_precision="YEAR")
    overlapping = education(b, "고려대학교", period_start="1990-03-01", period_start_precision="MONTH",
                            period_end="1994-02-01", period_end_precision="MONTH")
    undated = education(c, "고려대학교")
    assert derive_pair(left, overlapping).relation_type == "EDUCATION_TIME_OVERLAP"
    assert derive_pair(left, undated).overlap == Overlap.UNKNOWN
    # Same stated month range cannot prove overlap after conservative widening.
    tight = education(a, "연세대학교", period_start="2020-05-01", period_start_precision="MONTH",
                      period_end="2020-05-01", period_end_precision="MONTH")
    assert tight.period.start is None


def test_disjoint_known_intervals_are_not_overlap() -> None:
    from packages.rendering.relationship_projection import Period

    left = Period(start=date(2015, 1, 1), end=date(2016, 12, 31))
    right = Period(start=date(2017, 1, 1), end=date(2018, 1, 1))
    assert temporal_overlap(left, right)[0] == Overlap.NOT_OVERLAPPING


def test_witness_co_listing_is_not_a_relation_but_member_witness_is() -> None:
    committee = uuid4()
    w1, w2, m = uuid4(), uuid4(), uuid4()
    witnesses = []
    for person in (w1, w2):
        item = claim(person, "LISTED_AS_GUKGAM_WITNESS", {
            "source_contract": "gukgam_witness_reviewed_person_link", "committee_name": "정무위원회",
            "adoption_date": "2026-10-01", "category": "증인",
        }, status=EpistemicStatus.CLAIM)
        witnesses.append(affiliation(item, AffiliationContext(witness_committee_org={item.id: committee})))
    assert derive_pair(*witnesses) is None
    membership, _ = member(m, "9700008", "정무위원회")
    seat = affiliation(membership, AffiliationContext(committee_orgs_by_name={"정무위원회": committee}))
    relation = derive_pair(seat, witnesses[0])
    assert relation.relation_type == "COMMITTEE_WITNESS_REQUEST"
    assert relation.subject.person_id == m and relation.overlap == Overlap.UNKNOWN


def test_unsourced_draft_unknown_or_unmapped_claims_never_become_affiliations() -> None:
    person = uuid4()
    membership, context = member(person, "C1", "정무위원회")
    no_support = extract_affiliation(membership, [], context)
    assert no_support is None
    draft = claim(person, "ASSEMBLY_COMMITTEE_MEMBERSHIP", dict(membership.qualifiers),
                  publication=PublicationStatus.DRAFT)
    assert affiliation(draft) is None
    co_mention = claim(person, "NEWS_CO_MENTION", {"source_contract": "news"})
    photo = claim(person, "PHOTO_CO_APPEARANCE", {"source_contract": "photo"})
    residence = claim(person, "DECLARED_REAL_ESTATE", {"source_contract": "asset"})
    religion = claim(person, "RELIGION", {"source_contract": "inferred"})
    for item in (co_mention, photo, residence, religion):
        assert affiliation(item) is None
    other_contract = claim(person, "ASSEMBLY_COMMITTEE_MEMBERSHIP", {
        **membership.qualifiers, "source_contract": "unknown_contract",
    })
    assert affiliation(other_contract) is None


def test_conflicting_evidence_is_kept_visible() -> None:
    a, b = uuid4(), uuid4()
    (ca, xa), (cb, xb) = member(a, "C1", "정무위원회"), member(b, "C1", "정무위원회")
    conflicted = extract_affiliation(
        ca, [*evidence(ca), *evidence(ca, EvidenceStance.REFUTE)], xa
    )
    relation = derive_pair(conflicted, affiliation(cb, xb))
    assert relation.to_dict()["source_conflict"] is True


def test_former_biography_role_is_not_marked_current() -> None:
    item = affiliation(claim(uuid4(), "ASSEMBLY_BIOGRAPHY_CAREER", {
        "source_contract": "assembly_member_profile_biography", "organization_text": "한국개발연구원",
        "career_category": "CIVIC", "current_marker": "FORMER",
    }, status=EpistemicStatus.CLAIM))
    assert item.period.ongoing is None
    # Party/legislature biography lines duplicate roster facts and never become text affiliations.
    party_line = affiliation(claim(uuid4(), "ASSEMBLY_BIOGRAPHY_CAREER", {
        "source_contract": "assembly_member_profile_biography", "organization_text": "국민의힘",
        "career_category": "PARTY",
    }, status=EpistemicStatus.CLAIM))
    assert party_line is None


def test_party_requires_roster_field_and_is_excluded_from_default_paths() -> None:
    a, b = uuid4(), uuid4()
    roster = {"source_contract": "assembly_member_roster", "field_name": "party"}
    left = affiliation(claim(a, "ASSEMBLY_PARTY", roster, object_text="정당가"))
    right = affiliation(claim(b, "ASSEMBLY_PARTY", roster, object_text="정당가"))
    assert derive_pair(left, right).relation_type == "SAME_PARTY"
    assert shortest_evidence_path(a, b, [left, right]) is None
    path = shortest_evidence_path(a, b, [left, right], include_kinds=["PARTY"])
    assert path["path_length"] == 2


def test_shortest_path_crosses_canonical_organizations_with_claim_ids() -> None:
    a, b, c = uuid4(), uuid4(), uuid4()
    org = uuid4()
    organizations = {org: Organization(id=org, name="한국가기관")}
    alio = []
    for person in (a, b):
        item = claim(person, "ALIO_REVIEWED_PERSON_ROLE", {
            "source_contract": "alio_reviewed_person_role", "organization_id": str(org),
            "position_text": "비상임이사", "as_of": "2026-06-01",
        }, status=EpistemicStatus.CLAIM)
        alio.append(affiliation(item, AffiliationContext(organizations=organizations)))
    corp_b, corp_c = dart(b, "001", "가회사", "R1"), dart(c, "001", "가회사", "R1")
    path = shortest_evidence_path(a, c, [*alio, corp_b, corp_c])
    assert path["path_length"] == 4
    assert len(path["source_claim_ids"]) == 4
    assert all(edge["claim_ids"] and edge["evidence_ids"] for edge in path["edges"])
    assert derive_pair(*alio).relation_type == "PUBLIC_INSTITUTION_OVERLAP"


def test_cosponsorship_counts_shared_bills_by_member_code_claims() -> None:
    a, b, c = uuid4(), uuid4(), uuid4()
    participants = {
        f"BILL{index}": [(a, uuid4()), (b, uuid4()), *([(c, uuid4())] if index == 0 else [])]
        for index in range(10)
    }
    pairs = cosponsorship_pairs(a, participants)
    assert [(item.other_person_id, len(item.bill_ids)) for item in pairs] == [(b, 10), (c, 1)]
    assert pairs[0].to_dict()["relation_type"] == "REPEATED_COSPONSORSHIP"
    assert pairs[1].to_dict()["relation_type"] == "BILL_COSPONSORSHIP"
