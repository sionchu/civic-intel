from __future__ import annotations

from pathlib import Path

import httpx
from sqlalchemy import select

from packages.domain.db import FeederObservationRow
from packages.rendering.relationship_graph import load_relationship_graph
from packages.verification.assembly_former_members import (
    AssemblyFormerMemberPublisher,
    person_id_for,
)
from packages.verification.nec_assembly_candidates import NecAssemblyCandidatePublisher
from tests.test_assembly_former_members import SECRET as HISTORICAL_SECRET
from tests.test_assembly_former_members import handler as historical_handler
from tests.test_assembly_legislative_activity import prepare_repository
from workers.assembly_former_members import enumerate_terms
from workers.nec_assembly_candidates import enumerate_scope

NEC_SECRET = "nec-secret-must-not-persist"


def candidate(huboid: str, name: str, birthday: str, party: str, **extra: str) -> dict[str, str]:
    return {
        "huboid": huboid, "sgId": extra.pop("sgId"), "sgTypecode": "2", "sggName": "어느구",
        "sdName": "서울특별시", "name": name, "hanjaName": "", "birthday": birthday,
        "jdName": party, "edu": extra.pop("edu", "서울대학교 법학과 졸업"),
        "career1": extra.pop("career1", "(현)삼성전자 상무"), "career2": "(전)기획재정부 국장",
        "job": "회사원", "status": "등록", "addr": "비저장 주소 1번지", "gender": "남", "age": "50",
    }


ROWS = {
    "20240410": [
        candidate("H1", "가회원", "19700102", "테스트정당", sgId="20240410"),
        # Same name, different birth date: never matched.
        candidate("H2", "나회원", "19800101", "테스트정당", sgId="20240410"),
    ],
    "20200415": [
        candidate("H3", "전의원", "19600101", "미래통합당", sgId="20200415"),
    ],
}


def nec_handler(request: httpx.Request) -> httpx.Response:
    assert request.url.params["serviceKey"] == NEC_SECRET
    rows = ROWS[request.url.params["sgId"]]
    return httpx.Response(200, json={"response": {
        "header": {"resultCode": "INFO-00", "resultMsg": "NORMAL SERVICE"},
        "body": {"items": {"item": rows}, "numOfRows": 100, "pageNo": 1, "totalCount": len(rows)},
    }})


def test_candidate_submissions_attach_only_to_exact_identity_matches(tmp_path: Path) -> None:
    repository = prepare_repository(tmp_path)
    enumerate_terms(repository, api_key=HISTORICAL_SECRET,
                    transport=httpx.MockTransport(historical_handler), units=("100021",))
    AssemblyFormerMemberPublisher(repository).publish()
    for election in ("20240410", "20200415"):
        enumerate_scope(repository, election, 2, api_key=NEC_SECRET,
                        transport=httpx.MockTransport(nec_handler))
    result = NecAssemblyCandidatePublisher(repository).publish()
    assert (result.current_matched, result.former_matched) == (1, 1)

    with repository.sessions() as session:
        stored = str([row.normalized_json for row in session.scalars(
            select(FeederObservationRow).where(
                FeederObservationRow.feeder == "nec_national_assembly_candidates"))])
    for forbidden in (NEC_SECRET, "비저장 주소", "'gender'", "'age'"):
        assert forbidden not in stored

    former = person_id_for("F-001")
    claims = [c for c in repository.claims(person_id=former, published_only=True)
              if c.predicate.startswith("NEC_CANDIDATE_")]
    assert {c.qualifiers["identity_basis"] for c in claims} == {"EXACT_NAME_PARTY_AND_ELECTION_OF_TERM"}
    assert all(not c.asserted_as_true and c.epistemic_status.value == "CLAIM" for c in claims)
    again = NecAssemblyCandidatePublisher(repository).publish()
    assert again.claims == result.claims  # deterministic ids; inserts are idempotent

    graph = load_relationship_graph(repository)
    kinds = {a.via.kind for a in graph.affiliations if a.person_id == former}
    assert "EDUCATIONAL_INSTITUTION" in kinds
