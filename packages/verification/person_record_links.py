"""Human-reviewed links from source-listed records to an existing canonical Person.

Gukgam witness rows and OpenDART executive-status rows carry no provider Person ID. They never
create, auto-link or merge a Person. An operator may link one exact row to one existing RESOLVED
Person through the admin LINK_PERSON transaction, and only after the deterministic anchor checks
below pass. The resulting Person Claim is a DRAFT, source-attributed CLAIM until a separate
PUBLISH action.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID

from packages.domain.contracts import Claim
from packages.domain.enums import EpistemicStatus, PublicationStatus

LINKED_WITNESS_PREDICATE = "LISTED_AS_GUKGAM_WITNESS"
LINKED_WITNESS_SOURCE_CONTRACT = "gukgam_witness_reviewed_person_link"
OPENDART_ROLE_PREDICATE = "OPENDART_DISCLOSED_EXECUTIVE_ROLE"
OPENDART_ROLE_SOURCE_CONTRACT = "opendart_reviewed_executive_role"
OPENDART_EXECUTIVE_FEEDER = "opendart_disclosed_executives"
OPENDART_EXECUTIVE_SEMANTIC_SCOPE = "corporate_executive_disclosure"
REVIEWED_BRIDGE_IDENTITY_SCOPE = "OPERATOR_REVIEWED_BRIDGE"
NO_PROVIDER_PERSON_ID = "NO_PROVIDER_PERSON_ID_HUMAN_REVIEW_REQUIRED"
COMPANY_DISCLOSED_CAREER_SEMANTICS = "company_disclosed_not_independently_verified"

# Witness Claim qualifiers that may reach the public Person surface. received_via/received_at,
# request reasons and the Organization-subject identity semantics are deliberately excluded.
LINKED_WITNESS_COPIED_QUALIFIERS = (
    "committee_name",
    "list_title",
    "list_version",
    "list_year",
    "adoption_date",
    "category",
    "affiliation_title",
    "list_section",
    "attendance_date_text",
    "attendance_date",
    "assumed_year_basis",
    "acquisition_channel",
    "source_tag",
    "provenance_label",
    "row_number",
    "page_number",
    "table_index",
    "table_row",
    "event_semantics",
)
# Disclosure fields copied to the corporate role Claim. Birth year/month stays an identity
# anchor on the observation; the largest-shareholder relation is a different fact.
OPENDART_COPIED_FIELDS = (
    "corp_code",
    "corp_name",
    "stock_code",
    "business_year",
    "report_code",
    "receipt_no",
    "settlement_date",
    "position",
    "registered_status",
    "full_time_status",
    "responsibility",
    "tenure_text",
    "tenure_end_on",
    "reported_main_career",
)

_LISTED_NAME = re.compile(r"\s*[(（][^)）]*[)）]\s*$")
_BIRTH_YEAR_MONTH = re.compile(r"^\s*(\d{4})\s*년\s*(\d{1,2})\s*월\s*$")


class PersonRecordLinkError(ValueError):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


def listed_name(value: str) -> str:
    """The listed Korean name without a trailing Hanja/annotation parenthetical."""

    return _LISTED_NAME.sub("", value).strip()


def birth_year_month(value: str | None) -> tuple[int, int] | None:
    match = _BIRTH_YEAR_MONTH.match(value or "")
    if match is None:
        return None
    year, month = int(match.group(1)), int(match.group(2))
    return (year, month) if 1 <= month <= 12 else None


def birth_year_month_conflict(birth_date: date | None, disclosed: str | None) -> bool:
    """True only when both sides are known and the year/month differ."""

    parsed = birth_year_month(disclosed)
    if birth_date is None or parsed is None:
        return False
    return (birth_date.year, birth_date.month) != parsed


def witness_institution_anchors(
    normalized: Mapping[str, Any], organization_names: Iterable[str]
) -> tuple[str, ...]:
    """Organization names of the target's own role Claims that the witness row states."""

    affiliation = str(normalized.get("affiliation_title") or "")
    target = str(normalized.get("target_institution") or "")
    return tuple(
        sorted(
            {
                name
                for name in organization_names
                if len(name.strip()) >= 2 and (name in affiliation or name == target)
            }
        )
    )


