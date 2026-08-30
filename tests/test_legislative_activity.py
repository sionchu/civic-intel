import json

import httpx
import pytest

from packages.connectors.open_assembly_bills import (
    OpenAssemblyBillConnector,
    national_assembly_bill_policy,
)
from packages.domain.enums import SourceCollectionMode
from packages.verification.identity import IdentityCandidate
from packages.verification.policy import PolicyDenied
from workers.legislative_activity import LegislativeActivityStager, render_legislative_json

SECRET = "legislative-stage-secret"


def identity(name: str = "홍길동", member_code: str = "M001") -> IdentityCandidate:
    return IdentityCandidate(
        canonical_name=name,
        office="국회의원",
        organization="테스트정당",
        career_anchors=(f"assembly_member_code:{member_code}", "district:서울 테스트구"),
    )


def bill_rows() -> list[dict]:
    return [
        {
            "BILL_ID": "B1",
            "BILL_NO": "2200001",
            "BILL_NAME": "첫 번째 법률안",
            "COMMITTEE": "법제사법위원회",
            "PROPOSE_DT": "2026-01-10",
            "PROC_RESULT": "원안가결",
            "AGE": "22",
            "PROPOSER": "홍길동의원 등 10인",
            "RST_PROPOSER": "홍길동,공동대표",
            "PUBL_PROPOSER": "김공동,박공동",
            "RST_MONA_CD": "M001,M002",
            "PUBL_MONA_CD": "M003;M004",
            "DETAIL_LINK": "https://open.assembly.go.kr/bill/B1",
        },
        {
            "BILL_ID": "B2",
            "BILL_NO": "2200002",
            "BILL_NAME": "두 번째 법률안",
            "COMMITTEE": "정무위원회",
            "PROPOSE_DT": "2026-02-11",
            "PROC_RESULT": "대안반영폐기",
            "AGE": "22",
            "PROPOSER": "다른대표의원 등 11인",
            "RST_PROPOSER": "다른대표",
            "PUBL_PROPOSER": "홍길동,최공동",
            "RST_MONA_CD": "M005",
            "PUBL_MONA_CD": "M001;M006",
            "DETAIL_LINK": "https://open.assembly.go.kr/bill/B2",
        },
        {
            "BILL_ID": "B3",
            "BILL_NO": "2200003",
            "BILL_NAME": "세 번째 법률안",
            "COMMITTEE": "국방위원회",
            "PROPOSE_DT": "2026-03-12",
            "PROC_RESULT": "계류",
            "AGE": "22",
            "PROPOSER": "제삼자의원 등 8인",
            "RST_PROPOSER": "제삼자",
            "PUBL_PROPOSER": "다른공동",
            "RST_MONA_CD": "M007",
            "PUBL_MONA_CD": "M008;M009",
            "DETAIL_LINK": "https://open.assembly.go.kr/bill/B3",
        },
    ]


def payload(rows: list[dict], *, total: int = 3) -> dict:
    return {
        OpenAssemblyBillConnector.API_CODE: [
            {
                "head": [
                    {"list_total_count": total},
                    {"RESULT": {"CODE": "INFO-000", "MESSAGE": "정상"}},
                ]
            },
            {"row": rows},
        ]
    }


def paged_transport(
    *,
    rows: list[dict] | None = None,
    page_size: int = 2,
    total: int = 3,
    page2_override: list[dict] | None = None,
) -> httpx.MockTransport:
    source_rows = rows or bill_rows()

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["KEY"] == SECRET
        page = int(request.url.params["pIndex"])
        assert int(request.url.params["pSize"]) == page_size
        if page == 1:
            selected = source_rows[:page_size]
        elif page == 2 and page2_override is not None:
            selected = page2_override
        else:
            start = (page - 1) * page_size
            selected = source_rows[start : start + page_size]
        return httpx.Response(200, json=payload(selected, total=total))

    return httpx.MockTransport(handler)


def term_connector(
    *,
    rows: list[dict] | None = None,
    page_size: int = 2,
    total: int = 3,
    page2_override: list[dict] | None = None,
) -> OpenAssemblyBillConnector:
    return OpenAssemblyBillConnector(
        assembly_age=22,
        api_key=SECRET,
        page_size=page_size,
        transport=paged_transport(
            rows=rows,
            page_size=page_size,
            total=total,
            page2_override=page2_override,
        ),
    )


def test_complete_multi_page_scan_produces_exact_code_first_counts() -> None:
    summary = LegislativeActivityStager(identity(), term_connector()).stage()

    assert summary.member_code == "M001"
    assert summary.coverage_complete
    assert summary.role_code_coverage_complete
    assert summary.source_total_count == 3
    assert summary.source_unique_bill_count == 3
    assert summary.pages_fetched == 2
    assert summary.expected_pages == 2
    assert summary.representative_sponsored_count == 1
    assert summary.co_sponsored_count == 1
    assert summary.process_result_counts == {"대안반영폐기": 1, "원안가결": 1}
    assert {item.bill_id: item.role for item in summary.bills} == {
        "B1": "LEAD",
        "B2": "CO_SPONSOR",
    }


