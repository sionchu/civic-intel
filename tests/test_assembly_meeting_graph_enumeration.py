from __future__ import annotations

from pathlib import Path

import httpx
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import select

from packages.connectors.open_assembly_meetings import OpenAssemblyMinutesIndexConnector
from packages.domain.db import ClaimRow, FeederObservationRow, PersonRow, SourceSnapshotRow
from packages.domain.enums import SourceRunStatus
from packages.persistence import SqlAlchemyRepository
from workers.assembly_meeting_graph_enumeration import (
    AssemblyMeetingGraphCoverageError,
    AssemblyMeetingGraphEnumerator,
    reconcile_meeting_bills,
)
from workers.assembly_meeting_universe import AssemblyMeetingUniverseEnumerator

SECRET = "meeting-graph-secret-must-not-persist"
COMMITTEE = OpenAssemblyMinutesIndexConnector.COMMITTEE
PLENARY = OpenAssemblyMinutesIndexConnector.PLENARY
PDF = "https://record.assembly.go.kr/assembly/viewer/minutes/download/pdf.do?id={}"

# Shapes mirror keyed responses captured on 2026-10-05. Observed provider quirks reproduced here:
# repeated identical VCONFBILLLIST rows, and one BILL_ID listed with two different bill names.


def index_row(conf_id: str, number: int, day: str, plenary: bool) -> dict:
    row = {
        "CONFER_NUM": str(number),
        "TITLE": f"테스트 회의 ({day})",
        "CLASS_NAME": "국회본회의" if plenary else "상임위원회",
        "DAE_NUM": "22",
        "CONF_DATE": day,
        "SUB_NAME": "1. 안건",
        "PDF_LINK_URL": PDF.format(number),
        "CONF_ID": conf_id,
    }
    if not plenary:
        row.update({"COMM_NAME": "행정안전위원회", "DEPT_CD": "9700480"})
    return row


def detail_row(conf_id: str, day: str, **overrides) -> dict:
    row = {
        "CONF_ID": conf_id,
        "ERACO": "제22대",
        "SESS": "제439회",
        "DGR": "제3차",
        "CONF_DT": day,
        "CONF_KND": "상임위원회 회의록",
        "CMIT_NM": "행정안전위원회",
        "SB_CMIT_NM": None,
        "CONF_PLC": None,
        "BG_PTM": "10:00",
        "ED_PTM": "12:00",
        "CONF_PTM": None,
        "HR_HRG_YN": "N",
        "PBHRG_YN": "N",
        "HRG_YN": "N",
        "SITG_YN": "N",
        "RMND_SPH_YN": "N",
        "RDJM_SPH_YN": "N",
        "FRNGUS_SPH_YN": "N",
        "DOWN_URL": PDF.format(1) + f"&KEY={SECRET}",
    }
    row.update(overrides)
    return row


def agenda(conf_id: str, number: int, **overrides) -> dict:
    row = {
        "CONF_ID": conf_id,
        "ERACO": "제22대",
        "SESS": "제439회",
        "DGR": "제3차",
        "BLL_NO": number,
        "BLL_NM": f"{number}. 안건",
        "BLL_LV": 1,
    }
    row.update(overrides)
    return row


def bill(conf_id: str, bill_id: str, name: str) -> dict:
    return {
        "CONF_ID": conf_id,
        "ERACO": "제22대",
        "SESS": "제439회",
        "DGR": "제3차",
        "BILL_ID": bill_id,
        "BILL_NM": name,
        "LINK_URL": f"https://likms.assembly.go.kr/bill/billDetail.do?billId={bill_id}",
    }


def envelope(code: str, rows: list[dict], total: int | None = None) -> dict:
    count = len(rows) if total is None else total
    if count == 0:
        return {"RESULT": {"CODE": "INFO-200", "MESSAGE": "해당하는 데이터가 없습니다."}}
    return {
        code: [
            {"head": [{"list_total_count": count}, {"RESULT": {"CODE": "INFO-000"}}]},
            {"row": rows},
        ]
    }


