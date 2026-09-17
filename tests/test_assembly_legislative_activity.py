from __future__ import annotations

from pathlib import Path

import httpx
import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient

from apps.api.main import create_app
from packages.connectors.open_assembly import OpenAssemblyMemberConnector
from packages.connectors.open_assembly_bills import OpenAssemblyBillConnector
from packages.domain.enums import SourceRunStatus
from packages.persistence import SqlAlchemyRepository
from packages.verification.assembly_base_profile import AssemblyBaseProfilePublisher
from packages.verification.assembly_legislative_activity import (
    AssemblyLegislativeActivityError,
    AssemblyLegislativeActivityPublisher,
)
from workers.assembly_roster import AssemblyRosterEnumerator
from workers.legislative_activity import AssemblyBillParticipationEnumerator


def migrated_repository(database: Path) -> SqlAlchemyRepository:
    database.parent.mkdir(parents=True, exist_ok=True)
    database_url = f"sqlite:///{database.as_posix()}"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(config, "head")
    return SqlAlchemyRepository(database_url)


def member_row(code: str, name: str) -> dict[str, str]:
    return {
        "MONA_CD": code,
        "HG_NM": name,
        "BTH_DATE": "19700102",
        "POLY_NM": "테스트정당",
        "ORIG_NM": "서울 테스트구",
        "REELE_GBN_NM": "초선",
        "CMITS": "테스트위원회",
    }


class RosterApi:
    def __init__(self) -> None:
        self.rows = [member_row("M-001", "가회원"), member_row("M-002", "나회원")]

    def handle(self, request: httpx.Request) -> httpx.Response:
        assert request.url.params["pIndex"] == "1"
        return httpx.Response(
            200,
            json={
                OpenAssemblyMemberConnector.API_CODE: [
                    {"head": [{"list_total_count": 2}]},
                    {"row": self.rows},
                ]
            },
        )

    def connector(self) -> OpenAssemblyMemberConnector:
        return OpenAssemblyMemberConnector(
            api_key="assembly-legislative-roster-secret",
            page_size=100,
            transport=httpx.MockTransport(self.handle),
        )


class BillApi:
    def __init__(self, *, title: str = "테스트 법률안", lead: str = "M-001", co: str = "M-002") -> None:
        self.title = title
        self.lead = lead
        self.co = co

    def handle(self, request: httpx.Request) -> httpx.Response:
        assert request.url.params["pIndex"] == "1"
        row = {
            "BILL_ID": "BILL-001",
            "BILL_NO": "220001",
            "BILL_NAME": self.title,
            "COMMITTEE": "테스트위원회",
            "COMMITTEE_ID": "CMIT-001",
            "PROPOSE_DT": "2026-01-02",
            "PROC_RESULT": "계류",
            "AGE": "22",
            "RST_PROPOSER": "비저장대표",
            "PUBL_PROPOSER": "비저장공동",
            "RST_MONA_CD": self.lead,
            "PUBL_MONA_CD": self.co,
            "DETAIL_LINK": "https://open.assembly.go.kr/bill/BILL-001?billId=BILL-001",
        }
        return httpx.Response(
            200,
            json={
                OpenAssemblyBillConnector.API_CODE: [
                    {"head": [{"list_total_count": 1}]},
                    {"row": [row]},
                ]
            },
        )

    def connector(self) -> OpenAssemblyBillConnector:
        return OpenAssemblyBillConnector(
            assembly_age=22,
            api_key="assembly-legislative-bill-secret",
            page_size=100,
            transport=httpx.MockTransport(self.handle),
        )


def prepare_repository(tmp_path: Path) -> SqlAlchemyRepository:
    repository = migrated_repository(tmp_path / "assembly-legislative.db")
    roster = AssemblyRosterEnumerator(RosterApi().connector(), repository)
    roster.enumerate_and_materialize()
    AssemblyBaseProfilePublisher(repository).publish_latest_successful()
    return repository


