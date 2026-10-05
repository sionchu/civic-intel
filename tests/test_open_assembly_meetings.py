from __future__ import annotations

import json

import httpx
import pytest

from packages.connectors.open_assembly import (
    AssemblyApiError,
    MissingAssemblyApiKey,
)
from packages.connectors.open_assembly_bills import national_assembly_bill_policy
from packages.connectors.open_assembly_meetings import (
    OpenAssemblyMeetingAgendaConnector,
    OpenAssemblyMeetingBillConnector,
    OpenAssemblyMeetingDetailConnector,
)
from packages.domain.enums import SourceCollectionMode
from packages.verification.policy import PolicyDenied
from workers.assembly_meeting_graph import (
    AssemblyMeetingGraphError,
    AssemblyMeetingGraphStager,
)

SECRET = "meeting-secret-must-not-persist"
MEETING_ID = "053084"


def envelope(api_code: str, rows: list[dict], *, total: int | None = None, code="INFO-000"):
    if total is None:
        total = len(rows)
    return {
        api_code: [
            {
                "head": [
                    {"list_total_count": total},
                    {"RESULT": {"CODE": code, "MESSAGE": f"provider {SECRET}"}},
                ]
            },
            {"row": rows},
        ]
    }


def detail_row(*, meeting_id: str = MEETING_ID) -> dict[str, object]:
    return {
        "CONF_ID": meeting_id,
        "ERACO": "제21대",
        "SESS": "제408회",
        "DGR": "제2차",
        "CONF_DT": "2023-07-27",
        "CONF_KND": "국회본회의 회의록",
        "CMIT_NM": "국회본회의",
        "SB_CMIT_NM": None,
        "CONF_PLC": "본회의장",
        "BG_PTM": "14:06",
        "ED_PTM": "16:28",
        "CONF_PTM": "02:22",
        "HR_HRG_YN": "N",
        "PBHRG_YN": "N",
        "HRG_YN": "N",
        "SITG_YN": "N",
        "RMND_SPH_YN": "N",
        "RDJM_SPH_YN": "N",
        "FRNGUS_SPH_YN": "N",
        "DOWN_URL": (
            "https://record.assembly.go.kr/assembly/viewer/minutes/download/pdf.do"
            f"?id=47517&KEY={SECRET}"
        ),
        "KEY": SECRET,
    }


def agenda_row(
    agenda_no: int,
    *,
    meeting_id: str = MEETING_ID,
    session: str = "제408회",
) -> dict[str, object]:
    return {
        "CONF_ID": meeting_id,
        "ERACO": "제21대",
        "SESS": session,
        "DGR": "제2차",
        "BLL_NO": agenda_no,
        "BLL_NM": f"{agenda_no}. 테스트 안건 (의안번호 212300{agenda_no})",
        "BLL_LV": 1,
        "KEY": SECRET,
    }


def bill_row(
    bill_id: str,
    *,
    meeting_id: str = MEETING_ID,
    session: str = "제408회",
) -> dict[str, object]:
    return {
        "CONF_ID": meeting_id,
        "ERACO": "제21대",
        "SESS": session,
        "DGR": "제2차",
        "BILL_ID": bill_id,
        "BILL_NM": "1. 테스트 의안",
        "LINK_URL": (
            f"https://likms.assembly.go.kr/bill/billDetail.do?billId={bill_id}"
            f"&authKey={SECRET}"
        ),
        "KEY": SECRET,
    }


class MeetingApi:
    def __init__(self) -> None:
        self.calls: list[str] = []
        self.detail = detail_row()
        self.agendas = [agenda_row(1), agenda_row(2)]
        self.bills = [bill_row("PRC_TEST_1")]

    def handle(self, request: httpx.Request) -> httpx.Response:
        assert request.url.params["KEY"] == SECRET
        assert request.url.params["CONF_ID"] == MEETING_ID
        path = request.url.path
        self.calls.append(path)
        if path.endswith(OpenAssemblyMeetingDetailConnector.API_CODE):
            return httpx.Response(
                200,
                json=envelope(
                    OpenAssemblyMeetingDetailConnector.API_CODE,
                    [self.detail],
                    total=1,
                ),
            )
        if path.endswith(OpenAssemblyMeetingAgendaConnector.API_CODE):
            return httpx.Response(
                200,
                json=envelope(
                    OpenAssemblyMeetingAgendaConnector.API_CODE,
                    self.agendas,
                    total=len(self.agendas),
                ),
            )
        if path.endswith(OpenAssemblyMeetingBillConnector.API_CODE):
            return httpx.Response(
                200,
                json=envelope(
                    OpenAssemblyMeetingBillConnector.API_CODE,
                    self.bills,
                    total=len(self.bills),
                ),
            )
        raise AssertionError(path)

    @property
    def transport(self) -> httpx.MockTransport:
        return httpx.MockTransport(self.handle)

    def connectors(self):
        transport = self.transport
        return (
            OpenAssemblyMeetingDetailConnector(
                meeting_id=MEETING_ID, api_key=SECRET, transport=transport
            ),
            OpenAssemblyMeetingAgendaConnector(
                meeting_id=MEETING_ID, api_key=SECRET, transport=transport
            ),
            OpenAssemblyMeetingBillConnector(
                meeting_id=MEETING_ID, api_key=SECRET, transport=transport
            ),
        )