class Api:
    def __init__(self) -> None:
        self.index = {
            (PLENARY, "2025"): [index_row("N1", 10, "2025-03-04", True)],
            (COMMITTEE, "2025"): [
                index_row("N2", 11, "2025-04-01", False),
                index_row("N3", 12, "2025-04-02", False),
            ],
        }
        self.detail = {
            "N1": [detail_row("N1", "2025-03-04", CMIT_NM="국회본회의")],
            "N2": [detail_row("N2", "2025-04-01")],
            "N3": [detail_row("N3", "2025-04-02")],
        }
        self.agendas = {
            "N1": [agenda("N1", 1), agenda("N1", 2)],
            "N2": [agenda("N2", 1)],
            "N3": [agenda("N3", 1)],
        }
        self.bills = {
            "N1": [
                bill("N1", "PRC_A", "1. A법안"),
                bill("N1", "PRC_A", "1. A법안"),
                bill("N1", "PRC_B", "2. B법안"),
            ],
            "N2": [
                bill("N2", "PRC_C", "1. 조세특례제한법(갑 의원)"),
                bill("N2", "PRC_C", "2. 조세특례제한법(을 의원)"),
                bill("N2", "PRC_D", "3. D법안"),
            ],
            "N3": [],
        }
        self.calls: list[tuple[str, str]] = []

    def handle(self, request: httpx.Request) -> httpx.Response:
        assert request.url.params["KEY"] == SECRET
        code = request.url.path.rsplit("/", 1)[-1]
        page = int(request.url.params["pIndex"])
        size = int(request.url.params["pSize"])
        if code in (PLENARY, COMMITTEE):
            rows = self.index.get((code, request.url.params["CONF_DATE"]), [])
        else:
            conf_id = request.url.params["CONF_ID"]
            self.calls.append((code, conf_id))
            source = {"VCONFDETAIL": self.detail, "VCONFBLLLIST": self.agendas,
                      "VCONFBILLLIST": self.bills}[code]
            rows = source.get(conf_id, [])
        chunk = rows[(page - 1) * size : page * size]
        return httpx.Response(200, json=envelope(code, chunk, len(rows)))


def repository(tmp_path: Path) -> SqlAlchemyRepository:
    url = f"sqlite:///{(tmp_path / 'graph.db').as_posix()}"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", url)
    command.upgrade(config, "head")
    return SqlAlchemyRepository(url)


def enumerator(api: Api, repo: SqlAlchemyRepository, *, page_size: int = 1000, **kwargs):
    transport = httpx.MockTransport(api.handle)
    universe = AssemblyMeetingUniverseEnumerator(
        OpenAssemblyMinutesIndexConnector(
            index_code=COMMITTEE, assembly_age=22, year=2025, api_key=SECRET, transport=transport
        ),
        repo,
        from_year=2025,
        to_year=2025,
    )
    return AssemblyMeetingGraphEnumerator(
        universe, repo, api_key=SECRET, page_size=page_size, transport=transport, **kwargs
    )


def observations(repo: SqlAlchemyRepository) -> dict[str, dict]:
    with repo.sessions() as session:
        rows = session.scalars(select(FeederObservationRow)).all()
    return {row.provider_record_key: row.normalized_json for row in rows}


def test_reconcile_collapses_identical_rows_and_flags_conflicts():
    from packages.connectors.open_assembly_meetings import AssemblyMeetingBillRecord

    def rec(bill_id: str, name: str) -> AssemblyMeetingBillRecord:
        return AssemblyMeetingBillRecord("N", "제22대", "제1회", "제1차", bill_id, name, None)

    result = reconcile_meeting_bills(
        (rec("A", "x"), rec("A", "x"), rec("B", "y"), rec("B", "z"), rec("C", "w"))
    )
    assert result["bill_row_total"] == 5
    assert result["duplicate_bill_rows"] == 1
    assert result["bill_id_conflicts"] == ["B"]
    assert result["exact_bill_ids"] == ["A", "C"]
    assert [entry["provider_row_count"] for entry in result["bills"]] == [2, 1, 1, 1]


