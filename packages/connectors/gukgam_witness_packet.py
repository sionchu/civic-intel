from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from typing import Any
from urllib.parse import parse_qs, urlparse

from packages.connectors.assembly_minutes import MINUTES_HOST, MINUTES_PDF_PATH

WITNESS_PACKET_SCHEMA = "gukgam-witness-reviewed-packet.v2"
REVIEW_REQUIRED = "REVIEW_REQUIRED"
HUMAN_REVIEWED = "HUMAN_REVIEWED"
WITNESS_REVIEW_STATUSES = frozenset({REVIEW_REQUIRED, HUMAN_REVIEWED})
WITNESS_AUTOMATION_GATE = "AUTOMATED_COMMITTEE_HTML_BLOCKED"
WITNESS_CATEGORIES = ("증인", "참고인")
# Images (photos/screenshots of a list) are accepted only as owner-supplied copies.
IMAGE_ARTIFACT_FORMATS = frozenset({"JPG", "PNG"})
ARTIFACT_FORMATS = frozenset({"PDF", "HWP", "HWPX", "XLSX"}) | IMAGE_ARTIFACT_FORMATS
# XLSX has no pages either: table_index is the sheet number and table_row the sheet row.
# An image is one page: table_index 1 and table_row the printed row order.
PAGELESS_ARTIFACT_FORMATS = frozenset({"HWP", "HWPX", "XLSX"}) | IMAGE_ARTIFACT_FORMATS
CHANNEL_OFFICIAL_SITE = "OFFICIAL_SITE"
CHANNEL_OWNER_SUPPLIED_COPY = "OWNER_SUPPLIED_COPY"
# The committee adopted the list in a full-committee meeting and the official minutes
# (record.assembly.go.kr) print it; the operator saved that exact minutes PDF.
CHANNEL_OFFICIAL_MINUTES = "OFFICIAL_MINUTES"
ACQUISITION_CHANNELS = frozenset(
    {CHANNEL_OFFICIAL_SITE, CHANNEL_OWNER_SUPPLIED_COPY, CHANNEL_OFFICIAL_MINUTES}
)
# Owner rule (2026-10-06): every owner-supplied copy, HWP or not, is "아직 공식 발표 아님".
OWNER_COPY_LABEL = "아직 공식 발표 아님 — 제공받은 사본"
SOURCE_TAG_OFFICIAL_SITE = "#공식게시"
SOURCE_TAG_OFFICIAL_MINUTES = "#공식회의록"
SOURCE_TAG_OWNER_DOCUMENT = "#제공사본_HWP"
SOURCE_TAG_OWNER_NON_DOCUMENT = "#제공사본_비HWP"


def witness_source_tag(channel: str, artifact_format: str | None) -> str:
    """Owner-defined source tag: two official tags and two not-yet-official copy tags."""

    if channel == CHANNEL_OFFICIAL_SITE:
        return SOURCE_TAG_OFFICIAL_SITE
    if channel == CHANNEL_OFFICIAL_MINUTES:
        return SOURCE_TAG_OFFICIAL_MINUTES
    if artifact_format in IMAGE_ARTIFACT_FORMATS:
        return SOURCE_TAG_OWNER_NON_DOCUMENT
    return SOURCE_TAG_OWNER_DOCUMENT

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_LIST_VERSION = re.compile(r"^[0-9A-Za-z가-힣._-]{1,64}$")
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_PHONE = re.compile(r"\d{2,4}[-.\s]\d{3,4}[-.\s]\d{4}")
# "10. 7." / "10.7" / "2026. 10. 7." (leading text only; trailing weekday/time is ignored)
_PRINTED_DATE = re.compile(r"^\s*(?:(\d{4})\s*[.\-/]\s*)?(\d{1,2})\s*[.\-/]\s*(\d{1,2})(?!\d)")


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


def _optional_positive_int(value: object, field: str) -> int | None:
    if value is None:
        return None
    return _positive_int(value, field)


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


