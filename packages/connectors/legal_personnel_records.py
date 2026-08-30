from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from uuid import UUID

from packages.domain.contracts import SourcePolicy
from packages.domain.enums import LegalCareerEventType, LegalCareerType, SourceCollectionMode


class LegalPersonnelRecordError(ValueError):
    pass


MOJ_POLICY_ID = UUID("15000000-0000-0000-0000-000000000001")
SCOURT_POLICY_ID = UUID("15000000-0000-0000-0000-000000000002")


def moj_prosecution_personnel_policy() -> SourcePolicy:
    reviewed_at = datetime(2026, 8, 30, tzinfo=UTC)
    return SourcePolicy(
        id=MOJ_POLICY_ID,
        domain="moj.go.kr",
        source_class="official_personnel_notice",
        collection_mode=SourceCollectionMode.HTTP,
        can_fetch=False,
        can_store_metadata=True,
        can_store_fulltext=False,
        can_send_to_ai=False,
        can_show_excerpt=False,
        can_commercialize=False,
        terms_checked_at=reviewed_at,
        license="공공누리 제2유형 notice observed on reviewed 2026-08-24 MOJ page",
        policy_note=(
            "Reviewed 2026-08-30 against Ministry of Justice prosecutor personnel releases. "
            "This PR accepts normalized personnel metadata only; live attachment collection "
            "and reuse rights require a source-specific adapter review."
        ),
    )


def supreme_court_personnel_policy() -> SourcePolicy:
    reviewed_at = datetime(2026, 8, 30, tzinfo=UTC)
    return SourcePolicy(
        id=SCOURT_POLICY_ID,
        domain="scourt.go.kr",
        source_class="official_personnel_notice",
        collection_mode=SourceCollectionMode.HTTP,
        can_fetch=False,
        can_store_metadata=True,
        can_store_fulltext=False,
        can_send_to_ai=False,
        can_show_excerpt=False,
        can_commercialize=False,
        terms_checked_at=reviewed_at,
        license="No blanket commercial/fulltext right assumed for Court personnel notices",
        policy_note=(
            "Reviewed 2026-08-30 against Supreme Court personnel release and Court Gazette "
            "personnel-order structure. Normalized appointment metadata only in V0."
        ),
    )


@dataclass(frozen=True)
class LegalPersonnelRecord:
    record_id: str
    person_name: str
    event_date: date
    career_type: LegalCareerType
    event_type: LegalCareerEventType
    organization: str
    title: str
    previous_organization: str | None
    previous_title: str | None
    public_assignment_domain: str | None
    order_text: str | None
    source_ref: str
    source_lane: str


_EVENT_MAP = {
    "임용": LegalCareerEventType.APPOINTMENT,
    "보임": LegalCareerEventType.APPOINTMENT,
    "신규보임": LegalCareerEventType.APPOINTMENT,
    "전보": LegalCareerEventType.TRANSFER,
    "승진": LegalCareerEventType.PROMOTION,
    "보직": LegalCareerEventType.ASSIGNMENT,
    "겸임": LegalCareerEventType.CONCURRENT_APPOINTMENT,
    "겸임해임": LegalCareerEventType.CONCURRENT_RELEASE,
    "퇴직": LegalCareerEventType.RETIREMENT,
}

_PROSECUTION_TYPE_MAP = {
    "검사": LegalCareerType.PROSECUTOR,
    "부부장검사": LegalCareerType.PROSECUTOR,
    "부장검사": LegalCareerType.CHIEF_PROSECUTOR,
    "지청장": LegalCareerType.CHIEF_PROSECUTOR,
    "차장검사": LegalCareerType.CHIEF_PROSECUTOR,
    "검사장": LegalCareerType.CHIEF_PROSECUTOR,
    "지검장": LegalCareerType.CHIEF_PROSECUTOR,
    "고검장": LegalCareerType.CHIEF_PROSECUTOR,
    "검찰총장": LegalCareerType.PROSECUTOR_GENERAL,
}


def _required(row: dict, key: str) -> str:
    value = row.get(key)
    text = "" if value is None else str(value).strip()
    if not text:
        raise LegalPersonnelRecordError(f"missing required field: {key}")
    return text


def _optional(row: dict, key: str) -> str | None:
    value = row.get(key)
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _date(row: dict, key: str) -> date:
    value = _required(row, key)
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise LegalPersonnelRecordError(f"invalid ISO date: {key}") from None


def _event_type(row: dict) -> LegalCareerEventType:
    text = _required(row, "event_type")
    try:
        return _EVENT_MAP[text]
    except KeyError:
        raise LegalPersonnelRecordError(f"unsupported legal personnel event: {text}") from None


def _prosecution_career_type(title: str) -> LegalCareerType:
    for token in ("검찰총장", "고검장", "지검장", "검사장", "차장검사", "지청장", "부장검사", "부부장검사", "검사"):
        if token in title:
            return _PROSECUTION_TYPE_MAP[token]
    if "법무부" in title:
        return LegalCareerType.MINISTRY_OF_JUSTICE_LEGAL_ROLE
    raise LegalPersonnelRecordError(f"unsupported prosecution title: {title}")


def _judicial_career_type(organization: str, title: str) -> LegalCareerType:
    if "대법관" in title:
        return LegalCareerType.SUPREME_COURT_JUSTICE
    if "법원장" in title:
        return LegalCareerType.COURT_PRESIDENT
    if "법원행정처" in organization or "법원행정처" in title:
        return LegalCareerType.JUDICIAL_ADMINISTRATION
    if "판사" in title:
        return LegalCareerType.JUDGE
    raise LegalPersonnelRecordError(f"unsupported judicial title: {title}")


def parse_moj_prosecution_rows(rows: list[dict]) -> list[LegalPersonnelRecord]:
    records: list[LegalPersonnelRecord] = []
    for row in rows:
        title = _required(row, "title")
        records.append(
            LegalPersonnelRecord(
                record_id=_required(row, "record_id"),
                person_name=_required(row, "person_name"),
                event_date=_date(row, "event_date"),
                career_type=_prosecution_career_type(title),
                event_type=_event_type(row),
                organization=_required(row, "organization"),
                title=title,
                previous_organization=_optional(row, "previous_organization"),
                previous_title=_optional(row, "previous_title"),
                public_assignment_domain=_optional(row, "public_assignment_domain"),
                order_text=_optional(row, "order_text"),
                source_ref=_required(row, "source_ref"),
                source_lane="MOJ_PROSECUTION_PERSONNEL",
            )
        )
    return records


def parse_supreme_court_rows(rows: list[dict]) -> list[LegalPersonnelRecord]:
    records: list[LegalPersonnelRecord] = []
    for row in rows:
        organization = _required(row, "organization")
        title = _required(row, "title")
        records.append(
            LegalPersonnelRecord(
                record_id=_required(row, "record_id"),
                person_name=_required(row, "person_name"),
                event_date=_date(row, "event_date"),
                career_type=_judicial_career_type(organization, title),
                event_type=_event_type(row),
                organization=organization,
                title=title,
                previous_organization=_optional(row, "previous_organization"),
                previous_title=_optional(row, "previous_title"),
                public_assignment_domain=_optional(row, "public_assignment_domain"),
                order_text=_optional(row, "order_text"),
                source_ref=_required(row, "source_ref"),
                source_lane="SUPREME_COURT_PERSONNEL",
            )
        )
    return records