def test_full_graph_enumeration(tmp_path):
    api = Api()
    repo = repository(tmp_path)
    result = enumerator(api, repo, page_size=1).enumerate()

    assert result.run.status is SourceRunStatus.SUCCESS
    assert result.complete and result.meetings_committed_total == 3
    assert result.bill_conflict_meetings == {"N2": ["PRC_C"]}
    graph = observations(repo)
    assert sorted(graph) == ["N1", "N2", "N3"]
    n1 = graph["N1"]
    assert n1["agenda_total"] == 2 and [a["agenda_no"] for a in n1["agendas"]] == [1, 2]
    assert n1["bill_row_total"] == 3 and n1["duplicate_bill_rows"] == 1
    assert n1["exact_bill_ids"] == ["PRC_A", "PRC_B"]
    assert n1["agenda_to_bill_edges"] == 0
    assert n1["minutes_index"] == "plenary" and n1["minutes_number"] == 10
    assert n1["minutes_download_url"] == PDF.format(1)
    assert graph["N2"]["exact_bill_ids"] == ["PRC_D"]
    assert graph["N2"]["bill_id_conflicts"] == ["PRC_C"]
    assert graph["N3"]["bills"] == [] and graph["N3"]["bill_row_total"] == 0
    with repo.sessions() as session:
        assert session.scalars(select(PersonRow)).all() == []
        assert session.scalars(select(ClaimRow)).all() == []
        snapshots = session.scalars(select(SourceSnapshotRow)).all()
    assert SECRET not in str(graph)
    assert SECRET not in " ".join(str(vars(item)) for item in snapshots)


def test_rerun_is_idempotent(tmp_path):
    api = Api()
    repo = repository(tmp_path)
    enumerator(api, repo).enumerate()
    second = enumerator(api, repo).enumerate()
    assert second.run.observations_created == 0
    assert second.run.observations_unchanged == 3


def test_budget_then_resume(tmp_path):
    api = Api()
    repo = repository(tmp_path)
    first = enumerator(api, repo, max_meetings=1).enumerate()
    assert first.run.status is SourceRunStatus.PARTIAL and first.meetings_committed_total == 1
    api.calls.clear()
    second = enumerator(api, repo).enumerate(resume=True)
    assert second.complete and second.meetings_committed_this_run == 2
    assert {conf_id for _, conf_id in api.calls} == {"N2", "N3"}
    assert sorted(observations(repo)) == ["N1", "N2", "N3"]
    assert second.bill_conflict_meetings == {"N2": ["PRC_C"]}


def test_resume_refuses_changed_universe(tmp_path):
    api = Api()
    repo = repository(tmp_path)
    enumerator(api, repo, max_meetings=1).enumerate()
    api.index[(COMMITTEE, "2025")].append(index_row("N4", 13, "2025-05-01", False))
    with pytest.raises(AssemblyMeetingGraphCoverageError, match="universe changed"):
        enumerator(api, repo).enumerate(resume=True)


def test_detail_date_must_match_index(tmp_path):
    api = Api()
    api.detail["N2"] = [detail_row("N2", "2025-04-09")]
    with pytest.raises(AssemblyMeetingGraphCoverageError, match="date"):
        enumerator(api, repository(tmp_path)).enumerate()


def test_row_context_must_match_detail(tmp_path):
    api = Api()
    api.agendas["N3"] = [agenda("N3", 1, SESS="제440회")]
    with pytest.raises(AssemblyMeetingGraphCoverageError, match="context"):
        enumerator(api, repository(tmp_path)).enumerate()


def test_missing_detail_fails_closed(tmp_path):
    api = Api()
    api.detail["N3"] = []
    repo = repository(tmp_path)
    with pytest.raises(AssemblyMeetingGraphCoverageError, match="at least one"):
        enumerator(api, repo).enumerate()
    # Meetings before the failure stay committed and resumable.
    assert sorted(observations(repo)) == ["N1", "N2"]


def test_multi_row_detail_merges_only_meeting_type_flags(tmp_path):
    api = Api()
    api.detail["N3"] = [
        detail_row("N3", "2025-04-02", HRG_YN="Y", PBHRG_YN="N"),
        detail_row("N3", "2025-04-02", HRG_YN="N", PBHRG_YN="Y"),
    ]
    repo = repository(tmp_path)
    enumerator(api, repo).enumerate()
    n3 = observations(repo)["N3"]
    assert n3["hearing"] is True and n3["public_hearing"] is True
    assert n3["detail_row_count"] == 2
    assert [row["hearing"] for row in n3["detail_row_flag_sets"]] == [True, False]
    assert observations(repo)["N1"]["detail_row_count"] == 1


def test_multi_row_detail_with_other_differences_fails_closed(tmp_path):
    api = Api()
    api.detail["N3"] = [
        detail_row("N3", "2025-04-02"),
        detail_row("N3", "2025-04-02", CMIT_NM="다른위원회"),
    ]
    with pytest.raises(AssemblyMeetingGraphCoverageError, match="beyond the meeting-type flags"):
        enumerator(api, repository(tmp_path)).enumerate()
