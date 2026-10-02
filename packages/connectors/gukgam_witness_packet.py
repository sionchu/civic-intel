"""Offline, source-bounded witness packets. No network or identity resolution."""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any
from urllib.parse import parse_qs, urlparse

from pydantic import ValidationError

from packages.connectors.gukgam_reviewed_packet import (
    AUTOMATION_GATE,
    ReviewedGukgamSource,
)
from packages.domain.contracts import GukgamWitnessRow

WITNESS_PACKET_SCHEMA = "gukgam-witness-packet.v1"
DRAFT = "DRAFT_NOT_HUMAN_REVIEWED"
HUMAN_REVIEWED = "HUMAN_REVIEWED"
_SHA256 = re.compile(r"[0-9a-f]{64}")


class GukgamWitnessPacketError(ValueError):
    """Invalid minimized witness fields or inexact source provenance."""


def canonical_hash(value: object) -> str:
    body = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def _mapping(value: object) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise GukgamWitnessPacketError("witness packet requires an object")
    return value


def _keys(raw: Mapping[str, Any], expected: set[str]) -> None:
    if set(raw) != expected:
        # Never interpolate unknown keys/values: an input can contain credentials/private fields.
        raise GukgamWitnessPacketError("witness packet contains missing or unsupported fields")


def _source_key(source: ReviewedGukgamSource) -> str:
    return f"{source.ntt_id}:{source.atch_file_id}:{source.file_sn}"


def _official_url(value: object, *, attachment: bool) -> str:
    if not isinstance(value, str):
        raise GukgamWitnessPacketError("witness source URL is invalid")
    url = urlparse(value)
    allowed = (
        {"menuNo", "atchFileId", "fileSn", "historyBackUrl", "viewType"}
        if attachment else {"nttId", "menuNo", "hrCmtId", "pageUnit", "pdCndCd", "pageIndex"}
    )
    paths = (
        {"/cmmit/cmmn/file/fileDown.do", "/cmmit/prevew/docsPreview/previewDocs.do"}
        if attachment else {"/cmmit/bbs/BCMT2004/view.do"}
    )
    query = parse_qs(url.query, keep_blank_values=True)
    if (
        url.scheme != "https" or not (url.hostname or "").endswith(".na.go.kr")
        or url.username is not None or url.password is not None or url.netloc != url.hostname
        or url.fragment or url.path not in paths or set(query) - allowed
        or any(len(values) != 1 for values in query.values())
        or query.get("historyBackUrl", [""]) != [""]
    ):
        raise GukgamWitnessPacketError("witness source requires an exact credential-free official URL")
    return value


@dataclass(frozen=True)
class GukgamWitnessPacket:
    source: ReviewedGukgamSource
    attachment_url: str
    attachment_sha256: str
    page_count: int
    review_status: str
    selection: str
    rows: tuple[GukgamWitnessRow, ...]

    @property
    def source_key(self) -> str:
        return _source_key(self.source)

    def normalized(self) -> dict[str, object]:
        return {
            "schema": WITNESS_PACKET_SCHEMA,
            "source": self.source.normalized(),
            "attachment_url": self.attachment_url,
            "attachment_sha256": self.attachment_sha256,
            "page_count": self.page_count,
            "review_status": self.review_status,
            "selection": self.selection,
            "rows": [row.model_dump() for row in self.rows],
        }

    @property
    def content_hash(self) -> str:
        return canonical_hash(self.normalized())


