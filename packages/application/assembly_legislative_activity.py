from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from packages.application.ports import UnitOfWork, UnitOfWorkFactory
from packages.domain.contracts import Claim, ClaimEvidence, FeederObservation, Person
from packages.domain.enums import SourceRunStatus
from packages.verification.assembly_legislative_activity import (
    ASSEMBLY_LEGISLATIVE_FEEDER,
    ASSEMBLY_LEGISLATIVE_SOURCE_CONTRACT,
    AssemblyLegislativeActivityError,
    _code_list,
    build_assembly_legislative_activity_bundle,
)


@dataclass(frozen=True)
class AssemblyLegislativeActivityPublicationResult:
    run_id: UUID
    observations_considered: int
    observations_published: int
    published_claims: int
    unchanged_claims: int
    unresolved_member_codes: tuple[str, ...] = ()


class AssemblyLegislativeActivityPublisher:
    """Publish only the exact manifest of the latest successful bill enumeration."""

    def __init__(self, uows: UnitOfWorkFactory) -> None:
        self.uows = uows

    def _latest_successful_observations(
        self, uow: UnitOfWork
    ) -> tuple[UUID, tuple[FeederObservation, ...]]:
        checkpoint = uow.acquisition.source_checkpoint(
            ASSEMBLY_LEGISLATIVE_FEEDER, self._scope_key_from_checkpoint(uow)
        )
        if checkpoint is None or checkpoint.last_run_id is None:
            raise AssemblyLegislativeActivityError(
                "Assembly legislative success checkpoint is unavailable"
            )
        run = uow.acquisition.source_run(checkpoint.last_run_id)
        if (
            run is None
            or run.status != SourceRunStatus.SUCCESS
            or run.feeder != ASSEMBLY_LEGISLATIVE_FEEDER
            or (run.scope_key != checkpoint.scope_key)
        ):
            raise AssemblyLegislativeActivityError(
                "Assembly legislative activity requires the latest successful full enumeration"
            )
        metadata = checkpoint.metadata
        if metadata.get("source_contract") != ASSEMBLY_LEGISLATIVE_SOURCE_CONTRACT:
            raise AssemblyLegislativeActivityError(
                "Assembly legislative checkpoint source contract is invalid"
            )
        raw_hashes = metadata.get("seen_provider_hashes")
        if not isinstance(raw_hashes, dict):
            raise AssemblyLegislativeActivityError(
                "Assembly legislative checkpoint lacks provider manifest"
            )
        try:
            expected_total = int(metadata["list_total_count"])
            expected_pages = int(metadata["expected_pages"])
        except (KeyError, TypeError, ValueError):
            raise AssemblyLegislativeActivityError(
                "Assembly legislative checkpoint coverage metadata is invalid"
            ) from None
        if checkpoint.cursor != str(expected_pages) or len(raw_hashes) != expected_total:
            raise AssemblyLegislativeActivityError(
                "Assembly legislative checkpoint coverage is incomplete"
            )
        observations = uow.acquisition.feeder_observations(
            ASSEMBLY_LEGISLATIVE_FEEDER, checkpoint.scope_key
        )
        by_key: dict[str, FeederObservation] = {}
        for observation in observations:
            expected_hash = raw_hashes.get(observation.provider_record_key)
            if expected_hash != observation.content_hash:
                continue
            if observation.provider_record_key in by_key:
                raise AssemblyLegislativeActivityError(
                    "Assembly legislative manifest maps one provider key to multiple observations"
                )
            by_key[observation.provider_record_key] = observation
        if set(by_key) != set(raw_hashes):
            raise AssemblyLegislativeActivityError(
                "Assembly legislative manifest lacks committed observations"
            )
        return (run.id, tuple(by_key[key] for key in sorted(by_key)))

    def _scope_key_from_checkpoint(self, uow: UnitOfWork) -> str:
        checkpoints = uow.acquisition.source_checkpoints(ASSEMBLY_LEGISLATIVE_FEEDER)
        if len(checkpoints) != 1:
            raise AssemblyLegislativeActivityError(
                "Assembly legislative activity requires exactly one bounded scope checkpoint"
            )
        return checkpoints[0].scope_key

    def _publish(self, uow: UnitOfWork) -> AssemblyLegislativeActivityPublicationResult:
        run_id, observations = self._latest_successful_observations(uow)
        contexts = uow.profiles.assembly_legislative_source_contexts(
            [observation.id for observation in observations]
        )
        member_codes = sorted(
            {
                code
                for observation in observations
                for key in ("representative_proposer_codes", "co_proposer_codes")
                for code in _code_list(observation.normalized, key)
            }
        )
        people_by_code = uow.profiles.assembly_current_person_contexts(member_codes)
        unresolved = sorted(set(member_codes) - set(people_by_code))
        pending: list[
            tuple[Person, FeederObservation, tuple[Claim, ...], tuple[ClaimEvidence, ...]]
        ] = []
        observations_published = 0
        for observation in observations:
            context = contexts.get(observation.id)
            if context is None:
                raise AssemblyLegislativeActivityError(
                    "Assembly legislative observation provenance is incomplete"
                )
            source, policy = context
            normalized = observation.normalized
            for role, field_name in (
                ("REPRESENTATIVE_PROPOSER", "representative_proposer_codes"),
                ("CO_PROPOSER", "co_proposer_codes"),
            ):
                for mona_cd in _code_list(normalized, field_name):
                    person = people_by_code.get(mona_cd)
                    if person is None:
                        continue
                    bundle = build_assembly_legislative_activity_bundle(
                        person,
                        observation,
                        source=source,
                        policy=policy,
                        participation_role=role,
                        mona_cd=mona_cd,
                    )
                    pending.append((person, observation, bundle.claims, bundle.evidence))
                    observations_published += 1
        existing_before = {
            claim.id
            for person in people_by_code.values()
            for claim in uow.public.claims(
                person_id=person.id, published_only=True, current_only=True
            )
        }
        stored = uow.profiles.import_assembly_legislative_claims_batch(pending)
        requested_ids = {claim.id for _, _, claims, _ in pending for claim in claims}
        unchanged_claims = len(existing_before & requested_ids) if requested_ids else 0
        return AssemblyLegislativeActivityPublicationResult(
            run_id=run_id,
            observations_considered=len(observations),
            observations_published=observations_published,
            published_claims=len(stored) - unchanged_claims,
            unchanged_claims=unchanged_claims,
            unresolved_member_codes=tuple(unresolved),
        )

    def publish_latest_successful(self) -> AssemblyLegislativeActivityPublicationResult:
        self.uows.assert_ready()
        with self.uows() as uow:
            result = self._publish(uow)
            uow.commit()
            return result
