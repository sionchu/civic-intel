from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from packages.domain.contracts import (
    FeederObservation,
    SourceCheckpoint,
    SourceRun,
)
from packages.domain.enums import IdentityStatus, PublicationStatus
from packages.persistence import models as db
from packages.persistence.source_context_person_materialization import (
    checkpoint_from_row,
    lock_source_context_person_materialization,
    normalize_receipt_sha256,
    observation_from_row,
    persist_source_context_person_packets,
    policy_from_row,
    run_from_row,
    snapshot_from_row,
    source_from_row,
)
from packages.verification.nec_person_materialization import (
    NEC_CANDIDACY_PREDICATE,
    NEC_CANDIDATE_FEEDER,
    NecPersonMaterializationError,
    NecPersonMaterializationPacket,
    build_nec_source_context_packet,
    validate_nec_candidate_source_context,
)

DRY_RUN_SEMANTICS = "NEC_CANDIDATE_SOURCE_CONTEXT_PERSON_DRY_RUN_V1"
COMMIT_SEMANTICS = "NEC_CANDIDATE_SOURCE_CONTEXT_PERSON_COMMIT_V1"
DEFAULT_ELECTION_TYPES = (3, 4, 5, 6, 11)


@dataclass(frozen=True)
class PreparedNecPerson:
    observation_id: UUID
    scope_key: str
    provider_record_key: str
    content_hash: str
    canonical_name: str
    action: str
    reason: str
    packet: NecPersonMaterializationPacket | None = None

    def selected_dict(self) -> dict[str, object]:
        if self.packet is None:
            raise ValueError("selected item has no materialization packet")
        return {
            "observation_id": str(self.observation_id),
            "scope_key": self.scope_key,
            "provider_record_key": self.provider_record_key,
            "content_hash": self.content_hash,
            "canonical_name": self.canonical_name,
            **self.packet.ids(),
            "person_identity_status": self.packet.person.identity_status.value,
            "person_birth_date": (
                self.packet.person.birth_date.isoformat() if self.packet.person.birth_date else None
            ),
            "link_action": self.packet.link.action.value,
            "link_decision_class": self.packet.link.decision_class.value,
            "claim_predicate": self.packet.claim.predicate,
            "claim_epistemic_status": self.packet.claim.epistemic_status.value,
            "claim_publication_status": self.packet.claim.publication_status.value,
            "claim_asserted_as_true": self.packet.claim.asserted_as_true,
            "claim_identity_scope": self.packet.claim.qualifiers.get("identity_scope"),
            "evidence_stance": self.packet.evidence.stance.value,
        }


