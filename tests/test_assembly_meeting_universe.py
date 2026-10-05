from __future__ import annotations

from pathlib import Path

import httpx
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import select

from packages.connectors.open_assembly import AssemblyApiError, MissingAssemblyApiKey
from packages.connectors.open_assembly_meetings import OpenAssemblyMinutesIndexConnector
from packages.domain.db import (
    ClaimRow,
    FeederObservationRow,
    OrganizationRow,
    PersonRow,
    SourceSnapshotRow,
)
from packages.domain.enums import SourceRunStatus
from packages.persistence import SqlAlchemyRepository
from workers.assembly_meeting_universe import (
    AssemblyMeetingUniverseEnumerator,
    AssemblyMeetingUniverseError,
)

SECRET = "meeting-universe-secret-must-not-persist"
COMMITTEE = OpenAssemblyMinutesIndexConnector.COMMITTEE
PLENARY = OpenAssemblyMinutesIndexConnector.PLENARY
PDF = "https://record.assembly.go.kr/assembly/viewer/minutes/download/pdf.do?id={}"

# Row shapes mirror keyed responses captured from open.assembly.go.kr on 2026-10-05
# (ncwgseseafwbuheph / nzbyfwhwaoanttzje, DAE_NUM=22, CONF_DATE=YYYY): one row per agenda item.


def committee_row(conf_id: str, number: int, day: str, agenda: int, **overrides) -> dict:
    row: dict[str, object] = {
        "CONFER_NUM": str(number),
        "TITLE": f"제22대 제439회 제3차 행정안전위원회 ({day})",
        "CLASS_NAME": "상임위원회",
        "DAE_NUM": "22",
        "COMM_NAME": "행정안전위원회",
        "VODCOMM_CODE": None,
        "CONF_DATE": day,
        "SUB_NAME": f"{agenda}. 테스트 안건",
        "VOD_LINK_URL": "http://w3.assembly.go.kr/main/player.do?menu=1",
        "CONF_LINK_URL": f"https://record.assembly.go.kr/assembly/viewer/minutes/xml.do?id={number}",
        "PDF_LINK_URL": PDF.format(number),
        "PDF_FILE_ID": "1391295",
        "DEPT_CD": "9700480",
        "CONF_ID": conf_id,
        "KEY": SECRET,
    }
    row.update(overrides)
    return row


def plenary_row(conf_id: str, number: int, day: str, agenda: int) -> dict:
    return {
        "CONFER_NUM": str(number),
        "TITLE": f"제22대 제439회 제10차 국회본회의 ({day})",
        "CLASS_NAME": "국회본회의",
        "DAE_NUM": "22",
        "CONF_DATE": day,
        "SUB_NAME": f"{agenda}. 본회의 안건",
        "VOD_LINK_URL": None,
        "CONF_LINK_URL": None,
        "PDF_LINK_URL": PDF.format(number),
        "CONF_ID": conf_id,
    }


def envelope(code: str, rows: list[dict], total: int) -> dict:
    if total == 0:
        return {"RESULT": {"CODE": "INFO-200", "MESSAGE": "해당하는 데이터가 없습니다."}}
    return {
        code: [
            {"head": [{"list_total_count": total}, {"RESULT": {"CODE": "INFO-000"}}]},
            {"row": rows},
        ]
    }


