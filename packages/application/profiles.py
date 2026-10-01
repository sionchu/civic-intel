from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from packages.application.ports import UnitOfWorkFactory
from packages.domain.contracts import (
    Claim,
    ClaimEvidence,
    FeederObservation,
    Person,
    Source,
    SourcePolicy,
)


class ProfilesService:
    def __init__(self, uows: UnitOfWorkFactory):
        self.uows = uows

    def assembly_base_profile_contexts(
        self, observation_ids: Sequence[UUID]
    ) -> dict[UUID, tuple[Person, Source, SourcePolicy]]:
        with self.uows(read_only=True) as uow:
            result = uow.profiles.assembly_base_profile_contexts(observation_ids)
            return result

    def assembly_legislative_source_contexts(
        self, observation_ids: Sequence[UUID]
    ) -> dict[UUID, tuple[Source, SourcePolicy]]:
        with self.uows(read_only=True) as uow:
            result = uow.profiles.assembly_legislative_source_contexts(observation_ids)
            return result

    def assembly_current_person_contexts(self, member_codes: Sequence[str]) -> dict[str, Person]:
        with self.uows(read_only=True) as uow:
            result = uow.profiles.assembly_current_person_contexts(member_codes)
            return result

    def import_assembly_base_profile_claims(
        self,
        person: Person,
        observation: FeederObservation,
        claims: Sequence[Claim],
        evidence: Sequence[ClaimEvidence],
    ) -> tuple[Claim, ...]:
        self.uows.assert_ready()
        with self.uows(read_only=False) as uow:
            result = uow.profiles.import_assembly_base_profile_claims(
                person, observation, claims, evidence
            )
            uow.commit()
            return result

    def import_assembly_base_profile_claims_batch(
        self,
        items: Sequence[tuple[Person, FeederObservation, Sequence[Claim], Sequence[ClaimEvidence]]],
    ) -> tuple[Claim, ...]:
        self.uows.assert_ready()
        with self.uows(read_only=False) as uow:
            result = uow.profiles.import_assembly_base_profile_claims_batch(items)
            uow.commit()
            return result

    def import_assembly_legislative_claims_batch(
        self,
        items: Sequence[tuple[Person, FeederObservation, Sequence[Claim], Sequence[ClaimEvidence]]],
    ) -> tuple[Claim, ...]:
        self.uows.assert_ready()
        with self.uows(read_only=False) as uow:
            result = uow.profiles.import_assembly_legislative_claims_batch(items)
            uow.commit()
            return result
