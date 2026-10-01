from __future__ import annotations

from collections.abc import Iterable, Sequence
from contextlib import AbstractContextManager
from typing import Any, Protocol
from uuid import UUID

from packages.application.results import (
    BatchPageCommitResult,
    OrganizationBatchResult,
    OrganizationClaimBatchResult,
)
from packages.domain.contracts import (
    Claim,
    ClaimEvidence,
    FeederObservation,
    IdentityReviewItem,
    MaterializationDecision,
    Organization,
    Person,
    PersonObservationLink,
    Source,
    SourceCheckpoint,
    SourcePolicy,
    SourceRun,
    SourceSnapshot,
)
from packages.domain.enums import (
    IdentityReviewStatus,
    PublicationStatus,
    SourceRunStatus,
)
from packages.verification.golden import GoldenSet
from packages.verification.person_onboarding import ReviewedPersonBundle


class AcquisitionRepositoryPort(Protocol):
    def start_source_run(
        self, feeder: str, scope_key: str, metadata: dict | None = None
    ) -> SourceRun: ...

    def finish_source_run(
        self,
        run_id: UUID,
        status: SourceRunStatus,
        *,
        error_code: str | None = None,
        error_summary: str | None = None,
    ) -> SourceRun: ...

    def source_run(self, run_id: UUID) -> SourceRun | None: ...

    def source_runs(
        self, feeder: str | None = None, scope_key: str | None = None
    ) -> list[SourceRun]: ...

    def source_checkpoint(self, feeder: str, scope_key: str) -> SourceCheckpoint | None: ...

    def source_checkpoints(self, feeder: str | None = None) -> list[SourceCheckpoint]: ...

    def feeder_observations(
        self, feeder: str, scope_key: str, provider_record_key: str | None = None
    ) -> list[FeederObservation]: ...

    def feeder_observation_hash_manifest(
        self, feeder: str, scope_key: str
    ) -> list[tuple[str, str]]: ...

    def feeder_observation(self, observation_id: UUID) -> FeederObservation | None: ...

    def feeder_observation_contexts(
        self, observation_ids: Iterable[UUID]
    ) -> dict[UUID, tuple[FeederObservation, SourceSnapshot, Source, SourcePolicy]]: ...

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
    ) -> BatchPageCommitResult: ...


class IdentityRepositoryPort(Protocol):
    def person_observation_links(
        self, person_id: UUID | None = None
    ) -> list[PersonObservationLink]: ...

    def active_person_ids_by_observation(
        self, observation_ids: Sequence[UUID]
    ) -> dict[UUID, frozenset[UUID]]: ...

    def matching_people(
        self, observation: FeederObservation
    ) -> tuple[tuple[Person, ...], tuple[Person, ...]]: ...

    def add_person(self, person: Person) -> None: ...

    def link_observation(self, link: PersonObservationLink) -> None: ...


class ProfilesRepositoryPort(Protocol):
    def assembly_base_profile_contexts(
        self, observation_ids: Sequence[UUID]
    ) -> dict[UUID, tuple[Person, Source, SourcePolicy]]: ...

    def assembly_legislative_source_contexts(
        self, observation_ids: Sequence[UUID]
    ) -> dict[UUID, tuple[Source, SourcePolicy]]: ...

    def assembly_current_person_contexts(
        self, member_codes: Sequence[str]
    ) -> dict[str, Person]: ...

    def import_assembly_base_profile_claims(
        self,
        person: Person,
        observation: FeederObservation,
        claims: Sequence[Claim],
        evidence: Sequence[ClaimEvidence],
    ) -> tuple[Claim, ...]: ...

    def import_assembly_base_profile_claims_batch(
        self,
        items: Sequence[tuple[Person, FeederObservation, Sequence[Claim], Sequence[ClaimEvidence]]],
    ) -> tuple[Claim, ...]: ...

    def import_assembly_legislative_claims_batch(
        self,
        items: Sequence[tuple[Person, FeederObservation, Sequence[Claim], Sequence[ClaimEvidence]]],
    ) -> tuple[Claim, ...]: ...


class ReviewRepositoryPort(Protocol):
    def identity_review_items(
        self, status: IdentityReviewStatus | None = None
    ) -> list[IdentityReviewItem]: ...

    def resolve_assembly_distinct_person_review(
        self, review_item_id: UUID, *, resolution_note: str
    ) -> MaterializationResult: ...

    def ensure_materialization_review(
        self, observation: FeederObservation, decision: MaterializationDecision
    ) -> IdentityReviewItem: ...


class OnboardingRepositoryPort(Protocol):
    def seed_golden(self, golden: GoldenSet | None = None) -> None: ...

    def import_reviewed_person(self, bundle: ReviewedPersonBundle) -> Person: ...

    def set_publication_status(self, claim_id: UUID, status: PublicationStatus) -> None: ...

    def add_claim(self, claim: Claim, evidence: ClaimEvidence) -> None: ...