def _official_minutes_pdf_url(value: object, field: str) -> str:
    url = _required_text(value, field)
    parsed = urlparse(url)
    query = parse_qs(parsed.query, keep_blank_values=True)
    if (
        parsed.scheme != "https"
        or parsed.hostname != MINUTES_HOST
        or parsed.path != MINUTES_PDF_PATH
        or parsed.username
        or parsed.password
        or parsed.fragment
        or set(query) != {"id"}
        or not query["id"][0].isdigit()
    ):
        raise GukgamWitnessPacketError(
            f"witness packet {field} must be the exact official minutes pdf.do?id=<n> URL"
        )
    return url


@dataclass(frozen=True)
class AssumedYear:
    """Year the packet declares for printed dates that carry no year, with its basis."""

    year: int
    basis: str

    @classmethod
    def from_mapping(cls, raw: object) -> AssumedYear:
        if not isinstance(raw, Mapping):
            raise GukgamWitnessPacketError("witness packet assumed_year is malformed")
        _exact_keys(raw, {"year", "basis"}, "witness packet assumed_year")
        year = _positive_int(raw.get("year"), "assumed_year.year")
        if not 2000 <= year <= 2100:
            raise GukgamWitnessPacketError("witness packet assumed_year.year is out of range")
        return cls(year=year, basis=_required_text(raw.get("basis"), "assumed_year.basis"))

    def normalized(self) -> dict[str, object]:
        return {"year": self.year, "basis": self.basis}