@dataclass(frozen=True)
class NecPersonPreflight:
    items: tuple[PreparedNecPerson, ...]
    election_id: str
    election_types: tuple[int, ...]
    current_people: int
    current_claims: int
    current_evidence: int
    current_links: int
    current_published_claims: int
    current_candidate_rows: int
    scope_totals: dict[str, int]

    @property
    def create_items(self) -> tuple[PreparedNecPerson, ...]:
        return tuple(item for item in self.items if item.action == "CREATE")

    def action_counts(self) -> dict[str, int]:
        counts = Counter(item.action for item in self.items)
        return {key: counts.get(key, 0) for key in ("CREATE", "REVIEW", "CONFLICT", "NOOP")}

    def reason_counts(self) -> dict[str, int]:
        counts = Counter(item.reason for item in self.items)
        return dict(sorted(counts.items()))

    def canonical_payload(self) -> dict[str, Any]:
        creates = self.create_items
        return {
            "semantics": DRY_RUN_SEMANTICS,
            "feeder": NEC_CANDIDATE_FEEDER,
            "election_id": self.election_id,
            "election_types": list(self.election_types),
            "scope_totals": dict(sorted(self.scope_totals.items())),
            "current_candidate_rows": self.current_candidate_rows,
            "current_people": self.current_people,
            "current_claims": self.current_claims,
            "current_evidence": self.current_evidence,
            "current_links": self.current_links,
            "current_published_claims": self.current_published_claims,
            "action_counts": self.action_counts(),
            "reason_counts": self.reason_counts(),
            "selected_count": len(creates),
            "expected_post_counts": {
                "people": self.current_people + len(creates),
                "claims": self.current_claims + len(creates),
                "evidence": self.current_evidence + len(creates),
                "links": self.current_links + len(creates),
                "published_claims": self.current_published_claims,
            },
            "selected": [item.selected_dict() for item in creates],
            "source_fetch": False,
            "claim_publication": False,
            "cross_source_link": False,
            "human_verified": False,
        }

    def sha256(self) -> str:
        raw = json.dumps(
            self.canonical_payload(),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
        return hashlib.sha256(raw).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        payload = self.canonical_payload()
        payload.update(
            {
                "status": "DRY_RUN",
                "receipt_sha256": self.sha256(),
                "write_performed": False,
            }
        )
        return payload


def _packet_state(
    packet: NecPersonMaterializationPacket,
    *,
    people: dict[str, db.PersonRow],
    links: dict[str, db.PersonObservationLinkRow],
    claims: dict[str, db.ClaimRow],
    evidence_rows: dict[str, db.ClaimEvidenceRow],
    aliases_by_person: dict[str, set[str]],
) -> str:
    person = people.get(str(packet.person.id))
    link = links.get(str(packet.link.id))
    claim = claims.get(str(packet.claim.id))
    evidence = evidence_rows.get(str(packet.evidence.id))
    present = [person is not None, link is not None, claim is not None, evidence is not None]
    if not any(present):
        return "ABSENT"
    if not all(present):
        return "PARTIAL"
    assert person is not None and link is not None and claim is not None and evidence is not None

    expected_name_available = (
        person.canonical_name == packet.person.canonical_name
        or packet.person.canonical_name in aliases_by_person.get(person.id, set())
    )
    immutable_exact = (
        expected_name_available
        and person.birth_date == packet.person.birth_date
        and person.identity_status in {IdentityStatus.REVIEW.value, IdentityStatus.RESOLVED.value}
        and link.person_id == str(packet.person.id)
        and link.observation_id == str(packet.link.observation_id)
        and link.action == packet.link.action.value
        and link.decision_class == packet.link.decision_class.value
        and link.superseded_at is None
        and claim.person_id == str(packet.person.id)
        and claim.organization_id is None
        and claim.predicate == NEC_CANDIDACY_PREDICATE
        and claim.proposition == packet.claim.proposition
        and claim.subject == packet.claim.subject
        and claim.object_text == packet.claim.object_text
        and claim.qualifiers == packet.claim.qualifiers
        and claim.epistemic_status == packet.claim.epistemic_status.value
        and claim.asserted_as_true is False
        and claim.publication_status
        in {
            PublicationStatus.DRAFT.value,
            PublicationStatus.REVIEW.value,
            PublicationStatus.PUBLISHED.value,
            PublicationStatus.WITHHELD.value,
        }
        and claim.superseded_at is None
        and evidence.claim_id == str(packet.claim.id)
        and evidence.source_id == str(packet.evidence.source_id)
        and evidence.snapshot_id == str(packet.evidence.snapshot_id)
        and evidence.feeder_observation_id == str(packet.evidence.feeder_observation_id)
        and evidence.stance == packet.evidence.stance.value
    )
    if not immutable_exact:
        return "CONFLICT"

    initial_exact = (
        person.canonical_name == packet.person.canonical_name
        and person.identity_status == packet.person.identity_status.value
        and person.valid_from == packet.person.valid_from
        and person.recorded_at == packet.person.recorded_at
        and person.superseded_at is None
        and link.linked_at == packet.link.linked_at
        and claim.publication_status == packet.claim.publication_status.value
        and claim.valid_from == packet.claim.valid_from
        and claim.recorded_at == packet.claim.recorded_at
    )
    return "EXACT" if initial_exact else "MANAGED"


def prepare_nec_person_materialization(
    session: Session,
    *,
    election_id: str = "20260603",
    election_types: Sequence[int] = DEFAULT_ELECTION_TYPES,
) -> NecPersonPreflight:
    type_tuple = tuple(sorted({int(item) for item in election_types}))
    if not election_id.isdigit() or len(election_id) != 8 or not type_tuple:
        raise ValueError("valid election_id and at least one election type are required")

    rows_by_scope: dict[str, list[db.FeederObservationRow]] = {}
    current_rows: list[db.FeederObservationRow] = []
    contexts_by_scope: dict[str, tuple[SourceCheckpoint, SourceRun, dict[str, str]]] = {}
    scope_totals: dict[str, int] = {}

    for election_type in type_tuple:
        scope = f"{election_id}:{election_type}"
        checkpoint_row = session.scalar(
            select(db.SourceCheckpointRow).where(
                db.SourceCheckpointRow.feeder == NEC_CANDIDATE_FEEDER,
                db.SourceCheckpointRow.scope_key == scope,
            )
        )
        if checkpoint_row is None or checkpoint_row.last_run_id is None:
            raise NecPersonMaterializationError(
                "CHECKPOINT_REQUIRED", f"missing NEC candidate checkpoint for {scope}"
            )
        run_row = session.get(db.SourceRunRow, checkpoint_row.last_run_id)
        if run_row is None:
            raise NecPersonMaterializationError(
                "CHECKPOINT_REQUIRED", f"missing NEC candidate run for {scope}"
            )
        checkpoint = checkpoint_from_row(checkpoint_row)
        run = run_from_row(run_row)
        hashes = checkpoint.metadata.get("seen_provider_hashes")
        try:
            total = int(checkpoint.metadata["total_count"])
        except (KeyError, TypeError, ValueError):
            raise NecPersonMaterializationError(
                "CHECKPOINT_CONFLICT", f"invalid NEC candidate checkpoint for {scope}"
            ) from None
        if not isinstance(hashes, dict) or len(hashes) != total:
            raise NecPersonMaterializationError(
                "CHECKPOINT_CONFLICT", f"incomplete NEC candidate manifest for {scope}"
            )
        rows = list(
            session.scalars(
                select(db.FeederObservationRow)
                .where(
                    db.FeederObservationRow.feeder == NEC_CANDIDATE_FEEDER,
                    db.FeederObservationRow.scope_key == scope,
                )
                .order_by(
                    db.FeederObservationRow.provider_record_key,
                    db.FeederObservationRow.recorded_at,
                )
            )
        )
        version_rows: dict[str, list[db.FeederObservationRow]] = defaultdict(list)
        current: dict[str, db.FeederObservationRow] = {}
        for row in rows:
            version_rows[row.provider_record_key].append(row)
            if hashes.get(row.provider_record_key) == row.content_hash:
                if row.provider_record_key in current:
                    raise NecPersonMaterializationError(
                        "CURRENT_VERSION_DUPLICATE",
                        f"duplicate current NEC candidate row in {scope}",
                    )
                current[row.provider_record_key] = row
        if set(current) != set(hashes):
            raise NecPersonMaterializationError(
                "CURRENT_VERSION_MISSING",
                f"checkpoint manifest differs from persisted NEC candidate rows in {scope}",
            )
        rows_by_scope[scope] = rows
        current_rows.extend(current.values())
        contexts_by_scope[scope] = (checkpoint, run, hashes)
        scope_totals[scope] = total

    huboid_counts = Counter(row.provider_record_key for row in current_rows)
    active_people = list(
        session.scalars(select(db.PersonRow).where(db.PersonRow.superseded_at.is_(None)))
    )
    collision_names = {row.canonical_name for row in active_people}
    collision_names.update(
        session.scalars(
            select(db.PersonAliasRow.name).where(db.PersonAliasRow.superseded_at.is_(None))
        )
    )

    artifact_people = {row.id: row for row in session.scalars(select(db.PersonRow))}
    aliases_by_person: dict[str, set[str]] = defaultdict(set)
    for alias in session.scalars(select(db.PersonAliasRow)):
        aliases_by_person[alias.person_id].add(alias.name)
    artifact_links = {row.id: row for row in session.scalars(select(db.PersonObservationLinkRow))}
    artifact_claims = {row.id: row for row in session.scalars(select(db.ClaimRow))}
    artifact_evidence = {row.id: row for row in session.scalars(select(db.ClaimEvidenceRow))}

    observation_ids = [row.id for row in current_rows]
    active_links: dict[str, list[db.PersonObservationLinkRow]] = defaultdict(list)
    if observation_ids:
        for link in session.scalars(
            select(db.PersonObservationLinkRow).where(
                db.PersonObservationLinkRow.observation_id.in_(observation_ids),
                db.PersonObservationLinkRow.superseded_at.is_(None),
            )
        ):
            active_links[link.observation_id].append(link)

    snapshot_ids = {row.snapshot_id for row in current_rows}
    snapshots = {
        row.id: row
        for row in session.scalars(
            select(db.SourceSnapshotRow).where(db.SourceSnapshotRow.id.in_(snapshot_ids))
        )
    }
    source_ids = {row.source_id for row in snapshots.values()}
    sources = {
        row.id: row
        for row in session.scalars(select(db.SourceRow).where(db.SourceRow.id.in_(source_ids)))
    }
    policy_ids = {row.policy_id for row in sources.values()}
    policies = {
        row.id: row
        for row in session.scalars(
            select(db.SourcePolicyRow).where(db.SourcePolicyRow.id.in_(policy_ids))
        )
    }

    versions_by_identity: dict[tuple[str, str], tuple[FeederObservation, ...]] = {}
    for scope, rows in rows_by_scope.items():
        grouped: dict[str, list[FeederObservation]] = defaultdict(list)
        for row in rows:
            grouped[row.provider_record_key].append(observation_from_row(row))
        for provider_key, observation_versions in grouped.items():
            versions_by_identity[(scope, provider_key)] = tuple(observation_versions)

    items: list[PreparedNecPerson] = []
    for row in sorted(current_rows, key=lambda item: (item.scope_key, item.provider_record_key)):
        observation = observation_from_row(row)
        canonical_name = str(observation.normalized.get("canonical_name") or "").strip()
        snapshot_row = snapshots.get(row.snapshot_id)
        source_row = sources.get(snapshot_row.source_id) if snapshot_row else None
        policy_row = policies.get(source_row.policy_id) if source_row else None
        if snapshot_row is None or source_row is None or policy_row is None:
            items.append(
                PreparedNecPerson(
                    observation.id,
                    observation.scope_key,
                    observation.provider_record_key,
                    observation.content_hash,
                    canonical_name,
                    "CONFLICT",
                    "PROVENANCE_MISSING",
                )
            )
            continue

        checkpoint, run, _ = contexts_by_scope[observation.scope_key]
        try:
            context = validate_nec_candidate_source_context(
                observation,
                snapshot=snapshot_from_row(snapshot_row),
                source=source_from_row(source_row),
                policy=policy_from_row(policy_row),
                checkpoint=checkpoint,
                run=run,
                versions=versions_by_identity[
                    (observation.scope_key, observation.provider_record_key)
                ],
            )
        except NecPersonMaterializationError as exc:
            action = (
                "REVIEW"
                if exc.code in {"HISTORICAL_VERSION_DRIFT", "IDENTITY_ANCHOR_MISSING"}
                else "CONFLICT"
            )
            items.append(
                PreparedNecPerson(
                    observation.id,
                    observation.scope_key,
                    observation.provider_record_key,
                    observation.content_hash,
                    canonical_name,
                    action,
                    exc.code,
                )
            )
            continue

        packet = build_nec_source_context_packet(context)
        state = _packet_state(
            packet,
            people=artifact_people,
            links=artifact_links,
            claims=artifact_claims,
            evidence_rows=artifact_evidence,
            aliases_by_person=aliases_by_person,
        )
        if state in {"EXACT", "MANAGED"}:
            items.append(
                PreparedNecPerson(
                    observation.id,
                    observation.scope_key,
                    observation.provider_record_key,
                    observation.content_hash,
                    context.canonical_name,
                    "NOOP",
                    "ALREADY_MATERIALIZED" if state == "EXACT" else "ALREADY_MANAGED",
                    packet,
                )
            )
            continue
        if state in {"PARTIAL", "CONFLICT"}:
            items.append(
                PreparedNecPerson(
                    observation.id,
                    observation.scope_key,
                    observation.provider_record_key,
                    observation.content_hash,
                    context.canonical_name,
                    "CONFLICT",
                    "PARTIAL_OR_CONFLICTING_MATERIALIZATION",
                    packet,
                )
            )
            continue

        links = active_links.get(row.id, [])
        if links:
            items.append(
                PreparedNecPerson(
                    observation.id,
                    observation.scope_key,
                    observation.provider_record_key,
                    observation.content_hash,
                    context.canonical_name,
                    "CONFLICT" if len(links) > 1 else "REVIEW",
                    "MULTIPLE_ACTIVE_LINKS" if len(links) > 1 else "ALREADY_LINKED_OTHER_CONTEXT",
                )
            )
            continue
        if huboid_counts[context.candidate_id] != 1:
            items.append(
                PreparedNecPerson(
                    observation.id,
                    observation.scope_key,
                    observation.provider_record_key,
                    observation.content_hash,
                    context.canonical_name,
                    "REVIEW",
                    "HUBOID_REPEATED_ACROSS_CURRENT_SCOPES",
                )
            )
            continue
        if context.canonical_name in collision_names:
            items.append(
                PreparedNecPerson(
                    observation.id,
                    observation.scope_key,
                    observation.provider_record_key,
                    observation.content_hash,
                    context.canonical_name,
                    "REVIEW",
                    "CURRENT_PERSON_OR_ALIAS_COLLISION",
                )
            )
            continue

        items.append(
            PreparedNecPerson(
                observation.id,
                observation.scope_key,
                observation.provider_record_key,
                observation.content_hash,
                context.canonical_name,
                "CREATE",
                "SAFE_NEC_SOURCE_CONTEXT",
                packet,
            )
        )

    current_people = (
        session.scalar(
            select(func.count())
            .select_from(db.PersonRow)
            .where(db.PersonRow.superseded_at.is_(None))
        )
        or 0
    )
    current_claims = (
        session.scalar(
            select(func.count()).select_from(db.ClaimRow).where(db.ClaimRow.superseded_at.is_(None))
        )
        or 0
    )
    current_evidence = session.scalar(select(func.count()).select_from(db.ClaimEvidenceRow)) or 0
    current_links = (
        session.scalar(
            select(func.count())
            .select_from(db.PersonObservationLinkRow)
            .where(db.PersonObservationLinkRow.superseded_at.is_(None))
        )
        or 0
    )
    current_published = (
        session.scalar(
            select(func.count())
            .select_from(db.ClaimRow)
            .where(
                db.ClaimRow.superseded_at.is_(None),
                db.ClaimRow.publication_status == PublicationStatus.PUBLISHED.value,
            )
        )
        or 0
    )
    if len(items) != len(current_rows):
        raise NecPersonMaterializationError(
            "ACCOUNTING_MISMATCH", "NEC candidate preflight did not classify every current row"
        )

    return NecPersonPreflight(
        items=tuple(items),
        election_id=election_id,
        election_types=type_tuple,
        current_people=current_people,
        current_claims=current_claims,
        current_evidence=current_evidence,
        current_links=current_links,
        current_published_claims=current_published,
        current_candidate_rows=len(current_rows),
        scope_totals=scope_totals,
    )


def commit_nec_person_materialization(
    session: Session,
    *,
    expected_receipt_sha256: str,
    election_id: str = "20260603",
    election_types: Sequence[int] = DEFAULT_ELECTION_TYPES,
) -> dict[str, Any]:
    expected = normalize_receipt_sha256(expected_receipt_sha256)
    lock_source_context_person_materialization(session, advisory_lock_id=187465324)

    preflight = prepare_nec_person_materialization(
        session,
        election_id=election_id,
        election_types=election_types,
    )
    if preflight.sha256() != expected:
        raise NecPersonMaterializationError(
            "STALE_PREFLIGHT", "NEC materialization preflight changed; run a fresh dry-run"
        )
    creates = preflight.create_items
    if not creates:
        return {
            **preflight.to_dict(),
            "status": "NOOP",
            "semantics": COMMIT_SEMANTICS,
            "write_performed": False,
            "created_people": 0,
            "created_claims": 0,
            "created_evidence": 0,
            "created_links": 0,
        }

    packets = []
    for item in creates:
        assert item.packet is not None
        packets.append(item.packet)
    created = persist_source_context_person_packets(session, packets)
    if created != len(creates):
        raise RuntimeError("NEC materialization persisted an unexpected packet count")

    return {
        **preflight.to_dict(),
        "status": "COMMITTED",
        "semantics": COMMIT_SEMANTICS,
        "write_performed": True,
        "created_people": created,
        "created_claims": created,
        "created_evidence": created,
        "created_links": created,
    }
