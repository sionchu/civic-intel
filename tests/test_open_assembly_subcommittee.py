from __future__ import annotations

import json

import httpx
import pytest

from packages.connectors.open_assembly import (
    AssemblyApiError,
    MissingAssemblyApiKey,
)
from packages.connectors.open_assembly_bills import national_assembly_bill_policy
from packages.connectors.open_assembly_subcommittee import (
    OpenAssemblySubcommitteeReviewConnector,
)
from packages.domain.enums import SourceCollectionMode
from packages.verification.policy import PolicyDenied
from workers.assembly_subcommittee_review import AssemblySubcommitteeReviewStager

SECRET = "subcommittee-secret-must-not-persist"


def review_row(
    *,
    bill_id: str = "PRC_TEST_1",
    bill_no: str = "2200002",
    age: str = "22",
    present_date: str = "2024-09-04",
    process_date: str = "2024-11-07",
    result: str = "대안반영폐기",
    direct_referral: str = "N",
) -> dict[str, object]:
    return {
        "AGE": age,
        "BILL_NO": bill_no,
        "BILL_ID": bill_id,
        "COMMITTEE_ID": "9700479",
        "COMMITTEE_NAME": "과학기술정보방송통신위원회",
        "SUB_COMMITTEE_NAME": "과학기술원자력법안심사소위원회",
        "PRESENT_SESSION": "418",
        "PRESENT_CHA": "1",
        "PROC_SESSION": "418",
        "PROC_CHA": "2",
        "SUBMIT_DT": "2024-07-16",
        "PRESENT_DT": present_date,
        "PROC_DT": process_date,
        "PROC_RESULT_CD": result,
        "ENROLL_TYPE": direct_referral,
        "CONF_BIGO": "",
        "KEY": SECRET,
    }


def payload(
    rows: list[dict[str, object]],
    *,
    total: int | None = None,
    result_code: str = "INFO-000",
) -> dict[str, object]:
    if total is None:
        total = len(rows)
    return {
        OpenAssemblySubcommitteeReviewConnector.API_CODE: [
            {
                "head": [
                    {"list_total_count": total},
                    {"RESULT": {"CODE": result_code, "MESSAGE": f"provider {SECRET}"}},
                ]
            },
            {"row": rows},
        ]
    }


def test_normal_mode_requires_api_key_before_network(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("ASSEMBLY_API_KEY", raising=False)
    connector = OpenAssemblySubcommitteeReviewConnector(
        assembly_age=22,
        transport=httpx.MockTransport(
            lambda request: pytest.fail(f"unexpected fetch: {request}")
        ),
    )
    with pytest.raises(MissingAssemblyApiKey, match="ASSEMBLY_API_KEY"):
        connector.fetch(connector.discover()[0])


def test_sample_mode_is_explicitly_bounded_and_url_is_credential_free() -> None:
    connector = OpenAssemblySubcommitteeReviewConnector(
        assembly_age=22,
        page_index=1,
        page_size=5,
        sample_mode=True,
    )
    url = httpx.URL(connector.discover()[0])
    assert url.host == connector.HOST
    assert url.path == connector.PATH
    assert url.params["Type"] == "json"
    assert url.params["AGE"] == "22"
    assert url.params["pIndex"] == "1"
    assert url.params["pSize"] == "5"
    assert "KEY" not in url.params

    with pytest.raises(ValueError, match="sample mode"):
        OpenAssemblySubcommitteeReviewConnector(
            assembly_age=22,
            page_index=2,
            page_size=5,
            sample_mode=True,
        )
    with pytest.raises(ValueError, match="sample mode"):
        OpenAssemblySubcommitteeReviewConnector(
            assembly_age=22,
            page_index=1,
            page_size=100,
            sample_mode=True,
        )


def test_filters_are_allowlisted_and_direct_referral_is_strict() -> None:
    connector = OpenAssemblySubcommitteeReviewConnector(
        assembly_age=22,
        api_key=SECRET,
        page_index=2,
        page_size=50,
        bill_no="2206067",
        bill_id="PRC_TEST_1",
        direct_referral="y",
    )
    url = httpx.URL(connector.discover()[0])
    assert url.params["BILL_NO"] == "2206067"
    assert url.params["BILL_ID"] == "PRC_TEST_1"
    assert url.params["ENROLL_TYPE"] == "Y"
    assert SECRET not in str(url)
    assert "KEY" not in url.params

    with pytest.raises(ValueError, match="direct_referral"):
        OpenAssemblySubcommitteeReviewConnector(
            assembly_age=22,
            direct_referral="MAYBE",
        )

    bad_url = (
        f"{connector.BASE_URL}?Type=json&pIndex=1&pSize=5&AGE=22&UNKNOWN=x"
    )
    with pytest.raises(ValueError, match="unsupported"):
        connector.fetch(bad_url)


def test_fetch_sanitizes_provider_payload_and_parses_review_semantics() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["KEY"] == SECRET
        assert request.url.params["AGE"] == "22"
        return httpx.Response(200, json=payload([review_row()]))

    connector = OpenAssemblySubcommitteeReviewConnector(
        assembly_age=22,
        api_key=SECRET,
        transport=httpx.MockTransport(handler),
    )
    document = connector.fetch(connector.discover()[0])
    records = connector.parse_reviews(document)

    assert document.metadata["api_code"] == "TVBPMCONFINFO"
    assert document.metadata["assembly_age"] == "22"
    assert document.metadata["list_total_count"] == "1"
    assert document.metadata["row_count"] == "1"
    assert SECRET not in document.url
    assert SECRET not in document.body
    assert SECRET not in repr(document.metadata)

    parsed = json.loads(document.body)
    safe_row = parsed[connector.API_CODE][1]["row"][0]
    assert set(safe_row) == set(connector.SAFE_FIELDS)
    assert "KEY" not in safe_row

    assert len(records) == 1
    record = records[0]
    assert record.assembly_age == 22
    assert record.bill_no == "2200002"
    assert record.bill_id == "PRC_TEST_1"
    assert record.committee_id == "9700479"
    assert record.subcommittee_name == "과학기술원자력법안심사소위원회"
    assert record.present_session == "418"
    assert record.present_degree == "1"
    assert record.process_session == "418"
    assert record.process_degree == "2"
    assert record.referral_date is not None
    assert record.referral_date.isoformat() == "2024-07-16"
    assert record.present_date is not None
    assert record.present_date.isoformat() == "2024-09-04"
    assert record.process_date is not None
    assert record.process_date.isoformat() == "2024-11-07"
    assert record.process_result == "대안반영폐기"
    assert record.direct_referral is False
    assert record.review_note is None


def test_pending_review_preserves_missing_values_as_none() -> None:
    row = review_row(
        present_date="",
        process_date="",
        result="",
    )
    row["SUB_COMMITTEE_NAME"] = ""
    row["PRESENT_SESSION"] = ""
    row["PRESENT_CHA"] = ""
    row["PROC_SESSION"] = ""
    row["PROC_CHA"] = ""

    connector = OpenAssemblySubcommitteeReviewConnector(
        assembly_age=22,
        api_key=SECRET,
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json=payload([row]))
        ),
    )
    record = connector.parse_reviews(connector.fetch(connector.discover()[0]))[0]

    assert record.subcommittee_name is None
    assert record.present_session is None
    assert record.present_degree is None
    assert record.process_session is None
    assert record.process_degree is None
    assert record.present_date is None
    assert record.process_date is None
    assert record.process_result is None


