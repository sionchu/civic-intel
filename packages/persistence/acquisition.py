from __future__ import annotations

from collections.abc import Iterable, Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from packages.application.results import BatchPageCommitResult
from packages.domain.contracts import (
    FeederObservation,
    Source,
    SourceCheckpoint,
    SourcePolicy,
    SourceRun,
    SourceSnapshot,
    now_utc,
)
from packages.domain.enums import SourceRunStatus
from packages.persistence.mapping import (
    _checkpoint,
    _observation,
    _policy,
    _snapshot,
    _source,
    _source_run,
)
from packages.persistence.models import (
    FeederObservationRow,
    SourceCheckpointRow,
    SourcePolicyRow,
    SourceRow,
    SourceRunRow,
    SourceSnapshotRow,
)


class AcquisitionRepository:
    def __init__(self, session: Session):
        self._session = session

    def start_source_run(
        self, feeder: str, scope_key: str, metadata: dict | None = None
    ) -> SourceRun:
        session = self._session
        checkpoint = session.scalar(
            select(SourceCheckpointRow).where(
                SourceCheckpointRow.feeder == feeder, SourceCheckpointRow.scope_key == scope_key
            )
        )
        run = SourceRun(
            feeder=feeder,
            scope_key=scope_key,
            checkpoint_before=checkpoint.cursor if checkpoint else None,
            metadata=metadata or {},
        )
        session.add(
            SourceRunRow(
                id=str(run.id),
                feeder=run.feeder,
                scope_key=run.scope_key,
                started_at=run.started_at,
                finished_at=None,
                status=run.status.value,
                checkpoint_before=run.checkpoint_before,
                checkpoint_after=None,
                records_seen=0,
                observations_created=0,
                observations_unchanged=0,
                error_code=None,
                error_summary=None,
                metadata_json=run.metadata,
            )
        )
        session.flush()
        return run

    def finish_source_run(
        self,
        run_id: UUID,
        status: SourceRunStatus,
        *,
        error_code: str | None = None,
        error_summary: str | None = None,
    ) -> SourceRun:
        if status not in {SourceRunStatus.SUCCESS, SourceRunStatus.PARTIAL, SourceRunStatus.FAILED}:
            raise ValueError("source run can only finish with a terminal status")
        lowered = (error_summary or "").casefold()
        if any(token in lowered for token in ("key=", "authkey=", "api_key", "token=")):
            raise ValueError("error_summary may not contain credentials")
        session = self._session
        row = session.get(SourceRunRow, str(run_id))
        if row is None:
            raise ValueError("source run does not exist")
        if row.status != SourceRunStatus.RUNNING.value:
            raise ValueError("source run is already finished")
        row.status = status.value
        row.finished_at = now_utc()
        row.error_code = error_code
        row.error_summary = error_summary
        session.flush()
        session.refresh(row)
        return _source_run(row)

    def source_run(self, run_id: UUID) -> SourceRun | None:
        session = self._session
        row = session.get(SourceRunRow, str(run_id))
        return _source_run(row) if row else None

    def source_runs(
        self, feeder: str | None = None, scope_key: str | None = None
    ) -> list[SourceRun]:
        statement = select(SourceRunRow)
        if feeder is not None:
            statement = statement.where(SourceRunRow.feeder == feeder)
        if scope_key is not None:
            statement = statement.where(SourceRunRow.scope_key == scope_key)
        session = self._session
        rows = session.scalars(statement.order_by(SourceRunRow.started_at, SourceRunRow.id))
        return [_source_run(row) for row in rows]

    def source_checkpoint(self, feeder: str, scope_key: str) -> SourceCheckpoint | None:
        session = self._session
        row = session.scalar(
            select(SourceCheckpointRow).where(
                SourceCheckpointRow.feeder == feeder, SourceCheckpointRow.scope_key == scope_key
            )
        )
        return _checkpoint(row) if row else None

    def source_checkpoints(self, feeder: str | None = None) -> list[SourceCheckpoint]:
        statement = select(SourceCheckpointRow)
        if feeder is not None:
            statement = statement.where(SourceCheckpointRow.feeder == feeder)
        session = self._session
        rows = session.scalars(statement.order_by(SourceCheckpointRow.scope_key))
        return [_checkpoint(row) for row in rows]

    def feeder_observations(
        self, feeder: str, scope_key: str, provider_record_key: str | None = None
    ) -> list[FeederObservation]:
        statement = select(FeederObservationRow).where(
            FeederObservationRow.feeder == feeder, FeederObservationRow.scope_key == scope_key
        )
        if provider_record_key is not None:
            statement = statement.where(
                FeederObservationRow.provider_record_key == provider_record_key
            )
        session = self._session
        rows = session.scalars(statement.order_by(FeederObservationRow.recorded_at))
        return [_observation(row) for row in rows]

    def feeder_observation_hash_manifest(
        self, feeder: str, scope_key: str
    ) -> list[tuple[str, str]]:
        """Load only provider identity and content hash for a feeder scope."""
        statement = select(
            FeederObservationRow.provider_record_key, FeederObservationRow.content_hash
        ).where(FeederObservationRow.feeder == feeder, FeederObservationRow.scope_key == scope_key)
        session = self._session
        return [
            (provider_record_key, content_hash)
            for provider_record_key, content_hash in session.execute(statement)
        ]

    def feeder_observation(self, observation_id: UUID) -> FeederObservation | None:
        session = self._session
        row = session.get(FeederObservationRow, str(observation_id))
        return _observation(row) if row else None

    def feeder_observation_contexts(
        self, observation_ids: Iterable[UUID]
    ) -> dict[UUID, tuple[FeederObservation, SourceSnapshot, Source, SourcePolicy]]:
        """Load exact observation-to-source provenance for a bounded batch."""
        requested_ids = tuple(sorted({str(observation_id) for observation_id in observation_ids}))
        if not requested_ids:
            return {}
        statement = (
            select(FeederObservationRow, SourceSnapshotRow, SourceRow, SourcePolicyRow)
            .join(SourceSnapshotRow, SourceSnapshotRow.id == FeederObservationRow.snapshot_id)
            .join(SourceRow, SourceRow.id == SourceSnapshotRow.source_id)
            .join(SourcePolicyRow, SourcePolicyRow.id == SourceRow.policy_id)
            .where(FeederObservationRow.id.in_(requested_ids))
        )
        contexts: dict[UUID, tuple[FeederObservation, SourceSnapshot, Source, SourcePolicy]] = {}
        session = self._session
        for observation_row, snapshot_row, source_row, policy_row in session.execute(statement):
            observation = _observation(observation_row)
            if observation.id in contexts:
                raise ValueError("feeder observation has multiple provenance contexts")
            contexts[observation.id] = (
                observation,
                _snapshot(snapshot_row),
                _source(source_row),
                _policy(policy_row),
            )
        return contexts

    def commit_source_page(
        self,
        *,
        run_id: UUID,
        policy: SourcePolicy,
        source: Source,
        snapshot: SourceSnapshot,
        observations: Sequence[FeederObservation],
        cursor: str,
        checkpoint_metadata: dict,
    ) -> BatchPageCommitResult:
        if source.policy_id != policy.id:
            raise ValueError("source policy identity does not match SourcePolicy")
        if snapshot.source_id != source.id:
            raise ValueError("snapshot source identity does not match Source")
        for observation in observations:
            if observation.run_id != run_id:
                raise ValueError("observation run identity does not match source run")
            if observation.snapshot_id != snapshot.id:
                raise ValueError("observation snapshot identity does not match page snapshot")
        session = self._session
        run_row = session.get(SourceRunRow, str(run_id))
        if run_row is None or run_row.status != SourceRunStatus.RUNNING.value:
            raise ValueError("source page requires a running source run")
        for observation in observations:
            if observation.feeder != run_row.feeder or observation.scope_key != run_row.scope_key:
                raise ValueError("observation scope does not match source run")
        policy_row = session.get(SourcePolicyRow, str(policy.id))
        domain_policy = session.scalar(
            select(SourcePolicyRow).where(SourcePolicyRow.domain == policy.domain)
        )
        if policy_row is None and domain_policy is not None:
            raise ValueError("SourcePolicy domain is already bound to another policy")
        if policy_row is None:
            policy_data = policy.model_dump()
            policy_data["id"] = str(policy.id)
            policy_data["collection_mode"] = policy.collection_mode.value
            session.add(SourcePolicyRow(**policy_data))
            session.flush()
        elif policy_row.domain != policy.domain:
            raise ValueError("SourcePolicy identity conflict")
        source_row = session.scalar(select(SourceRow).where(SourceRow.url == str(source.url)))
        if source_row is None:
            source_row = SourceRow(
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
            session.add(source_row)
            session.flush()
        elif source_row.policy_id != str(policy.id):
            raise ValueError("source URL is bound to an incompatible SourcePolicy")
        snapshot_row = session.scalar(
            select(SourceSnapshotRow).where(
                SourceSnapshotRow.source_id == source_row.id,
                SourceSnapshotRow.content_hash == snapshot.content_hash,
            )
        )
        if snapshot_row is None:
            snapshot_row = SourceSnapshotRow(
                id=str(snapshot.id),
                source_id=source_row.id,
                fetched_at=snapshot.fetched_at,
                content_hash=snapshot.content_hash,
                metadata_json=snapshot.metadata,
                fulltext=snapshot.fulltext,
            )
            session.add(snapshot_row)
            session.flush()
        created = 0
        unchanged = 0
        observation_ids: list[UUID] = []
        provider_keys = {item.provider_record_key for item in observations}
        existing_rows = (
            list(
                session.scalars(
                    select(FeederObservationRow).where(
                        FeederObservationRow.feeder == run_row.feeder,
                        FeederObservationRow.scope_key == run_row.scope_key,
                        FeederObservationRow.provider_record_key.in_(provider_keys),
                    )
                )
            )
            if provider_keys
            else []
        )
        existing_by_identity = {
            (row.provider_record_key, row.content_hash): row for row in existing_rows
        }
        for observation in observations:
            existing = existing_by_identity.get(
                (observation.provider_record_key, observation.content_hash)
            )
            if existing is not None:
                unchanged += 1
                observation_ids.append(UUID(existing.id))
                continue
            row = FeederObservationRow(
                id=str(observation.id),
                feeder=observation.feeder,
                scope_key=observation.scope_key,
                provider_record_key=observation.provider_record_key,
                snapshot_id=snapshot_row.id,
                run_id=str(observation.run_id),
                recorded_at=observation.recorded_at,
                provider_observed_at=observation.provider_observed_at,
                semantic_scope=observation.semantic_scope,
                identity_hints_json=observation.identity_hints,
                normalized_json=observation.normalized,
                content_hash=observation.content_hash,
            )
            session.add(row)
            existing_by_identity[observation.provider_record_key, observation.content_hash] = row
            created += 1
            observation_ids.append(observation.id)
        checkpoint_row = session.scalar(
            select(SourceCheckpointRow).where(
                SourceCheckpointRow.feeder == run_row.feeder,
                SourceCheckpointRow.scope_key == run_row.scope_key,
            )
        )
        if checkpoint_row is None:
            checkpoint = SourceCheckpoint(
                feeder=run_row.feeder,
                scope_key=run_row.scope_key,
                cursor=cursor,
                metadata=checkpoint_metadata,
                last_run_id=run_id,
            )
            checkpoint_row = SourceCheckpointRow(
                id=str(checkpoint.id),
                feeder=checkpoint.feeder,
                scope_key=checkpoint.scope_key,
                cursor=checkpoint.cursor,
                metadata_json=checkpoint.metadata,
                updated_at=checkpoint.updated_at,
                last_run_id=str(run_id),
            )
            session.add(checkpoint_row)
        else:
            checkpoint_row.cursor = cursor
            checkpoint_row.metadata_json = checkpoint_metadata
            checkpoint_row.updated_at = now_utc()
            checkpoint_row.last_run_id = str(run_id)
        run_row.records_seen += len(observations)
        run_row.observations_created += created
        run_row.observations_unchanged += unchanged
        run_row.checkpoint_after = cursor
        session.flush()
        return BatchPageCommitResult(
            snapshot_id=UUID(snapshot_row.id),
            observation_ids=tuple(observation_ids),
            observations_created=created,
            observations_unchanged=unchanged,
        )
