import json

import httpx
import pytest

from packages.connectors.open_assembly import (
    AssemblyMemberRecord,
    OpenAssemblyMemberConnector,
    national_assembly_member_policy,
)
from packages.domain.enums import IdentityStatus, SourceCollectionMode
from packages.verification.identity import resolve_identity
from packages.verification.policy import PolicyDenied
from workers.assembly_roster import (
    AssemblyRosterStager,
    StagedAssemblyMember,
    assembly_member_to_identity_candidate,
    render_staged_json,
)

SECRET = "staging-test-secret"


def api_payload() -> dict:
    return {
        OpenAssemblyMemberConnector.API_CODE: [
            {
                "head": [
                    {"list_total_count": 1},
                    {"RESULT": {"CODE": "INFO-000", "MESSAGE": "정상"}},
                ]
            },
            {
                "row": [
                    {
                        "MONA_CD": "M-001",
                        "HG_NM": "홍길동",
                        "HJ_NM": "洪吉童",
                        "ENG_NM": "Hong Gil-dong",
                        "BTH_DATE": "19700102",
                        "POLY_NM": "테스트정당",
                        "ORIG_NM": "서울 테스트구",
                        "REELE_GBN_NM": "재선",
                        "ELECT_GBN_NM": "지역구",
                        "CMITS": "테스트위원회",
                        "TEL_NO": "02-1111-2222",
                        "E_MAIL": "do-not-stage@example.invalid",
                    }
                ]
            },
        ]
    }


def mock_transport() -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["KEY"] == SECRET
        return httpx.Response(200, json=api_payload())

    return httpx.MockTransport(handler)


def test_mapper_builds_existing_identity_candidate_without_private_fields() -> None:
    record = AssemblyMemberRecord(
        member_code="M-001",
        name_ko="홍길동",
        name_hanja="洪吉童",
        name_en="Hong Gil-dong",
        birth_date=None,
        party="테스트정당",
        district="서울 테스트구",
        reelection="재선",
        election_type="지역구",
        committees="테스트위원회",
    )
    candidate = assembly_member_to_identity_candidate(record)

    assert candidate.canonical_name == "홍길동"
    assert candidate.aliases == ("洪吉童", "Hong Gil-dong")
    assert candidate.birth_date is None
    assert candidate.office == "국회의원"
    assert candidate.organization == "테스트정당"
    assert "assembly_member_code:M-001" in candidate.career_anchors
    assert "district:서울 테스트구" in candidate.career_anchors


def test_mapper_does_not_invent_missing_optional_values() -> None:
    record = AssemblyMemberRecord(member_code="M-002", name_ko="김테스트")
    candidate = assembly_member_to_identity_candidate(record)

    assert candidate.aliases == ()
    assert candidate.birth_date is None
    assert candidate.organization is None
    assert candidate.office == "국회의원"
    assert candidate.career_anchors == ("assembly_member_code:M-002",)


def test_stager_returns_candidates_consumable_by_identity_resolver() -> None:
    connector = OpenAssemblyMemberConnector(api_key=SECRET, transport=mock_transport())
    staged = AssemblyRosterStager(connector).stage()

    assert len(staged) == 1
    candidate = staged[0].candidate
    assert candidate.birth_date is not None
    assert candidate.birth_date.isoformat() == "1970-01-02"
    assert resolve_identity(candidate, candidate).status == IdentityStatus.RESOLVED


def test_restricted_policy_blocks_staging_before_network_fetch() -> None:
    def forbidden_handler(request: httpx.Request) -> httpx.Response:
        pytest.fail(f"network should not be reached: {request}")

    connector = OpenAssemblyMemberConnector(
        api_key=SECRET,
        transport=httpx.MockTransport(forbidden_handler),
    )
    for mode in (SourceCollectionMode.BLOCKED, SourceCollectionMode.DISCOVERY_ONLY):
        policy = national_assembly_member_policy().model_copy(
            update={"collection_mode": mode, "can_fetch": False}
        )
        with pytest.raises(PolicyDenied):
            AssemblyRosterStager(connector, policy).stage()


def test_wrong_domain_policy_is_rejected_before_network_fetch() -> None:
    connector = OpenAssemblyMemberConnector(
        api_key=SECRET,
        transport=httpx.MockTransport(
            lambda request: pytest.fail(f"network should not be reached: {request}")
        ),
    )
    policy = national_assembly_member_policy().model_copy(update={"domain": "example.gov"})
    with pytest.raises(PolicyDenied, match="domain"):
        AssemblyRosterStager(connector, policy).stage()


def test_staged_json_is_safe_review_output_only() -> None:
    candidate = assembly_member_to_identity_candidate(
        AssemblyMemberRecord(
            member_code="M-003",
            name_ko="박검토",
            name_en="Park Review",
            party="검토당",
            district="검토구",
        )
    )
    payload = render_staged_json([StagedAssemblyMember("M-003", candidate)])
    decoded = json.loads(payload)

    assert decoded[0]["member_code"] == "M-003"
    assert decoded[0]["canonical_name"] == "박검토"
    assert SECRET not in payload
    assert "TEL_NO" not in payload
    assert "E_MAIL" not in payload
    assert "telephone" not in payload.casefold()
    assert "email" not in payload.casefold()
