from __future__ import annotations

from pathlib import Path

import httpx
from sqlalchemy import select

from packages.connectors.open_assembly_historical import HISTORICAL_API_CODE
from packages.domain.db import FeederObservationRow, IdentityReviewItemRow, PersonAliasRow
from packages.rendering.relationship_graph import load_relationship_graph
from packages.rendering.relationship_projection import relations_for_person
from packages.verification.assembly_former_members import (
    AssemblyFormerMemberPublisher,
    person_id_for,
    split_term_label,
)
from tests.test_assembly_legislative_activity import prepare_repository
from workers.assembly_former_members import enumerate_terms

SECRET = "former-member-secret-must-not-persist"
ROWS = {
    "100021": [
        {"HG_NM": "전의원", "HJ_NM": "前議員", "FRTO_DATE": "2020.05.30 ~ 2024.05.29",
         "PROFILE_SJ": "제21대 미래통합당 경남 창원시성산구", "MONA_CD": "F-001",
         "PROFILE_UNIT_CD": "100021", "PROFILE_UNIT_NM": "제21대", "TEL_NO": "02-000-0000"},
        {"HG_NM": "후의원", "HJ_NM": "後議員", "FRTO_DATE": "2023.04.06 ~ 2024.05.29",
         "PROFILE_SJ": "제21대 진보당 전북 전주시을", "MONA_CD": "F-002",
         "PROFILE_UNIT_CD": "100021", "PROFILE_UNIT_NM": "제21대"},
        # Same name as a current-roster Person: never created, never merged — review.
        {"HG_NM": "가회원", "HJ_NM": "假會員", "FRTO_DATE": "2020.05.30 ~ 2024.05.29",
         "PROFILE_SJ": "제21대 더불어민주당 비례대표", "MONA_CD": "F-003",
         "PROFILE_UNIT_CD": "100021", "PROFILE_UNIT_NM": "제21대"},
    ],
    "100020": [
        {"HG_NM": "전의원", "HJ_NM": "前議員", "FRTO_DATE": "2016.05.30 ~ 2020.05.29",
         "PROFILE_SJ": "제20대 새누리당 경남 창원시성산구", "MONA_CD": "F-001",
         "PROFILE_UNIT_CD": "100020", "PROFILE_UNIT_NM": "제20대"},
    ],
}


def handler(request: httpx.Request) -> httpx.Response:
    assert request.url.params["KEY"] == SECRET
    rows = ROWS[request.url.params["PROFILE_UNIT_CD"]]
    return httpx.Response(200, json={HISTORICAL_API_CODE: [
        {"head": [{"list_total_count": len(rows)}, {"RESULT": {"CODE": "INFO-000"}}]},
        {"row": rows},
    ]})


def run(repository):
    enumerate_terms(repository, api_key=SECRET, transport=httpx.MockTransport(handler),
                    units=("100020", "100021"))
    return AssemblyFormerMemberPublisher(repository).publish()


def test_party_label_split() -> None:
    assert split_term_label("제21대 미래통합당 경남 창원시성산구") == ("미래통합당", "경남 창원시성산구")
    assert split_term_label("제21대 알수없는당 서울") == (None, None)


def test_former_members_auto_create_by_mona_cd_and_fail_closed_on_name(tmp_path: Path) -> None:
    repository = prepare_repository(tmp_path)
    result = run(repository)
    assert (result.members, result.created, result.review_required, result.claims) == (3, 2, 1, 3)
    again = run(repository)
    assert again.created == 0 and again.linked_existing == 2  # idempotent per MONA_CD

    with repository.sessions() as session:
        stored = str([row.normalized_json for row in session.scalars(
            select(FeederObservationRow).where(
                FeederObservationRow.feeder == "national_assembly_historical_members"))])
        reviews = list(session.scalars(select(IdentityReviewItemRow)))
        aliases = {row.name for row in session.scalars(select(PersonAliasRow))}
    assert SECRET not in stored and "02-000-0000" not in stored
    assert [item.details_json["provider_person_key"] for item in reviews] == ["F-003"]
    assert aliases == {"前議員", "後議員"}

    first = repository.person(person_id_for("F-001"))
    assert first is not None and first.canonical_name == "전의원"
    terms = [c for c in repository.claims(person_id=first.id, published_only=True)
             if c.predicate == "ASSEMBLY_HISTORICAL_TERM"]
    assert sorted(c.qualifiers["party"] for c in terms) == ["미래통합당", "새누리당"]
    assert repository.person_is_public(first.id)

    graph = load_relationship_graph(repository)
    relations = relations_for_person(first.id, graph.affiliations)
    types = {(r.relation_type, r.overlap.value) for r in relations}
    assert ("SAME_LEGISLATIVE_TERM", "VERIFIED") in types  # 2023-04-06 ~ overlaps
    assert all(r.counterpart.person_id != person_id_for("F-003") for r in relations)
