from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from uuid import UUID

from packages.domain.contracts import SourcePolicy
from packages.domain.enums import SourceCollectionMode


class LaborUnionRecordError(ValueError):
    pass


POLICY_ID = UUID("16000000-0000-0000-0000-000000000001")
_MASK_CHARS = frozenset({"○", "●", "*", "＊", "□", "■"})


def nationwide_labor_union_policy() -> SourcePolicy:
    reviewed_at = datetime(2026, 8, 30, tzinfo=UTC)
    return SourcePolicy(
        id=POLICY_ID,
        domain="data.go.kr",
        source_class="official_standard_dataset",
        collection_mode=SourceCollectionMode.API,
        can_fetch=False,
        can_store_metadata=True,
        can_store_fulltext=False,
        can_send_to_ai=False,
        can_show_excerpt=False,
        can_commercialize=False,
        terms_checked_at=reviewed_at,
        license="Nationwide standard dataset available as CSV/XML/JSON; item-level reuse terms pending adapter review",
        policy_note=(
            "Reviewed 2026-08-30 against 전국노동조합표준데이터 fields. V0 stages only "
            "union organization metadata and explicitly public representative names; address, "
            "telephone and coordinates are discarded. No ordinary membership data is allowed."
        ),
    )


@dataclass(frozen=True)
class LaborOrganizationRecord:
    record_id: str
    union_name: str
    union_form: str | None
    established_date: date | None
    affiliated_federation: str | None
    representative_name: str | None
    membership_count: int | None
    workplace_name: str | None
    as_of: date
    source_ref: str


def _required(row: dict, key: str) -> str:
    value = row.get(key)
    text = "" if value is None else str(value).strip()
    if not text:
        raise LaborUnionRecordError(f"missing required field: {key}")
    return text


def _optional(row: dict, key: str) -> str | None:
    value = row.get(key)
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _optional_date(row: dict, key: str) -> date | None:
    value = _optional(row, key)
    if value is None:
        return None
    normalized = value.replace(".", "-").replace("/", "-")
    try:
        return date.fromisoformat(normalized)
    except ValueError:
        raise LaborUnionRecordError(f"invalid date: {key}") from None


def _required_date(row: dict, key: str) -> date:
    value = _optional_date(row, key)
    if value is None:
        raise LaborUnionRecordError(f"missing required field: {key}")
    return value


def _membership_count(row: dict) -> int | None:
    value = _optional(row, "조합원수")
    if value is None:
        return None
    try:
        count = int(value.replace(",", ""))
    except ValueError:
        raise LaborUnionRecordError("invalid membership count") from None
    if count < 0:
        raise LaborUnionRecordError("membership count must be non-negative")
    return count


def _public_representative(value: str | None) -> str | None:
    if value is None:
        return None
    text = " ".join(value.split())
    compact = text.replace(" ", "")
    if not compact or any(char in _MASK_CHARS for char in compact):
        return None
    if text in {"없음", "미상", "공석", "-"}:
        return None
    return text


def parse_labor_union_rows(rows: list[dict]) -> list[LaborOrganizationRecord]:
    records: list[LaborOrganizationRecord] = []
    for row in rows:
        records.append(
            LaborOrganizationRecord(
                record_id=_required(row, "record_id"),
                union_name=_required(row, "노동조합명"),
                union_form=_optional(row, "노동조합형태"),
                established_date=_optional_date(row, "설립일자"),
                affiliated_federation=_optional(row, "소속연합단체명"),
                representative_name=_public_representative(_optional(row, "대표자명")),
                membership_count=_membership_count(row),
                workplace_name=_optional(row, "소속사업장명"),
                as_of=_required_date(row, "데이터기준일자"),
                source_ref=_required(row, "source_ref"),
            )
        )
    return records
