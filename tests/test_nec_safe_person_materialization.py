from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from apps.api.main import create_app
from packages.connectors.nec_local_elections import NecApiError, NecCandidateConnector
from packages.domain import db
from packages.domain.admin import AdminCommand
from packages.domain.enums import IdentityStatus, PublicationStatus
from packages.persistence import SqlAlchemyRepository
from packages.verification.nec_person_materialization import (
    NEC_CANDIDACY_PREDICATE,
    NecPersonMaterializationError,
)
from workers.local_elections import LocalElectionCandidateEnumerator
from workers.nec_safe_person_materialization import main

SECRET = "nec-materialization-secret"
SCOPE = "20260603:4"


def candidate_row(
    candidate_id: str,
    name: str,
    *,
    birthday: str = "19700102",
    status: str = "등록",
    party: str = "테스트당",
) -> dict[str, str]:
    return {
        "sgId": "20260603",
        "sgTypecode": "4",
        "huboid": candidate_id,
        "sggName": "테스트시장선거",
        "sdName": "경기도",
        "wiwName": "테스트시",
        "giho": "1",
        "gihoSangse": "",
        "jdName": party,
        "name": name,
        "hanjaName": f"{name}漢字",
        "birthday": birthday,
        "job": "정당인",
        "edu": "테스트대학교 졸업",
        "career1": "(전) 테스트시의원",
        "career2": "-",
        "status": status,
    }


class CandidateApi:
    def __init__(
        self,
        pages: dict[int, list[dict[str, str]]],
        *,
        fail_once_page: int | None = None,
    ) -> None:
        self.pages = pages
        self.fail_once_page = fail_once_page
        self.failed = False

    def handle(self, request: httpx.Request) -> httpx.Response:
        assert request.url.params["serviceKey"] == SECRET
        page = int(request.url.params["pageNo"])
        page_size = int(request.url.params["numOfRows"])
        if page == self.fail_once_page and not self.failed:
            self.failed = True
            raise httpx.ReadError("synthetic provider interruption", request=request)
        rows = self.pages.get(page, [])
        total = sum(len(items) for items in self.pages.values())
        return httpx.Response(
            200,
            json={
                "response": {
                    "header": {"resultCode": "INFO-00", "resultMsg": "NORMAL SERVICE"},
                    "body": {
                        "pageNo": page,
                        "numOfRows": page_size,
                        "totalCount": total,
                        "items": {"item": rows} if rows else {},
                    },
                }
            },
        )

    def connector(self, *, page_size: int = 2) -> NecCandidateConnector:
        return NecCandidateConnector(
            election_id="20260603",
            election_type=4,
            api_key=SECRET,
            page_size=page_size,
            transport=httpx.MockTransport(self.handle),
        )


def migrated_repository(database: Path) -> SqlAlchemyRepository:
    url = f"sqlite:///{database.as_posix()}"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", url)
    command.upgrade(config, "head")
    return SqlAlchemyRepository(url)


def ready_repository(tmp_path: Path) -> tuple[SqlAlchemyRepository, CandidateApi]:
    repository = migrated_repository(tmp_path / "nec-materialization.db")
    api = CandidateApi(
        {
            1: [
                candidate_row("C-001", "가후보"),
                candidate_row("C-002", "나후보", birthday="19800203"),
            ],
            2: [candidate_row("C-003", "다후보", birthday="19900304")],
        }
    )
    LocalElectionCandidateEnumerator(api.connector(), repository).enumerate()
    return repository, api


def test_preflight_creates_private_source_context_packets(tmp_path: Path) -> None:
    repository, _ = ready_repository(tmp_path)

    preflight = repository.prepare_nec_person_materialization(election_types=(4,))
    payload = preflight.to_dict()

    assert payload["current_candidate_rows"] == 3
    assert payload["scope_totals"] == {SCOPE: 3}
    assert payload["action_counts"] == {
        "CREATE": 3,
        "REVIEW": 0,
        "CONFLICT": 0,
        "NOOP": 0,
    }
    assert payload["source_fetch"] is False
    assert payload["claim_publication"] is False
    assert payload["cross_source_link"] is False
    assert payload["human_verified"] is False
    assert payload["selected_count"] == 3
    assert all(
        item["person_identity_status"] == IdentityStatus.REVIEW.value
        for item in payload["selected"]
    )
    assert all(
        item["claim_predicate"] == NEC_CANDIDACY_PREDICATE
        and item["claim_publication_status"] == PublicationStatus.DRAFT.value
        and item["claim_asserted_as_true"] is False
        for item in payload["selected"]
    )


