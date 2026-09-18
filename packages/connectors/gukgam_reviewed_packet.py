from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from typing import Any
from urllib.parse import parse_qs, urlparse

PACKET_SCHEMA = "gukgam-plan-reviewed-packet.v1"
REVIEW_STATUS = "HUMAN_REVIEWED"
AUTOMATION_GATE = "AUTOMATED_COMMITTEE_HTML_BLOCKED"


class GukgamReviewedPacketError(ValueError):
    """A reviewed Gukgam packet cannot be interpreted safely."""


def _required_text(value: object, field: str) -> str:
    if value is None:
        raise GukgamReviewedPacketError(f"reviewed Gukgam packet lacks {field}")
    text = str(value).strip()
    if not text:
        raise GukgamReviewedPacketError(f"reviewed Gukgam packet has empty {field}")
    return text


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _exact_keys(payload: Mapping[str, Any], allowed: set[str], label: str) -> None:
    unknown = sorted(set(payload) - allowed)
    if unknown:
        raise GukgamReviewedPacketError(
            f"{label} contains unsupported fields: {', '.join(unknown)}"
        )


@dataclass(frozen=True)
class ReviewedGukgamSource:
    committee_name: str
    ntt_id: str
    detail_url: str
    title: str
    published_date: date
    atch_file_id: str
    file_sn: int
    attachment_filename: str
    rights_mark: str
    automation_gate: str

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> ReviewedGukgamSource:
        _exact_keys(
            raw,
            {
                "committee_name",
                "ntt_id",
                "detail_url",
                "title",
                "published_date",
                "atch_file_id",
                "file_sn",
                "attachment_filename",
                "rights_mark",
                "automation_gate",
            },
            "reviewed Gukgam source",
        )
        detail_url = _required_text(raw.get("detail_url"), "source.detail_url")
        parsed = urlparse(detail_url)
        if parsed.scheme != "https" or not (parsed.hostname or "").endswith(".na.go.kr"):
            raise GukgamReviewedPacketError(
                "reviewed Gukgam source must use an official https *.na.go.kr URL"
            )
        ntt_id = _required_text(raw.get("ntt_id"), "source.ntt_id")
        query = parse_qs(parsed.query)
        if query.get("nttId") != [ntt_id]:
            raise GukgamReviewedPacketError(
                "reviewed Gukgam source ntt_id does not match detail_url"
            )
        try:
            published_date = date.fromisoformat(
                _required_text(raw.get("published_date"), "source.published_date")
            )
        except ValueError:
            raise GukgamReviewedPacketError(
                "reviewed Gukgam source published_date is invalid"
            ) from None
        try:
            file_sn = int(raw.get("file_sn"))
        except (TypeError, ValueError):
            raise GukgamReviewedPacketError(
                "reviewed Gukgam source file_sn is invalid"
            ) from None
        if file_sn < 1:
            raise GukgamReviewedPacketError(
                "reviewed Gukgam source file_sn must be positive"
            )
        automation_gate = _required_text(
            raw.get("automation_gate"), "source.automation_gate"
        )
        if automation_gate != AUTOMATION_GATE:
            raise GukgamReviewedPacketError(
                "reviewed Gukgam source automation gate is not the reviewed blocked state"
            )
        return cls(
            committee_name=_required_text(
                raw.get("committee_name"), "source.committee_name"
            ),
            ntt_id=ntt_id,
            detail_url=detail_url,
            title=_required_text(raw.get("title"), "source.title"),
            published_date=published_date,
            atch_file_id=_required_text(
                raw.get("atch_file_id"), "source.atch_file_id"
            ),
            file_sn=file_sn,
            attachment_filename=_required_text(
                raw.get("attachment_filename"), "source.attachment_filename"
            ),
            rights_mark=_required_text(raw.get("rights_mark"), "source.rights_mark"),
            automation_gate=automation_gate,
        )

    def normalized(self) -> dict[str, object]:
        return {
            "committee_name": self.committee_name,
            "ntt_id": self.ntt_id,
            "detail_url": self.detail_url,
            "title": self.title,
            "published_date": self.published_date.isoformat(),
            "atch_file_id": self.atch_file_id,
            "file_sn": self.file_sn,
            "attachment_filename": self.attachment_filename,
            "rights_mark": self.rights_mark,
            "automation_gate": self.automation_gate,
        }


