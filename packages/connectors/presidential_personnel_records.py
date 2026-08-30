from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from uuid import UUID

from packages.domain.contracts import SourcePolicy
from packages.domain.enums import (
    InstitutionalBodyType,
    PresidentialPersonnelAction,
    PresidentialRoleScope,
    SourceCollectionMode,
)


class PresidentialPersonnelRecordError(ValueError):
    pass


POLICY_ID = UUID("17000000-0000-0000-0000-000000000001")
_MASK_CHARS = frozenset({"○", "●", "*", "＊", "□", "■"})


def presidential_personnel_policy() -> SourcePolicy:
    reviewed_at = datetime(2026, 8, 30, tzinfo=UTC)
    return SourcePolicy(
        id=POLICY_ID,
        domain="president.go.kr",
        source_class="official_presidential_personnel_release",
        collection_mode=SourceCollectionMode.HTTP,
        can_fetch=False,
        can_store_metadata=True,
        can_store_fulltext=False,
        can_send_to_ai=False,
        can_show_excerpt=False,
        can_commercialize=False,
        terms_checked_at=reviewed_at,
        license="No blanket fulltext/commercial reuse right assumed; normalized metadata only",
        policy_note=(
            "Reviewed 2026-08-30 against the official Presidential Office organization page "
            "and personnel briefings. V0 accepts normalized public personnel metadata only; "
            "live page collection requires a source-specific adapter review."
        ),
    )


_ACTION_MAP = {
    "임명": PresidentialPersonnelAction.APPOINTED,
    "지명": PresidentialPersonnelAction.NOMINATED,
    "내정": PresidentialPersonnelAction.DESIGNATED,
    "위촉": PresidentialPersonnelAction.COMMISSIONED,
    "보직": PresidentialPersonnelAction.ASSIGNED,
    "겸임": PresidentialPersonnelAction.ASSIGNED,
    "해촉": PresidentialPersonnelAction.RELEASED,
    "면직": PresidentialPersonnelAction.RELEASED,
    "사임수리": PresidentialPersonnelAction.RELEASED,
}

_SCOPE_MAP = {
    "대통령비서실": PresidentialRoleScope.PRESIDENTIAL_SECRETARIAT,
    "국가안보실": PresidentialRoleScope.NATIONAL_SECURITY_OFFICE,
    "대통령특별보좌관": PresidentialRoleScope.SPECIAL_ADVISER,
    "대통령직속위원회": PresidentialRoleScope.PRESIDENTIAL_COMMISSION,
    "대통령직속TF": PresidentialRoleScope.PRESIDENTIAL_TASK_FORCE,
}

_BODY_TYPE_MAP = {
    PresidentialRoleScope.PRESIDENTIAL_COMMISSION: InstitutionalBodyType.PRESIDENTIAL_COMMISSION,
    PresidentialRoleScope.PRESIDENTIAL_TASK_FORCE: InstitutionalBodyType.TASK_FORCE,
}


@dataclass(frozen=True)
class PresidentialPersonnelRecord:
    record_id: str
    person_name: str | None
    event_date: date
    action: PresidentialPersonnelAction
    action_text: str
    role_scope: PresidentialRoleScope
    organization: str
    role: str
    institutional_body_type: InstitutionalBodyType | None
    reported_prior_careers: tuple[str, ...]
    source_ref: str
    record_kind: str



def _required(row: dict, key: str) -> str:
    value = row.get(key)
    text = "" if value is None else str(value).strip()
    if not text:
        raise PresidentialPersonnelRecordError(f"missing required field: {key}")
    return text



def _optional(row: dict, key: str) -> str | None:
    value = row.get(key)
    if value is None:
        return None
    text = str(value).strip()
    return text or None



def _public_person_name(row: dict) -> str | None:
    value = _optional(row, "person_name")
    if value is None:
        return None
    compact = "".join(value.split())
    if not compact or any(char in _MASK_CHARS for char in compact):
        return None
    if value in {"미정", "미상", "공석", "-"}:
        return None
    return value



def _date(row: dict, key: str) -> date:
    value = _required(row, key)
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise PresidentialPersonnelRecordError(f"invalid ISO date: {key}") from None



def _prior_careers(row: dict) -> tuple[str, ...]:
    value = row.get("reported_prior_careers")
    if value is None:
        return ()
    if isinstance(value, list):
        return tuple(text for item in value if (text := str(item).strip()))
    text = str(value).strip()
    if not text:
        return ()
    return tuple(part.strip() for part in text.split("\n") if part.strip())



def parse_presidential_personnel_rows(rows: list[dict]) -> list[PresidentialPersonnelRecord]:
    records: list[PresidentialPersonnelRecord] = []
    for row in rows:
        record_kind = _required(row, "record_kind")
        if record_kind != "PERSONNEL_ACTION":
            raise PresidentialPersonnelRecordError(
                "meeting attendance or non-personnel records cannot enter personnel feeder"
            )

        action_text = _required(row, "action")
        scope_text = _required(row, "role_scope")
        try:
            action = _ACTION_MAP[action_text]
        except KeyError:
            raise PresidentialPersonnelRecordError(
                f"unsupported presidential personnel action: {action_text}"
            ) from None
        try:
            scope = _SCOPE_MAP[scope_text]
        except KeyError:
            raise PresidentialPersonnelRecordError(
                f"unsupported presidential role scope: {scope_text}"
            ) from None

        records.append(
            PresidentialPersonnelRecord(
                record_id=_required(row, "record_id"),
                person_name=_public_person_name(row),
                event_date=_date(row, "event_date"),
                action=action,
                action_text=action_text,
                role_scope=scope,
                organization=_required(row, "organization"),
                role=_required(row, "role"),
                institutional_body_type=_BODY_TYPE_MAP.get(scope),
                reported_prior_careers=_prior_careers(row),
                source_ref=_required(row, "source_ref"),
                record_kind=record_kind,
            )
        )
    return records
