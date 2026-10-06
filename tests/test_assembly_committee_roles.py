from __future__ import annotations

from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from apps.api.main import create_app
from packages.connectors.open_assembly_committees import OpenAssemblyCommitteeMemberConnector
from packages.domain.db import FeederObservationRow, SourceRow, SourceSnapshotRow
from packages.domain.enums import SourceRunStatus
from packages.persistence import SqlAlchemyRepository
from packages.verification.assembly_committee_roles import (
    AssemblyCommitteeRoleError,
    AssemblyCommitteeRolePublisher,
)
from tests.test_assembly_legislative_activity import prepare_repository
from workers.assembly_committees import (
    AssemblyCommitteeCoverageError,
    AssemblyCommitteeMembershipEnumerator,
    main,
)

SECRET = "assembly-committee-secret-must-not-persist"


def member_list_row(dept: str, mona: str, role: str, **overrides: str) -> dict[str, str]:
    row = {
        "DEPT_CD": dept,
        "DEPT_NM": f"{dept}위원회",
        "JOB_RES_NM": role,
        "HG_NM": "비저장위원",
        "HJ_NM": "非貯藏",
        "ORIG_NM": "비저장선거구",
        "POLY_NM": "비저장정당",
        "ASSEM_TEL": "02-000-0000",
        "ASSEM_EMAIL": "private@example.invalid",
        "ROOM_NO": "000",
        "STAFF": "비저장보좌관",
        "SECRETARY": "비저장비서관",
        "SECRETARY2": "비저장비서",
        "MONA_CD": mona,
    }
    row.update(overrides)
    return row


class MemberListApi:
    def __init__(self, rows: list[dict[str, str]], *, total: int | None = None) -> None:
        self.rows = rows
        self.total = len(rows) if total is None else total
        self.requests: list[httpx.Request] = []

    def handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        size = int(request.url.params["pSize"])
        index = int(request.url.params["pIndex"])
        page = self.rows[(index - 1) * size : index * size]
        return httpx.Response(
            200,
            json={
                OpenAssemblyCommitteeMemberConnector.API_CODE: [
                    {"head": [{"list_total_count": self.total}, {"RESULT": {"CODE": "INFO-000"}}]},
                    {"row": page},
                ]
            },
        )

    def connector(self, *, page_size: int = 1000) -> OpenAssemblyCommitteeMemberConnector:
        return OpenAssemblyCommitteeMemberConnector(
            api_key=SECRET,
            page_size=page_size,
            transport=httpx.MockTransport(self.handle),
        )


DEFAULT_ROWS = [
    member_list_row("C1", "M-001", "위원장"),
    member_list_row("C1", "M-002", "간사"),
    member_list_row("C2", "M-001", "위원"),
    member_list_row("C2", "M-999", "간사"),
]


def enumerate_members(repository: SqlAlchemyRepository, rows=None, *, page_size: int = 1000):
    api = MemberListApi(DEFAULT_ROWS if rows is None else rows)
    result = AssemblyCommitteeMembershipEnumerator(
        api.connector(page_size=page_size), repository
    ).enumerate()
    return api, result


def test_full_member_list_is_persisted_without_names_contacts_or_key(tmp_path: Path) -> None:
    repository = prepare_repository(tmp_path)
    api, result = enumerate_members(repository, page_size=3)

    assert result.run.status == SourceRunStatus.SUCCESS
    assert result.list_total_count == 4
    assert result.pages_committed == 2
    assert [request.url.params["pIndex"] for request in api.requests] == ["1", "2"]
    with repository.sessions() as session:
        observations = list(
            session.scalars(
                select(FeederObservationRow).where(
                    FeederObservationRow.feeder == "assembly_committee_memberships"
                )
            )
        )
        stored = str([row.normalized_json for row in observations])
        stored += str([row.url for row in session.scalars(select(SourceRow))])
        stored += str([row.metadata_json for row in session.scalars(select(SourceSnapshotRow))])
    assert {row.provider_record_key for row in observations} == {
        "C1:M-001",
        "C1:M-002",
        "C2:M-001",
        "C2:M-999",
    }
    for forbidden in (SECRET, "비저장", "非貯藏", "private@example.invalid", "02-000-0000"):
        assert forbidden not in stored


