from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from urllib.parse import urlparse


class CompanyProfileRecordError(ValueError):
    pass


ELIGIBLE_PUBLIC_SCOPES = frozenset(
    {
        "CEO",
        "PRESIDENT",
        "REGISTERED_DIRECTOR",
        "CTO",
        "CSO",
        "CIO",
        "RESEARCH_INSTITUTE_HEAD",
        "TECH_CENTER_HEAD",
        "BUSINESS_UNIT_HEAD",
        "OTHER_PUBLIC_SENIOR_LEADER",
    }
)


@dataclass(frozen=True)
class CompanyOfficialSeniorProfileRecord:
    record_id: str
    person_name: str
    company_name: str
    title: str
    public_scope: str
    responsibility: str | None
    valid_from: date | None
    valid_to: date | None
    source_url: str
    source_domain: str
    source_ref: str
    source_policy_ref: str


def _required(row: dict, key: str) -> str:
    value = row.get(key)
    text = "" if value is None else str(value).strip()
    if not text:
        raise CompanyProfileRecordError(f"missing required field: {key}")
    return text


def _optional(row: dict, key: str) -> str | None:
    value = row.get(key)
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _date(row: dict, key: str) -> date | None:
    value = _optional(row, key)
    if value is None:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise CompanyProfileRecordError(f"invalid ISO date: {key}") from None


def parse_company_official_profile_rows(
    rows: list[dict],
) -> list[CompanyOfficialSeniorProfileRecord]:
    records: list[CompanyOfficialSeniorProfileRecord] = []
    for row in rows:
        scope = _required(row, "public_scope")
        if scope not in ELIGIBLE_PUBLIC_SCOPES:
            raise CompanyProfileRecordError("ordinary/non-senior company staff cannot enter feeder")
        source_url = _required(row, "source_url")
        parsed = urlparse(source_url)
        if parsed.scheme != "https" or not parsed.netloc:
            raise CompanyProfileRecordError("company official source_url must be HTTPS")
        source_domain = _required(row, "source_domain")
        if parsed.netloc != source_domain:
            raise CompanyProfileRecordError("company official source domain mismatch")
        policy_ref = _required(row, "source_policy_ref")
        if policy_ref in {"UNREVIEWED", "NONE", "UNKNOWN"}:
            raise CompanyProfileRecordError("company official profile requires reviewed SourcePolicy reference")
        valid_from = _date(row, "valid_from")
        valid_to = _date(row, "valid_to")
        if valid_from and valid_to and valid_to < valid_from:
            raise CompanyProfileRecordError("profile valid_to precedes valid_from")
        records.append(
            CompanyOfficialSeniorProfileRecord(
                record_id=_required(row, "record_id"),
                person_name=_required(row, "person_name"),
                company_name=_required(row, "company_name"),
                title=_required(row, "title"),
                public_scope=scope,
                responsibility=_optional(row, "responsibility"),
                valid_from=valid_from,
                valid_to=valid_to,
                source_url=source_url,
                source_domain=source_domain,
                source_ref=_required(row, "source_ref"),
                source_policy_ref=policy_ref,
            )
        )
    return records
