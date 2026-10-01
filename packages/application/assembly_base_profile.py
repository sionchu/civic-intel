from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from packages.application.ports import UnitOfWork, UnitOfWorkFactory
from packages.domain.contracts import Claim, ClaimEvidence, FeederObservation, Person
from packages.domain.enums import IdentityStatus
from packages.verification.assembly_base_profile import (
    ASSEMBLY_BASE_PROFILE_FEEDER,
    ASSEMBLY_BASE_PROFILE_FIELDS,
    ASSEMBLY_BASE_PROFILE_SCOPE,
    ASSEMBLY_BASE_PROFILE_SOURCE_CONTRACT,
    AssemblyBaseProfileError,
    build_assembly_base_profile_bundle,
)


@dataclass(frozen=True)
class AssemblyBaseProfileRunResult:
    run_id: UUID
    observations_considered: int
    observations_published: int
    published_claims: int
    unchanged_claims: int
    missing_field_counts: dict[str, int] = field(default_factory=dict)
    skipped_observation_ids: tuple[UUID, ...] = ()


class AssemblyBaseProfilePublisher:
    """Publish only the exact manifest of the latest successful full roster run."""

    def __init__(self, uows: UnitOfWorkFactory) -> None:
        self.uows = uows

    def _latest_successful_observations(
        self, uow: UnitOfWork
    ) -> tuple[UUID, tuple[FeederObservation, ...]]:
        checkpoint = uow.acquisition.source_checkpoint(
            ASSEMBLY_BASE_PROFILE_FEEDER, ASSEMBLY_BASE_PROFILE_SCOPE
        )
        if checkpoint is None or checkpoint.last_run_id is None:
            raise AssemblyBaseProfileError(
                "Assembly current-roster success checkpoint is unavailable"
            )
        run = uow.acquisition.source_run(checkpoint.last_run_id)
        if (
            run is None
            or run.status.value != "SUCCESS"
            or run.feeder != ASSEMBLY_BASE_PROFILE_FEEDER
            or (run.scope_key != ASSEMBLY_BASE_PROFILE_SCOPE)
        ):
            raise AssemblyBaseProfileError(
                "Assembly base profile requires the latest successful full enumeration"
            )
        metadata = checkpoint.metadata
        if metadata.get("source_contract") != ASSEMBLY_BASE_PROFILE_SOURCE_CONTRACT:
            raise AssemblyBaseProfileError("Assembly success checkpoint source contract is invalid")
        raw_hashes = metadata.get("seen_provider_hashes")
        if not isinstance(raw_hashes, dict) or not raw_hashes:
            raise AssemblyBaseProfileError("Assembly success checkpoint lacks provider manifest")
        try:
            expected_total = int(metadata["list_total_count"])
            expected_pages = int(metadata["expected_pages"])
        except (KeyError, TypeError, ValueError):
            raise AssemblyBaseProfileError(
                "Assembly success checkpoint coverage metadata is invalid"
            ) from None
        if checkpoint.cursor != str(expected_pages) or len(raw_hashes) != expected_total:
            raise AssemblyBaseProfileError("Assembly success checkpoint coverage is incomplete")
        observations = uow.acquisition.feeder_observations(
            ASSEMBLY_BASE_PROFILE_FEEDER, ASSEMBLY_BASE_PROFILE_SCOPE
        )
        by_key: dict[str, FeederObservation] = {}
        for observation in observations:
            expected_hash = raw_hashes.get(observation.provider_record_key)
            if expected_hash != observation.content_hash:
                continue
            if observation.provider_record_key in by_key:
                raise AssemblyBaseProfileError(
                    "Assembly success manifest maps one provider key to multiple observations"
                )
            by_key[observation.provider_record_key] = observation
        if set(by_key) != set(raw_hashes):
            raise AssemblyBaseProfileError("Assembly success manifest lacks committed observations")
        return (run.id, tuple(by_key[key] for key in sorted(by_key)))

    def _publish(self, uow: UnitOfWork) -> AssemblyBaseProfileRunResult:
        run_id, observations = self._latest_successful_observations(uow)
        contexts = uow.profiles.assembly_base_profile_contexts(
            [observation.id for observation in observations]
        )
        missing_field_counts = {item.name: 0 for item in ASSEMBLY_BASE_PROFILE_FIELDS}
        skipped: list[UUID] = []
        pending: list[
            tuple[Person, FeederObservation, tuple[Claim, ...], tuple[ClaimEvidence, ...]]
        ] = []
        observations_published = 0
        published_claims = 0
        unchanged_claims = 0
        existing_ids = {
            claim.id for claim in uow.public.claims(published_only=True, current_only=True)
        }
        for observation in observations:
            context = contexts.get(observation.id)
            if context is None:
                skipped.append(observation.id)
                continue
            person, source, policy = context
            if person.identity_status != IdentityStatus.RESOLVED:
                raise AssemblyBaseProfileError(
                    "Assembly base profile link does not resolve to a canonical Person"
                )
            bundle = build_assembly_base_profile_bundle(
                person, observation, source=source, policy=policy
            )
            for field_name in bundle.missing_fields:
                missing_field_counts[field_name] += 1
            observations_published += 1
            if not bundle.claims:
                continue
            if all(claim.id in existing_ids for claim in bundle.claims):
                published_claims += len(bundle.claims)
                unchanged_claims += len(bundle.claims)
                continue
            pending.append((person, observation, bundle.claims, bundle.evidence))
        stored = uow.profiles.import_assembly_base_profile_claims_batch(pending)
        published_claims += len(stored)
        unchanged_claims += sum(item.id in existing_ids for item in stored)
        return AssemblyBaseProfileRunResult(
            run_id=run_id,
            observations_considered=len(observations),
            observations_published=observations_published,
            published_claims=published_claims,
            unchanged_claims=unchanged_claims,
            missing_field_counts={
                key: value for key, value in missing_field_counts.items() if value
            },
            skipped_observation_ids=tuple(skipped),
        )

    def publish_latest_successful(self) -> AssemblyBaseProfileRunResult:
        self.uows.assert_ready()
        with self.uows() as uow:
            result = self._publish(uow)
            uow.commit()
            return result