@dataclass(frozen=True)
class ReviewedGukgamScheduleRow:
    ordinal: int
    audit_date: date
    time_text: str | None
    venue: str | None
    section: str
    audited_targets: tuple[str, ...]
    page_number: int

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> ReviewedGukgamScheduleRow:
        _exact_keys(
            raw,
            {
                "ordinal",
                "audit_date",
                "time_text",
                "venue",
                "section",
                "audited_targets",
                "page_number",
            },
            "reviewed Gukgam schedule row",
        )
        try:
            ordinal = int(raw.get("ordinal"))
            page_number = int(raw.get("page_number"))
        except (TypeError, ValueError):
            raise GukgamReviewedPacketError(
                "reviewed Gukgam schedule ordinal/page_number is invalid"
            ) from None
        if ordinal < 1 or page_number < 1:
            raise GukgamReviewedPacketError(
                "reviewed Gukgam schedule ordinal/page_number must be positive"
            )
        try:
            audit_date = date.fromisoformat(
                _required_text(raw.get("audit_date"), "schedule.audit_date")
            )
        except ValueError:
            raise GukgamReviewedPacketError(
                "reviewed Gukgam schedule audit_date is invalid"
            ) from None
        targets_raw = raw.get("audited_targets")
        if not isinstance(targets_raw, list) or not targets_raw:
            raise GukgamReviewedPacketError(
                "reviewed Gukgam schedule requires audited_targets"
            )
        targets = tuple(
            _required_text(value, "schedule.audited_targets") for value in targets_raw
        )
        if len(set(targets)) != len(targets):
            raise GukgamReviewedPacketError(
                "reviewed Gukgam schedule audited_targets must be unique"
            )
        return cls(
            ordinal=ordinal,
            audit_date=audit_date,
            time_text=_optional_text(raw.get("time_text")),
            venue=_optional_text(raw.get("venue")),
            section=_required_text(raw.get("section"), "schedule.section"),
            audited_targets=targets,
            page_number=page_number,
        )

    def normalized(self) -> dict[str, object]:
        return {
            "ordinal": self.ordinal,
            "audit_date": self.audit_date.isoformat(),
            "time_text": self.time_text,
            "venue": self.venue,
            "section": self.section,
            "audited_targets": list(self.audited_targets),
            "page_number": self.page_number,
        }


@dataclass(frozen=True)
class ReviewedGukgamPlanPacket:
    source: ReviewedGukgamSource
    schedule: tuple[ReviewedGukgamScheduleRow, ...]
    witness_rows_included: bool

    def normalized(self) -> dict[str, object]:
        return {
            "schema": PACKET_SCHEMA,
            "review_status": REVIEW_STATUS,
            "source": self.source.normalized(),
            "schedule": [row.normalized() for row in self.schedule],
            "witness_rows_included": self.witness_rows_included,
        }

    @property
    def content_hash(self) -> str:
        canonical = json.dumps(
            self.normalized(),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def schedule_record_key(self, row: ReviewedGukgamScheduleRow) -> str:
        return (
            f"{self.source.ntt_id}:{self.source.atch_file_id}:"
            f"{self.source.file_sn}:schedule:{row.ordinal}"
        )


def parse_reviewed_gukgam_plan_packet(
    raw: Mapping[str, Any],
) -> ReviewedGukgamPlanPacket:
    _exact_keys(
        raw,
        {"schema", "review_status", "source", "schedule", "witness_rows_included"},
        "reviewed Gukgam packet",
    )
    if raw.get("schema") != PACKET_SCHEMA:
        raise GukgamReviewedPacketError("reviewed Gukgam packet schema is unsupported")
    if raw.get("review_status") != REVIEW_STATUS:
        raise GukgamReviewedPacketError("reviewed Gukgam packet is not human-reviewed")
    source_raw = raw.get("source")
    if not isinstance(source_raw, Mapping):
        raise GukgamReviewedPacketError("reviewed Gukgam packet source is malformed")
    schedule_raw = raw.get("schedule")
    if not isinstance(schedule_raw, list):
        raise GukgamReviewedPacketError("reviewed Gukgam packet schedule is malformed")
    witness_rows_included = raw.get("witness_rows_included")
    if not isinstance(witness_rows_included, bool):
        raise GukgamReviewedPacketError(
            "reviewed Gukgam packet witness_rows_included must be boolean"
        )
    if witness_rows_included:
        raise GukgamReviewedPacketError(
            "plan packet must not embed witness/reference-person rows"
        )

    schedule_rows: list[ReviewedGukgamScheduleRow] = []
    for row in schedule_raw:
        if not isinstance(row, Mapping):
            raise GukgamReviewedPacketError(
                "reviewed Gukgam schedule row is malformed"
            )
        schedule_rows.append(ReviewedGukgamScheduleRow.from_mapping(row))
    schedule = tuple(schedule_rows)
    ordinals = [row.ordinal for row in schedule]
    if len(set(ordinals)) != len(ordinals):
        raise GukgamReviewedPacketError(
            "reviewed Gukgam schedule ordinals must be unique"
        )
    if ordinals != sorted(ordinals):
        raise GukgamReviewedPacketError(
            "reviewed Gukgam schedule rows must be ordered by ordinal"
        )

    return ReviewedGukgamPlanPacket(
        source=ReviewedGukgamSource.from_mapping(source_raw),
        schedule=schedule,
        witness_rows_included=witness_rows_included,
    )
