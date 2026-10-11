from __future__ import annotations

from pathlib import Path
from urllib.parse import parse_qs

import httpx
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import select

from packages.connectors.seoul_personnel_notices import (
    SeoulPersonnelNoticeConnector,
    SeoulPersonnelNoticeError,
    seoul_personnel_notice_policy,
)
from packages.domain.db import (
    ClaimRow,
    OrganizationRow,
    PersonRow,
    SourceRow,
    SourceSnapshotRow,
)
from packages.domain.enums import SourceCollectionMode, SourceRunStatus
from packages.persistence import SqlAlchemyRepository
from packages.verification.policy import PolicyDenied
from workers.seoul_personnel_notices import (
    SeoulPersonnelNoticeEnumerator,
)

PHONE = "02-1234-5678"
EMAIL = "staff@example.invalid"
AUTHOR = "민감작성자"
CONTENTS = "<p>상세 본문은 저장하지 않는다.</p>"


def provider_row(
    board_id: str,
    *,
    title: str = "2026년 하반기 4급이상 인사발령",
    filename: str = "3급이상 발령.hwp",
) -> dict[str, object]:
    return {
        "appd_file_name": filename,
        "date_check": "OLD",
        "position": "인사과",
        "file_size": 64000.0,
        "contents": CONTENTS,
        "tel": PHONE,
        "read_cnt": 5193.0,
        "board_id": board_id,
        "file_url": (
            "http://seoulboard.seoul.go.kr/comm/getFile"
            f"?srvcId=BBSTY1&upperNo=461270&fileTy=ATTACH&fileNo={board_id[-1]}&bbsNo=162"
        ),
        "kor_name": AUTHOR,
        "end_date": "2031-07-08 18:33:00.0",
        "title": title,
        "create_date": "",
        "organ": "서울시",
        "email": EMAIL,
        "update_date": "2026-07-16 15:33:33.0",
        "file_count": 0.0,
        "file_appd_id": board_id[-1],
        "start_date": "2026-07-08 18:33:00.0",
    }


def provider_payload(rows: list[dict[str, object]]) -> dict[str, object]:
    return {
        "DESCRIPTION": {
            "BOARD_ID": "게시물 아이디",
            "TITLE": "게시물 제목",
            "TEL": "전화번호",
            "EMAIL": "이메일",
            "CONTENTS": "내용",
            "APPD_FILE_NAME": "파일명",
        },
        "DATA": rows,
    }


class SeoulProvider:
    def __init__(self, rows: list[dict[str, object]] | None = None) -> None:
        self.rows = rows or [
            provider_row("4612707"),
            provider_row("4612708", filename="행정4급 발령.hwp"),
            provider_row("46127010", filename="기술연구4급 발령.hwp"),
        ]
        self.calls = 0
        self.forms: list[dict[str, list[str]]] = []
        self.fail = False

    def handle(self, request: httpx.Request) -> httpx.Response:
        self.calls += 1
        assert request.method == "POST"
        assert str(request.url) == SeoulPersonnelNoticeConnector.DOWNLOAD_URL
        form = parse_qs(request.content.decode(), keep_blank_values=True)
        self.forms.append(form)
        assert form == {
            "srvType": ["S"],
            "infId": ["OA-2483"],
            "serviceKind": ["1"],
            "pageNo": ["1"],
            "strWhere": [""],
            "strOrderby": ["CREATE_DATE DESC"],
            "filterCol": ["필터선택"],
            "txtFilter": [""],
        }
        if self.fail:
            return httpx.Response(503, text="provider unavailable")
        return httpx.Response(200, json=provider_payload(self.rows))

    def connector(self) -> SeoulPersonnelNoticeConnector:
        return SeoulPersonnelNoticeConnector(
            transport=httpx.MockTransport(self.handle)
        )


def migrated_repository(database: Path) -> SqlAlchemyRepository:
    database_url = f"sqlite:///{database.as_posix()}"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(config, "head")
    return SqlAlchemyRepository(database_url)


def test_connector_uses_credential_free_full_download_and_minimizes_content() -> None:
    provider = SeoulProvider()
    connector = provider.connector()

    document = connector.fetch(connector.discover()[0])
    records = connector.parse_records(document)

    assert provider.calls == 1
    assert document.metadata["source_contract"] == connector.SOURCE_CONTRACT
    assert document.metadata["record_count"] == "3"
    assert document.metadata["full_download"] == "true"
    assert records[0].board_id == "4612707"
    assert records[0].organ == "서울시"
    assert records[0].position == "인사과"
    assert records[0].appd_file_name == "3급이상 발령.hwp"

    serialized = document.body
    assert PHONE not in serialized
    assert EMAIL not in serialized
    assert AUTHOR not in serialized
    assert CONTENTS not in serialized
    assert "read_cnt" not in serialized
    assert "tel" not in serialized
    assert "email" not in serialized
    assert "kor_name" not in serialized
    assert "contents" not in serialized
    assert "gridTotalCnt" not in repr(provider.forms)
    assert "ssUserId" not in repr(provider.forms)

    with pytest.raises(ValueError, match="unsupported Seoul personnel-download URL"):
        connector.fetch(
            "https://datafile.seoul.go.kr/bigfile/iot/sheet/json/download.do?key=secret"
        )


