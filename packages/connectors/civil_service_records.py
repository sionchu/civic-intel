from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from packages.domain.enums import (
    CivilServiceAppointmentRoute,
    CivilServiceCategory,
    CivilServiceEventType,
    EmploymentReviewDecision,
)


class CivilServiceRecordError(ValueError):
    pass


ELIGIBLE_PUBLIC_SCOPES = frozenset({"SENIOR_DECISION_MAKER", "PATH_RELEVANT_NAMED_ROLE"})

_CATEGORY_MAP = {
    "중앙일반직": CivilServiceCategory.CENTRAL_GENERAL,
    "지방일반직": CivilServiceCategory.LOCAL_GENERAL,
    "외무": CivilServiceCategory.FOREIGN_SERVICE,
    "경찰": CivilServiceCategory.POLICE,
    "소방": CivilServiceCategory.FIRE,
    "세무": CivilServiceCategory.TAX,
    "관세": CivilServiceCategory.CUSTOMS,
    "감사": CivilServiceCategory.AUDIT,
    "교정": CivilServiceCategory.CORRECTIONS,
    "출입국": CivilServiceCategory.IMMIGRATION,
    "기타특정직": CivilServiceCategory.OTHER_SPECIFIC,
}

_EVENT_MAP = {
    "임용": CivilServiceEventType.APPOINTMENT,
    "승진": CivilServiceEventType.PROMOTION,
    "전보": CivilServiceEventType.TRANSFER,
    "전출입": CivilServiceEventType.SECONDMENT,
    "파견": CivilServiceEventType.DISPATCH,
    "퇴직": CivilServiceEventType.RETIREMENT,
}

_ROUTE_MAP = {
    "일반": CivilServiceAppointmentRoute.REGULAR,
    "고위공무원단": CivilServiceAppointmentRoute.SENIOR_CIVIL_SERVICE,
    "개방형직위": CivilServiceAppointmentRoute.OPEN_POSITION,
    "공모직위": CivilServiceAppointmentRoute.COMPETITIVE_POSITION,
    "임기제": CivilServiceAppointmentRoute.FIXED_TERM,
    "경력개방": CivilServiceAppointmentRoute.EXTERNAL_CAREER,
}

_REVIEW_MAP = {
    "취업가능": EmploymentReviewDecision.EMPLOYABLE,
    "취업승인": EmploymentReviewDecision.APPROVED,
    "취업제한": EmploymentReviewDecision.RESTRICTED,
    "취업불승인": EmploymentReviewDecision.DISAPPROVED,
}

_MASK_CHARS = frozenset({"○", "●", "*", "＊", "□", "■"})


@dataclass(frozen=True)
class CivilServicePersonnelRecord:
    record_id: str
    person_name: str
    event_date: date
    category: CivilServiceCategory
    event_type: CivilServiceEventType
    appointment_route: CivilServiceAppointmentRoute
    organization: str
    title: str
    grade: str | None
    previous_organization: str | None
    previous_title: str | None
    source_ref: str
    public_scope: str


@dataclass(frozen=True)
class RetiredOfficialEmploymentReviewRecord:
    record_id: str
    person_name: str | None
    review_date: date
    former_organization: str
    former_title: str | None
    destination_organization: str
    destination_title: str | None
    decision: EmploymentReviewDecision
    decision_text: str
    employment_start_date: date | None
    source_ref: str


def _required(row: dict, key: str) -> str:
    value = row.get(key)
    text = "" if value is None else str(value).strip()
    if not text:
        raise CivilServiceRecordError(f"missing required field: {key}")
    return text


def _optional(row: dict, key: str) -> str | None:
    value = row.get(key)
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _date(row: dict, key: str, *, required: bool = True) -> date | None:
    value = _optional(row, key)
    if value is None:
        if required:
            raise CivilServiceRecordError(f"missing required field: {key}")
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise CivilServiceRecordError(f"invalid ISO date: {key}") from None


def _public_person_name(row: dict) -> str | None:
    value = _optional(row, "person_name")
    if value is None:
        return None
    compact = "".join(value.split())
    if not compact or all(char in _MASK_CHARS for char in compact):
        return None
    if any(char in _MASK_CHARS for char in compact):
        return None
    return value


def parse_personnel_notice_rows(rows: list[dict]) -> list[CivilServicePersonnelRecord]:
    records: list[CivilServicePersonnelRecord] = []
    for row in rows:
        public_scope = _required(row, "public_scope")
        if public_scope not in ELIGIBLE_PUBLIC_SCOPES:
            raise CivilServiceRecordError("ordinary/non-public-interest staff cannot enter feeder")
        category_text = _required(row, "service_category")
        event_text = _required(row, "event_type")
        route_text = _required(row, "appointment_route")
        try:
            category = _CATEGORY_MAP[category_text]
            event_type = _EVENT_MAP[event_text]
            route = _ROUTE_MAP[route_text]
        except KeyError as exc:
            raise CivilServiceRecordError(f"unsupported civil-service code: {exc.args[0]}") from None
        event_date = _date(row, "event_date")
        assert event_date is not None
        records.append(
            CivilServicePersonnelRecord(
                record_id=_required(row, "record_id"),
                person_name=_required(row, "person_name"),
                event_date=event_date,
                category=category,
                event_type=event_type,
                appointment_route=route,
                organization=_required(row, "organization"),
                title=_required(row, "title"),
                grade=_optional(row, "grade"),
                previous_organization=_optional(row, "previous_organization"),
                previous_title=_optional(row, "previous_title"),
                source_ref=_required(row, "source_ref"),
                public_scope=public_scope,
            )
        )
    return records


def parse_employment_review_rows(rows: list[dict]) -> list[RetiredOfficialEmploymentReviewRecord]:
    records: list[RetiredOfficialEmploymentReviewRecord] = []
    for row in rows:
        decision_text = _required(row, "decision")
        decision = _REVIEW_MAP.get(decision_text, EmploymentReviewDecision.UNKNOWN)
        review_date = _date(row, "review_date")
        assert review_date is not None
        records.append(
            RetiredOfficialEmploymentReviewRecord(
                record_id=_required(row, "record_id"),
                person_name=_public_person_name(row),
                review_date=review_date,
                former_organization=_required(row, "former_organization"),
                former_title=_optional(row, "former_title"),
                destination_organization=_required(row, "destination_organization"),
                destination_title=_optional(row, "destination_title"),
                decision=decision,
                decision_text=decision_text,
                employment_start_date=_date(row, "employment_start_date", required=False),
                source_ref=_required(row, "source_ref"),
            )
        )
    return records