def parse_gukgam_witness_packet(raw: Mapping[str, Any]) -> GukgamWitnessPacket:
    _keys(raw, {
        "schema", "source", "attachment_url", "attachment_sha256", "page_count",
        "review_status", "selection", "rows",
    })
    if raw["schema"] != WITNESS_PACKET_SCHEMA or raw["review_status"] not in (DRAFT, HUMAN_REVIEWED):
        raise GukgamWitnessPacketError("witness packet schema or review status is invalid")
    if raw["selection"] not in ("COMPLETE_ATTACHMENT", "EXPLICIT_REVIEW_SUBSET"):
        raise GukgamWitnessPacketError("witness packet selection is invalid")
    source_raw = _mapping(raw["source"])
    _official_url(source_raw.get("detail_url"), attachment=False)
    source = ReviewedGukgamSource.from_mapping(source_raw)
    if not re.fullmatch(r"[0-9]+", source.ntt_id) or not re.fullmatch(
        r"[A-Za-z0-9_-]+", source.atch_file_id
    ):
        raise GukgamWitnessPacketError("witness source identifiers are invalid")
    attachment_url = _official_url(raw["attachment_url"], attachment=True)
    attachment = urlparse(attachment_url)
    query = parse_qs(attachment.query)
    if (
        attachment.hostname != urlparse(source.detail_url).hostname
        or query.get("atchFileId") != [source.atch_file_id]
        or query.get("fileSn") != [str(source.file_sn)]
    ):
        raise GukgamWitnessPacketError("witness attachment locator differs from its source")
    digest = raw["attachment_sha256"]
    pages = raw["page_count"]
    if not isinstance(digest, str) or not _SHA256.fullmatch(digest):
        raise GukgamWitnessPacketError("witness attachment hash is invalid")
    if type(pages) is not int or pages < 1:
        raise GukgamWitnessPacketError("witness page count is invalid")
    if not isinstance(raw["rows"], list) or not raw["rows"]:
        raise GukgamWitnessPacketError("witness packet requires at least one row")
    try:
        rows = tuple(GukgamWitnessRow.model_validate(item) for item in raw["rows"])
    except ValidationError:
        raise GukgamWitnessPacketError("witness row contract is invalid") from None
    if any(row.source_key != _source_key(source) or row.page_number > pages for row in rows):
        raise GukgamWitnessPacketError("witness row provenance differs from its packet")
    if len({row.record_key for row in rows}) != len(rows):
        raise GukgamWitnessPacketError("witness row keys must be unique")
    names_by_cell: dict[str, str] = {}
    for row in rows:
        prior = names_by_cell.setdefault(row.source_name_cell_key, row.printed_name)
        if prior != row.printed_name:
            raise GukgamWitnessPacketError("merged witness name cell has inconsistent names")
    if raw["selection"] == "COMPLETE_ATTACHMENT":
        owner_cells = {row.source_name_cell_key for row in rows if not row.name_from_merged_cell}
        if any(row.source_name_cell_key not in owner_cells for row in rows):
            raise GukgamWitnessPacketError("complete witness packet lacks a merged-name owner row")
    return GukgamWitnessPacket(
        source, attachment_url, digest, pages, raw["review_status"], raw["selection"], rows,
    )


