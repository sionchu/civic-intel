import json
from datetime import UTC, date, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from pydantic import ValidationError

from packages.connectors.civil_service_records import (
    CivilServiceRecordError,
    parse_employment_review_rows,
    parse_personnel_notice_rows,
)
from packages.domain.contracts import CivilServiceCareerEpisode, EmploymentReviewEvent
from packages.domain.enums import (
    CivilServiceAppointmentRoute,
    CivilServiceCategory,
    CivilServiceEventType,
    EmploymentReviewDecision,
)
from packages.verification.identity import IdentityStatus, resolve_identity
from workers.civil_service import (
    render_civil_service_json,
    stage_employment_review_rows,
    stage_personnel_rows,
)

FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> list[dict]:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_personnel_fixture_preserves_distinct_event_and_route_semantics() -> None:
    records = parse_personnel_notice_rows(load_fixture("civil_service_personnel.json"))

    assert [item.event_type for item in records] == [
        CivilServiceEventType.PROMOTION,
        CivilServiceEventType.APPOINTMENT,
        CivilServiceEventType.TRANSFER,
    ]
    assert records[0].appointment_route == CivilServiceAppointmentRoute.SENIOR_CIVIL_SERVICE
    assert records[1].appointment_route == CivilServiceAppointmentRoute.OPEN_POSITION
    assert records[2].category == CivilServiceCategory.FOREIGN_SERVICE
    assert records[1].previous_organization == "민간정책연구원"


def test_ordinary_staff_cannot_enter_civil_service_feeder() -> None:
    row = {
        "record_id": "ordinary-001",
        "person_name": "일반직원",
        "event_date": "2026-01-01",
        "service_category": "중앙일반직",
        "event_type": "전보",
        "appointment_route": "일반",
        "organization": "테스트부",
        "title": "주무관",
        "source_ref": "ordinary-personnel-notice",
        "public_scope": "ORDINARY_STAFF",
    }
    with pytest.raises(CivilServiceRecordError, match="cannot enter feeder"):
        parse_personnel_notice_rows([row])


def test_staged_personnel_record_is_consumable_by_existing_identity_resolver() -> None:
    staged = stage_personnel_rows(load_fixture("civil_service_personnel.json"))
    assert len(staged) == 3
    observed = staged[0].candidate
    assert observed.canonical_name == "김정책"
    assert observed.office == "정책기획관"
    assert observed.organization == "테스트부"
    assert "civil_service_route:SENIOR_CIVIL_SERVICE" in observed.career_anchors
    assert resolve_identity(observed, observed).status == IdentityStatus.RESOLVED


def test_private_fields_in_personnel_input_do_not_reach_staging_output() -> None:
    row = load_fixture("civil_service_personnel.json")[0] | {
        "phone": "010-0000-0000",
        "email": "private@example.invalid",
        "address": "수집금지 주소",
    }
    rendered = json.dumps(stage_personnel_rows([row])[0].to_dict(), ensure_ascii=False)

    assert "010-0000-0000" not in rendered
    assert "private@example.invalid" not in rendered
    assert "수집금지 주소" not in rendered


def test_employment_review_preserves_all_official_decision_types() -> None:
    records = parse_employment_review_rows(
        load_fixture("retired_official_employment_reviews.json")
    )
    assert [item.decision for item in records] == [
        EmploymentReviewDecision.APPROVED,
        EmploymentReviewDecision.RESTRICTED,
        EmploymentReviewDecision.EMPLOYABLE,
        EmploymentReviewDecision.DISAPPROVED,
    ]
    assert records[0].decision_text == "취업승인"
    assert records[1].decision_text == "취업제한"
    assert records[2].decision_text == "취업가능"
    assert records[3].decision_text == "취업불승인"


def test_masked_employment_review_name_never_creates_person_candidate() -> None:
    rows = load_fixture("retired_official_employment_reviews.json")
    staged = stage_employment_review_rows(rows)
    masked = staged[3]

    assert masked.record.person_name is None
    assert masked.candidate is None
    data = masked.to_dict()
    assert data["canonical_name"] is None
    assert data["identity_anchors"] == []
    assert data["identity_semantics"] == "PERSON_NAME_NOT_PUBLIC"

    partial = rows[0] | {"record_id": "partial-mask", "person_name": "김○○"}
    assert stage_employment_review_rows([partial])[0].candidate is None


def test_employment_review_output_omits_private_input_and_does_not_assert_wrongdoing() -> None:
    rendered = render_civil_service_json(
        stage_personnel_rows(load_fixture("civil_service_personnel.json")),
        stage_employment_review_rows(load_fixture("retired_official_employment_reviews.json")),
    )
    lowered = rendered.casefold()

    assert "010-0000-0000" not in rendered
    assert "private@example.invalid" not in rendered
    assert "수집금지 주소" not in rendered
    assert '"violation"' not in lowered
    assert '"wrongdoing"' not in lowered
    assert "취업가능·취업승인 결정을 위반이나 부당취업으로 해석하지 않는다" in rendered


def test_unknown_employment_review_decision_is_retained_as_unknown_not_guessed() -> None:
    row = load_fixture("retired_official_employment_reviews.json")[0] | {
        "record_id": "employment-review-unknown",
        "decision": "추가확인",
    }
    record = parse_employment_review_rows([row])[0]
    assert record.decision == EmploymentReviewDecision.UNKNOWN
    assert record.decision_text == "추가확인"


def test_canonical_civil_service_contract_requires_dated_source_backing() -> None:
    event = CivilServiceCareerEpisode(
        person_id=uuid4(),
        organization_id=uuid4(),
        category=CivilServiceCategory.CENTRAL_GENERAL,
        event_type=CivilServiceEventType.PROMOTION,
        appointment_route=CivilServiceAppointmentRoute.SENIOR_CIVIL_SERVICE,
        title="정책기획관",
        event_date=date(2026, 1, 15),
        valid_from=datetime(2026, 1, 15, tzinfo=UTC),
        source_ids=[uuid4()],
    )
    assert event.event_type == CivilServiceEventType.PROMOTION
    assert event.appointment_route == CivilServiceAppointmentRoute.SENIOR_CIVIL_SERVICE

    with pytest.raises(ValidationError):
        CivilServiceCareerEpisode(
            person_id=uuid4(),
            organization_id=uuid4(),
            category=CivilServiceCategory.CENTRAL_GENERAL,
            event_type=CivilServiceEventType.TRANSFER,
            title="국장",
            event_date=date(2026, 2, 1),
            source_ids=[],
        )


def test_employment_review_contract_has_no_guilt_or_violation_field() -> None:
    kwargs = {
        "person_id": uuid4(),
        "former_organization_id": uuid4(),
        "destination_organization_id": uuid4(),
        "review_date": date(2026, 8, 27),
        "decision": EmploymentReviewDecision.APPROVED,
        "decision_text": "취업승인",
        "source_ids": [uuid4()],
    }
    event = EmploymentReviewEvent(**kwargs)
    assert event.decision == EmploymentReviewDecision.APPROVED

    with pytest.raises(ValidationError):
        EmploymentReviewEvent(**kwargs, violation=True)
