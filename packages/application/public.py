from __future__ import annotations

from collections.abc import Iterable
from uuid import UUID

from packages.application.ports import UnitOfWorkFactory
from packages.domain.contracts import (
    Claim,
    ClaimEvidence,
    Organization,
    Person,
    Source,
    SourcePolicy,
    SourceSnapshot,
)


class PublicService:
    def __init__(self, uows: UnitOfWorkFactory):
        self.uows = uows

    def reviewed_person_role_contexts(
        self, *, person_id: UUID | None = None, organization_id: UUID | None = None
    ) -> list[tuple]:
        with self.uows(read_only=True) as uow:
            result = uow.public.reviewed_person_role_contexts(
                person_id=person_id, organization_id=organization_id
            )
            return result

    def people(self) -> list[Person]:
        with self.uows(read_only=True) as uow:
            result = uow.public.people()
            return result

    def public_people(self) -> list[Person]:
        with self.uows(read_only=True) as uow:
            result = uow.public.public_people()
            return result

    def person_is_public(self, person_id: UUID) -> bool:
        with self.uows(read_only=True) as uow:
            result = uow.public.person_is_public(person_id)
            return result

    def organizations(self, *, current_only: bool = False) -> list[Organization]:
        with self.uows(read_only=True) as uow:
            result = uow.public.organizations(current_only=current_only)
            return result

    def public_organizations(self) -> list[Organization]:
        with self.uows(read_only=True) as uow:
            result = uow.public.public_organizations()
            return result

    def published_person_claim_contexts(
        self, person_ids: Iterable[UUID]
    ) -> dict[UUID, tuple[tuple[Claim, ...], dict[UUID, tuple[ClaimEvidence, ...]]]]:
        with self.uows(read_only=True) as uow:
            result = uow.public.published_person_claim_contexts(person_ids)
            return result

    def published_organization_claim_contexts(
        self, organization_ids: Iterable[UUID]
    ) -> dict[UUID, tuple[tuple[Claim, ...], dict[UUID, tuple[ClaimEvidence, ...]]]]:
        with self.uows(read_only=True) as uow:
            result = uow.public.published_organization_claim_contexts(organization_ids)
            return result

    def person(self, person_id: UUID) -> Person | None:
        with self.uows(read_only=True) as uow:
            result = uow.public.person(person_id)
            return result

    def organization(self, organization_id: UUID) -> Organization | None:
        with self.uows(read_only=True) as uow:
            result = uow.public.organization(organization_id)
            return result

    def claims(
        self,
        person_id: UUID | None = None,
        published_only: bool = False,
        current_only: bool = False,
        *,
        organization_id: UUID | None = None,
    ) -> list[Claim]:
        with self.uows(read_only=True) as uow:
            result = uow.public.claims(
                person_id, published_only, current_only, organization_id=organization_id
            )
            return result

    def evidence_for(self, claim_id: UUID) -> list[ClaimEvidence]:
        with self.uows(read_only=True) as uow:
            result = uow.public.evidence_for(claim_id)
            return result

    def sources(self, source_ids: Iterable[UUID] | None = None) -> dict[UUID, Source]:
        with self.uows(read_only=True) as uow:
            result = uow.public.sources(source_ids)
            return result

    def source(self, source_id: UUID) -> Source | None:
        with self.uows(read_only=True) as uow:
            result = uow.public.source(source_id)
            return result

    def public_source(self, source_id: UUID) -> Source | None:
        with self.uows(read_only=True) as uow:
            result = uow.public.public_source(source_id)
            return result

    def source_snapshot(self, snapshot_id: UUID) -> SourceSnapshot | None:
        with self.uows(read_only=True) as uow:
            result = uow.public.source_snapshot(snapshot_id)
            return result

    def policies(self, policy_ids: Iterable[UUID] | None = None) -> dict[UUID, SourcePolicy]:
        with self.uows(read_only=True) as uow:
            result = uow.public.policies(policy_ids)
            return result

    def relationships(self, person_id: UUID) -> list[dict]:
        with self.uows(read_only=True) as uow:
            result = uow.public.relationships(person_id)
            return result

    def decision_episodes(self, person_id: UUID) -> list[dict]:
        with self.uows(read_only=True) as uow:
            result = uow.public.decision_episodes(person_id)
            return result
