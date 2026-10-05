from __future__ import annotations

import json

import httpx
import pytest

from packages.connectors.open_assembly import AssemblyApiError, MissingAssemblyApiKey
from packages.connectors.open_assembly_committees import (
    OpenAssemblyCommitteeMemberConnector,
    OpenAssemblyCommitteeStatusConnector,
    national_assembly_committee_policy,
)
from packages.domain.enums import SourceCollectionMode
from packages.verification.policy import PolicyDenied
from workers.assembly_committees import (
    AssemblyCommitteeRosterStager,
    committee_membership_provider_key,
    committee_status_provider_key,
)

SECRET = "committee-secret-must-not-persist"


def status_row() -> dict[str, object]:
    return {
        "CMT_DIV_CD": "001",
        "CMT_DIV_NM": "상임위원회",
        "HR_DEPT_CD": "9700005",
        "COMMITTEE_NAME": "국회운영위원회",
        "HG_NM": "한병도 (더불어민주당)",
        "HG_NM_LIST": "천준호 (더불어민주당),김승수 (국민의힘)",
        "LIMIT_CNT": 28,
        "CURR_CNT": 28,
        "POLY99_CNT": 3,
        "POLY_CNT": 25,
        "KEY": SECRET,
    }


def member_row(*, role: str = "위원") -> dict[str, object]:
    return {
        "DEPT_CD": "9700005",
        "DEPT_NM": "국회운영위원회",
        "JOB_RES_NM": role,
        "HG_NM": "김기웅",
        "ORIG_NM": "대구 중구남구",
        "POLY_NM": "국민의힘",
        "ASSEM_TEL": "02-784-8630",
        "ASSEM_EMAIL": "private-ish@example.invalid",
        "HJ_NM": "金基雄",
        "ROOM_NO": "432호",
        "STAFF": "보좌관A, 보좌관B",
        "SECRETARY": "비서관A",
        "SECRETARY2": "비서A",
        "MONA_CD": "HE08888N",
        "KEY": SECRET,
    }


def payload(api_code: str, row: dict[str, object], *, total: int = 1) -> dict:
    return {
        api_code: [
            {
                "head": [
                    {"list_total_count": total},
                    {"RESULT": {"CODE": "INFO-000", "MESSAGE": "정상 처리되었습니다."}},
                ]
            },
            {"row": [row]},
        ]
    }


def test_normal_mode_requires_api_key_without_network(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("ASSEMBLY_API_KEY", raising=False)
    connector = OpenAssemblyCommitteeMemberConnector(
        transport=httpx.MockTransport(
            lambda request: pytest.fail(f"unexpected fetch: {request}")
        )
    )
    with pytest.raises(MissingAssemblyApiKey, match="ASSEMBLY_API_KEY"):
        connector.fetch(connector.discover()[0])


def test_sample_mode_is_explicitly_bounded_and_has_no_key_in_url() -> None:
    connector = OpenAssemblyCommitteeMemberConnector(
        page_index=1,
        page_size=5,
        sample_mode=True,
    )
    url = httpx.URL(connector.discover()[0])
    assert url.host == connector.HOST
    assert url.path == f"/portal/openapi/{connector.API_CODE}"
    assert url.params["Type"] == "json"
    assert url.params["pIndex"] == "1"
    assert url.params["pSize"] == "5"
    assert "KEY" not in url.params

    with pytest.raises(ValueError, match="sample mode"):
        OpenAssemblyCommitteeMemberConnector(
            page_index=2,
            page_size=5,
            sample_mode=True,
        )
    with pytest.raises(ValueError, match="sample mode"):
        OpenAssemblyCommitteeStatusConnector(
            page_index=1,
            page_size=100,
            sample_mode=True,
        )


def test_committee_status_fetch_and_parse_keep_only_documented_status_fields() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["KEY"] == SECRET
        assert request.url.params["Type"] == "json"
        return httpx.Response(
            200,
            json=payload(OpenAssemblyCommitteeStatusConnector.API_CODE, status_row()),
        )

    connector = OpenAssemblyCommitteeStatusConnector(
        api_key=SECRET,
        transport=httpx.MockTransport(handler),
    )
    document = connector.fetch(connector.discover()[0])
    statuses = connector.parse_statuses(document)

    assert document.metadata["list_total_count"] == "1"
    assert document.metadata["row_count"] == "1"
    assert document.metadata["sample_mode"] == "false"
    assert SECRET not in document.url
    assert SECRET not in document.body
    assert '"MESSAGE"' not in document.body
    assert SECRET not in repr(document.metadata)
    assert len(statuses) == 1
    record = statuses[0]
    assert record.committee_code == "9700005"
    assert record.committee_name == "국회운영위원회"
    assert record.authorized_count == 28
    assert record.current_count == 28
    assert committee_status_provider_key(record) == "9700005"


def test_committee_member_fetch_discards_contacts_room_and_staff_before_body() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["KEY"] == SECRET
        return httpx.Response(
            200,
            json=payload(OpenAssemblyCommitteeMemberConnector.API_CODE, member_row()),
        )

    connector = OpenAssemblyCommitteeMemberConnector(
        api_key=SECRET,
        transport=httpx.MockTransport(handler),
    )
    document = connector.fetch(connector.discover()[0])
    memberships = connector.parse_memberships(document)

    assert len(memberships) == 1
    record = memberships[0]
    assert record.committee_code == "9700005"
    assert record.member_code == "HE08888N"
    assert record.role == "위원"
    assert record.name_ko == "김기웅"
    assert record.party == "국민의힘"
    assert record.district == "대구 중구남구"
    assert committee_membership_provider_key(record) == "9700005:HE08888N"

    serialized = document.body
    for forbidden in (
        "ASSEM_TEL",
        "ASSEM_EMAIL",
        "ROOM_NO",
        "STAFF",
        "SECRETARY",
        "SECRETARY2",
        "02-784-8630",
        "private-ish@example.invalid",
        "432호",
        "보좌관A",
        "비서관A",
        "비서A",
        SECRET,
    ):
        assert forbidden not in serialized

    parsed = json.loads(serialized)
    safe_row = parsed[connector.API_CODE][1]["row"][0]
    assert set(safe_row) == set(connector.SAFE_FIELDS)


def test_role_change_keeps_same_relationship_provider_key() -> None:
    def build(role: str):
        connector = OpenAssemblyCommitteeMemberConnector(
            api_key=SECRET,
            transport=httpx.MockTransport(
                lambda request: httpx.Response(
                    200,
                    json=payload(
                        OpenAssemblyCommitteeMemberConnector.API_CODE,
                        member_row(role=role),
                    ),
                )
            ),
        )
        return connector.parse_memberships(connector.fetch(connector.discover()[0]))[0]

    member = build("위원")
    secretary = build("간사")
    assert committee_membership_provider_key(member) == committee_membership_provider_key(
        secretary
    )
    assert member.role != secretary.role


def test_filters_are_allowlisted_and_credentials_never_enter_discovery_url() -> None:
    connector = OpenAssemblyCommitteeMemberConnector(
        api_key=SECRET,
        page_index=2,
        page_size=50,
        filters={
            "DEPT_CD": "9700005",
            "MONA_CD": "HE08888N",
            "POLY_NM": "국민의힘",
        },
    )
    url = httpx.URL(connector.discover()[0])
    assert url.params["DEPT_CD"] == "9700005"
    assert url.params["MONA_CD"] == "HE08888N"
    assert url.params["POLY_NM"] == "국민의힘"
    assert SECRET not in str(url)
    assert "KEY" not in url.params

    with pytest.raises(ValueError, match="unsupported"):
        OpenAssemblyCommitteeMemberConnector(filters={"ASSEM_EMAIL": "x@example.com"})


def test_provider_error_is_safe_and_does_not_leak_key() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                OpenAssemblyCommitteeStatusConnector.API_CODE: [
                    {
                        "head": [
                            {"list_total_count": 0},
                            {
                                "RESULT": {
                                    "CODE": "INFO-200",
                                    "MESSAGE": f"error {SECRET}",
                                }
                            },
                        ]
                    }
                ]
            },
        )

    connector = OpenAssemblyCommitteeStatusConnector(
        api_key=SECRET,
        transport=httpx.MockTransport(handler),
    )
    with pytest.raises(AssemblyApiError) as exc_info:
        connector.fetch(connector.discover()[0])
    assert "INFO-200" in str(exc_info.value)
    assert SECRET not in str(exc_info.value)




