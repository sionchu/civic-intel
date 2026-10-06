from __future__ import annotations

from pathlib import Path

import httpx
from fastapi.testclient import TestClient
from sqlalchemy import select

from apps.api.main import create_app
from packages.connectors.open_assembly import OpenAssemblyMemberConnector
from packages.domain.db import FeederObservationRow, SourceSnapshotRow
from packages.verification.assembly_committee_roles import AssemblyCommitteeRolePublisher
from packages.verification.assembly_member_biography import AssemblyBiographyPublisher
from tests.test_assembly_committee_roles import MemberListApi, member_list_row
from tests.test_assembly_legislative_activity import prepare_repository, publish_activity
from workers.assembly_committees import AssemblyCommitteeMembershipEnumerator
from workers.assembly_member_biographies import AssemblyBiographyEnumerator

SECRET = "biography-secret-must-not-persist"
BIOGRAPHIES = {
    "M-001": "[학력]\r\n춘천고등학교 졸업\r\n서울대학교 법과대학 졸업\r\n[경력]\r\n현) 국회 정무위원회 위원\r\n"
    "2022.3~2022.5 제20대 대통령직 인수위원회 자문위원\r\n대표전화 02-788-1234",
    "M-002": "<학력>\r\n춘천고등학교 졸업\r\n서울대학교 법과대학 졸업\r\n<경력>\r\n2022.4~2022.5 제20대 대통령직 인수위원회 자문위원",
}


class BiographyApi:
    def handle(self, request: httpx.Request) -> httpx.Response:
        rows = [
            {
                "MONA_CD": code,
                "HG_NM": "비저장이름",
                "MEM_TITLE": text,
                "TEL_NO": "02-000-0000",
                "E_MAIL": "private@example.invalid",
                "STAFF": "비저장보좌진",
            }
            for code, text in BIOGRAPHIES.items()
        ]
        return httpx.Response(
            200,
            json={
                OpenAssemblyMemberConnector.API_CODE: [
                    {"head": [{"list_total_count": len(rows)}, {"RESULT": {"CODE": "INFO-000"}}]},
                    {"row": rows},
                ]
            },
        )


def build(tmp_path: Path):
    repository = prepare_repository(tmp_path)
    api = MemberListApi([
        member_list_row("C1", "M-001", "위원"),
        member_list_row("C1", "M-002", "간사"),
        member_list_row("C2", "M-002", "위원"),
    ])
    AssemblyCommitteeMembershipEnumerator(api.connector(), repository).enumerate()
    result = AssemblyCommitteeRolePublisher(repository).publish_latest_successful(memberships=True)
    assert result.published_claims == 3
    publish_activity(repository)
    AssemblyBiographyEnumerator(
        repository, api_key=SECRET, transport=httpx.MockTransport(BiographyApi().handle)
    ).enumerate()
    biography = AssemblyBiographyPublisher(repository).publish_latest_successful()
    assert biography.education_claims == 4 and biography.career_claims == 3
    people = {
        claim.qualifiers["provider_person_key"]: claim.person_id
        for claim in repository.claims(published_only=True, current_only=True)
        if claim.predicate == "ASSEMBLY_COMMITTEE_MEMBERSHIP"
    }
    return repository, people


def test_biography_observation_keeps_only_member_code_and_lines(tmp_path: Path) -> None:
    repository, _ = build(tmp_path)
    with repository.sessions() as session:
        stored = str([
            row.normalized_json
            for row in session.scalars(
                select(FeederObservationRow).where(
                    FeederObservationRow.feeder == "national_assembly_member_biographies"
                )
            )
        ])
        stored += str([row.metadata_json for row in session.scalars(select(SourceSnapshotRow))])
    for forbidden in (SECRET, "비저장", "private@example.invalid", "02-000-0000", "02-788-1234"):
        assert forbidden not in stored
    assert "서울대학교 법과대학 졸업" in stored


def test_person_relationships_compare_and_path_are_claim_traceable(tmp_path: Path) -> None:
    repository, people = build(tmp_path)
    first, second = people["M-001"], people["M-002"]
    with TestClient(create_app(repository)) as client:
        payload = client.get(f"/relationships/people/{first}").json()
        compare = client.get("/relationships/compare", params={"a": str(first), "b": str(second)}).json()
        with_candidates = client.get(
            "/relationships/compare",
            params={"a": str(first), "b": str(second), "include_candidates": "true"},
        ).json()
        path = client.get("/relationships/path", params={"from": str(first), "to": str(second)}).json()
        rules = client.get("/relationships/rules").json()
        same = client.get("/relationships/compare", params={"a": str(first), "b": str(first)})

    types = {
        relation["relation_type"] for group in payload["groups"] for relation in group["relations"]
    }
    # Committee code, roster party, exact university name and the presidential transition
    # committee bind; a high-school name (homonyms across regions) stays CANDIDATE.
    assert {"SAME_PARLIAMENTARY_COMMITTEE", "SAME_PARTY", "SAME_DEPARTMENT",
            "SAME_TRANSITION_COMMITTEE_OVERLAP"} <= types
    assert "SAME_HIGH_SCHOOL" not in types
    committee = next(group for group in payload["groups"] if group["via"]["label"] == "C1위원회")
    relation = committee["relations"][0]
    assert relation["counterpart"]["id"] == str(second)
    assert relation["temporal"]["overlap"] == "VERIFIED"
    assert len(relation["source_claim_ids"]) == 2 and relation["evidence_ids"]
    assert payload["cosponsorship"][0]["shared_bill_count"] == 1

    assert compare["multiplex_layers"] == ["CAMPAIGN", "EDUCATION", "LEGISLATIVE", "POLITICAL"]
    assert compare["cosponsorship"]["relation_type"] == "BILL_COSPONSORSHIP"
    assert compare["shortest_evidence_path"]["path_length"] == 2
    candidates = [
        item for item in with_candidates["direct_relations"] if item["status"] == "CANDIDATE"
    ]
    assert [item["relation_type"] for item in candidates] == ["SAME_HIGH_SCHOOL"]
    assert path["path_length"] == 2 and path["edges"][0]["claim_ids"]
    assert "PARTY" in path["excluded_kinds"]
    assert {rule["rule_id"] for rule in rules["rules"]} >= {"shared_parliamentary_committee", "bill_cosponsorship"}
    assert rules["coverage"]["public_people"] == 2
    assert same.status_code == 422
