from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from packages.domain import db
from packages.domain.contracts import (
    Claim,
    FeederObservation,
    Organization,
    Source,
    SourceCheckpoint,
    SourcePolicy,
    SourceRun,
    SourceSnapshot,
)
from packages.domain.enums import IdentityStatus, PublicationStatus, SourceRunStatus
from packages.rendering.alio_organization_content import (
    ALIO_EXECUTIVE_FEEDER,
    ALIO_EXECUTIVE_PREDICATE,
    ALIO_EXECUTIVE_SCOPE,
    ALIO_EXECUTIVE_SEMANTIC_SCOPE,
    ALIO_EXECUTIVE_SOURCE_CONTRACT,
)
from packages.verification.alio_person_materialization import (
    AlioPersonMaterializationError,
    AlioPersonMaterializationPacket,
    build_alio_source_context_packet,
    validate_alio_person_source_context,
)

DRY_RUN_SEMANTICS = "ALIO_SAFE_SOURCE_CONTEXT_PERSON_DRY_RUN_V2"
COMMIT_SEMANTICS = "ALIO_SAFE_SOURCE_CONTEXT_PERSON_COMMIT_V2"


@dataclass(frozen=True)
class PreparedAlioPerson:
    observation_id: UUID
    provider_record_key: str
    content_hash: str
    canonical_name: str
    institution_name: str
    action: str
    reason: str
    packet: AlioPersonMaterializationPacket | None = None

    def selected_dict(self) -> dict[str, object]:
        if self.packet is None:
            raise ValueError("selected item has no materialization packet")
        return {
            "observation_id": str(self.observation_id),
            "provider_record_key": self.provider_record_key,
            "content_hash": self.content_hash,
            "canonical_name": self.canonical_name,
            "institution_name": self.institution_name,
            **self.packet.ids(),
            "person_identity_status": self.packet.person.identity_status.value,
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
class AlioPersonPreflight:
    items: tuple[PreparedAlioPerson, ...]
    current_people: int
    current_claims: int
    current_evidence: int
    current_links: int
    current_published_claims: int
    current_named_rows: int

    @property
    def create_items(self) -> tuple[PreparedAlioPerson, ...]:
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
            "source_contract": ALIO_EXECUTIVE_SOURCE_CONTRACT,
            "feeder": ALIO_EXECUTIVE_FEEDER,
            "scope_key": ALIO_EXECUTIVE_SCOPE,
            "current_named_rows": self.current_named_rows,
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


def _observation(row: db.FeederObservationRow) -> FeederObservation:
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


def _snapshot(row: db.SourceSnapshotRow) -> SourceSnapshot:
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


def _source(row: db.SourceRow) -> Source:
    return Source.model_validate(row, from_attributes=True)


def _policy(row: db.SourcePolicyRow) -> SourcePolicy:
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


def _checkpoint(row: db.SourceCheckpointRow) -> SourceCheckpoint:
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


def _run(row: db.SourceRunRow) -> SourceRun:
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


def _claim(row: db.ClaimRow) -> Claim:
    return Claim.model_validate(row, from_attributes=True)


def _organization(row: db.OrganizationRow) -> Organization:
    return Organization.model_validate(row, from_attributes=True)


def _packet_state(
    packet: AlioPersonMaterializationPacket,
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
        and person.identity_status in {
            IdentityStatus.REVIEW.value,
            IdentityStatus.RESOLVED.value,
        }
        and link.person_id == str(packet.person.id)
        and link.observation_id == str(packet.link.observation_id)
        and link.action == packet.link.action.value
        and link.decision_class == packet.link.decision_class.value
        and claim.person_id == str(packet.person.id)
        and claim.organization_id is None
        and claim.subject == packet.claim.subject
        and claim.predicate == packet.claim.predicate
        and claim.proposition == packet.claim.proposition
        and claim.object_text == packet.claim.object_text
        and claim.epistemic_status == packet.claim.epistemic_status.value
        and claim.asserted_as_true is False
        and claim.qualifiers == packet.claim.qualifiers
        and claim.publication_status in {
            PublicationStatus.DRAFT.value,
            PublicationStatus.REVIEW.value,
            PublicationStatus.PUBLISHED.value,
            PublicationStatus.WITHHELD.value,
        }
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
        and person.valid_to == packet.person.valid_to
        and person.recorded_at == packet.person.recorded_at
        and person.superseded_at is None
        and link.linked_at == packet.link.linked_at
        and link.superseded_at is None
        and claim.publication_status == packet.claim.publication_status.value
        and claim.valid_from == packet.claim.valid_from
        and claim.valid_to == packet.claim.valid_to
        and claim.recorded_at == packet.claim.recorded_at
        and claim.superseded_at is None
    )
    return "EXACT" if initial_exact else "MANAGED"


def _current_checkpoint(
    session: Session,
) -> tuple[SourceCheckpoint, SourceRun, dict[str, str]]:
    row = session.scalar(
        select(db.SourceCheckpointRow).where(
            db.SourceCheckpointRow.feeder == ALIO_EXECUTIVE_FEEDER,
            db.SourceCheckpointRow.scope_key == ALIO_EXECUTIVE_SCOPE,
        )
    )
    if row is None or row.last_run_id is None:
        raise AlioPersonMaterializationError(
            "CHECKPOINT_REQUIRED",
            "ALIO safe materialization requires a committed current-roster checkpoint",
        )
    checkpoint = _checkpoint(row)
    run_row = session.get(db.SourceRunRow, str(checkpoint.last_run_id))
    if run_row is None:
        raise AlioPersonMaterializationError("CHECKPOINT_REQUIRED", "checkpoint run is missing")
    run = _run(run_row)
    metadata = checkpoint.metadata
    hashes = metadata.get("seen_provider_hashes")
    disclosures = metadata.get("seen_current_disclosures")
    no_current = metadata.get("no_current_disclosures")
    institution_codes = metadata.get("institution_codes")
    institution_total = metadata.get("institution_total")
    coverage_ok = (
        isinstance(institution_total, int)
        and institution_total > 0
        and isinstance(institution_codes, list)
        and len(institution_codes) == institution_total
        and len(set(institution_codes)) == institution_total
        and isinstance(disclosures, dict)
        and isinstance(no_current, list)
        and (set(disclosures.values()) | set(no_current)) == set(institution_codes)
        and not (set(disclosures.values()) & set(no_current))
        and checkpoint.cursor == str(institution_total)
    )
    if (
        run.status != SourceRunStatus.SUCCESS
        or run.feeder != ALIO_EXECUTIVE_FEEDER
        or run.scope_key != ALIO_EXECUTIVE_SCOPE
        or run.checkpoint_after != checkpoint.cursor
        or metadata.get("source_contract") != ALIO_EXECUTIVE_SOURCE_CONTRACT
        or not coverage_ok
        or not isinstance(hashes, dict)
        or not hashes
        or run.records_seen < len(hashes)
        or any(
            not isinstance(key, str)
            or not isinstance(value, str)
            or len(value) != 64
            for key, value in hashes.items()
        )
    ):
        raise AlioPersonMaterializationError(
            "CHECKPOINT_INVALID",
            "ALIO current-roster checkpoint coverage is inconsistent",
        )
    return checkpoint, run, hashes


def prepare_alio_person_materialization(
    session: Session,
) -> AlioPersonPreflight:
    checkpoint, run, current_hashes = _current_checkpoint(session)

    rows = list(
        session.scalars(
            select(db.FeederObservationRow)
            .where(
                db.FeederObservationRow.feeder == ALIO_EXECUTIVE_FEEDER,
                db.FeederObservationRow.scope_key == ALIO_EXECUTIVE_SCOPE,
            )
            .order_by(db.FeederObservationRow.provider_record_key, db.FeederObservationRow.recorded_at)
        )
    )
    versions_by_key: dict[str, list[db.FeederObservationRow]] = defaultdict(list)
    current_by_key: dict[str, db.FeederObservationRow] = {}
    for row in rows:
        versions_by_key[row.provider_record_key].append(row)
        if current_hashes.get(row.provider_record_key) == row.content_hash:
            if row.provider_record_key in current_by_key:
                raise AlioPersonMaterializationError(
                    "CURRENT_VERSION_DUPLICATE",
                    "current ALIO provider identity maps to multiple persisted rows",
                )
            current_by_key[row.provider_record_key] = row
    if set(current_by_key) != set(current_hashes):
        raise AlioPersonMaterializationError(
            "CURRENT_VERSION_MISSING",
            "current ALIO checkpoint manifest and persisted observations differ",
        )

    named_rows = [
        row
        for row in current_by_key.values()
        if row.semantic_scope == ALIO_EXECUTIVE_SEMANTIC_SCOPE
        and row.normalized_json.get("name_status") == "PUBLIC"
        and isinstance(row.normalized_json.get("canonical_name"), str)
        and row.normalized_json.get("canonical_name", "").strip()
    ]
    name_counts = Counter(row.normalized_json["canonical_name"].strip() for row in named_rows)

    active_people = list(
        session.scalars(select(db.PersonRow).where(db.PersonRow.superseded_at.is_(None)))
    )
    collision_names = {row.canonical_name for row in active_people}
    collision_names.update(
        session.scalars(
            select(db.PersonAliasRow.name).where(db.PersonAliasRow.superseded_at.is_(None))
        )
    )
    artifact_people = {
        row.id: row for row in session.scalars(select(db.PersonRow))
    }
    aliases_by_person: dict[str, set[str]] = defaultdict(set)
    for alias_row in session.scalars(select(db.PersonAliasRow)):
        aliases_by_person[alias_row.person_id].add(alias_row.name)
    artifact_links = {
        row.id: row for row in session.scalars(select(db.PersonObservationLinkRow))
    }
    artifact_claims = {
        row.id: row for row in session.scalars(select(db.ClaimRow))
    }
    artifact_evidence = {
        row.id: row for row in session.scalars(select(db.ClaimEvidenceRow))
    }

    observation_ids = [row.id for row in named_rows]
    active_links: dict[str, list[db.PersonObservationLinkRow]] = defaultdict(list)
    if observation_ids:
        for link_row in session.scalars(
            select(db.PersonObservationLinkRow).where(
                db.PersonObservationLinkRow.observation_id.in_(observation_ids),
                db.PersonObservationLinkRow.superseded_at.is_(None),
            )
        ):
            active_links[link_row.observation_id].append(link_row)

    snapshot_ids = {row.snapshot_id for row in named_rows}
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

    org_claims_by_observation: dict[str, list[Claim]] = defaultdict(list)
    if observation_ids:
        pairs = session.execute(
            select(db.ClaimEvidenceRow.feeder_observation_id, db.ClaimRow)
            .join(db.ClaimRow, db.ClaimEvidenceRow.claim_id == db.ClaimRow.id)
            .where(
                db.ClaimEvidenceRow.feeder_observation_id.in_(observation_ids),
                db.ClaimRow.predicate == ALIO_EXECUTIVE_PREDICATE,
                db.ClaimRow.publication_status == PublicationStatus.PUBLISHED.value,
                db.ClaimRow.superseded_at.is_(None),
            )
        ).all()
        for observation_id, claim_row in pairs:
            if observation_id:
                org_claims_by_observation[observation_id].append(_claim(claim_row))
    organization_ids = {
        claim.organization_id
        for claims in org_claims_by_observation.values()
        for claim in claims
        if claim.organization_id is not None
    }
    organizations = {
        row.id: _organization(row)
        for row in session.scalars(
            select(db.OrganizationRow).where(db.OrganizationRow.id.in_([str(i) for i in organization_ids]))
        )
    }

    items: list[PreparedAlioPerson] = []
    for row in sorted(named_rows, key=lambda item: (item.provider_record_key, item.content_hash)):
        observation = _observation(row)
        name = observation.normalized["canonical_name"].strip()
        institution_name = str(observation.normalized.get("institution_name") or "").strip()

        snapshot_row = snapshots.get(row.snapshot_id)
        source_row = sources.get(snapshot_row.source_id) if snapshot_row else None
        policy_row = policies.get(source_row.policy_id) if source_row else None
        if snapshot_row is None or source_row is None or policy_row is None:
            items.append(
                PreparedAlioPerson(
                    observation.id,
                    observation.provider_record_key,
                    observation.content_hash,
                    name,
                    institution_name,
                    "CONFLICT",
                    "PROVENANCE_MISSING",
                )
            )
            continue

        candidate_claims = tuple(org_claims_by_observation.get(row.id, ()))
        candidate_org_ids = {claim.organization_id for claim in candidate_claims if claim.organization_id}
        organization = (
            organizations.get(str(next(iter(candidate_org_ids))))
            if len(candidate_org_ids) == 1
            else None
        )
        try:
            context = validate_alio_person_source_context(
                observation,
                snapshot=_snapshot(snapshot_row),
                source=_source(source_row),
                policy=_policy(policy_row),
                checkpoint=checkpoint,
                run=run,
                versions=tuple(_observation(item) for item in versions_by_key[row.provider_record_key]),
                organization_claims=candidate_claims,
                organization=organization,
            )
        except AlioPersonMaterializationError as exc:
            action = "REVIEW" if exc.code == "HISTORICAL_VERSION_DRIFT" else "CONFLICT"
            items.append(
                PreparedAlioPerson(
                    observation.id,
                    observation.provider_record_key,
                    observation.content_hash,
                    name,
                    institution_name,
                    action,
                    exc.code,
                )
            )
            continue

        packet = build_alio_source_context_packet(context)
        state = _packet_state(
            packet,
            people=artifact_people,
            links=artifact_links,
            claims=artifact_claims,
            evidence_rows=artifact_evidence,
            aliases_by_person=aliases_by_person,
        )
        links = active_links.get(row.id, [])
        if state in {"EXACT", "MANAGED"}:
            items.append(
                PreparedAlioPerson(
                    observation.id,
                    observation.provider_record_key,
                    observation.content_hash,
                    name,
                    institution_name,
                    "NOOP",
                    (
                        "ALREADY_MATERIALIZED"
                        if state == "EXACT"
                        else "ALREADY_MANAGED"
                    ),
                    packet,
                )
            )
            continue
        if state in {"PARTIAL", "CONFLICT"}:
            items.append(
                PreparedAlioPerson(
                    observation.id,
                    observation.provider_record_key,
                    observation.content_hash,
                    name,
                    institution_name,
                    "CONFLICT",
                    "PARTIAL_OR_CONFLICTING_MATERIALIZATION",
                    packet,
                )
            )
            continue
        if links:
            reason = "ALREADY_MANAGED_LINK" if len(links) == 1 else "MULTIPLE_ACTIVE_LINKS"
            action = "NOOP" if len(links) == 1 else "CONFLICT"
            items.append(
                PreparedAlioPerson(
                    observation.id,
                    observation.provider_record_key,
                    observation.content_hash,
                    name,
                    institution_name,
                    action,
                    reason,
                )
            )
            continue
        if name_counts[name] != 1:
            items.append(
                PreparedAlioPerson(
                    observation.id,
                    observation.provider_record_key,
                    observation.content_hash,
                    name,
                    institution_name,
                    "REVIEW",
                    "CURRENT_NAME_REPEATED",
                )
            )
            continue
        if name in collision_names:
            items.append(
                PreparedAlioPerson(
                    observation.id,
                    observation.provider_record_key,
                    observation.content_hash,
                    name,
                    institution_name,
                    "REVIEW",
                    "CURRENT_PERSON_OR_ALIAS_COLLISION",
                )
            )
            continue

        items.append(
            PreparedAlioPerson(
                observation.id,
                observation.provider_record_key,
                observation.content_hash,
                name,
                institution_name,
                "CREATE",
                "SAFE_SINGLETON_SOURCE_CONTEXT",
                packet,
            )
        )

    current_people = (
        session.scalar(
            select(func.count()).select_from(db.PersonRow).where(db.PersonRow.superseded_at.is_(None))
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
    if len(items) != len(named_rows):
        raise AlioPersonMaterializationError(
            "ACCOUNTING_MISMATCH",
            "ALIO named-row preflight did not classify every current named row",
        )
    return AlioPersonPreflight(
        items=tuple(items),
        current_people=current_people,
        current_claims=current_claims,
        current_evidence=current_evidence,
        current_links=current_links,
        current_published_claims=current_published,
        current_named_rows=len(named_rows),
    )


def commit_alio_person_materialization(
    session: Session,
    *,
    expected_receipt_sha256: str,
) -> dict[str, Any]:
    if len(expected_receipt_sha256) != 64 or any(
        char not in "0123456789abcdef" for char in expected_receipt_sha256.casefold()
    ):
        raise ValueError("expected receipt SHA-256 must be 64 hex characters")
    expected = expected_receipt_sha256.casefold()

    if session.get_bind().dialect.name == "postgresql":
        session.execute(text("SELECT pg_advisory_xact_lock(187465323)"))
        session.execute(text("LOCK TABLE people IN SHARE ROW EXCLUSIVE MODE"))
        session.execute(text("LOCK TABLE person_observation_links IN SHARE ROW EXCLUSIVE MODE"))
        session.execute(text("LOCK TABLE claims IN SHARE ROW EXCLUSIVE MODE"))
        session.execute(text("LOCK TABLE claim_evidence IN SHARE ROW EXCLUSIVE MODE"))

    preflight = prepare_alio_person_materialization(session)
    if preflight.sha256() != expected:
        raise AlioPersonMaterializationError(
            "STALE_PREFLIGHT",
            "ALIO materialization preflight changed; run a fresh dry-run",
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

    people_rows = []
    link_rows = []
    claim_rows = []
    evidence_rows = []
    for item in creates:
        assert item.packet is not None
        packet = item.packet
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

    return {
        **preflight.to_dict(),
        "status": "COMMITTED",
        "semantics": COMMIT_SEMANTICS,
        "write_performed": True,
        "created_people": len(creates),
        "created_claims": len(creates),
        "created_evidence": len(creates),
        "created_links": len(creates),
    }