class IndexApi:
    def __init__(self) -> None:
        self.rows: dict[tuple[str, str], list[dict]] = {
            (PLENARY, "2024"): [
                plenary_row("053846", 900, "2024-06-05", 1),
            ],
            (PLENARY, "2025"): [
                plenary_row("N054001", 950, "2025-03-04", 1),
                plenary_row("N054001", 950, "2025-03-04", 2),
            ],
            (COMMITTEE, "2024"): [
                committee_row("053900", 901, "2024-07-01", 1),
                committee_row("053900", 901, "2024-07-01", 2),
                committee_row("053900", 901, "2024-07-01", 3),
            ],
            (COMMITTEE, "2025"): [
                committee_row("N054010", 960, "2025-04-01", 1),
                committee_row("N054011", 961, "2025-04-02", 1),
            ],
        }
        self.total_override: dict[tuple[str, str, int], int] = {}
        self.calls: list[tuple[str, str, int]] = []

    def handle(self, request: httpx.Request) -> httpx.Response:
        assert request.url.params["KEY"] == SECRET
        assert request.url.params["DAE_NUM"] == "22"
        code = request.url.path.rsplit("/", 1)[-1]
        year = request.url.params["CONF_DATE"]
        page = int(request.url.params["pIndex"])
        size = int(request.url.params["pSize"])
        self.calls.append((code, year, page))
        rows = self.rows.get((code, year), [])
        total = self.total_override.get((code, year, page), len(rows))
        return httpx.Response(
            200, json=envelope(code, rows[(page - 1) * size : page * size], total)
        )

    def connector(self, *, page_size: int = 2) -> OpenAssemblyMinutesIndexConnector:
        return OpenAssemblyMinutesIndexConnector(
            index_code=COMMITTEE,
            assembly_age=22,
            year=2024,
            api_key=SECRET,
            page_size=page_size,
            transport=httpx.MockTransport(self.handle),
        )


def migrated_repository(tmp_path: Path) -> SqlAlchemyRepository:
    database_url = f"sqlite:///{(tmp_path / 'universe.db').as_posix()}"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(config, "head")
    return SqlAlchemyRepository(database_url)


def enumerator(api: IndexApi, repository: SqlAlchemyRepository, **kwargs):
    kwargs.setdefault("from_year", 2024)
    kwargs.setdefault("to_year", 2025)
    return AssemblyMeetingUniverseEnumerator(api.connector(), repository, **kwargs)


def test_universe_observes_each_conf_id_once_across_indexes_years_and_pages(tmp_path):
    api = IndexApi()
    repository = migrated_repository(tmp_path)

    result = enumerator(api, repository).enumerate()

    assert result.run.status is SourceRunStatus.SUCCESS
    assert result.index_row_count == 8
    assert result.meeting_count == 5
    assert result.meetings_by_index == {"committee": 3, "plenary": 2}
    assert result.run.observations_created == 5
    # Lower-bound probes for both indexes, then every page of every (index, year).
    assert (PLENARY, "2023", 1) in api.calls and (COMMITTEE, "2023", 1) in api.calls
    assert (COMMITTEE, "2024", 2) in api.calls

    with repository.sessions() as session:
        observations = session.scalars(select(FeederObservationRow)).all()
        snapshots = session.scalars(select(SourceSnapshotRow)).all()
        assert session.scalars(select(PersonRow)).all() == []
        assert session.scalars(select(OrganizationRow)).all() == []
        assert session.scalars(select(ClaimRow)).all() == []
    by_key = {item.provider_record_key: item for item in observations}
    assert sorted(by_key) == ["053846", "053900", "N054001", "N054010", "N054011"]
    meeting = by_key["053900"].normalized_json
    assert meeting["index_agenda_row_count"] == 3
    assert meeting["minutes_number"] == 901
    assert meeting["minutes_index"] == "committee"
    assert meeting["committee_dept_code"] == "9700480"
    assert meeting["minutes_pdf_url"] == PDF.format(901)
    assert "SUB_NAME" not in str(meeting) and "테스트 안건" not in str(meeting)
    assert by_key["N054001"].normalized_json["committee_name"] is None
    assert by_key["053900"].identity_hints_json == {}
    dumped = " ".join(
        str(value) for item in [*observations, *snapshots] for value in vars(item).values()
    )
    assert SECRET not in dumped
    assert "VOD_LINK_URL" not in dumped


def test_rerun_is_idempotent(tmp_path):
    api = IndexApi()
    repository = migrated_repository(tmp_path)
    first = enumerator(api, repository).enumerate()
    second = enumerator(api, repository).enumerate()
    assert first.universe_fingerprint == second.universe_fingerprint
    assert second.run.observations_created == 0
    assert second.run.observations_unchanged == 5


def test_lower_bound_must_be_empty(tmp_path):
    api = IndexApi()
    api.rows[(COMMITTEE, "2023")] = [committee_row("053000", 800, "2023-12-01", 1)]
    repository = migrated_repository(tmp_path)
    with pytest.raises(AssemblyMeetingUniverseError, match="lower bound"):
        enumerator(api, repository).enumerate()
    with repository.sessions() as session:
        assert session.scalars(select(FeederObservationRow)).all() == []