def test_joint_lead_and_semicolon_co_sponsor_codes_are_parsed_conservatively() -> None:
    connector = term_connector()
    document = connector.fetch(connector.discover()[0])
    records = connector.parse_bills(document)

    assert records[0].representative_proposer_codes == ("M001", "M002")
    assert records[0].co_proposer_codes == ("M003", "M004")
    assert records[0].role_for_code("M002") == "LEAD"
    assert records[1].co_proposer_codes == ("M001", "M006")
    assert records[1].role_for_code("M001") == "CO_SPONSOR"


def test_member_name_is_not_used_when_code_fields_are_available() -> None:
    summary = LegislativeActivityStager(
        identity(name="이름이다름", member_code="M001"), term_connector()
    ).stage()
    assert summary.representative_sponsored_count == 1
    assert summary.co_sponsored_count == 1
    assert {item.bill_id for item in summary.bills} == {"B1", "B2"}


def test_missing_role_code_field_fails_closed_even_on_unrelated_bill() -> None:
    rows = bill_rows()
    rows[2] = {key: value for key, value in rows[2].items() if key != "PUBL_MONA_CD"}
    summary = LegislativeActivityStager(identity(), term_connector(rows=rows)).stage()

    assert summary.coverage_complete
    assert not summary.role_code_coverage_complete
    assert summary.representative_sponsored_count is None
    assert summary.co_sponsored_count is None
    assert summary.process_result_counts == {}
    assert summary.role_code_errors == ("ROLE_CODE_FIELDS_MISSING_OR_MALFORMED",)


def test_malformed_documented_delimiter_fails_closed_without_name_fallback() -> None:
    rows = bill_rows()
    rows[1] = rows[1] | {"PUBL_MONA_CD": "M001,M006"}
    summary = LegislativeActivityStager(identity(), term_connector(rows=rows)).stage()

    assert summary.coverage_complete
    assert not summary.role_code_coverage_complete
    assert summary.representative_sponsored_count is None
    assert summary.co_sponsored_count is None


def test_max_page_guard_returns_incomplete_coverage_and_no_exact_counts() -> None:
    summary = LegislativeActivityStager(identity(), term_connector(), max_pages=1).stage()

    assert not summary.coverage_complete
    assert not summary.role_code_coverage_complete
    assert summary.pages_fetched == 1
    assert summary.expected_pages == 2
    assert summary.representative_sponsored_count is None
    assert summary.co_sponsored_count is None
    assert "EXPECTED_PAGES_EXCEED_MAX" in summary.coverage_errors
    assert "UNIQUE_BILL_COUNT_MISMATCH" in summary.coverage_errors


def test_conflicting_duplicate_bill_id_fails_closed() -> None:
    conflicting = [bill_rows()[0] | {"BILL_NAME": "충돌하는 법률안명"}]
    connector = term_connector(page2_override=conflicting)
    with pytest.raises(ValueError, match="conflicting duplicate BILL_ID"):
        LegislativeActivityStager(identity(), connector).stage()


def test_staging_requires_existing_assembly_member_identity_anchor() -> None:
    candidate = IdentityCandidate(canonical_name="홍길동", office="국회의원")
    with pytest.raises(ValueError, match="assembly_member_code"):
        LegislativeActivityStager(candidate, term_connector())


def test_exact_scan_rejects_filtered_or_nonfirst_page_connector() -> None:
    filtered = OpenAssemblyBillConnector(
        assembly_age=22,
        api_key=SECRET,
        proposer="홍길동",
        transport=paged_transport(),
    )
    with pytest.raises(ValueError, match="unfiltered"):
        LegislativeActivityStager(identity(), filtered)

    page_two = OpenAssemblyBillConnector(
        assembly_age=22,
        api_key=SECRET,
        page_index=2,
        transport=paged_transport(),
    )
    with pytest.raises(ValueError, match="page 1"):
        LegislativeActivityStager(identity(), page_two)


def test_restricted_source_policy_blocks_before_network() -> None:
    def forbidden(request: httpx.Request) -> httpx.Response:
        pytest.fail(f"network should not be reached: {request}")

    connector = OpenAssemblyBillConnector(
        assembly_age=22,
        api_key=SECRET,
        transport=httpx.MockTransport(forbidden),
    )
    for mode in (SourceCollectionMode.BLOCKED, SourceCollectionMode.DISCOVERY_ONLY):
        policy = national_assembly_bill_policy().model_copy(
            update={"collection_mode": mode, "can_fetch": False}
        )
        with pytest.raises(PolicyDenied):
            LegislativeActivityStager(identity(), connector, policy).stage()


def test_review_json_exposes_blocked_bill_text_source_and_no_faction_or_secret_fields() -> None:
    rendered = render_legislative_json(
        LegislativeActivityStager(identity(), term_connector()).stage()
    )
    data = json.loads(rendered)

    assert data["coverage"]["complete"] is True
    assert data["coverage"]["role_codes_complete"] is True
    assert data["counts"]["representative_sponsored"] == 1
    assert data["counts"]["co_sponsored"] == 1
    assert data["counts"]["semantics"] == "DESCRIPTIVE_COUNTS_NOT_PERFORMANCE_SCORE"
    assert data["bill_purpose_source"]["status"] == "BLOCKED_NO_VERIFIED_STRUCTURED_SOURCE"
    assert SECRET not in rendered
    lowered = rendered.casefold()
    assert "faction" not in lowered
    assert "계파" not in rendered
    assert "telephone" not in lowered
    assert "email" not in lowered
    assert "bpmbillsummary" not in lowered