def publish_activity(repository: SqlAlchemyRepository, *, title: str = "테스트 법률안"):
    enumeration = AssemblyBillParticipationEnumerator(
        BillApi(title=title).connector(), repository
    ).enumerate()
    assert enumeration.run.status == SourceRunStatus.SUCCESS
    return AssemblyLegislativeActivityPublisher(repository).publish_latest_successful()


def test_exact_mona_crosswalk_publishes_role_separated_activity_and_profile_trace(
    tmp_path: Path,
) -> None:
    repository = prepare_repository(tmp_path)

    result = publish_activity(repository)

    assert result.observations_considered == 1
    assert result.observations_published == 2
    assert result.published_claims == 2
    assert result.unchanged_claims == 0
    assert result.unresolved_member_codes == ()

    people = repository.public_people()
    assert len(people) == 2
    with TestClient(create_app(repository)) as client:
        for person in people:
            payload = client.get(f"/people/{person.id}").json()
            activity = next(
                item for item in payload["profile"]["sections"] if item["id"] == "legislative_activity"
            )
            assert activity["status"] == "AVAILABLE"
            entry = activity["entries"][0]
            assert entry["details"]["predicate"] == "ASSEMBLY_BILL_PARTICIPATION"
            assert entry["details"]["participation_role"] in {
                "REPRESENTATIVE_PROPOSER",
                "CO_PROPOSER",
            }
            assert entry["details"]["detail_url"].startswith("https://open.assembly.go.kr/")
            assert entry["evidence"][0]["snapshot_id"]
            assert entry["evidence"][0]["feeder_observation_id"]
            assert "normalized" not in str(payload)

        first = client.get(f"/people/{people[0].id}").json()
        second = client.get(f"/people/{people[1].id}").json()
        first_role = next(
            item
            for item in first["profile"]["sections"]
            if item["id"] == "legislative_activity"
        )["entries"][0]["details"]["participation_role"]
        second_role = next(
            item
            for item in second["profile"]["sections"]
            if item["id"] == "legislative_activity"
        )["entries"][0]["details"]["participation_role"]
        assert {first_role, second_role} == {"REPRESENTATIVE_PROPOSER", "CO_PROPOSER"}


def test_unlinked_mona_code_is_not_name_matched_or_published(tmp_path: Path) -> None:
    repository = prepare_repository(tmp_path / "unlinked")
    enumeration = AssemblyBillParticipationEnumerator(
        BillApi(lead="M-999", co="M-001").connector(), repository
    ).enumerate()
    assert enumeration.run.status == SourceRunStatus.SUCCESS
    result = AssemblyLegislativeActivityPublisher(repository).publish_latest_successful()
    assert result.unresolved_member_codes == ("M-999",)
    assert result.published_claims == 1
    assert all(
        claim.qualifiers.get("provider_person_key") == "M-001"
        for claim in repository.claims(published_only=True, current_only=True)
        if claim.predicate == "ASSEMBLY_BILL_PARTICIPATION"
    )


def test_activity_publication_is_idempotent_and_version_conflict_fails_closed(
    tmp_path: Path,
) -> None:
    repository = prepare_repository(tmp_path)
    first = publish_activity(repository)
    second = AssemblyLegislativeActivityPublisher(repository).publish_latest_successful()

    assert first.published_claims == 2
    assert first.unchanged_claims == 0
    assert second.published_claims == 0
    assert second.unchanged_claims == 2

    AssemblyBillParticipationEnumerator(
        BillApi(title="수정된 법률안").connector(), repository
    ).enumerate()
    with pytest.raises(
        AssemblyLegislativeActivityError,
        match="immutable observation version",
    ):
        AssemblyLegislativeActivityPublisher(repository).publish_latest_successful()
    claims = [
        claim
        for claim in repository.claims(published_only=True, current_only=True)
        if claim.predicate == "ASSEMBLY_BILL_PARTICIPATION"
    ]
    assert len(claims) == 2
    assert {claim.object_text for claim in claims} == {"테스트 법률안"}