@pytest.mark.parametrize(
    "connector_cls",
    [
        OpenAssemblyMeetingDetailConnector,
        OpenAssemblyMeetingAgendaConnector,
        OpenAssemblyMeetingBillConnector,
    ],
)
def test_normal_mode_requires_api_key_before_network(
    connector_cls,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("ASSEMBLY_API_KEY", raising=False)
    connector = connector_cls(
        meeting_id=MEETING_ID,
        transport=httpx.MockTransport(
            lambda request: pytest.fail(f"unexpected fetch: {request}")
        ),
    )
    with pytest.raises(MissingAssemblyApiKey, match="ASSEMBLY_API_KEY"):
        connector.fetch(connector.discover()[0])


@pytest.mark.parametrize(
    "connector_cls",
    [
        OpenAssemblyMeetingDetailConnector,
        OpenAssemblyMeetingAgendaConnector,
        OpenAssemblyMeetingBillConnector,
    ],
)
def test_sample_mode_is_bounded_and_urls_are_credential_free(connector_cls) -> None:
    connector = connector_cls(
        meeting_id=MEETING_ID,
        page_index=1,
        page_size=5,
        sample_mode=True,
    )
    url = httpx.URL(connector.discover()[0])
    assert url.params["CONF_ID"] == MEETING_ID
    assert url.params["Type"] == "json"
    assert url.params["pIndex"] == "1"
    assert url.params["pSize"] == "5"
    assert "KEY" not in url.params

    with pytest.raises(ValueError, match="sample mode"):
        connector_cls(
            meeting_id=MEETING_ID,
            page_index=2,
            page_size=5,
            sample_mode=True,
        )


def test_detail_parses_documented_fields_and_sanitizes_download_url() -> None:
    api = MeetingApi()
    detail, _, _ = api.connectors()
    document = detail.fetch(detail.discover()[0])
    record = detail.parse_detail(document)

    assert record.meeting_id == MEETING_ID
    assert record.meeting_date.isoformat() == "2023-07-27"
    assert record.committee_name == "국회본회의"
    assert record.start_time == "14:06"
    assert record.end_time == "16:28"
    assert record.duration == "02:22"
    assert record.personnel_hearing is False
    assert record.public_hearing is False
    assert record.joint_meeting is False
    assert record.minutes_download_url is not None
    assert "id=47517" in record.minutes_download_url
    assert SECRET not in record.minutes_download_url
    assert SECRET not in document.body
    assert "KEY=" not in document.body


def test_agenda_keeps_agenda_number_separate_from_bill_identity() -> None:
    api = MeetingApi()
    _, agenda, _ = api.connectors()
    document = agenda.fetch(agenda.discover()[0])
    records = agenda.parse_agendas(document)

    assert len(records) == 2
    assert records[0].meeting_id == MEETING_ID
    assert records[0].agenda_no == 1
    assert records[0].agenda_level == 1
    assert "의안번호 2123001" in records[0].agenda_name
    assert not hasattr(records[0], "bill_id")
    assert SECRET not in document.body


def test_bill_rows_expose_exact_bill_id_and_sanitized_link() -> None:
    api = MeetingApi()
    _, _, bills = api.connectors()
    document = bills.fetch(bills.discover()[0])
    records = bills.parse_bills(document)

    assert len(records) == 1
    assert records[0].meeting_id == MEETING_ID
    assert records[0].bill_id == "PRC_TEST_1"
    assert records[0].link_url is not None
    assert "billId=PRC_TEST_1" in records[0].link_url
    assert SECRET not in records[0].link_url
    assert SECRET not in document.body


def test_bill_connector_allows_optional_bill_filter_without_url_credentials() -> None:
    connector = OpenAssemblyMeetingBillConnector(
        meeting_id=MEETING_ID,
        bill_id="PRC_TEST_1",
        api_key=SECRET,
    )
    url = httpx.URL(connector.discover()[0])
    assert url.params["CONF_ID"] == MEETING_ID
    assert url.params["BILL_ID"] == "PRC_TEST_1"
    assert SECRET not in str(url)
    assert "KEY" not in url.params


def test_graph_stages_only_exact_meeting_edges_and_keeps_lists_separate() -> None:
    api = MeetingApi()
    graph = AssemblyMeetingGraphStager(*api.connectors()).stage()
    output = graph.to_dict()

    assert graph.meeting.meeting_id == MEETING_ID
    assert len(graph.agendas) == 2
    assert len(graph.bills) == 1
    assert graph.detail_total == 1
    assert graph.agenda_total == 2
    assert graph.bill_total == 1
    assert output["exact_edges"] == {
        "meeting_to_agendas": 2,
        "meeting_to_bills": 1,
        "agenda_to_bill": 0,
    }
    serialized = json.dumps(output, ensure_ascii=False)
    assert "provider_record_key" not in serialized
    assert SECRET not in serialized


def test_graph_rejects_filtered_bill_list() -> None:
    api = MeetingApi()
    detail, agenda, _ = api.connectors()
    filtered = OpenAssemblyMeetingBillConnector(
        meeting_id=MEETING_ID,
        bill_id="PRC_TEST_1",
        api_key=SECRET,
        transport=api.transport,
    )
    with pytest.raises(AssemblyMeetingGraphError, match="must not filter BILL_ID"):
        AssemblyMeetingGraphStager(detail, agenda, filtered).stage()


def test_graph_fails_closed_on_cross_source_context_drift() -> None:
    api = MeetingApi()
    api.agendas = [agenda_row(1, session="제999회")]
    with pytest.raises(AssemblyMeetingGraphError, match="agenda row"):
        AssemblyMeetingGraphStager(*api.connectors()).stage()


def test_detail_requires_exactly_one_source_row() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=envelope(
                OpenAssemblyMeetingDetailConnector.API_CODE,
                [detail_row(), detail_row()],
                total=2,
            ),
        )

    connector = OpenAssemblyMeetingDetailConnector(
        meeting_id=MEETING_ID,
        api_key=SECRET,
        transport=httpx.MockTransport(handler),
    )
    document = connector.fetch(connector.discover()[0])
    with pytest.raises(AssemblyApiError, match="exactly one"):
        connector.parse_detail(document)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("CONF_DT", "2023/07/27", "invalid date"),
        ("HR_HRG_YN", "MAYBE", "invalid Y/N"),
    ],
)
def test_detail_invalid_semantics_fail_closed(field: str, value: str, message: str) -> None:
    row = detail_row()
    row[field] = value
    connector = OpenAssemblyMeetingDetailConnector(
        meeting_id=MEETING_ID,
        api_key=SECRET,
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                json=envelope(
                    OpenAssemblyMeetingDetailConnector.API_CODE,
                    [row],
                    total=1,
                ),
            )
        ),
    )
    document = connector.fetch(connector.discover()[0])
    with pytest.raises(AssemblyApiError, match=message):
        connector.parse_detail(document)