def parse_gukgam_witness_research(raw: Mapping[str, Any]) -> tuple[GukgamWitnessPacket, ...]:
    """Adapt the pinned research format to DRAFT packets without inventing human review."""
    _keys(raw, {
        "artifact_kind", "review_status", "checked_at", "scope", "maturity",
        "operational_import_eligible", "identity_state", "attendance_state", "effect_counts",
        "counts", "limitations", "sources", "institution_heading_checks", "records",
    })
    if (
        raw["artifact_kind"] != "RESEARCH_ONLY_GUKGAM_WITNESS_LINKAGE"
        or raw["review_status"] != DRAFT or raw["operational_import_eligible"] is not False
        or raw["maturity"] != "L0_RESEARCHED"
    ):
        raise GukgamWitnessPacketError("research input must remain unreviewed and non-operational")
    effects = _mapping(raw["effect_counts"])
    _keys(effects, {"operational_observations", "persons", "organizations", "identity_links",
                    "claims", "evidence"})
    if any(type(value) is not int or value != 0 for value in effects.values()):
        raise GukgamWitnessPacketError("research input contains operational effects")
    if not isinstance(raw["sources"], list) or not isinstance(raw["records"], list):
        raise GukgamWitnessPacketError("research source/row lists are invalid")
    records: list[dict[str, Any]] = []
    for item in raw["records"]:
        record = dict(_mapping(item))
        digest = record.pop("normalization_hash", None)
        if canonical_hash(record) != digest:
            raise GukgamWitnessPacketError("research row normalization hash differs")
        records.append(record)
    packets: list[GukgamWitnessPacket] = []
    source_keys: set[str] = set()
    for item in raw["sources"]:
        source_raw = _mapping(item)
        _keys(source_raw, {
            "source_key", "committee_name", "ntt_id", "title", "published_date", "detail_url",
            "atch_file_id", "file_sn", "attachment_filename", "attachment_url",
            "attachment_sha256", "page_count", "rights_mark", "acquisition", "automated_fetch",
            "verified_at", "later_amendment_completeness",
        })
        source = {key: source_raw[key] for key in (
            "committee_name", "ntt_id", "detail_url", "title", "published_date", "atch_file_id",
            "file_sn", "attachment_filename", "rights_mark",
        )}
        source["automation_gate"] = AUTOMATION_GATE
        if source_raw["automated_fetch"] != "BLOCKED" or source_raw["acquisition"] != (
            "BOUNDED_ASIDE_OPERATOR_CAPTURE"
        ):
            raise GukgamWitnessPacketError("research capture boundary differs")
        packet = parse_gukgam_witness_packet({
            "schema": WITNESS_PACKET_SCHEMA, "source": source,
            "attachment_url": source_raw["attachment_url"],
            "attachment_sha256": source_raw["attachment_sha256"],
            "page_count": source_raw["page_count"], "review_status": DRAFT,
            "selection": "COMPLETE_ATTACHMENT",
            "rows": [row for row in records if row.get("source_key") == source_raw["source_key"]],
        })
        if source_raw["source_key"] != packet.source_key or packet.source_key in source_keys:
            raise GukgamWitnessPacketError("research source keys are inconsistent")
        source_keys.add(packet.source_key)
        packets.append(packet)
    if not packets or sum(len(packet.rows) for packet in packets) != len(records):
        raise GukgamWitnessPacketError("research rows do not all belong to declared sources")
    rows = [row for packet in packets for row in packet.rows]
    counts = Counter(row.category for row in rows)
    headings = raw["institution_heading_checks"]
    if not isinstance(headings, list):
        raise GukgamWitnessPacketError("research heading checks are invalid")
    expected_counts = {
        "source_documents": len(packets), "institution_role_rows": counts["INSTITUTION_WITNESS"],
        "institution_source_name_cells": len({row.source_name_cell_key for row in rows
                                             if row.category == "INSTITUTION_WITNESS"}),
        "general_witness_rows": counts["GENERAL_WITNESS"],
        "reference_person_rows": counts["REFERENCE_PERSON"],
        "total_role_or_request_rows": len(rows), "institution_heading_tables": len(headings),
    }
    if raw["counts"] != expected_counts:
        raise GukgamWitnessPacketError("research coverage counts differ from source rows")
    counts_raw = _mapping(raw["counts"])
    if any(type(value) is not int for value in counts_raw.values()):
        raise GukgamWitnessPacketError("research coverage counts must be integers")
    seen_headings: set[tuple[str, int, int]] = set()
    for item in headings:
        heading = _mapping(item)
        _keys(heading, {"source_key", "page_number", "table_number", "printed_heading",
                        "expected_named_cells", "actual_named_cells", "role_rows"})
        if not isinstance(heading["source_key"], str) or any(
            type(heading[key]) is not int or heading[key] < 1
            for key in ("page_number", "table_number", "expected_named_cells", "actual_named_cells",
                        "role_rows")
        ):
            raise GukgamWitnessPacketError("research heading count or locator is invalid")
        identity = (heading["source_key"], heading["page_number"], heading["table_number"])
        group = [row for row in rows if row.category == "INSTITUTION_WITNESS" and
                 (row.source_key, row.page_number, row.table_number) == identity]
        if (
            identity in seen_headings or not group
            or {row.source_section for row in group} != {heading["printed_heading"]}
            or len(group) != heading["role_rows"]
            or len({row.source_name_cell_key for row in group}) != heading["expected_named_cells"]
            or heading["actual_named_cells"] != heading["expected_named_cells"]
        ):
            raise GukgamWitnessPacketError("research heading coverage differs from its literal rows")
        seen_headings.add(identity)
    if seen_headings != {(row.source_key, row.page_number, row.table_number) for row in rows
                         if row.category == "INSTITUTION_WITNESS"}:
        raise GukgamWitnessPacketError("research heading checks do not cover all institution rows")
    return tuple(packets)
