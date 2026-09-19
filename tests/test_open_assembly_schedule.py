from datetime import date

import httpx
import pytest

from packages.connectors.open_assembly import AssemblyApiError, MissingAssemblyApiKey
from packages.connectors.open_assembly_schedule import (
    OpenAssemblyScheduleConnector,
    national_assembly_schedule_policy,
)
from packages.domain.enums import SourceCollectionMode
from packages.verification.policy import PolicyDenied
from workers.ingest import IngestionPipeline

SECRET = "schedule-test-secret"


def schedule_payload(
    *,
    result_code: str = "INFO-000",
    rows: list[dict] | None = None,
) -> dict:
    schedule_rows = rows if rows is not None else [
        {
            "SCH_KIND": "위원회",
            "SCH_DT": "20261006",
            "SCH_TM": "10:00",
            "CMIT_NM": "과학기술정보방송통신위원회",
            "SCH_CN": "2026년도 국정감사",
            "EV_PLC": "국회",
            "CONF_SESS": "439",
            "CONF_DGR": "1",
            "KEY": SECRET,
        },
        {
            "SCH_KIND": "위원회",
            "SCH_DT": "20261007",
            "SCH_TM": "14:00",
            "CMIT_NM": "과학기술정보방송통신위원회",
            "SCH_CN": "법률안 상정 및 의결",
            "EV_PLC": "국회",
            "CONF_SESS": "439",
            "CONF_DGR": "2",
        },
    ]
    blocks: list[dict] = [
        {
            "head": [
                {"list_total_count": len(schedule_rows)},
                {"RESULT": {"CODE": result_code, "MESSAGE": "정상"}},
            ]
        }
    ]
    if result_code != "DATA-000":
        blocks.append({"row": schedule_rows})
    return {OpenAssemblyScheduleConnector.API_CODE: blocks}


def success_transport(payload: dict | None = None) -> httpx.MockTransport:
    response_payload = payload or schedule_payload()

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["KEY"] == SECRET
        assert request.url.host == OpenAssemblyScheduleConnector.HOST
        return httpx.Response(200, json=response_payload)

    return httpx.MockTransport(handler)


def test_schedule_discovery_is_bounded_and_keeps_key_out_of_url() -> None:
    connector = OpenAssemblyScheduleConnector(
        api_key=SECRET,
        page_index=2,
        page_size=50,
        schedule_date=date(2026, 10, 6),
        committee="과학기술정보방송통신위원회",
    )

    url = httpx.URL(connector.discover()[0])

    assert url.params["Type"] == "json"
    assert url.params["pIndex"] == "2"
    assert url.params["pSize"] == "50"
    assert url.params["SCH_DT"] == "20261006"
    assert url.params["CMIT_NM"] == "과학기술정보방송통신위원회"
    assert "KEY" not in url.params
    assert SECRET not in str(url)


def test_missing_key_blocks_live_fetch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ASSEMBLY_API_KEY", raising=False)
    connector = OpenAssemblyScheduleConnector(
        transport=httpx.MockTransport(
            lambda request: pytest.fail(f"unexpected fetch: {request}")
        )
    )

    with pytest.raises(MissingAssemblyApiKey):
        connector.fetch(connector.discover()[0])


def test_schedule_parser_exposes_governance_fields_and_gukgam_candidates() -> None:
    connector = OpenAssemblyScheduleConnector(
        api_key=SECRET,
        transport=success_transport(),
    )
    document = connector.fetch(connector.discover()[0])
    records = connector.parse_schedules(document)
    candidates = connector.gukgam_candidates(records)

    assert document.publisher == "국회 국회사무처"
    assert document.metadata["source_contract"] == "national_assembly_schedule_v1"
    assert document.metadata["list_total_count"] == "2"
    assert SECRET not in document.url
    assert SECRET not in document.body
    assert SECRET not in repr(document.metadata)

    assert len(records) == 2
    assert records[0].schedule_date.isoformat() == "2026-10-06"
    assert records[0].committee_name == "과학기술정보방송통신위원회"
    assert records[0].content == "2026년도 국정감사"
    assert records[0].place == "국회"
    assert records[0].session == "439"
    assert records[0].degree == "1"
    assert len(candidates) == 1
    assert candidates[0] == records[0]
    assert not hasattr(records[0], "witnesses")
    assert not hasattr(records[0], "audited_organizations")


def test_schedule_data_000_is_an_empty_result() -> None:
    connector = OpenAssemblyScheduleConnector(
        api_key=SECRET,
        transport=success_transport(
            schedule_payload(result_code="DATA-000", rows=[])
        ),
    )

    document = connector.fetch(connector.discover()[0])

    assert document.metadata["result_code"] == "DATA-000"
    assert document.metadata["list_total_count"] == "0"
    assert connector.parse_schedules(document) == []


def test_schedule_info_200_is_not_treated_as_no_data() -> None:
    connector = OpenAssemblyScheduleConnector(
        api_key=SECRET,
        transport=success_transport(
            schedule_payload(result_code="INFO-200", rows=[])
        ),
    )

    with pytest.raises(AssemblyApiError, match="INFO-200"):
        connector.fetch(connector.discover()[0])


def test_schedule_top_level_provider_error_preserves_code() -> None:
    payload = {
        "RESULT": {
            "CODE": "ERROR-290",
            "MESSAGE": "인증키가 유효하지 않습니다.",
        }
    }
    connector = OpenAssemblyScheduleConnector(
        api_key=SECRET,
        transport=success_transport(payload),
    )

    with pytest.raises(AssemblyApiError, match="ERROR-290") as exc_info:
        connector.fetch(connector.discover()[0])

    assert SECRET not in str(exc_info.value)


def test_schedule_provider_error_does_not_leak_key() -> None:
    connector = OpenAssemblyScheduleConnector(
        api_key=SECRET,
        transport=success_transport(schedule_payload(result_code="ERROR-999")),
    )

    with pytest.raises(AssemblyApiError) as exc_info:
        connector.fetch(connector.discover()[0])

    assert SECRET not in str(exc_info.value)


def test_schedule_parser_fails_closed_on_invalid_date() -> None:
    payload = schedule_payload()
    payload[OpenAssemblyScheduleConnector.API_CODE][1]["row"][0]["SCH_DT"] = (
        "2026-13-40"
    )
    connector = OpenAssemblyScheduleConnector(
        api_key=SECRET,
        transport=success_transport(payload),
    )

    document = connector.fetch(connector.discover()[0])

    with pytest.raises(AssemblyApiError, match="invalid SCH_DT"):
        connector.parse_schedules(document)


def test_schedule_policy_is_metadata_only_and_blocks_before_fetch() -> None:
    connector = OpenAssemblyScheduleConnector(
        api_key=SECRET,
        transport=success_transport(),
    )
    policy = national_assembly_schedule_policy()
    blocked = policy.model_copy(
        update={
            "collection_mode": SourceCollectionMode.BLOCKED,
            "can_fetch": False,
        }
    )

    with pytest.raises(PolicyDenied):
        IngestionPipeline(connector).ingest(connector.discover()[0], blocked)

    result = IngestionPipeline(connector).ingest(connector.discover()[0], policy)
    assert result.snapshot.fulltext is None
    assert policy.can_fetch
    assert policy.can_store_metadata
    assert not policy.can_store_fulltext
    assert not policy.can_send_to_ai
    assert not policy.can_show_excerpt
    assert policy.can_commercialize
    assert policy.license == "이용허락범위 제한 없음"
