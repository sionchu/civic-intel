from __future__ import annotations

from collections.abc import Iterable, Sequence
from uuid import UUID

from packages.application.ports import UnitOfWorkFactory
from packages.application.results import (
    BatchPageCommitResult,
)
from packages.domain.contracts import (
    FeederObservation,
    Source,
    SourceCheckpoint,
    SourcePolicy,
    SourceRun,
    SourceSnapshot,
)
from packages.domain.enums import (
    SourceRunStatus,
)


class AcquisitionService:
    def __init__(self, uows: UnitOfWorkFactory):
        self.uows = uows

    def start_source_run(
        self, feeder: str, scope_key: str, metadata: dict | None = None
    ) -> SourceRun:
        self.uows.assert_ready()
        with self.uows(read_only=False) as uow:
            result = uow.acquisition.start_source_run(feeder, scope_key, metadata)
            uow.commit()
            return result

    def finish_source_run(
        self,
        run_id: UUID,
        status: SourceRunStatus,
        *,
        error_code: str | None = None,
        error_summary: str | None = None,
    ) -> SourceRun:
        self.uows.assert_ready()
        with self.uows(read_only=False) as uow:
            result = uow.acquisition.finish_source_run(
                run_id, status, error_code=error_code, error_summary=error_summary
            )
            uow.commit()
            return result

    def source_run(self, run_id: UUID) -> SourceRun | None:
        with self.uows(read_only=True) as uow:
            result = uow.acquisition.source_run(run_id)
            return result

    def source_runs(
        self, feeder: str | None = None, scope_key: str | None = None
    ) -> list[SourceRun]:
        with self.uows(read_only=True) as uow:
            result = uow.acquisition.source_runs(feeder, scope_key)
            return result

    def source_checkpoint(self, feeder: str, scope_key: str) -> SourceCheckpoint | None:
        with self.uows(read_only=True) as uow:
            result = uow.acquisition.source_checkpoint(feeder, scope_key)
            return result

    def source_checkpoints(self, feeder: str | None = None) -> list[SourceCheckpoint]:
        with self.uows(read_only=True) as uow:
            result = uow.acquisition.source_checkpoints(feeder)
            return result

    def feeder_observations(
        self, feeder: str, scope_key: str, provider_record_key: str | None = None
    ) -> list[FeederObservation]:
        with self.uows(read_only=True) as uow:
            result = uow.acquisition.feeder_observations(feeder, scope_key, provider_record_key)
            return result

    def feeder_observation_hash_manifest(
        self, feeder: str, scope_key: str
    ) -> list[tuple[str, str]]:
        with self.uows(read_only=True) as uow:
            result = uow.acquisition.feeder_observation_hash_manifest(feeder, scope_key)
            return result

    def feeder_observation(self, observation_id: UUID) -> FeederObservation | None:
        with self.uows(read_only=True) as uow:
            result = uow.acquisition.feeder_observation(observation_id)
            return result

    def feeder_observation_contexts(
        self, observation_ids: Iterable[UUID]
    ) -> dict[UUID, tuple[FeederObservation, SourceSnapshot, Source, SourcePolicy]]:
        with self.uows(read_only=True) as uow:
            result = uow.acquisition.feeder_observation_contexts(observation_ids)
            return result

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
        self.uows.assert_ready()
        with self.uows(read_only=False) as uow:
            result = uow.acquisition.commit_source_page(
                run_id=run_id,
                policy=policy,
                source=source,
                snapshot=snapshot,
                observations=observations,
                cursor=cursor,
                checkpoint_metadata=checkpoint_metadata,
            )
            uow.commit()
            return result
