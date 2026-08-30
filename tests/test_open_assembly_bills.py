import httpx
import pytest

from packages.connectors.open_assembly import AssemblyApiError, MissingAssemblyApiKey
from packages.connectors.open_assembly_bills import (
    OpenAssemblyBillConnector,
    national_assembly_bill_policy,
)
from packages.domain.enums import SourceCollectionMode
from packages.verification.policy import PolicyDenied
from workers.ingest import IngestionPipeline

SECRET = "bill-test-secret"


def bill_payload(*, result_code: str = "INFO-000", rows: list[dict] | None = None) -> dict:
    bill_rows = rows if rows is not None else [
        {
            "BILL_ID": "PRC_TEST_1",
            "BILL_NO": "2200001",
            "BILL_NAME": "테스트법 일부개정법률안",
            "COMMITTEE": "행정안전위원회",
            "PROPOSE_DT": "2026-04-01",
            "PROC_RESULT": "원안가결",
            "AGE": "22",
            "DETAIL_LINK": "http://likms.assembly.go.kr/bill/billDetail.do?billId=PRC_TEST_1",
            "PROPOSER": "홍길동의원 등 10인",
            "RST_PROPOSER": "홍길동",
            "PUBL_PROPOSER": "김공동,박공동",
            "COMMITTEE_ID": "9700001",
            "KEY": SECRET,
        }
    ]
    blocks: list[dict] = [
        {
            "head": [
                {"list_total_count": len(bill_rows)},
                {"RESULT": {"CODE": result_code, "MESSAGE": "정상"}},
            ]
        }
    ]
    if result_code != "INFO-200":
        blocks.append({"row": bill_rows})
    return {OpenAssemblyBillConnector.API_CODE: blocks}


def success_transport(payload: dict | None = None) -> httpx.MockTransport:
    response_payload = payload or bill_payload()

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["KEY"] == SECRET
        assert request.url.host == OpenAssemblyBillConnector.HOST
        return httpx.Response(200, json=response_payload)

    return httpx.MockTransport(handler)


def test_discovery_requires_age_and_keeps_key_out_of_url() -> None:
    connector = OpenAssemblyBillConnector(
        assembly_age=22,
        api_key=SECRET,
        proposer="홍길동",
        committee="행정안전위원회",
        page_size=50,
    )
    url = httpx.URL(connector.discover()[0])
    assert url.params["AGE"] == "22"
    assert url.params["PROPOSER"] == "홍길동"
    assert url.params["COMMITTEE"] == "행정안전위원회"
    assert "KEY" not in url.params
    assert SECRET not in str(url)


def test_missing_key_blocks_fetch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ASSEMBLY_API_KEY", raising=False)
    connector = OpenAssemblyBillConnector(
        assembly_age=22,
        transport=httpx.MockTransport(lambda request: pytest.fail(f"unexpected fetch: {request}")),
    )
    with pytest.raises(MissingAssemblyApiKey):
        connector.fetch(connector.discover()[0])


def test_bill_parser_preserves_documented_roles_and_status() -> None:
    connector = OpenAssemblyBillConnector(
        assembly_age=22,
        api_key=SECRET,
        transport=success_transport(),
    )
    document = connector.fetch(connector.discover()[0])
    bills = connector.parse_bills(document)

    assert SECRET not in document.body
    assert SECRET not in document.url
    assert document.metadata["list_total_count"] == "1"
    assert len(bills) == 1
    bill = bills[0]
    assert bill.bill_id == "PRC_TEST_1"
    assert bill.bill_name == "테스트법 일부개정법률안"
    assert bill.proposed_date is not None
    assert bill.proposed_date.isoformat() == "2026-04-01"
    assert bill.process_result == "원안가결"
    assert bill.representative_proposers == ("홍길동",)
    assert bill.co_proposers == ("김공동", "박공동")
    assert bill.role_for("홍길동") == "LEAD"
    assert bill.role_for("김공동") == "CO_SPONSOR"
    assert bill.role_for("없는사람") is None


def test_no_records_is_empty_result_not_false_error() -> None:
    connector = OpenAssemblyBillConnector(
        assembly_age=22,
        api_key=SECRET,
        transport=success_transport(bill_payload(result_code="INFO-200", rows=[])),
    )
    document = connector.fetch(connector.discover()[0])
    assert document.metadata["result_code"] == "INFO-200"
    assert document.metadata["list_total_count"] == "0"
    assert connector.parse_bills(document) == []


def test_provider_error_does_not_leak_key() -> None:
    connector = OpenAssemblyBillConnector(
        assembly_age=22,
        api_key=SECRET,
        transport=success_transport(bill_payload(result_code="ERROR-999")),
    )
    with pytest.raises(AssemblyApiError) as exc_info:
        connector.fetch(connector.discover()[0])
    assert SECRET not in str(exc_info.value)


def test_bill_policy_blocks_before_fetch_and_does_not_store_raw_body() -> None:
    connector = OpenAssemblyBillConnector(
        assembly_age=22,
        api_key=SECRET,
        transport=success_transport(),
    )
    blocked = national_assembly_bill_policy().model_copy(
        update={"collection_mode": SourceCollectionMode.BLOCKED, "can_fetch": False}
    )
    with pytest.raises(PolicyDenied):
        IngestionPipeline(connector).ingest(connector.discover()[0], blocked)

    policy = national_assembly_bill_policy()
    result = IngestionPipeline(connector).ingest(connector.discover()[0], policy)
    assert result.snapshot.fulltext is None
    assert policy.can_commercialize
    assert not policy.can_send_to_ai