def test_rows_sharing_conf_id_must_agree(tmp_path):
    api = IndexApi()
    api.rows[(COMMITTEE, "2024")][1] = committee_row(
        "053900", 901, "2024-07-01", 2, COMM_NAME="다른위원회"
    )
    with pytest.raises(AssemblyMeetingUniverseError, match="disagree"):
        enumerator(api, migrated_repository(tmp_path)).enumerate()


def test_conf_id_must_not_span_indexes(tmp_path):
    api = IndexApi()
    api.rows[(PLENARY, "2024")].append(plenary_row("053900", 901, "2024-07-01", 9))
    with pytest.raises(AssemblyMeetingUniverseError, match="disagree"):
        enumerator(api, migrated_repository(tmp_path)).enumerate()


def test_minutes_number_must_map_to_one_conf_id(tmp_path):
    api = IndexApi()
    api.rows[(COMMITTEE, "2025")][1] = committee_row("N054011", 960, "2025-04-01", 1)
    with pytest.raises(AssemblyMeetingUniverseError, match="CONFER_NUM"):
        enumerator(api, migrated_repository(tmp_path)).enumerate()


def test_row_outside_requested_year_fails_closed(tmp_path):
    api = IndexApi()
    api.rows[(COMMITTEE, "2025")].append(committee_row("N054099", 999, "2026-01-02", 1))
    with pytest.raises(AssemblyApiError, match="outside the requested year"):
        enumerator(api, migrated_repository(tmp_path)).enumerate()


def test_non_official_pdf_url_fails_closed(tmp_path):
    api = IndexApi()
    api.rows[(COMMITTEE, "2025")][0] = committee_row(
        "N054010", 960, "2025-04-01", 1, PDF_LINK_URL=PDF.format(960) + f"&KEY={SECRET}"
    )
    with pytest.raises(AssemblyApiError, match="exact official PDF"):
        enumerator(api, migrated_repository(tmp_path)).enumerate()


def test_total_change_during_enumeration_fails_closed(tmp_path):
    api = IndexApi()
    api.total_override[(COMMITTEE, "2024", 2)] = 4
    repository = migrated_repository(tmp_path)
    with pytest.raises(AssemblyMeetingUniverseError, match="changed"):
        enumerator(api, repository).enumerate()
    with repository.sessions() as session:
        assert session.scalars(select(FeederObservationRow)).all() == []


def test_incomplete_page_fails_closed(tmp_path):
    api = IndexApi()
    api.total_override[(COMMITTEE, "2025", 1)] = 3
    api.total_override[(COMMITTEE, "2025", 2)] = 3
    with pytest.raises(AssemblyMeetingUniverseError, match="incomplete"):
        enumerator(api, migrated_repository(tmp_path)).enumerate()


def test_future_to_year_and_inverted_range_are_rejected(tmp_path):
    repository = migrated_repository(tmp_path)
    with pytest.raises(ValueError, match="future"):
        enumerator(IndexApi(), repository, to_year=9999)
    with pytest.raises(ValueError, match="from_year"):
        enumerator(IndexApi(), repository, from_year=2025, to_year=2024)


def test_connector_requires_key_and_rejects_embedded_credentials(monkeypatch):
    monkeypatch.delenv("ASSEMBLY_API_KEY", raising=False)
    connector = OpenAssemblyMinutesIndexConnector(index_code=PLENARY, assembly_age=22, year=2025)
    with pytest.raises(MissingAssemblyApiKey):
        connector.fetch(connector.discover()[0])
    with pytest.raises(ValueError, match="credentials"):
        connector.fetch(connector.discover()[0] + "&KEY=x")
    with pytest.raises(ValueError, match="scope"):
        connector.fetch(connector.discover()[0].replace("CONF_DATE=2025", "CONF_DATE=2026"))
    with pytest.raises(ValueError, match="unsupported minutes index"):
        OpenAssemblyMinutesIndexConnector(index_code="VCONFDETAIL", assembly_age=22, year=2025)