@dataclass(frozen=True)
class WitnessSource:
    committee_name: str
    acquisition_channel: str
    artifact_format: str
    artifact_sha256: str
    artifact_filename: str | None
    page_url: str | None
    attachment_url: str | None
    received_via: str | None
    received_at: date | None
    list_title: str
    list_version: str
    adoption_date: date | None
    assumed_year: AssumedYear | None
    rights_mark: str | None
    automation_gate: str

    @property
    def is_owner_supplied_copy(self) -> bool:
        return self.acquisition_channel == CHANNEL_OWNER_SUPPLIED_COPY

    @property
    def list_year(self) -> int:
        if self.adoption_date is not None:
            return self.adoption_date.year
        assert self.assumed_year is not None  # enforced by from_mapping
        return self.assumed_year.year

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> WitnessSource:
        _exact_keys(
            raw,
            {
                "committee_name",
                "acquisition_channel",
                "artifact_format",
                "artifact_sha256",
                "artifact_filename",
                "page_url",
                "attachment_url",
                "received_via",
                "received_at",
                "list_title",
                "list_version",
                "adoption_date",
                "assumed_year",
                "rights_mark",
                "automation_gate",
            },
            "witness packet source",
        )
        channel = _required_text(raw.get("acquisition_channel"), "source.acquisition_channel")
        if channel not in ACQUISITION_CHANNELS:
            raise GukgamWitnessPacketError("witness packet acquisition_channel is unsupported")
        artifact_format = _required_text(raw.get("artifact_format"), "source.artifact_format")
        if artifact_format not in ARTIFACT_FORMATS:
            raise GukgamWitnessPacketError("witness packet artifact_format is unsupported")
        if artifact_format in IMAGE_ARTIFACT_FORMATS and channel != CHANNEL_OWNER_SUPPLIED_COPY:
            raise GukgamWitnessPacketError(
                "witness packet image artifacts are accepted only as OWNER_SUPPLIED_COPY"
            )
        sha256 = _required_text(raw.get("artifact_sha256"), "source.artifact_sha256")
        if not _SHA256.fullmatch(sha256):
            raise GukgamWitnessPacketError("witness packet artifact_sha256 is invalid")
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

        page_url = (
            _official_https_url(raw["page_url"], "source.page_url")
            if raw.get("page_url") is not None
            else None
        )
        if channel == CHANNEL_OFFICIAL_MINUTES:
            attachment_url: str | None = _official_minutes_pdf_url(
                raw.get("attachment_url"), "source.attachment_url"
            )
        else:
            attachment_url = (
                _official_https_url(raw["attachment_url"], "source.attachment_url")
                if raw.get("attachment_url") is not None
                else None
            )
        if channel != CHANNEL_OFFICIAL_MINUTES and page_url and attachment_url and (
            urlparse(page_url).hostname != urlparse(attachment_url).hostname
        ):
            raise GukgamWitnessPacketError(
                "witness packet attachment must be on the same official host as the page"
            )
        filename = _optional_text(raw.get("artifact_filename"), "source.artifact_filename")
        received_via = _optional_text(raw.get("received_via"), "source.received_via")
        received_at = _optional_iso_date(raw.get("received_at"), "source.received_at")
        adoption_date = _optional_iso_date(raw.get("adoption_date"), "source.adoption_date")
        assumed_raw = raw.get("assumed_year")
        assumed_year = AssumedYear.from_mapping(assumed_raw) if assumed_raw is not None else None

        if channel == CHANNEL_OFFICIAL_SITE:
            if page_url is None or attachment_url is None:
                raise GukgamWitnessPacketError(
                    "witness packet OFFICIAL_SITE requires page_url and attachment_url"
                )
            if filename is None:
                raise GukgamWitnessPacketError("witness packet lacks source.artifact_filename")
            if adoption_date is None:
                raise GukgamWitnessPacketError("witness packet lacks source.adoption_date")
            if received_via is not None or received_at is not None:
                raise GukgamWitnessPacketError(
                    "witness packet received_via/received_at apply to OWNER_SUPPLIED_COPY only"
                )
        elif channel == CHANNEL_OFFICIAL_MINUTES:
            if artifact_format != "PDF":
                raise GukgamWitnessPacketError("witness packet OFFICIAL_MINUTES must be a PDF")
            if page_url is not None:
                raise GukgamWitnessPacketError(
                    "witness packet OFFICIAL_MINUTES carries the minutes PDF URL only"
                )
            if filename is None:
                raise GukgamWitnessPacketError("witness packet lacks source.artifact_filename")
            if adoption_date is None:
                raise GukgamWitnessPacketError(
                    "witness packet OFFICIAL_MINUTES requires the meeting date as adoption_date"
                )
            if received_via is not None or received_at is not None:
                raise GukgamWitnessPacketError(
                    "witness packet received_via/received_at apply to OWNER_SUPPLIED_COPY only"
                )
        else:
            if received_via is None:
                raise GukgamWitnessPacketError("witness packet lacks source.received_via")
            if received_at is None:
                raise GukgamWitnessPacketError("witness packet lacks source.received_at")
            if adoption_date is None and assumed_year is None:
                raise GukgamWitnessPacketError(
                    "witness packet needs adoption_date or assumed_year to fix the list year"
                )
        if (
            adoption_date is not None
            and assumed_year is not None
            and adoption_date.year != assumed_year.year
        ):
            raise GukgamWitnessPacketError(
                "witness packet assumed_year conflicts with adoption_date"
            )
        return cls(
            committee_name=_required_text(
                raw.get("committee_name"), "source.committee_name"
            ),
            acquisition_channel=channel,
            artifact_format=artifact_format,
            artifact_sha256=sha256,
            artifact_filename=filename,
            page_url=page_url,
            attachment_url=attachment_url,
            received_via=received_via,
            received_at=received_at,
            list_title=_required_text(raw.get("list_title"), "source.list_title"),
            list_version=list_version,
            adoption_date=adoption_date,
            assumed_year=assumed_year,
            rights_mark=_optional_text(raw.get("rights_mark"), "source.rights_mark"),
            automation_gate=WITNESS_AUTOMATION_GATE,
        )

    def normalized(self) -> dict[str, object]:
        return {
            "committee_name": self.committee_name,
            "acquisition_channel": self.acquisition_channel,
            "artifact_format": self.artifact_format,
            "artifact_sha256": self.artifact_sha256,
            "artifact_filename": self.artifact_filename,
            "page_url": self.page_url,
            "attachment_url": self.attachment_url,
            "received_via": self.received_via,
            "received_at": self.received_at.isoformat() if self.received_at else None,
            "list_title": self.list_title,
            "list_version": self.list_version,
            "adoption_date": self.adoption_date.isoformat() if self.adoption_date else None,
            "assumed_year": self.assumed_year.normalized() if self.assumed_year else None,
            "rights_mark": self.rights_mark,
            "automation_gate": self.automation_gate,
        }