def _required(values: Mapping[str, Any], key: str) -> str:
    value = values.get(key)
    if not isinstance(value, str) or not value.strip():
        raise PersonRecordLinkError("SOURCE_RECORD_INCOMPLETE", f"원본 기록에 {key} 값이 없습니다.")
    return value.strip()


def build_linked_witness_claim(
    *,
    claim_id: UUID,
    person_id: UUID,
    person_name: str,
    witness_claim: Claim,
    observation_id: str,
    observation_hash: str,
    review_id: str,
    recorded_at: datetime,
) -> Claim:
    """A Person-subject Claim that one exact published witness-list row names this Person."""

    qualifiers = witness_claim.qualifiers
    committee = _required(qualifiers, "committee_name")
    category = _required(qualifiers, "category")
    list_title = _required(qualifiers, "list_title")
    list_version = _required(qualifiers, "list_version")
    copied = {
        key: qualifiers[key]
        for key in LINKED_WITNESS_COPIED_QUALIFIERS
        if isinstance(qualifiers.get(key), str) and qualifiers[key].strip()
    }
    return Claim(
        id=claim_id,
        person_id=person_id,
        subject=person_name,
        predicate=LINKED_WITNESS_PREDICATE,
        proposition=(
            f"{committee}의 {list_title}({list_version})은 {person_name}을 {category}으로 기재한다."
        ),
        object_text=f"{committee} · {category}",
        qualifiers={
            **copied,
            "source_contract": LINKED_WITNESS_SOURCE_CONTRACT,
            "source_claim_id": str(witness_claim.id),
            "source_observation_id": observation_id,
            "immutable_observation_hash": observation_hash,
            "identity_review_id": review_id,
            "identity_scope": REVIEWED_BRIDGE_IDENTITY_SCOPE,
        },
        epistemic_status=EpistemicStatus.CLAIM,
        publication_status=PublicationStatus.DRAFT,
        asserted_as_true=False,
        valid_from=witness_claim.valid_from,
        recorded_at=recorded_at,
    )


def build_opendart_role_claim(
    *,
    claim_id: UUID,
    person_id: UUID,
    person_name: str,
    normalized: Mapping[str, Any],
    observation_id: str,
    observation_hash: str,
    provider_observed_at: datetime | None,
    review_id: str,
    recorded_at: datetime,
) -> Claim:
    """"This company disclosed this Person in this role" — never an independent career FACT."""

    corp_name = _required(normalized, "corp_name")
    receipt_no = _required(normalized, "receipt_no")
    position = _required(normalized, "position")
    copied = {
        key: str(normalized[key]).strip()
        for key in OPENDART_COPIED_FIELDS
        if normalized.get(key) is not None and str(normalized[key]).strip()
    }
    if "reported_main_career" in copied:
        copied["reported_main_career_semantics"] = COMPANY_DISCLOSED_CAREER_SEMANTICS
    settlement = copied.get("settlement_date")
    valid_from = (
        datetime.combine(date.fromisoformat(settlement), datetime.min.time(), tzinfo=UTC)
        if settlement
        else provider_observed_at or recorded_at
    )
    return Claim(
        id=claim_id,
        person_id=person_id,
        subject=person_name,
        predicate=OPENDART_ROLE_PREDICATE,
        proposition=(
            f"{corp_name}의 OpenDART 임원 현황 공시(접수번호 {receipt_no})는 "
            f"{person_name}을 {position}으로 기재한다."
        ),
        object_text=f"{corp_name} · {position}",
        qualifiers={
            **copied,
            "source_contract": OPENDART_ROLE_SOURCE_CONTRACT,
            "source_observation_id": observation_id,
            "immutable_observation_hash": observation_hash,
            "identity_review_id": review_id,
            "identity_scope": REVIEWED_BRIDGE_IDENTITY_SCOPE,
        },
        epistemic_status=EpistemicStatus.CLAIM,
        publication_status=PublicationStatus.DRAFT,
        asserted_as_true=False,
        valid_from=valid_from,
        recorded_at=recorded_at,
    )
