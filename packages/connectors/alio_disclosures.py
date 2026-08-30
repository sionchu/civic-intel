from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from uuid import UUID

from packages.domain.contracts import SourcePolicy
from packages.domain.enums import (
    PublicInstitutionClassification,
    PublicInstitutionExecutiveKind,
    SourceCollectionMode,
)


class AlioRecordError(ValueError):
    pass


POLICY_ID = UUID("13000000-0000-0000-0000-000000000001")


def alio_public_institution_policy() -> SourcePolicy:
    """Reviewed metadata policy for ALIO public-institution disclosures.

    Live HTML/report collection stays disabled in this scope. The policy records the reviewed
    public-data rights and allows normalized metadata staging only.
    """

    reviewed_at = datetime(2026, 8, 30, tzinfo=UTC)
    return SourcePolicy(
        id=POLICY_ID,
        domain="alio.go.kr",
        source_class="official_structured_disclosure",
        collection_mode=SourceCollectionMode.HTTP,
        can_fetch=False,
        can_store_metadata=True,
        can_store_fulltext=False,
        can_send_to_ai=False,
        can_show_excerpt=False,
        can_commercialize=True,
        terms_checked_at=reviewed_at,
        license="이용허락범위 제한 없음 (공공데이터포털 공공기관 일반현황)",
        policy_note=(
            "Reviewed 2026-08-30 against ALIO disclosure items 4, 7-1 and 10 and the "
            "data.go.kr public-institution general dataset. Live report fetching remains "
            "disabled until a source-specific adapter contract is reviewed."
        ),
    )


_CLASSIFICATION_MAP = {
    "공기업": PublicInstitutionClassification.PUBLIC_CORPORATION,
    "준정부기관": PublicInstitutionClassification.QUASI_GOVERNMENT,
    "기타공공기관": PublicInstitutionClassification.OTHER_PUBLIC_INSTITUTION,
}

_EXECUTIVE_KIND_MAP = {
    "상임기관장": PublicInstitutionExecutiveKind.INSTITUTION_HEAD,
    "기관장": PublicInstitutionExecutiveKind.INSTITUTION_HEAD,
    "상임감사": PublicInstitutionExecutiveKind.STANDING_AUDITOR,
    "상임감사위원": PublicInstitutionExecutiveKind.STANDING_AUDITOR,
    "상임이사": PublicInstitutionExecutiveKind.STANDING_DIRECTOR,
    "비상임이사": PublicInstitutionExecutiveKind.NON_STANDING_DIRECTOR,
    "비상임이사(감사위원)": PublicInstitutionExecutiveKind.NON_STANDING_DIRECTOR,
    "비상임감사": PublicInstitutionExecutiveKind.NON_STANDING_AUDITOR,
}

_EXECUTIVE_REEMPLOYMENT_LABELS = frozenset({"임원", "기관장", "상임임원", "비상임임원"})
_MASK_CHARS = frozenset({"○", "●", "*", "＊", "□", "■"})


@dataclass(frozen=True)
class AlioInstitutionRecord:
    institution_code: str
    institution_name: str
    classification: PublicInstitutionClassification
    classification_text: str
    as_of: date
    source_ref: str


@dataclass(frozen=True)
class AlioExecutiveRecord:
    record_id: str
    institution_code: str
    institution_name: str
    classification: PublicInstitutionClassification
    classification_text: str
    person_name: str
    position_text: str
    title: str
    executive_kind: PublicInstitutionExecutiveKind
    term_start: date
    term_end: date | None
    reported_careers: tuple[str, ...]
    selection_procedure: str | None
    selection_rule: str | None
    as_of: date
    source_ref: str


@dataclass(frozen=True)
class AlioCompensationRecord:
    record_id: str
    institution_code: str
    institution_name: str
    classification: PublicInstitutionClassification
    executive_kind: PublicInstitutionExecutiveKind
    fiscal_year: int
    basis: str
    total_thousand_krw: int
    as_of: date
    source_ref: str


@dataclass(frozen=True)
class AlioReemploymentRecord:
    record_id: str
    institution_code: str
    institution_name: str
    person_name: str | None
    former_kind: str
    former_title: str | None
    retirement_date: date
    destination_organization: str
    reemployment_date: date
    relationship: str | None
    executive_person_scope: bool
    as_of: date
    source_ref: str


def _required(row: dict, key: str) -> str:
    value = row.get(key)
    text = "" if value is None else str(value).strip()
    if not text:
        raise AlioRecordError(f"missing required field: {key}")
    return text


def _optional(row: dict, key: str) -> str | None:
    value = row.get(key)
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _date_value(row: dict, key: str, *, required: bool = True) -> date | None:
    value = _optional(row, key)
    if value is None:
        if required:
            raise AlioRecordError(f"missing required field: {key}")
        return None
    normalized = value.replace("년", "-").replace("월", "-").replace("일", "")
    normalized = "-".join(part.strip() for part in normalized.replace(".", "-").split("-") if part.strip())
    try:
        if len(normalized) == 8 and normalized.isdigit():
            return date(int(normalized[:4]), int(normalized[4:6]), int(normalized[6:8]))
        parts = normalized.split("-")
        if len(parts) == 3:
            return date(int(parts[0]), int(parts[1]), int(parts[2]))
    except ValueError:
        pass
    raise AlioRecordError(f"invalid date: {key}")


def _classification(row: dict) -> tuple[PublicInstitutionClassification, str]:
    text = _required(row, "기관분류")
    normalized = text
    if "공기업" in text:
        normalized = "공기업"
    elif "준정부기관" in text:
        normalized = "준정부기관"
    elif "기타공공기관" in text:
        normalized = "기타공공기관"
    try:
        return _CLASSIFICATION_MAP[normalized], text
    except KeyError:
        raise AlioRecordError(f"unsupported public-institution classification: {text}") from None


