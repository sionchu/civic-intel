import json
from pathlib import Path

import pytest

from packages.connectors.civil_service_records import (
    CivilServiceRecordError,
    parse_employment_review_rows,
    parse_personnel_notice_rows,
)
from packages.domain.enums import (
    CivilServiceAppointmentRoute,
    CivilServiceEventType,
    EmploymentReviewDecision,
)
from workers.civil_service import (
    render_civil_service_json,
    stage_employment_review_rows,
    stage_personnel_rows,
)

FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> list[dict]:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_personnel_records_preserve_event_and_appointment_route() -> None:
    records = parse_personnel_notice_rows(load_fixture("civil_service_personnel.json"))

    assert [item.event_type for item in records] == [
        CivilServiceEventType.PROMOTION,
        CivilServiceEventType.APPOINTMENT,
        CivilServiceEventType.TRANSFER,
    ]
    assert records[0].appointment_route == CivilServiceAppointmentRoute.SENIOR_CIVIL_SERVICE
    assert records[1].appointment_route == CivilServiceAppointmentRoute.OPEN_POSITION
    assert records[1].previous_organization == "민간정책연구원"
    assert records[2].organization == "외교부"


def test_ordinary_staff_scope_is_rejected() -> None:
    row = load_fixture("civil_service_personnel.json")[0] | {
        "record_id": "ordinary-employee",
        "public_scope": "ORDINARY_EMPLOYEE",
    }
    with pytest.raises(CivilServiceRecordError, match="cannot enter feeder"):
        parse_personnel_notice_rows([row])


def test_staged_personnel_identity_uses_event_anchors_not_private_fields() -> None:
    row = load_fixture("civil_service_personnel.json")[0] | {
        "phone": "010-0000-0000",
        "email": "private@example.invalid",
        "address": "수집금지 주소",
    }
    staged = stage_personnel_rows([row])[0]
    rendered = json.dumps(staged.to_dict(), ensure_ascii=False)

    assert staged.candidate.canonical_name == "김정책"
    assert "civil_service_record:personnel-2026-001" in staged.candidate.career_anchors
    assert "010-0000-0000" not in rendered
    assert "private@example.invalid" not in rendered
    assert "수집금지 주소" not in rendered


def test_employment_review_decisions_preserve_official_meaning() -> None:
    records = parse_employment_review_rows(load_fixture("employment_reviews.json"))

    assert [item.decision for item in records] == [
        EmploymentReviewDecision.EMPLOYABLE,
        EmploymentReviewDecision.APPROVED,
        EmploymentReviewDecision.RESTRICTED,
        EmploymentReviewDecision.DISAPPROVED,
    ]
    assert records[0].decision_text == "취업가능"
    assert records[1].decision_text == "취업승인"


def test_masked_employment_review_name_never_creates_person_candidate() -> None:
    staged = stage_employment_review_rows(load_fixture("employment_reviews.json"))
    masked = staged[1]

    assert masked.record.person_name is None
    assert masked.candidate is None
    data = masked.to_dict()
    assert data["canonical_name"] is None
    assert data["identity_anchors"] == []
    assert data["identity_semantics"] == "PERSON_NAME_NOT_PUBLIC"

    partial = load_fixture("employment_reviews.json")[0] | {
        "record_id": "review-partial-mask",
        "person_name": "김○○",
    }
    assert stage_employment_review_rows([partial])[0].candidate is None


def test_employment_review_output_does_not_expose_private_fixture_fields_or_guilt_inference() -> None:
    careers = stage_personnel_rows(load_fixture("civil_service_personnel.json"))
    reviews = stage_employment_review_rows(load_fixture("employment_reviews.json"))
    rendered = render_civil_service_json(careers, reviews)
    semantics = str(reviews[0].to_dict()["employment_review"]["semantics"])

    assert "수집금지 주소" not in rendered
    assert "010-0000-0000" not in rendered
    assert "private@example.invalid" not in rendered
    assert "해석하지 않는다" in semantics
    assert "위반이다" not in semantics
    assert "부당취업이다" not in semantics


def test_unknown_review_text_fails_closed_to_unknown_without_rewriting_source_text() -> None:
    row = load_fixture("employment_reviews.json")[0] | {
        "record_id": "review-unknown",
        "decision": "추가검토",
    }
    record = parse_employment_review_rows([row])[0]

    assert record.decision == EmploymentReviewDecision.UNKNOWN
    assert record.decision_text == "추가검토"