def test_commit_is_atomic_idempotent_and_keeps_publication_closed(tmp_path: Path) -> None:
    repository, _ = ready_repository(tmp_path)
    before = repository.prepare_nec_person_materialization(election_types=(4,))

    committed = repository.commit_nec_person_materialization(
        expected_receipt_sha256=before.sha256(),
        election_types=(4,),
    )

    assert committed["status"] == "COMMITTED"
    assert committed["created_people"] == 3
    assert committed["created_claims"] == 3
    assert committed["created_evidence"] == 3
    assert committed["created_links"] == 3
    assert committed["claim_publication"] is False
    assert repository.public_people() == []

    with repository.sessions() as session:
        people = list(session.scalars(select(db.PersonRow)))
        claims = list(
            session.scalars(
                select(db.ClaimRow).where(db.ClaimRow.predicate == NEC_CANDIDACY_PREDICATE)
            )
        )
        evidence_count = session.scalar(select(func.count()).select_from(db.ClaimEvidenceRow))
        links = list(session.scalars(select(db.PersonObservationLinkRow)))
    assert len(people) == 3
    assert all(row.identity_status == IdentityStatus.REVIEW.value for row in people)
    assert len(claims) == 3
    assert all(row.publication_status == PublicationStatus.DRAFT.value for row in claims)
    assert evidence_count == 3
    assert len(links) == 3
    assert all(row.decision_class == "DETERMINISTIC_SOURCE_CONTEXT" for row in links)

    rerun = repository.prepare_nec_person_materialization(election_types=(4,))
    assert rerun.action_counts() == {
        "CREATE": 0,
        "REVIEW": 0,
        "CONFLICT": 0,
        "NOOP": 3,
    }
    assert rerun.reason_counts() == {"ALREADY_MATERIALIZED": 3}
    noop = repository.commit_nec_person_materialization(
        expected_receipt_sha256=rerun.sha256(),
        election_types=(4,),
    )
    assert noop["status"] == "NOOP"
    assert noop["write_performed"] is False


def test_existing_name_collision_never_auto_links(tmp_path: Path) -> None:
    repository, _ = ready_repository(tmp_path)
    now = datetime.now(UTC)
    with repository.sessions() as session:
        session.add(
            db.PersonRow(
                id="00000000-0000-0000-0000-000000000777",
                canonical_name="가후보",
                birth_date=None,
                identity_status=IdentityStatus.RESOLVED.value,
                valid_from=now,
                valid_to=None,
                recorded_at=now,
                superseded_at=None,
            )
        )
        session.commit()

    preflight = repository.prepare_nec_person_materialization(election_types=(4,))
    row = next(item for item in preflight.items if item.canonical_name == "가후보")

    assert row.action == "REVIEW"
    assert row.reason == "CURRENT_PERSON_OR_ALIAS_COLLISION"
    assert preflight.action_counts()["CREATE"] == 2


def test_historical_candidate_drift_is_review_not_second_person(tmp_path: Path) -> None:
    repository, api = ready_repository(tmp_path)
    api.pages[1][0] = candidate_row("C-001", "가후보", status="사퇴")
    LocalElectionCandidateEnumerator(api.connector(), repository).enumerate()

    preflight = repository.prepare_nec_person_materialization(election_types=(4,))
    row = next(item for item in preflight.items if item.provider_record_key == "C-001")

    assert row.action == "REVIEW"
    assert row.reason == "HISTORICAL_VERSION_DRIFT"


def test_stale_receipt_fails_before_write(tmp_path: Path) -> None:
    repository, api = ready_repository(tmp_path)
    preflight = repository.prepare_nec_person_materialization(election_types=(4,))
    api.pages[1][0] = candidate_row("C-001", "가후보", status="사퇴")
    LocalElectionCandidateEnumerator(api.connector(), repository).enumerate()

    with pytest.raises(NecPersonMaterializationError, match="preflight changed"):
        repository.commit_nec_person_materialization(
            expected_receipt_sha256=preflight.sha256(),
            election_types=(4,),
        )
    with repository.sessions() as session:
        assert session.scalar(select(func.count()).select_from(db.PersonRow)) == 0