def _executive_kind(value: str) -> PublicInstitutionExecutiveKind:
    normalized = value.strip()
    if normalized.startswith("상임기관장"):
        normalized = "상임기관장"
    elif normalized.startswith("상임감사위원"):
        normalized = "상임감사위원"
    elif normalized.startswith("상임감사"):
        normalized = "상임감사"
    elif normalized.startswith("상임이사"):
        normalized = "상임이사"
    elif normalized.startswith("비상임이사(감사위원)"):
        normalized = "비상임이사(감사위원)"
    elif normalized.startswith("비상임이사"):
        normalized = "비상임이사"
    elif normalized.startswith("비상임감사"):
        normalized = "비상임감사"
    try:
        return _EXECUTIVE_KIND_MAP[normalized]
    except KeyError:
        raise AlioRecordError(f"unsupported ALIO executive position: {value}") from None


def _public_name(value: str | None) -> str | None:
    if value is None:
        return None
    compact = "".join(value.split())
    if not compact or any(char in _MASK_CHARS for char in compact):
        return None
    return value.strip()


def _reported_careers(row: dict) -> tuple[str, ...]:
    raw = row.get("주요경력")
    if raw is None:
        return ()
    if isinstance(raw, list):
        return tuple(text for item in raw if (text := str(item).strip()))
    text = str(raw).strip()
    if not text:
        return ()
    return tuple(part.strip() for part in text.split("\n") if part.strip())


def parse_institution_rows(rows: list[dict]) -> list[AlioInstitutionRecord]:
    records: list[AlioInstitutionRecord] = []
    for row in rows:
        classification, classification_text = _classification(row)
        as_of = _date_value(row, "기준일")
        assert as_of is not None
        records.append(
            AlioInstitutionRecord(
                institution_code=_required(row, "기관코드"),
                institution_name=_required(row, "기관명"),
                classification=classification,
                classification_text=classification_text,
                as_of=as_of,
                source_ref=_required(row, "source_ref"),
            )
        )
    return records


def parse_executive_rows(rows: list[dict]) -> list[AlioExecutiveRecord]:
    records: list[AlioExecutiveRecord] = []
    for row in rows:
        classification, classification_text = _classification(row)
        position = _required(row, "직위")
        person_name = _public_name(_required(row, "성명"))
        if person_name is None:
            raise AlioRecordError("masked executive name cannot create an executive candidate")
        term_start = _date_value(row, "임기_시작일")
        term_end = _date_value(row, "임기_종료일", required=False)
        as_of = _date_value(row, "기준일")
        assert term_start is not None and as_of is not None
        records.append(
            AlioExecutiveRecord(
                record_id=_required(row, "record_id"),
                institution_code=_required(row, "기관코드"),
                institution_name=_required(row, "기관명"),
                classification=classification,
                classification_text=classification_text,
                person_name=person_name,
                position_text=position,
                title=_required(row, "직책"),
                executive_kind=_executive_kind(position),
                term_start=term_start,
                term_end=term_end,
                reported_careers=_reported_careers(row),
                selection_procedure=_optional(row, "선임절차"),
                selection_rule=_optional(row, "선임절차규정"),
                as_of=as_of,
                source_ref=_required(row, "source_ref"),
            )
        )
    return records


def parse_compensation_rows(rows: list[dict]) -> list[AlioCompensationRecord]:
    records: list[AlioCompensationRecord] = []
    for row in rows:
        classification, _ = _classification(row)
        year_text = _required(row, "연도")
        amount_text = _required(row, "합계_천원").replace(",", "")
        try:
            fiscal_year = int(year_text)
            total = int(amount_text)
        except ValueError:
            raise AlioRecordError("invalid ALIO compensation number") from None
        if fiscal_year < 1900 or total < 0:
            raise AlioRecordError("invalid ALIO compensation value")
        as_of = _date_value(row, "기준일")
        assert as_of is not None
        records.append(
            AlioCompensationRecord(
                record_id=_required(row, "record_id"),
                institution_code=_required(row, "기관코드"),
                institution_name=_required(row, "기관명"),
                classification=classification,
                executive_kind=_executive_kind(_required(row, "직위구분")),
                fiscal_year=fiscal_year,
                basis=_required(row, "기준"),
                total_thousand_krw=total,
                as_of=as_of,
                source_ref=_required(row, "source_ref"),
            )
        )
    return records


def parse_reemployment_rows(rows: list[dict]) -> list[AlioReemploymentRecord]:
    records: list[AlioReemploymentRecord] = []
    for row in rows:
        former_kind = _required(row, "구분")
        executive_scope = former_kind in _EXECUTIVE_REEMPLOYMENT_LABELS
        retirement_date = _date_value(row, "퇴직일")
        reemployment_date = _date_value(row, "재취업일")
        as_of = _date_value(row, "기준일")
        assert retirement_date is not None and reemployment_date is not None and as_of is not None
        person_name = _public_name(_optional(row, "퇴직_임직원명")) if executive_scope else None
        records.append(
            AlioReemploymentRecord(
                record_id=_required(row, "record_id"),
                institution_code=_required(row, "기관코드"),
                institution_name=_required(row, "기관명"),
                person_name=person_name,
                former_kind=former_kind,
                former_title=_optional(row, "직위_급"),
                retirement_date=retirement_date,
                destination_organization=_required(row, "재취업회사명"),
                reemployment_date=reemployment_date,
                relationship=_optional(row, "관계"),
                executive_person_scope=executive_scope and person_name is not None,
                as_of=as_of,
                source_ref=_required(row, "source_ref"),
            )
        )
    return records
