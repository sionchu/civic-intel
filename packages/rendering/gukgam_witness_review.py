"""Private source-row review. This projection has no Claim or Person authority."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from packages.connectors.gukgam_witness_packet import (
    HUMAN_REVIEWED,
    WITNESS_PACKET_SCHEMA,
    GukgamWitnessPacket,
    GukgamWitnessPacketError,
    canonical_hash,
    parse_gukgam_witness_packet,
)
from packages.domain.contracts import SourceRun
from packages.domain.enums import SourceCollectionMode, SourceRunStatus
from packages.rendering.gukgam_schedule_review import Context, GukgamScheduleReviewRepository
from packages.verification.gukgam_reviewed_plan_import import (
    EXACT_ATTACHMENT_RIGHTS,
    HUMAN_ASSISTED_CAPTURE,
)
from packages.verification.gukgam_witness_import import (
    GUKGAM_WITNESS_FEEDER,
    GUKGAM_WITNESS_SCOPE,
    GUKGAM_WITNESS_SOURCE_CONTRACT,
)


class GukgamWitnessReviewError(ValueError):
    pass


class GukgamWitnessReviewRepository(GukgamScheduleReviewRepository, Protocol):
    def source_run(self, run_id: UUID) -> SourceRun | None: ...


def _row(context: Context, *, scope_key: str, attachment_hash: str) -> dict:
    observation, snapshot, source, policy = context
    if (
        observation.feeder != GUKGAM_WITNESS_FEEDER or observation.scope_key != scope_key
        or observation.semantic_scope != GUKGAM_WITNESS_SCOPE or observation.identity_hints
        or observation.snapshot_id != snapshot.id or snapshot.source_id != source.id
        or source.policy_id != policy.id or snapshot.fulltext is not None
        or snapshot.content_hash != attachment_hash
        or snapshot.metadata.get("source_contract") != GUKGAM_WITNESS_SOURCE_CONTRACT
        or snapshot.metadata.get("content_hash_semantics") != "RAW_ATTACHMENT_SHA256"
        or snapshot.metadata.get("rights_scope") != EXACT_ATTACHMENT_RIGHTS
        or snapshot.metadata.get("capture_mode") != HUMAN_ASSISTED_CAPTURE
        or policy.source_class != "official_reviewed_committee_attachment"
        or policy.collection_mode != SourceCollectionMode.BROWSER
        or policy.can_fetch or not policy.can_store_metadata or policy.can_store_fulltext
        or policy.can_send_to_ai or policy.can_show_excerpt or policy.can_commercialize
    ):
        raise GukgamWitnessReviewError("witness source provenance or policy is inconsistent")
    normalized = dict(observation.normalized)
    if canonical_hash(normalized) != observation.content_hash:
        raise GukgamWitnessReviewError("witness observation hash differs")
    source_fields = snapshot.metadata.get("source")
    if not isinstance(source_fields, dict):
        raise GukgamWitnessReviewError("witness source metadata is incomplete")
    expected = {
        "packet_schema": WITNESS_PACKET_SCHEMA,
        "committee_name": source_fields.get("committee_name"),
        "source_published_date": source_fields.get("published_date"),
        "attachment_sha256": attachment_hash,
    }
    for key, value in expected.items():
        if normalized.pop(key, None) != value:
            raise GukgamWitnessReviewError("witness normalized source metadata differs")
    if normalized.get("record_key") != observation.provider_record_key:
        raise GukgamWitnessReviewError("witness provider locator differs")
    return normalized


@dataclass(frozen=True)
class CurrentGukgamWitnessDocument:
    packet: GukgamWitnessPacket
    contexts: tuple[Context, ...]


def load_current_gukgam_witness_documents(
    repository: GukgamWitnessReviewRepository, *, year: int = 2026,
) -> tuple[CurrentGukgamWitnessDocument, ...]:
    """Recover exact checkpoint-selected packets and provenance for private use cases."""
    documents: list[CurrentGukgamWitnessDocument] = []
    for checkpoint in repository.source_checkpoints(GUKGAM_WITNESS_FEEDER):
        if not checkpoint.scope_key.startswith(f"{year}:"):
            continue
        run = repository.source_run(checkpoint.last_run_id) if checkpoint.last_run_id else None
        meta = checkpoint.metadata
        if (
            run is None or run.status != SourceRunStatus.SUCCESS
            or run.feeder != GUKGAM_WITNESS_FEEDER or run.scope_key != checkpoint.scope_key
            or run.metadata != meta or meta.get("source_contract") != GUKGAM_WITNESS_SOURCE_CONTRACT
            or meta.get("review_status") != HUMAN_REVIEWED
            or meta.get("packet_schema") != WITNESS_PACKET_SCHEMA
            or checkpoint.cursor != (
                f"{meta.get('attachment_sha256')}:{meta.get('reviewed_packet_hash')}"
            )
        ):
            raise GukgamWitnessReviewError("witness checkpoint does not select a successful review")
        manifest = meta.get("row_manifest")
        expected_count = meta.get("witness_row_count")
        if (
            not isinstance(manifest, list) or not manifest
            or type(expected_count) is not int or len(manifest) != expected_count
            or any(not isinstance(item, dict) or set(item) != {"record_key", "content_hash"}
                   for item in manifest)
        ):
            raise GukgamWitnessReviewError("witness checkpoint row manifest is incomplete")
        expected = [(item["record_key"], item["content_hash"]) for item in manifest]
        if len({key for key, _ in expected}) != len(expected):
            raise GukgamWitnessReviewError("witness checkpoint row keys are duplicated")
        observations = repository.feeder_observations(GUKGAM_WITNESS_FEEDER, checkpoint.scope_key)
        contexts = repository.feeder_observation_contexts(item.id for item in observations)
        selected: dict[tuple[str, str], Context | None] = {}
        for item in observations:
            key = (item.provider_record_key, item.content_hash)
            if key in selected:
                raise GukgamWitnessReviewError("witness observation versions are duplicated")
            context = contexts.get(item.id)
            if context is not None and context[0] != item:
                raise GukgamWitnessReviewError("witness observation context differs")
            selected[key] = context
        current: list[Context] = []
        for identity in expected:
            context = selected.get(identity)
            if context is None:
                raise GukgamWitnessReviewError("witness checkpoint row provenance is incomplete")
            current.append(context)
        first = current[0]
        if any(context[1].id != first[1].id for context in current):
            raise GukgamWitnessReviewError("witness checkpoint mixes attachment snapshots")
        rows = [_row(context, scope_key=checkpoint.scope_key,
                     attachment_hash=meta["attachment_sha256"]) for context in current]
        snapshot, source = first[1], first[2]
        try:
            packet = parse_gukgam_witness_packet({
                "schema": WITNESS_PACKET_SCHEMA, "source": snapshot.metadata["source"],
                "attachment_url": str(source.url), "attachment_sha256": snapshot.content_hash,
                "page_count": snapshot.metadata.get("page_count"),
                "review_status": HUMAN_REVIEWED, "selection": meta.get("selection"), "rows": rows,
            })
        except (GukgamWitnessPacketError, ValueError):
            raise GukgamWitnessReviewError("witness reviewed row contract is invalid") from None
        expected_scope = f"{year}:{packet.source.committee_name}:{packet.source_key}"
        if checkpoint.scope_key != expected_scope or packet.content_hash != meta["reviewed_packet_hash"]:
            raise GukgamWitnessReviewError("witness reviewed packet hash or scope differs")
        documents.append(CurrentGukgamWitnessDocument(packet, tuple(current)))
    return tuple(documents)


def load_current_gukgam_witness_review(
    repository: GukgamWitnessReviewRepository, *, year: int = 2026,
) -> dict:
    documents: list[dict] = []
    for document in load_current_gukgam_witness_documents(repository, year=year):
        packet, current = document.packet, document.contexts
        snapshot, source = current[0][1], current[0][2]
        documents.append({
            "committee_name": packet.source.committee_name,
            "source_published_date": packet.source.published_date.isoformat(),
            "selection": packet.selection,
            "source": {
                "source_id": str(source.id), "snapshot_id": str(snapshot.id),
                "url": str(source.url), "parent_detail_url": packet.source.detail_url,
                "title": source.title, "publisher": source.publisher,
                "attachment_sha256": snapshot.content_hash, "rights_mark": packet.source.rights_mark,
            },
            "rows": [
                {"observation_id": str(context[0].id), **row.model_dump(),
                 "identity_state": "SOURCE_SCOPED_IDENTITY_REVIEW_REQUIRED",
                 "attendance_state": "NOT_VERIFIED"}
                for context, row in zip(current, packet.rows, strict=True)
            ],
        })
    return {
        "semantics": "REVIEW_ONLY_SOURCE_LISTED_WITNESSES",
        "source_document_count": len(documents),
        "row_count": sum(len(item["rows"]) for item in documents),
        "documents": sorted(documents, key=lambda item: (
            item["committee_name"], item["source_published_date"], item["source"]["url"])),
        "limitations": [
            "Rows are source listings, not canonical identities or actual attendance.",
            "Institution group headings do not establish individual employment.",
            "Each checkpoint selects one attachment series; cross-post replacements need review.",
            "Latest amendments and national completeness are not established.",
        ],
    }
