import json
from pathlib import Path

import pytest

from packages.connectors.presidential_personnel_records import (
    PresidentialPersonnelRecordError,
    parse_presidential_personnel_rows,
    presidential_personnel_policy,
)
from packages.domain.enums import (
    InstitutionalBodyType,
    PresidentialPersonnelAction,
    PresidentialRoleScope,
)
from packages.verification.identity import IdentityStatus, resolve_identity
from workers.presidential_personnel import (
    render_presidential_personnel_json,
    stage_presidential_personnel_rows,
)

FIXTURE = Path(__file__).parent / "fixtures" / "presidential_personnel.json"


def fixture() -> list[dict]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_presidential_source_policy_is_metadata_only_and_live_fetch_fail_closed() -> None:
    policy = presidential_personnel_policy()
    assert policy.domain == "president.go.kr"
    assert policy.can_store_metadata
    assert not policy.can_fetch
    assert not policy.can_store_fulltext
    assert not policy.can_send_to_ai
    assert not policy.can_show_excerpt
    assert not policy.can_commercialize


def test_official_personnel_actions_remain_distinct() -> None:
    records = parse_presidential_personnel_rows(fixture())

    assert [record.action for record in records] == [
        PresidentialPersonnelAction.APPOINTED,
        PresidentialPersonnelAction.APPOINTED,
        PresidentialPersonnelAction.DESIGNATED,
        PresidentialPersonnelAction.NOMINATED,
        PresidentialPersonnelAction.COMMISSIONED,
    ]
    assert records[2].action_text == "내정"
    assert records[3].action_text == "지명"
    assert records[4].action_text == "위촉"


def test_presidential_role_scopes_and_body_projection_remain_distinct() -> None:
    records = parse_presidential_personnel_rows(fixture())

    assert records[0].role_scope == PresidentialRoleScope.PRESIDENTIAL_SECRETARIAT
    assert records[1].role_scope == PresidentialRoleScope.NATIONAL_SECURITY_OFFICE
    assert records[3].role_scope == PresidentialRoleScope.PRESIDENTIAL_COMMISSION
    assert records[4].role_scope == PresidentialRoleScope.SPECIAL_ADVISER
    assert records[3].institutional_body_type == InstitutionalBodyType.PRESIDENTIAL_COMMISSION
    assert records[0].institutional_body_type is None

    task_force = fixture()[0] | {
        "record_id": "presidential-task-force-test",
        "person_name": "김공개",
        "action": "보직",
        "role_scope": "대통령직속TF",
        "organization": "테스트 대통령직속TF",
        "role": "단장",
    }
    staged = parse_presidential_personnel_rows([task_force])[0]
    assert staged.action == PresidentialPersonnelAction.ASSIGNED
    assert staged.role_scope == PresidentialRoleScope.PRESIDENTIAL_TASK_FORCE
    assert staged.institutional_body_type == InstitutionalBodyType.TASK_FORCE


def test_staging_uses_public_action_and_role_as_identity_anchors() -> None:
    staged = stage_presidential_personnel_rows(fixture())
    candidate = staged[3].candidate

    assert candidate is not None
    assert candidate.canonical_name == "하정우"
    assert candidate.office == "부위원장"
    assert candidate.organization == "국가AI전략위원회"
    assert "presidential_personnel_action:NOMINATED" in candidate.career_anchors
    assert "presidential_role_scope:PRESIDENTIAL_COMMISSION" in candidate.career_anchors
    assert resolve_identity(candidate, candidate).status == IdentityStatus.RESOLVED


def test_reported_prior_careers_are_source_attributed_not_independent_career_facts() -> None:
    data = stage_presidential_personnel_rows(fixture())[2].to_dict()
    action = data["personnel_action"]

    assert action["reported_prior_careers"] == ["조국혁신당 국회의원", "구글 엔지니어"]
    assert "원 출처로 독립 검증" in action["reported_prior_careers_semantics"]
    assert "서로 대체하지 않는다" in action["action_semantics"]


def test_meeting_attendance_or_non_personnel_record_cannot_enter_feeder() -> None:
    row = fixture()[0] | {
        "record_id": "meeting-attendance-test",
        "record_kind": "MEETING_ATTENDANCE",
    }
    with pytest.raises(PresidentialPersonnelRecordError, match="cannot enter personnel feeder"):
        parse_presidential_personnel_rows([row])


def test_masked_or_non_person_name_never_creates_identity_candidate() -> None:
    masked = fixture()[0] | {
        "record_id": "masked-person-test",
        "person_name": "김○○",
    }
    missing = fixture()[0] | {
        "record_id": "vacant-person-test",
        "person_name": "공석",
    }
    staged = stage_presidential_personnel_rows([masked, missing])

    assert staged[0].candidate is None
    assert staged[1].candidate is None
    assert staged[0].to_dict()["identity_semantics"] == "PERSON_NAME_NOT_PUBLIC_OR_USABLE"


def test_private_fields_and_political_inference_fields_never_reach_output() -> None:
    rendered = render_presidential_personnel_json(fixture())
    lowered = rendered.casefold()

    assert "02-0000-0000" not in rendered
    assert "수집금지 주소" not in rendered
    assert "faction" not in lowered
    assert "계파" not in rendered
    assert "loyalty" not in lowered
    assert "influence_score" not in lowered
    assert "candidate_probability" not in lowered
