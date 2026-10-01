from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from packages.domain.contracts import Person
from packages.domain.enums import PublicationStatus
from packages.persistence.errors import GoldenSeedError
from packages.persistence.mapping import _policy, _snapshot, _source, _temporal
from packages.persistence.models import (
    ClaimEvidenceRow,
    ClaimRow,
    DecisionEpisodeRow,
    FeederObservationRow,
    PersonRow,
    RelationshipRow,
    SourceOriginClusterRow,
    SourcePolicyRow,
    SourceRow,
    SourceSnapshotRow,
)
from packages.verification.claims import validate_claim_publication
from packages.verification.golden import GoldenSet, load_golden_set
from packages.verification.person_onboarding import ReviewedPersonBundle, ReviewedPersonImportError
from packages.verification.policy import PolicyAction, PolicyDenied, require_policy


class OnboardingRepository:
    def __init__(self, session: Session):
        self._session = session

    def seed_golden(self, golden: GoldenSet | None = None) -> None:
        session = self._session
        if session.scalar(select(PersonRow.id).limit(1)) is not None:
            raise GoldenSeedError("Golden Set seeding requires an empty migrated database")
        self._seed(session, golden or load_golden_set())
        session.flush()

    @staticmethod
    def _temporal(contract) -> dict:
        return {
            "valid_from": contract.valid_from,
            "valid_to": contract.valid_to,
            "recorded_at": contract.recorded_at,
            "superseded_at": contract.superseded_at,
        }

    def _seed(self, session: Session, golden: GoldenSet) -> None:
        for policy in golden.policies:
            data = policy.model_dump()
            data["id"] = str(policy.id)
            data["collection_mode"] = policy.collection_mode.value
            session.add(SourcePolicyRow(**data))
        session.flush()
        source_origin_clusters: dict[str, str] = {}
        for source in golden.sources:
            if source.origin_cluster_id is not None:
                source_origin_clusters[str(source.id)] = str(source.origin_cluster_id)
            session.add(
                SourceRow(
                    id=str(source.id),
                    url=str(source.url),
                    title=source.title,
                    publisher=source.publisher,
                    published_at=source.published_at,
                    policy_id=str(source.policy_id),
                    origin_cluster_id=None,
                )
            )
        session.flush()
        for snapshot in golden.snapshots:
            session.add(
                SourceSnapshotRow(
                    id=str(snapshot.id),
                    source_id=str(snapshot.source_id),
                    fetched_at=snapshot.fetched_at,
                    content_hash=snapshot.content_hash,
                    metadata_json=snapshot.metadata,
                    fulltext=snapshot.fulltext,
                )
            )
        session.flush()
        for cluster in golden.origin_clusters:
            session.add(
                SourceOriginClusterRow(
                    id=str(cluster.id),
                    canonical_source_id=str(cluster.canonical_source_id),
                    member_source_ids=[str(item) for item in cluster.member_source_ids],
                    reason=cluster.reason,
                )
            )
        session.flush()
        for source_id, cluster_id in source_origin_clusters.items():
            source_row = session.get(SourceRow, source_id)
            if source_row is None:
                raise GoldenSeedError(f"Golden source disappeared during seed: {source_id}")
            source_row.origin_cluster_id = cluster_id
        session.flush()
        for item in golden.people:
            person = item.person
            session.add(
                PersonRow(
                    id=str(person.id),
                    canonical_name=person.canonical_name,
                    birth_date=person.birth_date,
                    identity_status=person.identity_status.value,
                    **_temporal(person),
                )
            )
        session.flush()
        for claim in golden.claims:
            session.add(
                ClaimRow(
                    id=str(claim.id),
                    person_id=str(claim.person_id),
                    organization_id=None,
                    proposition=claim.proposition,
                    subject=claim.subject,
                    predicate=claim.predicate,
                    object_text=claim.object_text,
                    qualifiers=claim.qualifiers,
                    epistemic_status=claim.epistemic_status.value,
                    publication_status=claim.publication_status.value,
                    asserted_as_true=claim.asserted_as_true,
                    resolution_note=claim.resolution_note,
                    **_temporal(claim),
                )
            )
        session.flush()
        for evidence in golden.evidence:
            session.add(
                ClaimEvidenceRow(
                    id=str(evidence.id),
                    claim_id=str(evidence.claim_id),
                    source_id=str(evidence.source_id),
                    snapshot_id=str(evidence.snapshot_id) if evidence.snapshot_id else None,
                    stance=evidence.stance.value,
                    excerpt=evidence.excerpt,
                )
            )
        session.flush()
        for relationship in golden.relationships:
            session.add(
                RelationshipRow(
                    id=str(relationship.id),
                    payload=relationship.model_dump(mode="json"),
                    **_temporal(relationship),
                )
            )
        for episode in golden.episodes:
            session.add(
                DecisionEpisodeRow(
                    id=str(episode.id),
                    payload=episode.model_dump(mode="json"),
                    **_temporal(episode),
                )
            )

    def import_reviewed_person(self, bundle: ReviewedPersonBundle) -> Person:
        session = self._session
        if session.get(PersonRow, str(bundle.person.id)) is not None:
            raise ReviewedPersonImportError(
                "Person ID already exists; reviewed import does not upsert"
            )
        declared_rows = (
            *((SourcePolicyRow, item.id) for item in bundle.policies),
            *((SourceRow, item.id) for item in bundle.sources),
            *((SourceSnapshotRow, item.id) for item in bundle.snapshots),
            *((ClaimRow, item.id) for item in bundle.claims),
            *((ClaimEvidenceRow, item.id) for item in bundle.evidence),
        )
        for row_type, record_id in declared_rows:
            if session.get(row_type, str(record_id)) is not None:
                raise ReviewedPersonImportError(
                    f"reviewed import record ID already exists: {record_id}"
                )
        policies = {item.id: item for item in bundle.policies}
        sources = {item.id: item for item in bundle.sources}
        snapshots = {item.id: item for item in bundle.snapshots}
        needed_source_ids = {
            *(item.source_id for item in bundle.evidence),
            *(item.source_id for item in bundle.snapshots),
        }
        for source_id in needed_source_ids:
            if source_id in sources:
                continue
            source_row = session.get(SourceRow, str(source_id))
            if source_row is None:
                raise ReviewedPersonImportError(
                    f"reviewed import references missing source: {source_id}"
                )
            sources[source_id] = _source(source_row)
        needed_policy_ids = {source.policy_id for source in sources.values()}
        for policy_id in needed_policy_ids:
            if policy_id in policies:
                continue
            policy_row = session.get(SourcePolicyRow, str(policy_id))
            if policy_row is None:
                raise ReviewedPersonImportError(
                    f"reviewed import references missing SourcePolicy: {policy_id}"
                )
            policies[policy_id] = _policy(policy_row)
        for source in bundle.sources:
            policy = policies[source.policy_id]
            try:
                require_policy(policy, PolicyAction.STORE_METADATA)
            except PolicyDenied as exc:
                raise ReviewedPersonImportError(
                    f"SourcePolicy forbids metadata storage for source {source.id}"
                ) from exc
        for snapshot in bundle.snapshots:
            if snapshot.source_id not in sources:
                raise ReviewedPersonImportError(f"snapshot {snapshot.id} references missing source")
            policy = policies[sources[snapshot.source_id].policy_id]
            try:
                require_policy(policy, PolicyAction.STORE_METADATA)
                if snapshot.fulltext:
                    require_policy(policy, PolicyAction.STORE_FULLTEXT)
            except PolicyDenied as exc:
                raise ReviewedPersonImportError(
                    f"SourcePolicy forbids snapshot storage for {snapshot.id}"
                ) from exc
        existing_snapshot_ids = {
            item.snapshot_id for item in bundle.evidence if item.snapshot_id is not None
        } - set(snapshots)
        for snapshot_id in existing_snapshot_ids:
            snapshot_row = session.get(SourceSnapshotRow, str(snapshot_id))
            if snapshot_row is None:
                raise ReviewedPersonImportError(
                    f"reviewed import references missing snapshot: {snapshot_id}"
                )
            snapshots[snapshot_id] = _snapshot(snapshot_row)
        for evidence in bundle.evidence:
            if evidence.feeder_observation_id is None:
                continue
            observation_row = session.get(FeederObservationRow, str(evidence.feeder_observation_id))
            if observation_row is None:
                raise ReviewedPersonImportError(
                    f"reviewed import references missing feeder observation: {evidence.feeder_observation_id}"
                )
            if evidence.snapshot_id is None:
                raise ReviewedPersonImportError(
                    f"ClaimEvidence with feeder observation requires a snapshot: {evidence.id}"
                )
            if str(evidence.snapshot_id) != observation_row.snapshot_id:
                raise ReviewedPersonImportError(
                    f"ClaimEvidence snapshot does not match feeder observation: {evidence.id}"
                )
            snapshot_row = session.get(SourceSnapshotRow, str(evidence.snapshot_id))
            if snapshot_row is None or snapshot_row.source_id != str(evidence.source_id):
                raise ReviewedPersonImportError(
                    f"ClaimEvidence source does not match feeder observation snapshot: {evidence.id}"
                )
        evidence_by_claim = {
            claim.id: [item for item in bundle.evidence if item.claim_id == claim.id]
            for claim in bundle.claims
        }
        for claim in bundle.claims:
            if claim.publication_status != PublicationStatus.PUBLISHED:
                continue
            claim_evidence = evidence_by_claim[claim.id]
            claim_sources = {
                item.source_id: sources[item.source_id]
                for item in claim_evidence
                if item.source_id in sources
            }
            claim_policies = {
                source.policy_id: policies[source.policy_id] for source in claim_sources.values()
            }
            gate = validate_claim_publication(
                claim, bundle.person, claim_evidence, claim_sources, claim_policies
            )
            if not gate.publishable:
                raise ReviewedPersonImportError(
                    f"published claim {claim.id} failed publication gate: {gate.failures}"
                )
        for policy in bundle.policies:
            data = policy.model_dump()
            data["id"] = str(policy.id)
            data["collection_mode"] = policy.collection_mode.value
            session.add(SourcePolicyRow(**data))
        for source in bundle.sources:
            session.add(
                SourceRow(
                    id=str(source.id),
                    url=str(source.url),
                    title=source.title,
                    publisher=source.publisher,
                    published_at=source.published_at,
                    policy_id=str(source.policy_id),
                    origin_cluster_id=str(source.origin_cluster_id)
                    if source.origin_cluster_id
                    else None,
                )
            )
        for snapshot in bundle.snapshots:
            session.add(
                SourceSnapshotRow(
                    id=str(snapshot.id),
                    source_id=str(snapshot.source_id),
                    fetched_at=snapshot.fetched_at,
                    content_hash=snapshot.content_hash,
                    metadata_json=snapshot.metadata,
                    fulltext=snapshot.fulltext,
                )
            )
        session.add(
            PersonRow(
                id=str(bundle.person.id),
                canonical_name=bundle.person.canonical_name,
                birth_date=bundle.person.birth_date,
                identity_status=bundle.person.identity_status.value,
                **_temporal(bundle.person),
            )
        )
        session.flush()
        for claim in bundle.claims:
            session.add(
                ClaimRow(
                    id=str(claim.id),
                    person_id=str(claim.person_id),
                    organization_id=None,
                    proposition=claim.proposition,
                    subject=claim.subject,
                    predicate=claim.predicate,
                    object_text=claim.object_text,
                    qualifiers=claim.qualifiers,
                    epistemic_status=claim.epistemic_status.value,
                    publication_status=claim.publication_status.value,
                    asserted_as_true=claim.asserted_as_true,
                    resolution_note=claim.resolution_note,
                    **_temporal(claim),
                )
            )
        session.flush()
        for evidence in bundle.evidence:
            session.add(
                ClaimEvidenceRow(
                    id=str(evidence.id),
                    claim_id=str(evidence.claim_id),
                    source_id=str(evidence.source_id),
                    snapshot_id=str(evidence.snapshot_id) if evidence.snapshot_id else None,
                    feeder_observation_id=str(evidence.feeder_observation_id)
                    if evidence.feeder_observation_id
                    else None,
                    stance=evidence.stance.value,
                    excerpt=evidence.excerpt,
                )
            )
        session.flush()
        return bundle.person

    def set_publication_status(self, claim_id: UUID, status: PublicationStatus) -> None:
        row = self._session.get(ClaimRow, str(claim_id))
        if row is None:
            raise ValueError("claim does not exist")
        row.publication_status = status.value

    def add_claim(self, claim: Claim, evidence: ClaimEvidence) -> None:
        """Stage a claim and its evidence in the caller's transaction."""
        self._session.add(
            ClaimRow(
                id=str(claim.id),
                person_id=str(claim.person_id),
                proposition=claim.proposition,
                subject=claim.subject,
                predicate=claim.predicate,
                object_text=claim.object_text,
                qualifiers=claim.qualifiers,
                epistemic_status=claim.epistemic_status.value,
                publication_status=claim.publication_status.value,
                asserted_as_true=claim.asserted_as_true,
                resolution_note=claim.resolution_note,
                **_temporal(claim),
            )
        )
        self._session.add(
            ClaimEvidenceRow(
                id=str(evidence.id),
                claim_id=str(evidence.claim_id),
                source_id=str(evidence.source_id),
                snapshot_id=str(evidence.snapshot_id) if evidence.snapshot_id else None,
                feeder_observation_id=str(evidence.feeder_observation_id)
                if evidence.feeder_observation_id
                else None,
                stance=evidence.stance.value,
                excerpt=evidence.excerpt,
            )
        )


from uuid import UUID

from packages.domain.contracts import Claim, ClaimEvidence