def test_committee_policy_is_source_specific_and_minimized() -> None:
    policy = national_assembly_committee_policy()
    assert policy.domain == "open.assembly.go.kr"
    assert policy.can_fetch is True
    assert policy.can_store_metadata is True
    assert policy.can_store_fulltext is False
    assert policy.can_send_to_ai is False
    assert policy.can_show_excerpt is False
    assert policy.can_commercialize is True
    assert policy.license == "이용허락범위 제한 없음"
    assert "nktulghcadyhmiqxi" in (policy.policy_note or "")
    assert "Attribution" in (policy.policy_note or "")


def test_stager_policy_denial_happens_before_network() -> None:
    def forbidden(request: httpx.Request) -> httpx.Response:
        pytest.fail(f"policy denial should happen before network: {request}")

    status = OpenAssemblyCommitteeStatusConnector(
        api_key=SECRET,
        transport=httpx.MockTransport(forbidden),
    )
    members = OpenAssemblyCommitteeMemberConnector(
        api_key=SECRET,
        transport=httpx.MockTransport(forbidden),
    )
    blocked = national_assembly_committee_policy().model_copy(
        update={
            "collection_mode": SourceCollectionMode.BLOCKED,
            "can_fetch": False,
        }
    )
    with pytest.raises(PolicyDenied):
        AssemblyCommitteeRosterStager(status, members, blocked).stage()


def test_stager_returns_privacy_minimized_source_records() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith(OpenAssemblyCommitteeStatusConnector.API_CODE):
            return httpx.Response(
                200,
                json=payload(
                    OpenAssemblyCommitteeStatusConnector.API_CODE,
                    status_row(),
                ),
            )
        return httpx.Response(
            200,
            json=payload(
                OpenAssemblyCommitteeMemberConnector.API_CODE,
                member_row(),
            ),
        )

    transport = httpx.MockTransport(handler)
    staged = AssemblyCommitteeRosterStager(
        OpenAssemblyCommitteeStatusConnector(api_key=SECRET, transport=transport),
        OpenAssemblyCommitteeMemberConnector(api_key=SECRET, transport=transport),
    ).stage()

    output = json.dumps(staged.to_dict(), ensure_ascii=False)
    assert "9700005" in output
    assert "HE08888N" in output
    assert "김기웅" in output
    assert "ASSEM_TEL" not in output
    assert "ASSEM_EMAIL" not in output
    assert "STAFF" not in output
    assert "보좌관A" not in output
    assert SECRET not in output