def test_provider_error_does_not_leak_key() -> None:
    connector = OpenAssemblyMeetingAgendaConnector(
        meeting_id=MEETING_ID,
        api_key=SECRET,
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                json=envelope(
                    OpenAssemblyMeetingAgendaConnector.API_CODE,
                    [],
                    total=0,
                    code="INFO-300",
                ),
            )
        ),
    )
    with pytest.raises(AssemblyApiError) as exc_info:
        connector.fetch(connector.discover()[0])
    assert "INFO-300" in str(exc_info.value)
    assert SECRET not in str(exc_info.value)


def test_policy_denial_happens_before_network() -> None:
    def forbidden(request: httpx.Request) -> httpx.Response:
        pytest.fail(f"policy denial should happen before network: {request}")

    transport = httpx.MockTransport(forbidden)
    connectors = (
        OpenAssemblyMeetingDetailConnector(
            meeting_id=MEETING_ID, api_key=SECRET, transport=transport
        ),
        OpenAssemblyMeetingAgendaConnector(
            meeting_id=MEETING_ID, api_key=SECRET, transport=transport
        ),
        OpenAssemblyMeetingBillConnector(
            meeting_id=MEETING_ID, api_key=SECRET, transport=transport
        ),
    )
    blocked = national_assembly_bill_policy().model_copy(
        update={
            "collection_mode": SourceCollectionMode.BLOCKED,
            "can_fetch": False,
        }
    )
    with pytest.raises(PolicyDenied):
        AssemblyMeetingGraphStager(*connectors, policy=blocked).stage()
