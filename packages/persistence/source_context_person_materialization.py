from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol

from sqlalchemy import text
from sqlalchemy.orm import Session

from packages.domain.contracts import (
    Claim,
    ClaimEvidence,
    FeederObservation,
    Person,
    PersonObservationLink,
    Source,
    SourceCheckpoint,
    SourcePolicy,
    SourceRun,
    SourceSnapshot,
)
from packages.persistence import models as db


class SourceContextPersonPacket(Protocol):
    @property
    def person(self) -> Person: ...

    @property
    def link(self) -> PersonObservationLink: ...

    @property
    def claim(self) -> Claim: ...

    @property
    def evidence(self) -> ClaimEvidence: ...


def normalize_receipt_sha256(value: str) -> str:
    expected = value.casefold()
    if len(expected) != 64 or any(char not in "0123456789abcdef" for char in expected):
        raise ValueError("expected receipt SHA-256 must be 64 hex characters")
    return expected


def lock_source_context_person_materialization(
    session: Session,
    *,
    advisory_lock_id: int,
) -> None:
    if session.get_bind().dialect.name != "postgresql":
        return
    session.execute(
        text("SELECT pg_advisory_xact_lock(:lock_id)"),
        {"lock_id": advisory_lock_id},
    )
    session.execute(text("LOCK TABLE people IN SHARE ROW EXCLUSIVE MODE"))
    session.execute(text("LOCK TABLE person_observation_links IN SHARE ROW EXCLUSIVE MODE"))
    session.execute(text("LOCK TABLE claims IN SHARE ROW EXCLUSIVE MODE"))
    session.execute(text("LOCK TABLE claim_evidence IN SHARE ROW EXCLUSIVE MODE"))


def persist_source_context_person_packets(
    session: Session,
    packets: Iterable[SourceContextPersonPacket],
) -> int:
    items = list(packets)
    if not items:
        return 0

    people_rows: list[db.PersonRow] = []
    link_rows: list[db.PersonObservationLinkRow] = []
    claim_rows: list[db.ClaimRow] = []
    evidence_rows: list[db.ClaimEvidenceRow] = []
    for packet in items:
        people_rows.append(
            db.PersonRow(
                id=str(packet.person.id),
                canonical_name=packet.person.canonical_name,
                birth_date=packet.person.birth_date,
                identity_status=packet.person.identity_status.value,
                valid_from=packet.person.valid_from,
                valid_to=packet.person.valid_to,
                recorded_at=packet.person.recorded_at,
                superseded_at=packet.person.superseded_at,
            )
        )
        link_rows.append(
            db.PersonObservationLinkRow(
                id=str(packet.link.id),
                person_id=str(packet.link.person_id),
                observation_id=str(packet.link.observation_id),
                action=packet.link.action.value,
                decision_class=packet.link.decision_class.value,
                linked_at=packet.link.linked_at,
                superseded_at=None,
                review_item_id=None,
            )
        )
        claim_rows.append(
            db.ClaimRow(
                id=str(packet.claim.id),
                person_id=str(packet.claim.person_id),
                organization_id=None,
                proposition=packet.claim.proposition,
                subject=packet.claim.subject,
                predicate=packet.claim.predicate,
                object_text=packet.claim.object_text,
                qualifiers=packet.claim.qualifiers,
                epistemic_status=packet.claim.epistemic_status.value,
                publication_status=packet.claim.publication_status.value,
                asserted_as_true=packet.claim.asserted_as_true,
                resolution_note=packet.claim.resolution_note,
                valid_from=packet.claim.valid_from,
                valid_to=packet.claim.valid_to,
                recorded_at=packet.claim.recorded_at,
                superseded_at=packet.claim.superseded_at,
            )
        )
        evidence_rows.append(
            db.ClaimEvidenceRow(
                id=str(packet.evidence.id),
                claim_id=str(packet.evidence.claim_id),
                source_id=str(packet.evidence.source_id),
                snapshot_id=str(packet.evidence.snapshot_id),
                feeder_observation_id=str(packet.evidence.feeder_observation_id),
                stance=packet.evidence.stance.value,
                excerpt=None,
            )
        )

    session.add_all(people_rows)
    session.flush()
    session.add_all(link_rows)
    session.add_all(claim_rows)
    session.flush()
    session.add_all(evidence_rows)
    session.flush()
    return len(items)


def observation_from_row(row: db.FeederObservationRow) -> FeederObservation:
    return FeederObservation.model_validate(
        {
            "id": row.id,
            "feeder": row.feeder,
            "scope_key": row.scope_key,
            "provider_record_key": row.provider_record_key,
            "snapshot_id": row.snapshot_id,
            "run_id": row.run_id,
            "recorded_at": row.recorded_at,
            "provider_observed_at": row.provider_observed_at,
            "semantic_scope": row.semantic_scope,
            "identity_hints": row.identity_hints_json,
            "normalized": row.normalized_json,
            "content_hash": row.content_hash,
        }
    )


def snapshot_from_row(row: db.SourceSnapshotRow) -> SourceSnapshot:
    return SourceSnapshot.model_validate(
        {
            "id": row.id,
            "source_id": row.source_id,
            "fetched_at": row.fetched_at,
            "content_hash": row.content_hash,
            "metadata": row.metadata_json,
            "fulltext": row.fulltext,
        }
    )


def source_from_row(row: db.SourceRow) -> Source:
    return Source.model_validate(row, from_attributes=True)


def policy_from_row(row: db.SourcePolicyRow) -> SourcePolicy:
    return SourcePolicy.model_validate(
        {
            "id": row.id,
            "domain": row.domain,
            "source_class": row.source_class,
            "collection_mode": row.collection_mode,
            "can_fetch": row.can_fetch,
            "can_store_metadata": row.can_store_metadata,
            "can_store_fulltext": row.can_store_fulltext,
            "can_send_to_ai": row.can_send_to_ai,
            "can_show_excerpt": row.can_show_excerpt,
            "can_commercialize": row.can_commercialize,
            "robots_checked_at": row.robots_checked_at,
            "terms_checked_at": row.terms_checked_at,
            "license": row.license,
            "rate_limit": row.rate_limit,
            "policy_note": row.policy_note,
        }
    )


def checkpoint_from_row(row: db.SourceCheckpointRow) -> SourceCheckpoint:
    return SourceCheckpoint.model_validate(
        {
            "id": row.id,
            "feeder": row.feeder,
            "scope_key": row.scope_key,
            "cursor": row.cursor,
            "metadata": row.metadata_json,
            "updated_at": row.updated_at,
            "last_run_id": row.last_run_id,
        }
    )


def run_from_row(row: db.SourceRunRow) -> SourceRun:
    return SourceRun.model_validate(
        {
            "id": row.id,
            "feeder": row.feeder,
            "scope_key": row.scope_key,
            "started_at": row.started_at,
            "finished_at": row.finished_at,
            "status": row.status,
            "checkpoint_before": row.checkpoint_before,
            "checkpoint_after": row.checkpoint_after,
            "records_seen": row.records_seen,
            "observations_created": row.observations_created,
            "observations_unchanged": row.observations_unchanged,
            "error_code": row.error_code,
            "error_summary": row.error_summary,
            "metadata": row.metadata_json,
        }
    )