@dataclass(frozen=True)
class WitnessRowLocator:
    page_number: int | None
    table_index: int
    table_row: int

    def normalized(self) -> dict[str, int | None]:
        return {
            "page_number": self.page_number,
            "table_index": self.table_index,
            "table_row": self.table_row,
        }


def derive_attendance_date(
    text: str | None, assumed_year: AssumedYear | None
) -> date | None:
    """Derive an ISO date from printed text only with a printed or declared year."""

    if text is None:
        return None
    match = _PRINTED_DATE.match(text)
    if match is None:
        return None
    printed_year, month, day = match.groups()
    if printed_year is not None:
        year = int(printed_year)
    elif assumed_year is not None:
        year = assumed_year.year
    else:
        return None
    try:
        return date(year, int(month), int(day))
    except ValueError:
        raise GukgamWitnessPacketError(
            "witness packet row.attendance_date_text is not a valid date"
        ) from None


@dataclass(frozen=True)
class WitnessRow:
    row_number: int
    category: str
    name: str
    affiliation_title: str | None
    list_section: str | None
    attendance_date_text: str | None
    attendance_date: date | None
    target_institution: str | None
    request_reason_text: str | None
    locator: WitnessRowLocator

    @classmethod
    def from_mapping(
        cls,
        raw: Mapping[str, Any],
        *,
        artifact_format: str,
        assumed_year: AssumedYear | None,
    ) -> WitnessRow:
        _exact_keys(
            raw,
            {
                "row_number",
                "category",
                "name",
                "affiliation_title",
                "list_section",
                "attendance_date_text",
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
        page_number = _optional_positive_int(locator_raw.get("page_number"), "locator.page_number")
        if page_number is None and artifact_format not in PAGELESS_ARTIFACT_FORMATS:
            raise GukgamWitnessPacketError(
                "witness packet locator.page_number is required for PDF artifacts"
            )
        text = _optional_text(raw.get("attendance_date_text"), "row.attendance_date_text")
        explicit = _optional_iso_date(raw.get("attendance_date"), "row.attendance_date")
        derived = derive_attendance_date(text, assumed_year)
        if explicit is not None and text is not None:
            if derived is None:
                raise GukgamWitnessPacketError(
                    "witness packet row.attendance_date needs a printed year or assumed_year"
                )
            if derived != explicit:
                raise GukgamWitnessPacketError(
                    "witness packet row.attendance_date differs from attendance_date_text"
                )
        attendance_date = explicit or derived
        return cls(
            row_number=_positive_int(raw.get("row_number"), "row.row_number"),
            category=category,
            name=_required_text(raw.get("name"), "row.name"),
            affiliation_title=_optional_text(
                raw.get("affiliation_title"), "row.affiliation_title"
            ),
            list_section=_optional_text(raw.get("list_section"), "row.list_section"),
            attendance_date_text=text,
            attendance_date=attendance_date,
            target_institution=_optional_text(
                raw.get("target_institution"), "row.target_institution"
            ),
            request_reason_text=_optional_text(
                raw.get("request_reason_text"), "row.request_reason_text"
            ),
            locator=WitnessRowLocator(
                page_number=page_number,
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
            "attendance_date_text": self.attendance_date_text,
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
        """year + committee + list version + row number; never a name."""

        return (
            f"{self.source.list_year}:{self.source.committee_name}:"
            f"{self.source.list_version}:{row.row_number}"
        )

    @property
    def scope_key(self) -> str:
        return (
            f"{self.source.list_year}:{self.source.committee_name}:"
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

    source = WitnessSource.from_mapping(source_raw)
    rows: list[WitnessRow] = []
    for item in rows_raw:
        if not isinstance(item, Mapping):
            raise GukgamWitnessPacketError("witness packet row is malformed")
        rows.append(
            WitnessRow.from_mapping(
                item,
                artifact_format=source.artifact_format,
                assumed_year=source.assumed_year,
            )
        )
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
        source=source,
        declared_totals=totals,
        rows=tuple(rows),
    )