class OrganizationsRepositoryPort(Protocol):
    def import_organization_claim(
        self, organization: Organization, claim: Claim, evidence: Sequence[ClaimEvidence]
    ) -> Claim: ...

    def import_organization_claim_pair(
        self,
        organization: Organization,
        claim_pairs: Sequence[tuple[Claim, Sequence[ClaimEvidence]]],
    ) -> tuple[Claim, Claim]: ...

    def import_organization_claim_batch(
        self,
        organizations: Sequence[Organization],
        items: Sequence[tuple[Organization, Claim, Sequence[ClaimEvidence]]],
    ) -> OrganizationClaimBatchResult: ...

    def import_organization_batch(
        self, organizations: Sequence[Organization]
    ) -> OrganizationBatchResult: ...


class PublicRepositoryPort(Protocol):
    def claim(self, claim_id: UUID) -> Claim | None: ...

    def reviewed_person_role_contexts(
        self, *, person_id: UUID | None = None, organization_id: UUID | None = None
    ) -> list[tuple]: ...

    def people(self) -> list[Person]: ...

    def public_people(self) -> list[Person]: ...

    def person_is_public(self, person_id: UUID) -> bool: ...

    def organizations(self, *, current_only: bool = False) -> list[Organization]: ...

    def public_organizations(self) -> list[Organization]: ...

    def published_person_claim_contexts(
        self, person_ids: Iterable[UUID]
    ) -> dict[UUID, tuple[tuple[Claim, ...], dict[UUID, tuple[ClaimEvidence, ...]]]]: ...

    def published_organization_claim_contexts(
        self, organization_ids: Iterable[UUID]
    ) -> dict[UUID, tuple[tuple[Claim, ...], dict[UUID, tuple[ClaimEvidence, ...]]]]: ...

    def person(self, person_id: UUID) -> Person | None: ...

    def organization(self, organization_id: UUID) -> Organization | None: ...

    def claims(
        self,
        person_id: UUID | None = None,
        published_only: bool = False,
        current_only: bool = False,
        *,
        organization_id: UUID | None = None,
    ) -> list[Claim]: ...

    def evidence_for(self, claim_id: UUID) -> list[ClaimEvidence]: ...

    def sources(self, source_ids: Iterable[UUID] | None = None) -> dict[UUID, Source]: ...

    def source(self, source_id: UUID) -> Source | None: ...

    def public_source(self, source_id: UUID) -> Source | None: ...

    def source_snapshot(self, snapshot_id: UUID) -> SourceSnapshot | None: ...

    def policies(self, policy_ids: Iterable[UUID] | None = None) -> dict[UUID, SourcePolicy]: ...

    def relationships(self, person_id: UUID) -> list[dict]: ...

    def decision_episodes(self, person_id: UUID) -> list[dict]: ...


class AdministrationRepositoryPort(Protocol):
    def operator_summary(self) -> dict[str, Any]: ...

    def operator_records(self, kind: str, **filters: Any) -> dict[str, Any]: ...

    def operator_record_detail(self, kind: str, record_id: str) -> dict[str, Any] | None: ...

    def prepare_work_order_references(self, request) -> dict[str, Any]: ...

    def prepare_alio_person_materialization(self): ...

    def commit_alio_person_materialization(
        self, *, expected_receipt_sha256: str
    ) -> dict[str, Any]: ...

    def prepare_nec_person_materialization(
        self, *, election_id: str = "20260603", election_types: Sequence[int] = (3, 4, 5, 6, 11)
    ): ...

    def commit_nec_person_materialization(
        self,
        *,
        expected_receipt_sha256: str,
        election_id: str = "20260603",
        election_types: Sequence[int] = (3, 4, 5, 6, 11),
    ) -> dict[str, Any]: ...

    def admin_preview(self, command): ...

    def admin_commit(self, command, actor: str, state_hash: str) -> dict[str, Any]: ...

    def admin_evidence_options(self, q: str = "", limit: int = 10) -> list[dict[str, Any]]: ...

    def admin_queue(self, **filters: Any) -> dict[str, Any]: ...

    def admin_history(self, offset: int = 0, limit: int = 25) -> dict[str, Any]: ...

    def admin_schema_ready(self) -> bool: ...


class UnitOfWork(Protocol):
    @property
    def acquisition(self) -> AcquisitionRepositoryPort: ...

    @property
    def identity(self) -> IdentityRepositoryPort: ...

    @property
    def profiles(self) -> ProfilesRepositoryPort: ...

    @property
    def review(self) -> ReviewRepositoryPort: ...

    @property
    def onboarding(self) -> OnboardingRepositoryPort: ...

    @property
    def organizations(self) -> OrganizationsRepositoryPort: ...

    @property
    def public(self) -> PublicRepositoryPort: ...

    @property
    def administration(self) -> AdministrationRepositoryPort: ...

    def commit(self) -> None: ...


class UnitOfWorkFactory(Protocol):
    def assert_ready(self) -> None: ...

    def schema_revision(self) -> str: ...

    def __call__(self, *, read_only: bool = False) -> AbstractContextManager[UnitOfWork]: ...


from packages.verification.materialization import MaterializationResult
