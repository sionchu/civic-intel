from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from typing import Any
from urllib.parse import urlparse

WITNESS_PACKET_SCHEMA = "gukgam-witness-reviewed-packet.v1"
REVIEW_REQUIRED = "REVIEW_REQUIRED"
HUMAN_REVIEWED = "HUMAN_REVIEWED"
WITNESS_REVIEW_STATUSES = frozenset({REVIEW_REQUIRED, HUMAN_REVIEWED})
WITNESS_AUTOMATION_GATE = "AUTOMATED_COMMITTEE_HTML_BLOCKED"
WITNESS_CATEGORIES = ("증인", "참고인")
ATTACHMENT_TYPES = frozenset({"PDF", "HWP", "HWPX"})

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_LIST_VERSION = re.compile(r"^[0-9A-Za-z가-힣._-]{1,64}$")
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_PHONE = re.compile(r"\d{2,4}[-.\s]\d{3,4}[-.\s]\d{4}")


class GukgamWitnessPacketError(ValueError):
    """A reviewed Gukgam witness packet cannot be interpreted safely."""


def _exact_keys(payload: Mapping[str, Any], allowed: set[str], label: str) -> None:
    unknown = sorted(set(payload) - allowed)
    if unknown:
        raise GukgamWitnessPacketError(
            f"{label} contains unsupported fields: {', '.join(unknown)}"
        )


