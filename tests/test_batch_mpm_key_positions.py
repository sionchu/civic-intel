from __future__ import annotations

from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse
from xml.sax.saxutils import escape
from zipfile import ZipFile

import httpx
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import select

from packages.connectors.mpm_key_positions import (
    ATTACHMENTS,
    MpmKeyPositionsConnector,
    MpmKeyPositionsError,
    mpm_key_positions_policy,
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
from workers.mpm_key_positions import (
    MpmKeyPositionsCoverageError,
    MpmKeyPositionsEnumerator,
)

PHONE = "02-9999-9999"


def _cell(ref: str, value: str) -> str:
    return (
        f'<c r="{ref}" t="inlineStr"><is><t>{escape(value)}</t></is></c>'
    )


def xlsx_bytes(
    rows: list[tuple[str, str, str, str, str, str, str, str]],
    *,
    sheet_name: str = "테스트기관",
    valid_header: bool = True,
    compact_person_headers: bool = False,
    phone_header: str = "6) 전화번호",
) -> bytes:
    header_a = "연번" if valid_header else "번호"
    header = [
        header_a,
        "1) 소속부서",
        "",
        "2)직위(직위명)" if compact_person_headers else "2) 직위(직위명)",
        "3)성명" if compact_person_headers else "3) 성명",
        "4) 직급·직무등급",
        "5) 담당업무",
        phone_header,
    ]
    rendered_rows = [
        '<row r="2">' + _cell("A2", f"({sheet_name}) 주요직위 명부") + "</row>",
        '<row r="3">' + _cell("F3", "('26.4.30. 기준)") + "</row>",
        '<row r="4">'
        + "".join(_cell(f"{chr(65 + index)}4", value) for index, value in enumerate(header))
        + "</row>",
    ]
    for row_number, values in enumerate(rows, start=5):
        rendered_rows.append(
            f'<row r="{row_number}">'
            + "".join(
                _cell(f"{chr(65 + index)}{row_number}", value)
                for index, value in enumerate(values)
            )
            + "</row>"
        )
    worksheet = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        "<sheetData>"
        + "".join(rendered_rows)
        + "</sheetData></worksheet>"
    )
    workbook = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        "<sheets>"
        f'<sheet name="{escape(sheet_name)}" sheetId="1" r:id="rId1"/>'
        "</sheets></workbook>"
    )
    relationships = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
        'Target="worksheets/sheet1.xml"/>'
        "</Relationships>"
    )
    stream = BytesIO()
    with ZipFile(stream, "w") as archive:
        archive.writestr("xl/workbook.xml", workbook)
        archive.writestr("xl/_rels/workbook.xml.rels", relationships)
        archive.writestr("xl/worksheets/sheet1.xml", worksheet)
    return stream.getvalue()


def source_rows(
    *,
    person: str = "홍길동",
    responsibility: str = "기관 주요정책 총괄",
) -> list[tuple[str, str, str, str, str, str, str, str]]:
    return [
        ("1", "본부", "기획실", "실장", person, "고위공무원 가급", responsibility, PHONE),
        ("2", "본부", "감사관실", "감사관", "공석", "고위공무원 나급", "감사업무", PHONE),
    ]