@pytest.mark.parametrize(
    ("mutator", "message"),
    [
        (lambda row: row.update({"AGE": "21"}), "AGE is inconsistent"),
        (lambda row: row.update({"SUBMIT_DT": "2024/07/16"}), "invalid SUBMIT_DT"),
        (lambda row: row.update({"ENROLL_TYPE": "UNKNOWN"}), "invalid ENROLL_TYPE"),
    ],
)
def test_invalid_row_semantics_fail_closed(mutator, message: str) -> None:
    row = review_row()
    mutator(row)
    connector = OpenAssemblySubcommitteeReviewConnector(
        assembly_age=22,
        api_key=SECRET,
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json=payload([row]))
        ),
    )
    document = connector.fetch(connector.discover()[0])
    with pytest.raises(AssemblyApiError, match=message):
        connector.parse_reviews(document)


def test_info_200_is_a_valid_empty_source_result() -> None:
    connector = OpenAssemblySubcommitteeReviewConnector(
        assembly_age=22,
        api_key=SECRET,
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                json=payload([], total=0, result_code="INFO-200"),
            )
        ),
    )
    document = connector.fetch(connector.discover()[0])
    assert document.metadata["list_total_count"] == "0"
    assert document.metadata["row_count"] == "0"
    assert connector.parse_reviews(document) == ()


def test_provider_error_never_exposes_api_key() -> None:
    connector = OpenAssemblySubcommitteeReviewConnector(
        assembly_age=22,
        api_key=SECRET,
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                json=payload([], total=0, result_code="INFO-300"),
            )
        ),
    )
    with pytest.raises(AssemblyApiError) as exc_info:
        connector.fetch(connector.discover()[0])
    assert "INFO-300" in str(exc_info.value)
    assert SECRET not in str(exc_info.value)


def test_stager_enforces_source_policy_before_network() -> None:
    def forbidden(request: httpx.Request) -> httpx.Response:
        pytest.fail(f"policy denial should happen before network: {request}")

    connector = OpenAssemblySubcommitteeReviewConnector(
        assembly_age=22,
        api_key=SECRET,
        transport=httpx.MockTransport(forbidden),
    )
    blocked = national_assembly_bill_policy().model_copy(
        update={
            "collection_mode": SourceCollectionMode.BLOCKED,
            "can_fetch": False,
        }
    )
    with pytest.raises(PolicyDenied):
        AssemblySubcommitteeReviewStager(connector, blocked).stage()


def test_stager_exposes_no_synthetic_provider_row_key() -> None:
    connector = OpenAssemblySubcommitteeReviewConnector(
        assembly_age=22,
        api_key=SECRET,
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                json=payload([review_row()], total=18324),
            )
        ),
    )
    staged = AssemblySubcommitteeReviewStager(connector).stage()
    output = staged.to_dict()

    assert output["list_total_count"] == 18324
    assert output["sample_mode"] is False
    assert len(output["records"]) == 1
    serialized = json.dumps(output, ensure_ascii=False)
    assert "provider_record_key" not in serialized
    assert SECRET not in serialized
