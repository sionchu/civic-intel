"""Bind one operator-supplied official committee minutes PDF to speaker-turn observations.

Writes only SourcePolicy / Source / SourceSnapshot / FeederObservation rows (through the
shared repository). Never creates People, links speakers to Persons, publishes Claims or
fetches anything.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid5

from packages.connectors.assembly_minutes import (
    ACQUISITION_CHANNEL,
    MINUTES_HOST,
    MINUTES_PACKET_SCHEMA,
    PARSER_REVISION,
    TEXT_FORM,
    MinutesPacket,
    ParsedMinutes,
    SpeakerTurn,
    glyphs,
    parse_minutes_pages,
)
from packages.domain.contracts import FeederObservation, Source, SourcePolicy, SourceSnapshot
from packages.domain.enums import SourceCollectionMode

ASSEMBLY_MINUTES_FEEDER = "assembly_minutes_speaker_turns"
ASSEMBLY_MINUTES_SEMANTIC_SCOPE = "national_assembly_committee_minutes_speaker_turn"
ASSEMBLY_MINUTES_SOURCE_CONTRACT = "assembly_minutes_official_pdf_v1"
HUMAN_ASSISTED_CAPTURE = "HUMAN_ASSISTED_LOCAL_ARTIFACT"
RIGHTS_BASIS = (
    "OFFICIAL_RECORD: 국회법 제118조 회의록 반포; 저작권법 제24조 국회 공개 진술 이용; "
    "저작권법 제24조의2 공공저작물 자유이용"
)
_POLICY_NAMESPACE = UUID("3f6c2b7e-2a7d-4c55-9a43-6a9f0e1d8b52")


class AssemblyMinutesImportError(ValueError):
    """The supplied artifact, packet, text layer or policy does not permit persistence."""


def assembly_minutes_policy() -> SourcePolicy:
    """Reviewed policy for official committee minutes PDFs on record.assembly.go.kr."""

    return SourcePolicy(
        id=uuid5(_POLICY_NAMESPACE, MINUTES_HOST),
        domain=MINUTES_HOST,
        source_class="official_national_assembly_minutes",
        collection_mode=SourceCollectionMode.BROWSER,
        # robots.txt returned 404 on 2026-10-05 (no published rules). Absence of rules is not
        # treated as an automation contract: the operator supplies the exact PDF bytes.
        can_fetch=False,
        can_store_metadata=True,
        # No whole-document text in SourceSnapshot: no raw republication of the record.
        can_store_fulltext=False,
        can_send_to_ai=False,
        # Per-turn exact excerpts of a speaker's own public statement in an official meeting.
        can_show_excerpt=True,
        can_commercialize=False,
        robots_checked_at=datetime(2026, 10, 5, tzinfo=UTC),
        terms_checked_at=datetime(2026, 10, 5, tzinfo=UTC),
        license=RIGHTS_BASIS,
        policy_note=(
            "Primary official record. Human-assisted exact-PDF capture only (no fetch). "
            "Metadata plus per-turn exact glyph-sequence excerpts of the speaker's own words; "
            "no SourceSnapshot fulltext, no AI use. Compiling one speaker's statements for "
            "display (저작권법 제24조 단서) and any Claim publication require separate review."
        ),
    )


def _hash(payload: object) -> str:
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()


def text_layer_sha256(pages: Sequence[str]) -> str:
    return _hash(list(pages))


def validate_parsed_against_meeting(parsed: ParsedMinutes, packet: MinutesPacket) -> None:
    meeting = packet.meeting
    header = parsed.header
    if (header.session, header.sitting, header.meeting_date) != (
        meeting.session,
        meeting.sitting,
        meeting.conf_date,
    ):
        raise AssemblyMinutesImportError(
            "minutes page header session/sitting/date disagree with the Open Assembly row"
        )
    if header.committee_label + "위원회" != glyphs(meeting.comm_name):
        raise AssemblyMinutesImportError(
            "minutes page header committee disagrees with the Open Assembly row"
        )
    index = set(parsed.agenda_index)
    missing = [item for item in meeting.agenda_items if glyphs(item) not in index]
    if missing:
        raise AssemblyMinutesImportError(
            "Open Assembly agenda items are absent from the minutes agenda index"
        )


@dataclass(frozen=True)
class AssemblyMinutesCapture:
    packet: MinutesPacket
    parsed: ParsedMinutes
    extractor: str
    text_layer_sha256: str
    policy: SourcePolicy
    source: Source
    snapshot: SourceSnapshot

    @property
    def scope_key(self) -> str:
        meeting = self.packet.meeting
        return f"{meeting.dae_num}:{meeting.confer_num}:{PARSER_REVISION}"

    @property
    def cursor(self) -> str:
        return f"{self.packet.artifact_sha256}:{PARSER_REVISION}:{self.parsed.turns_hash}"

    @property
    def run_metadata(self) -> dict[str, object]:
        return {
            "source_contract": ASSEMBLY_MINUTES_SOURCE_CONTRACT,
            "packet_schema": MINUTES_PACKET_SCHEMA,
            "packet_hash": self.packet.content_hash,
            "artifact_sha256": self.packet.artifact_sha256,
            "parser_revision": PARSER_REVISION,
            "extractor": self.extractor,
            "text_layer_sha256": self.text_layer_sha256,
            "turn_count": len(self.parsed.turns),
            "turns_hash": self.parsed.turns_hash,
        }

    @property
    def checkpoint_metadata(self) -> dict[str, object]:
        return self.run_metadata | {"confer_num": self.packet.meeting.confer_num}

    def record_key(self, turn: SpeakerTurn) -> str:
        return f"{self.packet.meeting.confer_num}:{turn.ordinal}"

    def observations(self, run_id: UUID) -> tuple[FeederObservation, ...]:
        if not self.policy.can_store_metadata:
            raise AssemblyMinutesImportError("SourcePolicy does not permit metadata storage")
        retain_quote = self.policy.can_show_excerpt
        meeting = self.packet.meeting
        items: list[FeederObservation] = []
        for turn in self.parsed.turns:
            normalized: dict[str, object] = {
                "meeting_key": meeting.meeting_key,
                "conf_id": meeting.conf_id,
                "dae_num": meeting.dae_num,
                "class_name": meeting.class_name,
                "comm_name": meeting.comm_name,
                "meeting_title": meeting.title,
                "conf_date": meeting.conf_date.isoformat(),
                "session": meeting.session,
                "sitting": meeting.sitting,
                "turn_ordinal": turn.ordinal,
                "speaker_label_raw": turn.speaker_label_raw,
                "speaker_role_printed": turn.speaker_role,
                "speaker_name_printed": turn.speaker_name,
                "speaker_role_category": turn.speaker_role_category,
                "speaker_person_link": None,
                "agenda_items": list(turn.agenda_items),
                "last_time_marker": turn.last_time_marker,
                "page_start": turn.page_start,
                "page_end": turn.page_end,
                "pdf_page_start": turn.pdf_page_start,
                "pdf_page_end": turn.pdf_page_end,
                "text_form": TEXT_FORM,
                "quote_text": turn.quote_text if retain_quote else None,
                "quote_text_retained": retain_quote,
                "quote_sha256": turn.quote_sha256,
                "quote_char_length": turn.quote_char_length,
                "quote_segment_count": len(turn.segments),
                "stage_directions": list(turn.stage_directions),
                "contains_inline_parenthetical": turn.contains_inline_parenthetical,
                "artifact_sha256": self.packet.artifact_sha256,
                "parser_revision": PARSER_REVISION,
                "extractor": self.extractor,
                "packet_schema": MINUTES_PACKET_SCHEMA,
            }
            items.append(
                FeederObservation(
                    feeder=ASSEMBLY_MINUTES_FEEDER,
                    scope_key=self.scope_key,
                    provider_record_key=self.record_key(turn),
                    snapshot_id=self.snapshot.id,
                    run_id=run_id,
                    semantic_scope=ASSEMBLY_MINUTES_SEMANTIC_SCOPE,
                    # Speakers are printed labels only; never identity candidates here.
                    identity_hints={},
                    normalized=normalized,
                    content_hash=_hash(normalized),
                )
            )
        return tuple(items)


def build_assembly_minutes_capture(
    packet: MinutesPacket,
    *,
    artifact_bytes: bytes,
    pages: Sequence[str],
    extractor: str,
    policy: SourcePolicy | None = None,
) -> AssemblyMinutesCapture:
    """Verify the exact PDF bytes, parse its text layer and build the capture rows."""

    policy = policy or assembly_minutes_policy()
    if policy.domain != MINUTES_HOST:
        raise AssemblyMinutesImportError("SourcePolicy is not the minutes record policy")
    if not policy.can_store_metadata:
        raise AssemblyMinutesImportError("SourcePolicy does not permit metadata storage")
    if not artifact_bytes:
        raise AssemblyMinutesImportError("minutes artifact is empty")
    actual = hashlib.sha256(artifact_bytes).hexdigest()
    if actual != packet.artifact_sha256:
        raise AssemblyMinutesImportError("minutes artifact sha256 does not match the packet")
    if not extractor.strip():
        raise AssemblyMinutesImportError("minutes text-layer extractor identity is required")
    parsed = parse_minutes_pages(pages)
    validate_parsed_against_meeting(parsed, packet)
    layer_hash = text_layer_sha256(pages)
    meeting = packet.meeting
    source = Source(
        url=meeting.pdf_link_url,  # type: ignore[arg-type]
        title=meeting.title,
        publisher=f"대한민국 국회 {meeting.comm_name}",
        published_at=None,
        policy_id=policy.id,
    )
    snapshot = SourceSnapshot(
        source_id=source.id,
        content_hash=actual,
        metadata={
            "source_contract": ASSEMBLY_MINUTES_SOURCE_CONTRACT,
            "meeting": meeting.normalized(),
            "acquisition_channel": ACQUISITION_CHANNEL,
            "received_via": packet.received_via,
            "capture_mode": HUMAN_ASSISTED_CAPTURE,
            "content_hash_semantics": "RAW_ARTIFACT_SHA256",
            "rights_basis": RIGHTS_BASIS,
            "extractor": extractor,
            "text_layer_sha256": layer_hash,
            "text_form": TEXT_FORM,
            "parser_revision": PARSER_REVISION,
            "pdf_page_count": parsed.pdf_page_count,
            "printed_page_range": [parsed.printed_page_first, parsed.printed_page_last],
            "header_committee_label": parsed.header.committee_label,
            "open_marker": parsed.open_marker,
            "close_marker": parsed.close_marker,
            "agenda_index": list(parsed.agenda_index),
            "appendix_line_count": parsed.appendix_line_count,
            "turn_count": len(parsed.turns),
            "turns_hash": parsed.turns_hash,
            "fulltext_retained": False,
        },
        fulltext=None,
    )
    return AssemblyMinutesCapture(
        packet=packet,
        parsed=parsed,
        extractor=extractor,
        text_layer_sha256=layer_hash,
        policy=policy,
        source=source,
        snapshot=snapshot,
    )