class MpmProvider:
    def __init__(self) -> None:
        self.payloads = {
            item.group: xlsx_bytes(source_rows(), sheet_name=f"{item.group}-기관")
            for item in ATTACHMENTS
        }
        self.fail_groups: set[str] = set()
        self.calls: list[str] = []

    def handle(self, request: httpx.Request) -> httpx.Response:
        path = urlparse(str(request.url)).path
        attachment = next(item for item in ATTACHMENTS if item.path == path)
        self.calls.append(attachment.group)
        if attachment.group in self.fail_groups:
            return httpx.Response(503, text="provider unavailable")
        return httpx.Response(
            200,
            content=self.payloads[attachment.group],
            headers={
                "Content-Type": (
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            },
        )

    def connector(self, group: str = "ministries") -> MpmKeyPositionsConnector:
        return MpmKeyPositionsConnector(
            group=group,
            transport=httpx.MockTransport(self.handle),
        )


def migrated_repository(database: Path) -> SqlAlchemyRepository:
    database_url = f"sqlite:///{database.as_posix()}"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(config, "head")
    return SqlAlchemyRepository(database_url)


def test_connector_parses_named_and_vacant_rows_without_phone() -> None:
    provider = MpmProvider()
    connector = provider.connector()
    document = connector.fetch(connector.discover()[0])
    records = connector.parse_records(document)

    assert document.metadata["source_contract"] == connector.SOURCE_CONTRACT
    assert document.metadata["record_count"] == "2"
    assert document.metadata["sheet_count"] == "1"
    assert document.metadata["phone_retained"] == "false"
    assert PHONE not in document.body
    assert records[0].person_name == "홍길동"
    assert records[0].position_name == "실장"
    assert records[0].provider_record_key.startswith("FILE_000000100069052:1:")
    assert records[1].vacant is True
    assert records[1].person_name is None
    assert all(not hasattr(item, "phone") for item in records)

    with pytest.raises(ValueError, match="unsupported MPM key-position attachment path"):
        connector.fetch("https://www.mpm.go.kr/board/file/unreviewed.xlsx")




def test_parser_accepts_verified_live_header_variants() -> None:
    provider = MpmProvider()
    provider.payloads["ministries"] = xlsx_bytes(
        source_rows(),
        compact_person_headers=True,
        phone_header="7) 전화번호",
    )
    connector = provider.connector()
    records = connector.parse_records(connector.fetch(connector.discover()[0]))
    assert len(records) == 2
    assert records[0].person_name == "홍길동"
    assert PHONE not in repr(records)


def test_full_release_enumeration_is_complete_minimized_and_person_neutral(
    tmp_path: Path,
) -> None:
    repository = migrated_repository(tmp_path / "mpm.db")
    provider = MpmProvider()

    result = MpmKeyPositionsEnumerator(provider.connector(), repository).enumerate()

    assert result.run.status == SourceRunStatus.SUCCESS
    assert result.attachments_committed == 3
    assert result.unique_records == 6
    assert result.run.records_seen == 6
    assert result.run.observations_created == 6
    assert provider.calls == ["ministries", "other", "agencies"]

    checkpoint = repository.source_checkpoint(
        MpmKeyPositionsEnumerator.FEEDER,
        "as_of:2026-04-30",
    )
    assert checkpoint is not None
    assert checkpoint.cursor == "3"
    assert checkpoint.metadata["committed_records"] == 6
    assert checkpoint.metadata["expected_groups"] == ["ministries", "other", "agencies"]
    assert set(checkpoint.metadata["attachment_hashes"]) == {
        "ministries",
        "other",
        "agencies",
    }

    observations = repository.feeder_observations(
        MpmKeyPositionsEnumerator.FEEDER,
        "as_of:2026-04-30",
    )
    assert len(observations) == 6
    assert all(item.identity_hints == {} for item in observations)
    persisted = repr([item.model_dump(mode="json") for item in observations])
    assert PHONE not in persisted
    assert "office_phone" not in persisted
    assert "홍길동" in persisted

    with repository.sessions() as session:
        assert list(session.scalars(select(PersonRow))) == []
        assert list(session.scalars(select(OrganizationRow))) == []
        assert list(session.scalars(select(ClaimRow))) == []
        sources = list(session.scalars(select(SourceRow)))
        snapshots = list(session.scalars(select(SourceSnapshotRow)))
    assert len(sources) == 3
    assert len(snapshots) == 3
    assert all(item.fulltext is None for item in snapshots)
    assert PHONE not in repr([item.metadata_json for item in snapshots])


def test_rerun_is_noop_and_changed_source_row_creates_version(tmp_path: Path) -> None:
    repository = migrated_repository(tmp_path / "rerun.db")
    provider = MpmProvider()
    enumerator = MpmKeyPositionsEnumerator(provider.connector(), repository)

    first = enumerator.enumerate()
    second = enumerator.enumerate()
    provider.payloads["ministries"] = xlsx_bytes(
        source_rows(responsibility="정정된 기관 주요정책 총괄"),
        sheet_name="ministries-기관",
    )
    changed = enumerator.enumerate()

    assert first.run.observations_created == 6
    assert second.run.observations_created == 0
    assert second.run.observations_unchanged == 6
    assert changed.run.observations_created == 1
    assert changed.run.observations_unchanged == 5
    versions = repository.feeder_observations(
        MpmKeyPositionsEnumerator.FEEDER,
        "as_of:2026-04-30",
        "FILE_000000100069052:1:5",
    )
    assert len(versions) == 2
    assert len({item.content_hash for item in versions}) == 2


def test_partial_failure_resume_revalidates_completed_attachment(tmp_path: Path) -> None:
    repository = migrated_repository(tmp_path / "resume.db")
    provider = MpmProvider()
    provider.fail_groups.add("other")
    enumerator = MpmKeyPositionsEnumerator(provider.connector(), repository)

    with pytest.raises(MpmKeyPositionsError):
        enumerator.enumerate()

    partial = repository.source_runs(
        MpmKeyPositionsEnumerator.FEEDER,
        "as_of:2026-04-30",
    )[-1]
    assert partial.status == SourceRunStatus.PARTIAL
    assert partial.checkpoint_after == "1"

    provider.fail_groups.clear()
    resumed = enumerator.enumerate(resume=True)
    assert resumed.run.status == SourceRunStatus.SUCCESS
    assert resumed.attachments_committed == 2
    assert resumed.unique_records == 6
    assert provider.calls[-3:] == ["ministries", "other", "agencies"]


def test_resume_fails_closed_when_completed_attachment_changes(tmp_path: Path) -> None:
    repository = migrated_repository(tmp_path / "drift.db")
    provider = MpmProvider()
    provider.fail_groups.add("other")
    enumerator = MpmKeyPositionsEnumerator(provider.connector(), repository)
    with pytest.raises(MpmKeyPositionsError):
        enumerator.enumerate()

    provider.fail_groups.clear()
    provider.payloads["ministries"] = xlsx_bytes(
        source_rows(person="변경된이름"),
        sheet_name="ministries-기관",
    )
    with pytest.raises(MpmKeyPositionsCoverageError, match="changed before resume"):
        enumerator.enumerate(resume=True)


def test_parser_and_policy_fail_closed_on_schema_or_rights_change() -> None:
    provider = MpmProvider()
    provider.payloads["ministries"] = xlsx_bytes(
        source_rows(),
        valid_header=False,
    )
    connector = provider.connector()
    with pytest.raises(MpmKeyPositionsError, match="expected header"):
        connector.fetch(connector.discover()[0])

    policy = mpm_key_positions_policy()
    assert policy.can_fetch is True
    assert policy.can_store_metadata is True
    assert policy.can_store_fulltext is False
    assert policy.can_send_to_ai is False
    assert policy.can_show_excerpt is False
    assert policy.can_commercialize is True
    assert "15060548" in (policy.license or "")

    provider.calls.clear()
    blocked = policy.model_copy(
        update={"collection_mode": SourceCollectionMode.BLOCKED, "can_fetch": False}
    )
    repository = SqlAlchemyRepository("sqlite:///:memory:")
    with pytest.raises((PolicyDenied, RuntimeError)):
        MpmKeyPositionsEnumerator(provider.connector(), repository, blocked).enumerate()
    assert provider.calls == []