def _optional_text(value: object, field: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise GukgamWitnessPacketError(f"witness packet {field} must be text")
    text = value.strip()
    if not text:
        return None
    if _EMAIL.search(text) or _PHONE.search(text):
        raise GukgamWitnessPacketError(
            f"witness packet {field} must not contain contact details"
        )
    return text


def _required_text(value: object, field: str) -> str:
    text = _optional_text(value, field)
    if text is None:
        raise GukgamWitnessPacketError(f"witness packet lacks {field}")
    return text


def _positive_int(value: object, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise GukgamWitnessPacketError(f"witness packet {field} must be a positive integer")
    return value


def _iso_date(value: object, field: str) -> date:
    try:
        return date.fromisoformat(_required_text(value, field))
    except ValueError:
        raise GukgamWitnessPacketError(f"witness packet {field} is invalid") from None


def _optional_iso_date(value: object, field: str) -> date | None:
    if value is None:
        return None
    return _iso_date(value, field)


def _official_https_url(value: object, field: str) -> str:
    url = _required_text(value, field)
    parsed = urlparse(url)
    if (
        parsed.scheme != "https"
        or not (parsed.hostname or "").endswith(".na.go.kr")
        or parsed.username
        or parsed.password
    ):
        raise GukgamWitnessPacketError(
            f"witness packet {field} must be an official https *.na.go.kr URL"
        )
    lowered = parsed.query.casefold()
    if any(token in lowered for token in ("servicekey=", "authkey=", "token=", "key=")):
        raise GukgamWitnessPacketError(
            f"witness packet {field} must not contain credentials"
        )
    return url


@dataclass(frozen=True)
class WitnessSource:
    committee_name: str
    page_url: str
    attachment_url: str
    attachment_filename: str
    attachment_type: str
    attachment_sha256: str
    list_title: str
    list_version: str
    adoption_date: date
    rights_mark: str | None
    automation_gate: str

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> WitnessSource:
        _exact_keys(
            raw,
            {
                "committee_name",
                "page_url",
                "attachment_url",
                "attachment_filename",
                "attachment_type",
                "attachment_sha256",
                "list_title",
                "list_version",
                "adoption_date",
                "rights_mark",
                "automation_gate",
            },
            "witness packet source",
        )
        page_url = _official_https_url(raw.get("page_url"), "source.page_url")
        attachment_url = _official_https_url(
            raw.get("attachment_url"), "source.attachment_url"
        )
        if urlparse(page_url).hostname != urlparse(attachment_url).hostname:
            raise GukgamWitnessPacketError(
                "witness packet attachment must be on the same official host as the page"
            )
        attachment_type = _required_text(
            raw.get("attachment_type"), "source.attachment_type"
        )
        if attachment_type not in ATTACHMENT_TYPES:
            raise GukgamWitnessPacketError("witness packet attachment_type is unsupported")
        sha256 = _required_text(raw.get("attachment_sha256"), "source.attachment_sha256")
        if not _SHA256.fullmatch(sha256):
            raise GukgamWitnessPacketError("witness packet attachment_sha256 is invalid")
        list_version = _required_text(raw.get("list_version"), "source.list_version")
        if not _LIST_VERSION.fullmatch(list_version):
            raise GukgamWitnessPacketError("witness packet list_version is not key-safe")
        if (
            _required_text(raw.get("automation_gate"), "source.automation_gate")
            != WITNESS_AUTOMATION_GATE
        ):
            raise GukgamWitnessPacketError(
                "witness packet automation gate is not the reviewed blocked state"
            )
        return cls(
            committee_name=_required_text(
                raw.get("committee_name"), "source.committee_name"
            ),
            page_url=page_url,
            attachment_url=attachment_url,
            attachment_filename=_required_text(
                raw.get("attachment_filename"), "source.attachment_filename"
            ),
            attachment_type=attachment_type,
            attachment_sha256=sha256,
            list_title=_required_text(raw.get("list_title"), "source.list_title"),
            list_version=list_version,
            adoption_date=_iso_date(raw.get("adoption_date"), "source.adoption_date"),
            rights_mark=_optional_text(raw.get("rights_mark"), "source.rights_mark"),
            automation_gate=WITNESS_AUTOMATION_GATE,
        )

    def normalized(self) -> dict[str, object]:
        return {
            "committee_name": self.committee_name,
            "page_url": self.page_url,
            "attachment_url": self.attachment_url,
            "attachment_filename": self.attachment_filename,
            "attachment_type": self.attachment_type,
            "attachment_sha256": self.attachment_sha256,
            "list_title": self.list_title,
            "list_version": self.list_version,
            "adoption_date": self.adoption_date.isoformat(),
            "rights_mark": self.rights_mark,
            "automation_gate": self.automation_gate,
        }


@dataclass(frozen=True)
class WitnessRowLocator:
    page_number: int
    table_index: int
    table_row: int

    def normalized(self) -> dict[str, int]:
        return {
            "page_number": self.page_number,
            "table_index": self.table_index,
            "table_row": self.table_row,
        }


@dataclass(frozen=True)
class WitnessRow:
    row_number: int
    category: str
    name: str
    affiliation_title: str | None
    list_section: str | None
    attendance_date: date | None
    target_institution: str | None
    request_reason_text: str | None
    locator: WitnessRowLocator

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> WitnessRow:
        _exact_keys(
            raw,
            {
                "row_number",
                "category",
                "name",
                "affiliation_title",
                "list_section",
                "attendance_date",
                "target_institution",
                "request_reason_text",
                "locator",
            },
            "witness packet row",
        )
        category = _required_text(raw.get("category"), "row.category")
        if category not in WITNESS_CATEGORIES:
            raise GukgamWitnessPacketError("witness packet row category is unsupported")
        locator_raw = raw.get("locator")
        if not isinstance(locator_raw, Mapping):
            raise GukgamWitnessPacketError("witness packet row locator is malformed")
        _exact_keys(
            locator_raw, {"page_number", "table_index", "table_row"}, "witness row locator"
        )
        return cls(
            row_number=_positive_int(raw.get("row_number"), "row.row_number"),
            category=category,
            name=_required_text(raw.get("name"), "row.name"),
            affiliation_title=_optional_text(
                raw.get("affiliation_title"), "row.affiliation_title"
            ),
            list_section=_optional_text(raw.get("list_section"), "row.list_section"),
            attendance_date=_optional_iso_date(
                raw.get("attendance_date"), "row.attendance_date"
            ),
            target_institution=_optional_text(
                raw.get("target_institution"), "row.target_institution"
            ),
            request_reason_text=_optional_text(
                raw.get("request_reason_text"), "row.request_reason_text"
            ),
            locator=WitnessRowLocator(
                page_number=_positive_int(locator_raw.get("page_number"), "locator.page_number"),
                table_index=_positive_int(locator_raw.get("table_index"), "locator.table_index"),
                table_row=_positive_int(locator_raw.get("table_row"), "locator.table_row"),
            ),
        )

    def normalized(self) -> dict[str, object]:
        return {
            "row_number": self.row_number,
            "category": self.category,
            "name": self.name,
            "affiliation_title": self.affiliation_title,
            "list_section": self.list_section,
            "attendance_date": (
                self.attendance_date.isoformat() if self.attendance_date else None
            ),
            "target_institution": self.target_institution,
            "request_reason_text": self.request_reason_text,
            "locator": self.locator.normalized(),
        }


@dataclass(frozen=True)
class ReviewedGukgamWitnessPacket:
    review_status: str
    source: WitnessSource
    declared_totals: Mapping[str, int]
    rows: tuple[WitnessRow, ...]

    def normalized(self) -> dict[str, object]:
        return {
            "schema": WITNESS_PACKET_SCHEMA,
            "review_status": self.review_status,
            "source": self.source.normalized(),
            "declared_totals": dict(sorted(self.declared_totals.items())),
            "rows": [row.normalized() for row in self.rows],
        }

    @property
    def content_hash(self) -> str:
        canonical = json.dumps(
            self.normalized(), ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    @property
    def is_human_reviewed(self) -> bool:
        return self.review_status == HUMAN_REVIEWED

    def record_key(self, row: WitnessRow) -> str:
        """committee + list version + row number; never a name."""

        return (
            f"{self.source.adoption_date.year}:{self.source.committee_name}:"
            f"{self.source.list_version}:{row.row_number}"
        )

    @property
    def scope_key(self) -> str:
        return (
            f"{self.source.adoption_date.year}:{self.source.committee_name}:"
            f"{self.source.list_version}"
        )


def parse_reviewed_gukgam_witness_packet(
    raw: Mapping[str, Any],
) -> ReviewedGukgamWitnessPacket:
    _exact_keys(
        raw,
        {"schema", "review_status", "source", "declared_totals", "rows"},
        "witness packet",
    )
    if raw.get("schema") != WITNESS_PACKET_SCHEMA:
        raise GukgamWitnessPacketError("witness packet schema is unsupported")
    status = raw.get("review_status")
    if status not in WITNESS_REVIEW_STATUSES:
        raise GukgamWitnessPacketError("witness packet review_status is unsupported")
    source_raw = raw.get("source")
    rows_raw = raw.get("rows")
    if not isinstance(source_raw, Mapping) or not isinstance(rows_raw, list):
        raise GukgamWitnessPacketError("witness packet source/rows are malformed")
    totals_raw = raw.get("declared_totals", {})
    if not isinstance(totals_raw, Mapping):
        raise GukgamWitnessPacketError("witness packet declared_totals is malformed")
    totals: dict[str, int] = {}
    for key, value in totals_raw.items():
        if key not in WITNESS_CATEGORIES:
            raise GukgamWitnessPacketError("witness packet declared_totals key is unsupported")
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise GukgamWitnessPacketError("witness packet declared_totals value is invalid")
        totals[str(key)] = value

    rows: list[WitnessRow] = []
    for item in rows_raw:
        if not isinstance(item, Mapping):
            raise GukgamWitnessPacketError("witness packet row is malformed")
        rows.append(WitnessRow.from_mapping(item))
    numbers = [row.row_number for row in rows]
    if len(set(numbers)) != len(numbers) or numbers != sorted(numbers):
        raise GukgamWitnessPacketError(
            "witness packet row numbers must be unique and ordered"
        )
    locators = [
        (row.locator.page_number, row.locator.table_index, row.locator.table_row)
        for row in rows
    ]
    if len(set(locators)) != len(locators):
        raise GukgamWitnessPacketError("witness packet row locators must be unique")
    for category, expected in totals.items():
        actual = sum(1 for row in rows if row.category == category)
        if actual != expected:
            raise GukgamWitnessPacketError(
                f"witness packet {category} rows ({actual}) differ from declared total ({expected})"
            )
    return ReviewedGukgamWitnessPacket(
        review_status=str(status),
        source=WitnessSource.from_mapping(source_raw),
        declared_totals=totals,
        rows=tuple(rows),
    )