def test_full_download_persists_only_observations_and_no_people(tmp_path: Path) -> None:
    repository = migrated_repository(tmp_path / "seoul.db")
    provider = SeoulProvider()

    result = SeoulPersonnelNoticeEnumerator(
        provider.connector(), repository
    ).enumerate()

    assert result.run.status == SourceRunStatus.SUCCESS
    assert result.unique_records == 3
    assert result.run.records_seen == 3
    assert result.run.observations_created == 3

    checkpoint = repository.source_checkpoint(
        SeoulPersonnelNoticeEnumerator.FEEDER,
        SeoulPersonnelNoticeEnumerator.SCOPE_KEY,
    )
    assert checkpoint is not None
    assert checkpoint.cursor == "complete"
    assert checkpoint.metadata["record_count"] == 3
    assert checkpoint.metadata["full_download"] is True
    assert len(checkpoint.metadata["manifest_sha256"]) == 64

    observations = repository.feeder_observations(
        SeoulPersonnelNoticeEnumerator.FEEDER,
        SeoulPersonnelNoticeEnumerator.SCOPE_KEY,
    )
    assert len(observations) == 3
    assert all(item.identity_hints == {} for item in observations)
    persisted = repr([item.model_dump(mode="json") for item in observations])
    for blocked in (PHONE, EMAIL, AUTHOR, CONTENTS, "read_cnt", '"tel"', '"email"'):
        assert blocked not in persisted

    with repository.sessions() as session:
        assert list(session.scalars(select(PersonRow))) == []
        assert list(session.scalars(select(OrganizationRow))) == []
        assert list(session.scalars(select(ClaimRow))) == []
        sources = list(session.scalars(select(SourceRow)))
        snapshots = list(session.scalars(select(SourceSnapshotRow)))
    assert len(sources) == 1
    assert len(snapshots) == 1
    assert snapshots[0].fulltext is None
    assert PHONE not in repr(snapshots[0].metadata_json)
    assert EMAIL not in repr(snapshots[0].metadata_json)


def test_rerun_is_idempotent_and_changed_row_creates_new_version(tmp_path: Path) -> None:
    repository = migrated_repository(tmp_path / "rerun.db")
    provider = SeoulProvider()
    enumerator = SeoulPersonnelNoticeEnumerator(provider.connector(), repository)

    first = enumerator.enumerate()
    second = enumerator.enumerate()
    provider.rows[0] = provider_row(
        "4612707",
        title="2026년 하반기 4급이상 인사발령 정정",
    )
    changed = enumerator.enumerate()

    assert first.run.observations_created == 3
    assert second.run.observations_created == 0
    assert second.run.observations_unchanged == 3
    assert changed.run.observations_created == 1
    assert changed.run.observations_unchanged == 2

    versions = repository.feeder_observations(
        SeoulPersonnelNoticeEnumerator.FEEDER,
        SeoulPersonnelNoticeEnumerator.SCOPE_KEY,
        "4612707",
    )
    assert len(versions) == 2
    assert len({item.content_hash for item in versions}) == 2


def test_duplicate_or_missing_provider_identity_fails_closed(tmp_path: Path) -> None:
    duplicate_repository = migrated_repository(tmp_path / "duplicate.db")
    duplicate = SeoulProvider(
        [provider_row("4612707"), provider_row("4612707")]
    )
    with pytest.raises(SeoulPersonnelNoticeError, match="duplicate"):
        SeoulPersonnelNoticeEnumerator(
            duplicate.connector(), duplicate_repository
        ).enumerate()
    assert duplicate_repository.source_runs()[-1].status == SourceRunStatus.FAILED

    missing_repository = migrated_repository(tmp_path / "missing.db")
    bad = provider_row("4612707")
    bad.pop("board_id")
    missing = SeoulProvider([bad])
    with pytest.raises(SeoulPersonnelNoticeError, match="reviewed source fields"):
        SeoulPersonnelNoticeEnumerator(
            missing.connector(), missing_repository
        ).enumerate()
    assert missing_repository.source_runs()[-1].status == SourceRunStatus.FAILED


def test_policy_denial_precedes_network_and_rights_are_explicit(tmp_path: Path) -> None:
    repository = migrated_repository(tmp_path / "blocked.db")
    provider = SeoulProvider()
    policy = seoul_personnel_notice_policy()
    assert policy.can_fetch is True
    assert policy.can_store_metadata is True
    assert policy.can_store_fulltext is False
    assert policy.can_send_to_ai is False
    assert policy.can_show_excerpt is False
    assert policy.can_commercialize is True
    assert "공공누리 제1유형" in (policy.license or "")

    blocked = policy.model_copy(
        update={"collection_mode": SourceCollectionMode.BLOCKED, "can_fetch": False}
    )
    with pytest.raises(PolicyDenied):
        SeoulPersonnelNoticeEnumerator(
            provider.connector(), repository, blocked
        ).enumerate()
    assert provider.calls == 0
    assert repository.source_runs() == []


def test_http_failure_is_redacted_and_creates_failed_run(tmp_path: Path) -> None:
    repository = migrated_repository(tmp_path / "failure.db")
    provider = SeoulProvider()
    provider.fail = True

    with pytest.raises(SeoulPersonnelNoticeError, match="request failed"):
        SeoulPersonnelNoticeEnumerator(
            provider.connector(), repository
        ).enumerate()

    failed = repository.source_runs()[-1]
    assert failed.status == SourceRunStatus.FAILED
    assert failed.error_code == "SeoulPersonnelNoticeError"
    assert failed.error_summary == "Seoul personnel enumeration did not complete"