def test_cli_dry_run_and_exact_commit(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    repository, _ = ready_repository(tmp_path)
    database_url = str(repository.engine.url)

    assert (
        main(
            [
                "--database-url",
                database_url,
                "--types",
                "4",
            ]
        )
        == 0
    )
    dry_run = json.loads(capsys.readouterr().out)
    assert dry_run["selected_count"] == 3
    assert dry_run["write_performed"] is False

    assert (
        main(
            [
                "--database-url",
                database_url,
                "--types",
                "4",
                "--commit",
                "--expected-receipt-sha256",
                dry_run["receipt_sha256"],
            ]
        )
        == 0
    )
    committed = json.loads(capsys.readouterr().out)
    assert committed["status"] == "COMMITTED"
    assert committed["created_people"] == 3

def test_preflight_accepts_successful_resumed_full_checkpoint(tmp_path: Path) -> None:
    repository = migrated_repository(tmp_path / "nec-resume.db")
    api = CandidateApi(
        {
            1: [
                candidate_row("C-001", "가후보"),
                candidate_row("C-002", "나후보", birthday="19800203"),
            ],
            2: [candidate_row("C-003", "다후보", birthday="19900304")],
        },
        fail_once_page=2,
    )
    enumerator = LocalElectionCandidateEnumerator(api.connector(), repository)

    with pytest.raises(NecApiError):
        enumerator.enumerate()

    resumed = LocalElectionCandidateEnumerator(api.connector(), repository).enumerate(resume=True)
    assert resumed.run.status.value == "SUCCESS"
    assert resumed.run.checkpoint_before == "1"
    assert resumed.run.records_seen == 1

    preflight = repository.prepare_nec_person_materialization(election_types=(4,))
    assert preflight.action_counts() == {
        "CREATE": 3,
        "REVIEW": 0,
        "CONFLICT": 0,
        "NOOP": 0,
    }
    assert preflight.scope_totals == {SCOPE: 3}

def test_missing_birth_date_stays_review(tmp_path: Path) -> None:
    repository = migrated_repository(tmp_path / "nec-missing-birth.db")
    api = CandidateApi(
        {
            1: [candidate_row("C-001", "생년월일없음", birthday="")],
        }
    )
    LocalElectionCandidateEnumerator(api.connector(page_size=1), repository).enumerate()

    preflight = repository.prepare_nec_person_materialization(election_types=(4,))
    assert preflight.action_counts() == {
        "CREATE": 0,
        "REVIEW": 1,
        "CONFLICT": 0,
        "NOOP": 0,
    }
    assert preflight.reason_counts() == {"IDENTITY_ANCHOR_MISSING": 1}

def test_nec_source_context_requires_human_resolution_then_separate_publication(
    tmp_path: Path,
) -> None:
    repository, _ = ready_repository(tmp_path)
    preflight = repository.prepare_nec_person_materialization(election_types=(4,))
    repository.commit_nec_person_materialization(
        expected_receipt_sha256=preflight.sha256(),
        election_types=(4,),
    )
    item = preflight.create_items[0]
    assert item.packet is not None
    person_id = item.packet.person.id
    claim_id = item.packet.claim.id

    with TestClient(create_app(repository)) as client:
        assert client.get(f"/people/{person_id}").status_code == 404
        assert all(row["id"] != str(person_id) for row in client.get("/people").json())

    resolve = AdminCommand(
        request_id=uuid4(),
        action="RESOLVE_PERSON",
        record_ids=(person_id,),
        reason="공식 NEC 후보자 행의 이름·생년월일·선거 범위와 정확한 근거를 직접 확인했습니다.",
        human_verified=True,
    )
    preview = repository.admin_preview(resolve)
    receipt = repository.admin_commit(resolve, "test-reviewer", preview["state_hash"])
    assert receipt["result"]["outcomes"][0]["source_context_type"] == "NEC_CANDIDACY"
    assert receipt["result"]["outcomes"][0]["cross_source_merge"] is False
    assert repository.person(person_id).identity_status == IdentityStatus.RESOLVED

    with repository.sessions() as session:
        session.add(
            db.ClaimRow(
                id=str(uuid4()),
                person_id=str(person_id),
                organization_id=None,
                subject="다른 공개 기록",
                predicate="UNRELATED_PUBLISHED_CLAIM",
                object_text="NEC candidacy와 무관한 공개 기록",
                proposition="NEC candidacy와 무관한 공개 기록이다.",
                qualifiers={},
                epistemic_status="CLAIM",
                publication_status="PUBLISHED",
                asserted_as_true=False,
                resolution_note=None,
                valid_from=datetime.now(UTC),
                valid_to=None,
                recorded_at=datetime.now(UTC),
                superseded_at=None,
            )
        )
        session.commit()

    with TestClient(create_app(repository)) as client:
        assert client.get(f"/people/{person_id}").status_code == 404

    publish = AdminCommand(
        request_id=uuid4(),
        action="PUBLISH",
        record_ids=(claim_id,),
        reason="사람 확인과 별도로 NEC 후보자 Claim의 현재 근거를 확인해 공개합니다.",
    )
    publish_preview = repository.admin_preview(publish)
    repository.admin_commit(publish, "test-reviewer", publish_preview["state_hash"])

    with TestClient(create_app(repository)) as client:
        assert client.get(f"/people/{person_id}").status_code == 200
        assert any(row["id"] == str(person_id) for row in client.get("/people").json())

    rerun = repository.prepare_nec_person_materialization(election_types=(4,))
    selected = next(row for row in rerun.items if row.observation_id == item.observation_id)
    assert selected.action == "NOOP"
    assert selected.reason == "ALREADY_MANAGED"
