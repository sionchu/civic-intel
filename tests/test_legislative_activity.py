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


def identity(name: str = "홍길동") -> IdentityCandidate:
    return IdentityCandidate(
        canonical_name=name,
        office="국회의원",
        organization="테스트정당",
        career_anchors=("assembly_member_code:M-001", "district:서울 테스트구"),
    )


def payload(*, total: int = 2) -> dict:
    rows = [
        {
            "BILL_ID": "B1",
            "BILL_NO": "2200001",
            "BILL_NAME": "첫 번째 법률안",
            "COMMITTEE": "법제사법위원회",
            "PROPOSE_DT": "2026-01-10",
            "PROC_RESULT": "원안가결",
            "AGE": "22",
            "PROPOSER": "홍길동의원 등 10인",
            "RST_PROPOSER": "홍길동",
            "PUBL_PROPOSER": "김공동,박공동",
        },
        {
            "BILL_ID": "B2",
            "BILL_NO": "2200002",
            "BILL_NAME": "두 번째 법률안",
            "COMMITTEE": "정무위원회",
            "PROPOSE_DT": "2026-02-11",
            "PROC_RESULT": "대안반영폐기",
            "AGE": "22",
            "PROPOSER": "홍길동의원 등 11인",
            "RST_PROPOSER": "홍길동",
            "PUBL_PROPOSER": "이공동,최공동",
        },
    ]
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


def transport(*, total: int = 2) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["KEY"] == SECRET
        return httpx.Response(200, json=payload(total=total))

    return httpx.MockTransport(handler)


def test_complete_representative_query_produces_exact_lead_count_only() -> None:
    connector = OpenAssemblyBillConnector(
        assembly_age=22,
        api_key=SECRET,
        proposer="홍길동",
        page_size=100,
        transport=transport(total=2),
    )
    summary = LegislativeActivityStager(identity(), connector).stage()

    assert summary.member_code == "M-001"
    assert summary.coverage_complete
    assert summary.source_total_count == 2
    assert summary.representative_sponsored_count == 2
    assert summary.co_sponsored_count is None
    assert not summary.co_sponsor_coverage_complete
    assert summary.page_process_result_counts == {"대안반영폐기": 1, "원안가결": 1}
    assert {item.role for item in summary.bills} == {"LEAD"}


def test_partial_page_never_becomes_exact_count() -> None:
    connector = OpenAssemblyBillConnector(
        assembly_age=22,
        api_key=SECRET,
        proposer="홍길동",
        page_size=2,
        transport=transport(total=20),
    )
    summary = LegislativeActivityStager(identity(), connector).stage()
    assert not summary.coverage_complete
    assert summary.staged_bill_count == 2
    assert summary.representative_sponsored_count is None


def test_staging_requires_existing_assembly_member_identity_anchor() -> None:
    candidate = IdentityCandidate(canonical_name="홍길동", office="국회의원")
    connector = OpenAssemblyBillConnector(assembly_age=22, api_key=SECRET)
    with pytest.raises(ValueError, match="assembly_member_code"):
        LegislativeActivityStager(candidate, connector)


def test_restricted_source_policy_blocks_before_network() -> None:
    def forbidden(request: httpx.Request) -> httpx.Response:
        pytest.fail(f"network should not be reached: {request}")

    connector = OpenAssemblyBillConnector(
        assembly_age=22,
        api_key=SECRET,
        proposer="홍길동",
        transport=httpx.MockTransport(forbidden),
    )
    for mode in (SourceCollectionMode.BLOCKED, SourceCollectionMode.DISCOVERY_ONLY):
        policy = national_assembly_bill_policy().model_copy(
            update={"collection_mode": mode, "can_fetch": False}
        )
        with pytest.raises(PolicyDenied):
            LegislativeActivityStager(identity(), connector, policy).stage()


def test_review_json_has_coverage_and_no_faction_or_secret_fields() -> None:
    connector = OpenAssemblyBillConnector(
        assembly_age=22,
        api_key=SECRET,
        proposer="홍길동",
        transport=transport(total=2),
    )
    rendered = render_legislative_json(LegislativeActivityStager(identity(), connector).stage())
    data = json.loads(rendered)

    assert data["coverage"]["complete"] is True
    assert data["coverage"]["co_sponsor_complete"] is False
    assert data["counts"]["representative_sponsored"] == 2
    assert data["counts"]["co_sponsored"] is None
    assert SECRET not in rendered
    lowered = rendered.casefold()
    assert "faction" not in lowered
    assert "계파" not in rendered
    assert "telephone" not in lowered
    assert "email" not in lowered