def test_incomplete_or_conflicting_member_list_fails_closed(tmp_path: Path) -> None:
    repository = prepare_repository(tmp_path)
    short = MemberListApi(DEFAULT_ROWS[:3], total=4)
    with pytest.raises(AssemblyCommitteeCoverageError, match="row count is incomplete"):
        AssemblyCommitteeMembershipEnumerator(short.connector(), repository).enumerate()

    conflicting = [*DEFAULT_ROWS, member_list_row("C1", "M-001", "위원")]
    with pytest.raises(AssemblyCommitteeCoverageError, match="conflicting committee/member"):
        enumerate_members(repository, conflicting)
    with pytest.raises(AssemblyCommitteeRoleError, match="success checkpoint|latest successful"):
        AssemblyCommitteeRolePublisher(repository).publish_latest_successful()


def test_only_chair_and_secretary_of_exact_roster_members_become_claims(tmp_path: Path) -> None:
    repository = prepare_repository(tmp_path)
    enumerate_members(repository)

    dry = AssemblyCommitteeRolePublisher(repository).publish_latest_successful(dry_run=True)
    assert dry.published_claims == 2
    assert not [
        claim
        for claim in repository.claims(published_only=True, current_only=True)
        if claim.predicate == "ASSEMBLY_COMMITTEE_ROLE"
    ]

    result = AssemblyCommitteeRolePublisher(repository).publish_latest_successful()
    assert result.observations_considered == 4
    assert result.office_rows == 3
    assert result.published_claims == 2
    # M-999 is not on the current roster: never name-matched or published.
    assert result.unresolved_member_codes == ("M-999",)
    claims = [
        claim
        for claim in repository.claims(published_only=True, current_only=True)
        if claim.predicate == "ASSEMBLY_COMMITTEE_ROLE"
    ]
    assert sorted(claim.object_text for claim in claims) == ["C1위원회 간사", "C1위원회 위원장"]
    chair = next(claim for claim in claims if claim.qualifiers["committee_role"] == "위원장")
    assert chair.proposition.endswith("「C1위원회」 위원장으로 기재되어 있다.")
    secretary = next(claim for claim in claims if claim.qualifiers["committee_role"] == "간사")
    assert secretary.proposition.endswith("「C1위원회」 간사로 기재되어 있다.")

    again = AssemblyCommitteeRolePublisher(repository).publish_latest_successful()
    assert again.published_claims == 0
    assert again.unchanged_claims == 2

    with TestClient(create_app(repository)) as client:
        payload = client.get(f"/people/{chair.person_id}").json()
    current_role = next(
        item for item in payload["profile"]["sections"] if item["id"] == "current_role"
    )
    office = next(
        entry
        for entry in current_role["entries"]
        if entry["details"]["predicate"] == "ASSEMBLY_COMMITTEE_ROLE"
    )
    assert office["claim_id"] == str(chair.id)
    assert office["evidence"][0]["feeder_observation_id"]
    assert office["evidence"][0]["snapshot_id"]


def test_role_change_is_reported_stale_or_fails_closed(tmp_path: Path) -> None:
    repository = prepare_repository(tmp_path)
    enumerate_members(repository)
    AssemblyCommitteeRolePublisher(repository).publish_latest_successful()

    demoted = [member_list_row("C1", "M-001", "위원"), *DEFAULT_ROWS[1:]]
    enumerate_members(repository, demoted)
    result = AssemblyCommitteeRolePublisher(repository).publish_latest_successful(dry_run=True)
    assert len(result.stale_claim_ids) == 1

    changed = [member_list_row("C1", "M-001", "간사"), *DEFAULT_ROWS[1:]]
    enumerate_members(repository, changed)
    with pytest.raises(AssemblyCommitteeRoleError, match="immutable observation version"):
        AssemblyCommitteeRolePublisher(repository).publish_latest_successful()


def test_cli_refuses_dry_run_without_publish(tmp_path: Path) -> None:
    with pytest.raises(SystemExit):
        main(["--dry-run", "--database-url", f"sqlite:///{(tmp_path / 'x.db').as_posix()}"])
