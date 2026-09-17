from __future__ import annotations

import os
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date
from uuid import UUID, uuid5

from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session, sessionmaker

from packages.connectors.open_assembly import (
    POLICY_ID as ASSEMBLY_MEMBER_POLICY_ID,
)
from packages.connectors.open_assembly import OpenAssemblyMemberConnector
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
    now_utc,
)
from packages.domain.db import (
    ClaimEvidenceRow,
    ClaimRow,
    DecisionEpisodeRow,
    FeederObservationRow,
    IdentityReviewItemRow,
    OrganizationRow,
    PersonObservationLinkRow,
    PersonRow,
    RelationshipRow,
    SourceCheckpointRow,
    SourceOriginClusterRow,
    SourcePolicyRow,
    SourceRow,
    SourceRunRow,
    SourceSnapshotRow,
)
from packages.domain.enums import (
    EpistemicStatus,
    EvidenceStance,
    IdentityReviewStatus,
    IdentityStatus,
    MaterializationAction,
    MaterializationDecisionClass,
    PublicationStatus,
    SourceRunStatus,
)
from packages.persistence.database_url import normalize_database_url
from packages.verification.assembly_base_profile import (
    ASSEMBLY_BASE_PROFILE_FEEDER,
    ASSEMBLY_BASE_PROFILE_SCOPE,
    ASSEMBLY_BASE_PROFILE_SEMANTIC_SCOPE,
    ASSEMBLY_BASE_PROFILE_SOURCE_CONTRACT,
    AssemblyBaseProfileError,
    is_assembly_base_profile_field,
)
from packages.verification.assembly_legislative_activity import (
    ASSEMBLY_LEGISLATIVE_FEEDER,
    ASSEMBLY_LEGISLATIVE_PARTICIPATION_PREDICATE,
    ASSEMBLY_LEGISLATIVE_SEMANTIC_SCOPE,
    ASSEMBLY_LEGISLATIVE_SOURCE_CONTRACT,
    AssemblyLegislativeActivityError,
)
from packages.verification.claims import validate_claim_publication
from packages.verification.golden import GoldenSet, load_golden_set
from packages.verification.materialization import (
    MaterializationError,
    MaterializationResult,
    decide_materialization,
)
from packages.verification.person_onboarding import ReviewedPersonBundle, ReviewedPersonImportError
from packages.verification.policy import PolicyAction, PolicyDenied, require_policy


class DatabaseNotReady(RuntimeError):
    pass


EXPECTED_SCHEMA_REVISION = "0006"


class GoldenSeedError(RuntimeError):
    pass


class OrganizationClaimImportError(ValueError):
    pass


_ASSEMBLY_REVIEWED_ROLE_CLAIM_NAMESPACE = UUID(
    "a1e9f24f-4c9b-4f8a-9c7b-2d6c2a8de5f1"
)


def _assembly_reviewed_role_claim_id(
    review_item_id: UUID,
    person_id: UUID,
    observation: FeederObservation,
) -> UUID:
    return uuid5(
        _ASSEMBLY_REVIEWED_ROLE_CLAIM_NAMESPACE,
        "|".join(
            (
                str(review_item_id),
                str(person_id),
                str(observation.id),
                observation.content_hash,
            )
        ),
    )


def _assembly_reviewed_role_qualifiers(observation: FeederObservation) -> dict[str, str]:
    return {
        "source_contract": ASSEMBLY_BASE_PROFILE_SOURCE_CONTRACT,
        "source_scope": observation.scope_key,
        "semantic_scope": observation.semantic_scope,
        "provider_record_key": observation.provider_record_key,
        "immutable_observation_hash": observation.content_hash,
    }


def _build_assembly_reviewed_role_claim(
    person: Person,
    observation: FeederObservation,
    source: Source,
    review_item_id: UUID,
) -> tuple[Claim, ClaimEvidence]:
    claim_id = _assembly_reviewed_role_claim_id(review_item_id, person.id, observation)
    claim = Claim(
        id=claim_id,
        person_id=person.id,
        proposition=f"{person.canonical_name}는 국회의원 명부에 등재되어 있다.",
        subject=person.canonical_name,
        predicate="HELD_ROLE",
        object_text="국회의원",
        qualifiers=_assembly_reviewed_role_qualifiers(observation),
        epistemic_status=EpistemicStatus.FACT,
        publication_status=PublicationStatus.PUBLISHED,
        asserted_as_true=True,
        valid_from=observation.recorded_at,
        recorded_at=observation.recorded_at,
    )
    evidence = ClaimEvidence(
        id=uuid5(
            claim_id,
            "|".join(
                (
                    str(source.id),
                    str(observation.snapshot_id),
                    str(observation.id),
                    EvidenceStance.SUPPORT.value,
                )
            ),
        ),
        claim_id=claim.id,
        source_id=source.id,
        snapshot_id=observation.snapshot_id,
        feeder_observation_id=observation.id,
        stance=EvidenceStance.SUPPORT,
    )
    return claim, evidence


@dataclass(frozen=True)
class BatchPageCommitResult:
    snapshot_id: UUID
    observation_ids: tuple[UUID, ...]
    observations_created: int
    observations_unchanged: int


@dataclass(frozen=True)
class OrganizationClaimBatchResult:
    claims: tuple[Claim, ...]
    organizations_created: int
    organizations_reused: int
    claims_created: int
    claims_reused: int


def _expected_schema_revision() -> str:
    """Return the runtime schema contract without resolving source-tree paths."""

    return EXPECTED_SCHEMA_REVISION


class SqlAlchemyRepository:
    def __init__(self, database_url: str | None = None):
        url = normalize_database_url(
            database_url or os.getenv("DATABASE_URL") or "sqlite:///./civic_intel.db"
        )
        self.engine = create_engine(url)
        self.sessions = sessionmaker(self.engine, expire_on_commit=False)

    def assert_ready(self) -> None:
        database = inspect(self.engine)
        tables = set(database.get_table_names())
        required = {
            "alembic_version",
            "people",
            "claims",
            "claim_evidence",
            "sources",
            "source_runs",
            "source_checkpoints",
            "feeder_observations",
            "person_observation_links",
            "identity_review_items",
        }
        missing = sorted(required - tables)
        if missing:
            raise DatabaseNotReady(
                "Database is not migrated; run `python -m alembic upgrade head` "
                f"before starting the API (missing: {', '.join(missing)})"
            )
        expected = _expected_schema_revision()
        with self.engine.connect() as connection:
            current = connection.scalar(text("SELECT version_num FROM alembic_version"))
        if current != expected:
            raise DatabaseNotReady(
                f"Database schema revision is {current!r}; expected {expected!r}. "
                "Run `python -m alembic upgrade head`."
            )

    @staticmethod
    def _source_run(row: SourceRunRow) -> SourceRun:
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

    @staticmethod
    def _checkpoint(row: SourceCheckpointRow) -> SourceCheckpoint:
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

    @staticmethod
    def _observation(row: FeederObservationRow) -> FeederObservation:
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

    @staticmethod
    def _person_observation_link(row: PersonObservationLinkRow) -> PersonObservationLink:
        return PersonObservationLink.model_validate(row)

    @staticmethod
    def _identity_review_item(row: IdentityReviewItemRow) -> IdentityReviewItem:
        return IdentityReviewItem.model_validate(
            {
                "id": row.id,
                "observation_id": row.observation_id,
                "candidate_person_id": row.candidate_person_id,
                "reason_code": row.reason_code,
                "details": row.details_json,
                "status": row.status,
                "created_at": row.created_at,
                "resolved_at": row.resolved_at,
                "resolution_note": row.resolution_note,
            }
        )

    def start_source_run(
        self, feeder: str, scope_key: str, metadata: dict | None = None
    ) -> SourceRun:
        self.assert_ready()
        with self.sessions() as session:
            checkpoint = session.scalar(
                select(SourceCheckpointRow).where(
                    SourceCheckpointRow.feeder == feeder,
                    SourceCheckpointRow.scope_key == scope_key,
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
            session.commit()
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
        with self.sessions() as session:
            row = session.get(SourceRunRow, str(run_id))
            if row is None:
                raise ValueError("source run does not exist")
            if row.status != SourceRunStatus.RUNNING.value:
                raise ValueError("source run is already finished")
            row.status = status.value
            row.finished_at = now_utc()
            row.error_code = error_code
            row.error_summary = error_summary
            session.commit()
            session.refresh(row)
            return self._source_run(row)

    def source_run(self, run_id: UUID) -> SourceRun | None:
        with self.sessions() as session:
            row = session.get(SourceRunRow, str(run_id))
            return self._source_run(row) if row else None

    def source_runs(
        self, feeder: str | None = None, scope_key: str | None = None
    ) -> list[SourceRun]:
        statement = select(SourceRunRow)
        if feeder is not None:
            statement = statement.where(SourceRunRow.feeder == feeder)
        if scope_key is not None:
            statement = statement.where(SourceRunRow.scope_key == scope_key)
        with self.sessions() as session:
            rows = session.scalars(statement.order_by(SourceRunRow.started_at, SourceRunRow.id))
            return [self._source_run(row) for row in rows]

    def source_checkpoint(self, feeder: str, scope_key: str) -> SourceCheckpoint | None:
        with self.sessions() as session:
            row = session.scalar(
                select(SourceCheckpointRow).where(
                    SourceCheckpointRow.feeder == feeder,
                    SourceCheckpointRow.scope_key == scope_key,
                )
            )
            return self._checkpoint(row) if row else None

    def source_checkpoints(self, feeder: str | None = None) -> list[SourceCheckpoint]:
        statement = select(SourceCheckpointRow)
        if feeder is not None:
            statement = statement.where(SourceCheckpointRow.feeder == feeder)
        with self.sessions() as session:
            rows = session.scalars(statement.order_by(SourceCheckpointRow.scope_key))
            return [self._checkpoint(row) for row in rows]

    def feeder_observations(
        self,
        feeder: str,
        scope_key: str,
        provider_record_key: str | None = None,
    ) -> list[FeederObservation]:
        statement = select(FeederObservationRow).where(
            FeederObservationRow.feeder == feeder,
            FeederObservationRow.scope_key == scope_key,
        )
        if provider_record_key is not None:
            statement = statement.where(
                FeederObservationRow.provider_record_key == provider_record_key
            )
        with self.sessions() as session:
            rows = session.scalars(statement.order_by(FeederObservationRow.recorded_at))
            return [self._observation(row) for row in rows]

    def feeder_observation(self, observation_id: UUID) -> FeederObservation | None:
        with self.sessions() as session:
            row = session.get(FeederObservationRow, str(observation_id))
            return self._observation(row) if row else None

    def feeder_observation_contexts(
        self,
        observation_ids: Iterable[UUID],
    ) -> dict[UUID, tuple[FeederObservation, SourceSnapshot, Source, SourcePolicy]]:
        """Load exact observation-to-source provenance for a bounded batch."""

        requested_ids = tuple(sorted({str(observation_id) for observation_id in observation_ids}))
        if not requested_ids:
            return {}
        statement = (
            select(
                FeederObservationRow,
                SourceSnapshotRow,
                SourceRow,
                SourcePolicyRow,
            )
            .join(SourceSnapshotRow, SourceSnapshotRow.id == FeederObservationRow.snapshot_id)
            .join(SourceRow, SourceRow.id == SourceSnapshotRow.source_id)
            .join(SourcePolicyRow, SourcePolicyRow.id == SourceRow.policy_id)
            .where(FeederObservationRow.id.in_(requested_ids))
        )
        contexts: dict[UUID, tuple[FeederObservation, SourceSnapshot, Source, SourcePolicy]] = {}
        with self.sessions() as session:
            for observation_row, snapshot_row, source_row, policy_row in session.execute(statement):
                observation = self._observation(observation_row)
                if observation.id in contexts:
                    raise ValueError("feeder observation has multiple provenance contexts")
                contexts[observation.id] = (
                    observation,
                    self._snapshot(snapshot_row),
                    self._source(source_row),
                    self._policy(policy_row),
                )
        return contexts

    def person_observation_links(
        self, person_id: UUID | None = None
    ) -> list[PersonObservationLink]:
        statement = select(PersonObservationLinkRow)
        if person_id is not None:
            statement = statement.where(PersonObservationLinkRow.person_id == str(person_id))
        with self.sessions() as session:
            rows = session.scalars(statement.order_by(PersonObservationLinkRow.linked_at))
            return [self._person_observation_link(row) for row in rows]

    def assembly_base_profile_contexts(
        self, observation_ids: Sequence[UUID]
    ) -> dict[UUID, tuple[Person, Source, SourcePolicy]]:
        """Load resolved Assembly profile targets and provenance in one read session."""

        if not observation_ids:
            return {}
        statement = (
            select(
                PersonObservationLinkRow,
                PersonRow,
                FeederObservationRow,
                SourceSnapshotRow,
                SourceRow,
                SourcePolicyRow,
            )
            .join(PersonRow, PersonRow.id == PersonObservationLinkRow.person_id)
            .join(
                FeederObservationRow,
                FeederObservationRow.id == PersonObservationLinkRow.observation_id,
            )
            .join(
                SourceSnapshotRow,
                SourceSnapshotRow.id == FeederObservationRow.snapshot_id,
            )
            .join(SourceRow, SourceRow.id == SourceSnapshotRow.source_id)
            .join(SourcePolicyRow, SourcePolicyRow.id == SourceRow.policy_id)
            .where(
                PersonObservationLinkRow.observation_id.in_(
                    [str(item) for item in observation_ids]
                ),
                PersonObservationLinkRow.superseded_at.is_(None),
            )
        )
        contexts: dict[UUID, tuple[Person, Source, SourcePolicy]] = {}
        with self.sessions() as session:
            for link, person_row, observation_row, snapshot_row, source_row, policy_row in session.execute(
                statement
            ):
                observation_id = UUID(observation_row.id)
                if observation_id in contexts:
                    raise AssemblyBaseProfileError(
                        "Assembly observation has multiple active Person links"
                    )
                if snapshot_row.source_id != source_row.id:
                    raise AssemblyBaseProfileError(
                        "Assembly observation snapshot does not match Source"
                    )
                if source_row.policy_id != policy_row.id:
                    raise AssemblyBaseProfileError(
                        "Assembly Source does not match SourcePolicy"
                    )
                contexts[observation_id] = (
                    self._person(person_row),
                    self._source(source_row),
                    self._policy(policy_row),
                )
        return contexts

    def assembly_legislative_source_contexts(
        self, observation_ids: Sequence[UUID]
    ) -> dict[UUID, tuple[Source, SourcePolicy]]:
        """Load exact bill-observation Source and SourcePolicy provenance."""

        if not observation_ids:
            return {}
        statement = (
            select(FeederObservationRow, SourceSnapshotRow, SourceRow, SourcePolicyRow)
            .join(SourceSnapshotRow, SourceSnapshotRow.id == FeederObservationRow.snapshot_id)
            .join(SourceRow, SourceRow.id == SourceSnapshotRow.source_id)
            .join(SourcePolicyRow, SourcePolicyRow.id == SourceRow.policy_id)
            .where(FeederObservationRow.id.in_([str(item) for item in observation_ids]))
        )
        contexts: dict[UUID, tuple[Source, SourcePolicy]] = {}
        with self.sessions() as session:
            for observation_row, snapshot_row, source_row, policy_row in session.execute(statement):
                observation_id = UUID(observation_row.id)
                if observation_id in contexts:
                    raise AssemblyLegislativeActivityError(
                        "Assembly bill observation has multiple provenance contexts"
                    )
                if snapshot_row.source_id != source_row.id:
                    raise AssemblyLegislativeActivityError(
                        "Assembly bill observation snapshot does not match Source"
                    )
                if source_row.policy_id != policy_row.id:
                    raise AssemblyLegislativeActivityError(
                        "Assembly bill Source does not match SourcePolicy"
                    )
                contexts[observation_id] = (
                    self._source(source_row),
                    self._policy(policy_row),
                )
        return contexts

    def assembly_current_person_contexts(
        self, member_codes: Sequence[str]
    ) -> dict[str, Person]:
        """Resolve exact current-roster MONA_CD links without a name fallback."""

        if not member_codes:
            return {}
        statement = (
            select(FeederObservationRow, PersonObservationLinkRow, PersonRow)
            .join(
                PersonObservationLinkRow,
                PersonObservationLinkRow.observation_id == FeederObservationRow.id,
            )
            .join(PersonRow, PersonRow.id == PersonObservationLinkRow.person_id)
            .where(
                FeederObservationRow.feeder == ASSEMBLY_BASE_PROFILE_FEEDER,
                FeederObservationRow.scope_key == ASSEMBLY_BASE_PROFILE_SCOPE,
                FeederObservationRow.provider_record_key.in_(list(member_codes)),
                PersonObservationLinkRow.superseded_at.is_(None),
                PersonRow.identity_status == IdentityStatus.RESOLVED.value,
                PersonRow.superseded_at.is_(None),
            )
        )
        contexts: dict[str, Person] = {}
        with self.sessions() as session:
            for observation_row, _link_row, person_row in session.execute(statement):
                normalized = observation_row.normalized_json
                if not isinstance(normalized, dict) or normalized.get("member_code") != observation_row.provider_record_key:
                    raise AssemblyLegislativeActivityError(
                        "Assembly current-roster identity contract is invalid"
                    )
                member_code = observation_row.provider_record_key
                if member_code in contexts:
                    existing = contexts[member_code]
                    if existing.id != UUID(person_row.id):
                        raise AssemblyLegislativeActivityError(
                            "Assembly MONA_CD resolves to multiple active canonical People"
                        )
                    continue
                contexts[member_code] = self._person(person_row)
        return contexts

    def identity_review_items(
        self, status: IdentityReviewStatus | None = None
    ) -> list[IdentityReviewItem]:
        statement = select(IdentityReviewItemRow)
        if status is not None:
            statement = statement.where(IdentityReviewItemRow.status == status.value)
        with self.sessions() as session:
            rows = session.scalars(statement.order_by(IdentityReviewItemRow.created_at))
            return [self._identity_review_item(row) for row in rows]

    def materialize_feeder_observation(self, observation_id: UUID) -> MaterializationResult:
        self.assert_ready()
        with self.sessions() as session:
            try:
                observation_row = session.get(FeederObservationRow, str(observation_id))
                if observation_row is None:
                    raise MaterializationError("feeder observation does not exist")
                observation = self._observation(observation_row)
                canonical_name = observation.normalized.get("canonical_name")
                if not isinstance(canonical_name, str) or not canonical_name.strip():
                    raise MaterializationError("feeder observation lacks canonical_name")

                linked_rows = session.scalars(
                    select(PersonRow)
                    .join(
                        PersonObservationLinkRow,
                        PersonObservationLinkRow.person_id == PersonRow.id,
                    )
                    .join(
                        FeederObservationRow,
                        FeederObservationRow.id == PersonObservationLinkRow.observation_id,
                    )
                    .where(
                        FeederObservationRow.feeder == observation.feeder,
                        FeederObservationRow.scope_key == observation.scope_key,
                        FeederObservationRow.provider_record_key
                        == observation.provider_record_key,
                        PersonObservationLinkRow.superseded_at.is_(None),
                    )
                )
                linked_people = tuple(self._person(row) for row in linked_rows)
                same_name_rows = session.scalars(
                    select(PersonRow).where(
                        PersonRow.canonical_name == canonical_name,
                        PersonRow.superseded_at.is_(None),
                    )
                )
                same_name_people = tuple(self._person(row) for row in same_name_rows)
                decision = decide_materialization(
                    observation,
                    linked_people=linked_people,
                    same_name_people=same_name_people,
                )

                if decision.action in {
                    MaterializationAction.REVIEW_REQUIRED,
                    MaterializationAction.HARD_CONFLICT,
                }:
                    existing_review = session.scalar(
                        select(IdentityReviewItemRow).where(
                            IdentityReviewItemRow.observation_id == str(observation.id),
                            IdentityReviewItemRow.reason_code
                            == decision.decision_class.value,
                            IdentityReviewItemRow.status == IdentityReviewStatus.OPEN.value,
                        )
                    )
                    if existing_review is None:
                        review = IdentityReviewItem(
                            observation_id=observation.id,
                            candidate_person_id=decision.candidate_person_id,
                            reason_code=decision.decision_class.value,
                            details={
                                "action": decision.action.value,
                                "feeder": observation.feeder,
                                "provider_record_key": observation.provider_record_key,
                                "reasons": list(decision.reasons),
                            },
                        )
                        existing_review = IdentityReviewItemRow(
                            id=str(review.id),
                            observation_id=str(review.observation_id),
                            candidate_person_id=(
                                str(review.candidate_person_id)
                                if review.candidate_person_id
                                else None
                            ),
                            reason_code=review.reason_code,
                            details_json=review.details,
                            status=review.status.value,
                            created_at=review.created_at,
                            resolved_at=None,
                            resolution_note=None,
                        )
                        session.add(existing_review)
                    session.commit()
                    return MaterializationResult(
                        decision=decision,
                        review_item_id=UUID(existing_review.id),
                        created=False,
                    )

                if decision.action == MaterializationAction.AUTO_LINK:
                    if decision.candidate_person_id is None:
                        raise MaterializationError("AUTO_LINK requires a candidate Person")
                    existing_link = session.scalar(
                        select(PersonObservationLinkRow).where(
                            PersonObservationLinkRow.person_id
                            == str(decision.candidate_person_id),
                            PersonObservationLinkRow.observation_id == str(observation.id),
                            PersonObservationLinkRow.superseded_at.is_(None),
                        )
                    )
                    if existing_link is None:
                        link = PersonObservationLink(
                            person_id=decision.candidate_person_id,
                            observation_id=observation.id,
                            action=decision.action,
                            decision_class=decision.decision_class,
                        )
                        session.add(
                            PersonObservationLinkRow(
                                id=str(link.id),
                                person_id=str(link.person_id),
                                observation_id=str(link.observation_id),
                                action=link.action.value,
                                decision_class=link.decision_class.value,
                                linked_at=link.linked_at,
                                superseded_at=None,
                                review_item_id=None,
                            )
                        )
                    session.commit()
                    return MaterializationResult(
                        decision=decision,
                        person_id=decision.candidate_person_id,
                        created=False,
                    )

                if decision.action != MaterializationAction.AUTO_CREATE:
                    raise MaterializationError("unsupported materialization action")

                birth_date_value = observation.normalized.get("birth_date")
                birth_date = None
                if birth_date_value is not None:
                    if not isinstance(birth_date_value, str):
                        raise MaterializationError("observation birth_date is invalid")
                    try:
                        birth_date = date.fromisoformat(birth_date_value)
                    except ValueError:
                        raise MaterializationError("observation birth_date is invalid") from None
                person = Person(
                    canonical_name=canonical_name,
                    birth_date=birth_date,
                    identity_status=IdentityStatus.RESOLVED,
                )

                snapshot_row = session.get(SourceSnapshotRow, str(observation.snapshot_id))
                if snapshot_row is None:
                    raise MaterializationError("observation snapshot does not exist")
                source_row = session.get(SourceRow, snapshot_row.source_id)
                if source_row is None:
                    raise MaterializationError("observation source does not exist")
                policy_row = session.get(SourcePolicyRow, source_row.policy_id)
                if policy_row is None:
                    raise MaterializationError("observation SourcePolicy does not exist")
                source = self._source(source_row)
                policy = self._policy(policy_row)

                draft_claim = Claim(
                    person_id=person.id,
                    proposition=f"{canonical_name}는 국회의원 명부에 등재되어 있다.",
                    subject=canonical_name,
                    predicate="HELD_ROLE",
                    object_text="국회의원",
                    qualifiers={
                        "provider_record_key": observation.provider_record_key,
                        "source_scope": observation.scope_key,
                    },
                    epistemic_status=EpistemicStatus.FACT,
                    publication_status=PublicationStatus.DRAFT,
                    asserted_as_true=True,
                )
                evidence = ClaimEvidence(
                    claim_id=draft_claim.id,
                    source_id=source.id,
                    snapshot_id=observation.snapshot_id,
                    feeder_observation_id=observation.id,
                    stance=EvidenceStance.SUPPORT,
                )
                published_claim = draft_claim.model_copy(
                    update={"publication_status": PublicationStatus.PUBLISHED}
                )
                gate = validate_claim_publication(
                    published_claim,
                    person,
                    [evidence],
                    {source.id: source},
                    {policy.id: policy},
                )
                if not gate.publishable:
                    raise MaterializationError(
                        f"batch claim failed publication gate: {gate.failures}"
                    )

                link = PersonObservationLink(
                    person_id=person.id,
                    observation_id=observation.id,
                    action=decision.action,
                    decision_class=decision.decision_class,
                )
                session.add(
                    PersonRow(
                        id=str(person.id),
                        canonical_name=person.canonical_name,
                        birth_date=person.birth_date,
                        identity_status=person.identity_status.value,
                        **self._temporal(person),
                    )
                )
                session.flush()
                session.add(
                    ClaimRow(
                        id=str(published_claim.id),
                        person_id=str(published_claim.person_id),
                        organization_id=None,
                        proposition=published_claim.proposition,
                        subject=published_claim.subject,
                        predicate=published_claim.predicate,
                        object_text=published_claim.object_text,
                        qualifiers=published_claim.qualifiers,
                        epistemic_status=published_claim.epistemic_status.value,
                        publication_status=published_claim.publication_status.value,
                        asserted_as_true=published_claim.asserted_as_true,
                        resolution_note=published_claim.resolution_note,
                        **self._temporal(published_claim),
                    )
                )
                session.flush()
                session.add(
                    ClaimEvidenceRow(
                        id=str(evidence.id),
                        claim_id=str(evidence.claim_id),
                        source_id=str(evidence.source_id),
                        snapshot_id=str(evidence.snapshot_id),
                        feeder_observation_id=str(evidence.feeder_observation_id),
                        stance=evidence.stance.value,
                        excerpt=evidence.excerpt,
                    )
                )
                session.add(
                    PersonObservationLinkRow(
                        id=str(link.id),
                        person_id=str(link.person_id),
                        observation_id=str(link.observation_id),
                        action=link.action.value,
                        decision_class=link.decision_class.value,
                        linked_at=link.linked_at,
                        superseded_at=None,
                        review_item_id=None,
                    )
                )
                session.commit()
                return MaterializationResult(
                    decision=decision,
                    person_id=person.id,
                    claim_id=published_claim.id,
                    created=True,
                )
            except Exception:
                session.rollback()
                raise

    def _assembly_review_source_context(
        self, session: Session, observation: FeederObservation
    ) -> tuple[Source, SourcePolicy]:
        snapshot_row = session.get(SourceSnapshotRow, str(observation.snapshot_id))
        if snapshot_row is None:
            raise MaterializationError("Assembly review observation snapshot does not exist")
        source_row = session.get(SourceRow, snapshot_row.source_id)
        if source_row is None:
            raise MaterializationError("Assembly review observation Source does not exist")
        policy_row = session.get(SourcePolicyRow, source_row.policy_id)
        if policy_row is None:
            raise MaterializationError("Assembly review observation SourcePolicy does not exist")
        source = self._source(source_row)
        policy = self._policy(policy_row)
        if (
            policy.id != ASSEMBLY_MEMBER_POLICY_ID
            or policy.domain != OpenAssemblyMemberConnector.HOST
            or policy.source_class != "official_open_api"
            or policy.collection_mode.value != "API"
        ):
            raise MaterializationError("Assembly review requires the official member API SourcePolicy")
        try:
            OpenAssemblyMemberConnector._validated_query(str(source.url))
        except ValueError as exc:
            raise MaterializationError("Assembly review Source URL is outside the member API contract") from exc
        if (
            not isinstance(snapshot_row.metadata_json, dict)
            or snapshot_row.metadata_json.get("api_code") != OpenAssemblyMemberConnector.API_CODE
        ):
            raise MaterializationError("Assembly review snapshot is outside the member API contract")
        if snapshot_row.fulltext is not None:
            raise MaterializationError("Assembly review cannot use a fulltext snapshot")
        try:
            require_policy(policy, PolicyAction.STORE_METADATA)
        except PolicyDenied as exc:
            raise MaterializationError("Assembly review SourcePolicy does not permit metadata storage") from exc
        return source, policy

    @staticmethod
    def _assert_current_assembly_review_observation(
        session: Session, observation: FeederObservation
    ) -> None:
        checkpoint_row = session.scalar(
            select(SourceCheckpointRow).where(
                SourceCheckpointRow.feeder == ASSEMBLY_BASE_PROFILE_FEEDER,
                SourceCheckpointRow.scope_key == ASSEMBLY_BASE_PROFILE_SCOPE,
            )
        )
        if checkpoint_row is None or checkpoint_row.last_run_id is None:
            raise MaterializationError("Assembly review requires a committed roster checkpoint")
        metadata = checkpoint_row.metadata_json
        if not isinstance(metadata, dict) or metadata.get("source_contract") != ASSEMBLY_BASE_PROFILE_SOURCE_CONTRACT:
            raise MaterializationError("Assembly review checkpoint source contract is invalid")
        raw_hashes = metadata.get("seen_provider_hashes")
        if not isinstance(raw_hashes, dict):
            raise MaterializationError("Assembly review checkpoint lacks provider manifest")
        try:
            expected_total = int(metadata["list_total_count"])
            expected_pages = int(metadata["expected_pages"])
        except (KeyError, TypeError, ValueError):
            raise MaterializationError("Assembly review checkpoint coverage metadata is invalid") from None
        if (
            expected_total <= 0
            or expected_pages <= 0
            or checkpoint_row.cursor != str(expected_pages)
            or len(raw_hashes) != expected_total
            or raw_hashes.get(observation.provider_record_key) != observation.content_hash
        ):
            raise MaterializationError(
                "Assembly review observation is not the current successful roster version"
            )
        run_row = session.get(SourceRunRow, checkpoint_row.last_run_id)
        if (
            run_row is None
            or run_row.status != SourceRunStatus.SUCCESS.value
            or run_row.feeder != ASSEMBLY_BASE_PROFILE_FEEDER
            or run_row.scope_key != ASSEMBLY_BASE_PROFILE_SCOPE
            or run_row.records_seen != expected_total
        ):
            raise MaterializationError(
                "Assembly review requires the latest successful full roster enumeration"
            )

    @staticmethod
    def _reviewed_assembly_distinct_decision(
        candidate_person_id: UUID,
    ) -> MaterializationDecision:
        return MaterializationDecision(
            action=MaterializationAction.REVIEWED_CREATE,
            decision_class=MaterializationDecisionClass.REVIEWED_DISTINCT_IDENTITY,
            candidate_person_id=candidate_person_id,
            reasons=(
                "operator_reviewed_exact_provider_record_as_distinct_identity",
            ),
        )

    def _existing_assembly_reviewed_result(
        self,
        session: Session,
        review_row: IdentityReviewItemRow,
        observation: FeederObservation,
        source: Source,
        policy: SourcePolicy,
    ) -> MaterializationResult:
        if review_row.candidate_person_id is None:
            raise MaterializationError("resolved Assembly review lacks its candidate Person")
        candidate_person_id = UUID(review_row.candidate_person_id)
        links = list(
            session.scalars(
                select(PersonObservationLinkRow).where(
                    PersonObservationLinkRow.observation_id == str(observation.id),
                    PersonObservationLinkRow.superseded_at.is_(None),
                )
            )
        )
        if len(links) != 1:
            raise MaterializationError(
                "resolved Assembly review does not have exactly one active observation link"
            )
        link = links[0]
        if (
            link.action != MaterializationAction.REVIEWED_CREATE.value
            or link.decision_class != MaterializationDecisionClass.REVIEWED_DISTINCT_IDENTITY.value
            or link.review_item_id != review_row.id
            or link.person_id == str(candidate_person_id)
        ):
            raise MaterializationError("resolved Assembly review link semantics are invalid")
        person_row = session.get(PersonRow, link.person_id)
        if person_row is None:
            raise MaterializationError("resolved Assembly review Person does not exist")
        person = self._person(person_row)
        if person.identity_status != IdentityStatus.RESOLVED or person.superseded_at is not None:
            raise MaterializationError("resolved Assembly review Person is not public")

        expected_claim, expected_evidence = _build_assembly_reviewed_role_claim(
            person, observation, source, UUID(review_row.id)
        )
        claim_id = expected_claim.id
        claim_row = session.get(ClaimRow, str(claim_id))
        if claim_row is None:
            raise MaterializationError("resolved Assembly review role Claim does not exist")
        claim = self._claim(claim_row)
        if (
            self._person_claim_import_semantics(claim)
            != self._person_claim_import_semantics(expected_claim)
            or claim.valid_from != expected_claim.valid_from
            or claim.recorded_at != expected_claim.recorded_at
            or claim.superseded_at is not None
        ):
            raise MaterializationError("resolved Assembly review role Claim semantics are invalid")
        evidence_rows = list(
            session.scalars(
                select(ClaimEvidenceRow).where(ClaimEvidenceRow.claim_id == str(claim.id))
            )
        )
        if len(evidence_rows) != 1:
            raise MaterializationError("resolved Assembly review role Claim evidence is incomplete")
        evidence = self._evidence(evidence_rows[0])
        if self._evidence_import_semantics([evidence]) != self._evidence_import_semantics(
            [expected_evidence]
        ):
            raise MaterializationError("resolved Assembly review evidence provenance is invalid")
        gate = validate_claim_publication(
            claim,
            person,
            [evidence],
            {source.id: source},
            {policy.id: policy},
        )
        if not gate.publishable:
            raise MaterializationError(
                f"resolved Assembly review Claim failed publication gate: {gate.failures}"
            )
        return MaterializationResult(
            decision=self._reviewed_assembly_distinct_decision(candidate_person_id),
            person_id=person.id,
            claim_id=claim.id,
            review_item_id=UUID(review_row.id),
            created=False,
        )

    def resolve_assembly_distinct_person_review(
        self,
        review_item_id: UUID,
        *,
        resolution_note: str,
    ) -> MaterializationResult:
        """Resolve one exact Assembly DOB conflict as a reviewed distinct Person.

        This is deliberately narrower than the automatic materialization gate. It accepts only
        an existing open Assembly current-roster hard-conflict review, never merges into the
        candidate Person, and commits the new Person, role Claim/Evidence, link and review
        resolution together.
        """

        if not isinstance(resolution_note, str) or not resolution_note.strip():
            raise MaterializationError("Assembly review resolution requires a non-empty note")
        note = resolution_note.strip()
        if len(note) > 1000:
            raise MaterializationError("Assembly review resolution note is too long")
        lowered_note = note.casefold()
        if any(token in lowered_note for token in ("api_key", "authkey", "token=", "password")):
            raise MaterializationError("Assembly review resolution note may not contain credentials")

        self.assert_ready()
        with self.sessions() as session:
            try:
                review_row = session.get(IdentityReviewItemRow, str(review_item_id))
                if review_row is None:
                    raise MaterializationError("Assembly review item does not exist")
                observation_row = session.get(FeederObservationRow, review_row.observation_id)
                if observation_row is None:
                    raise MaterializationError("Assembly review observation does not exist")
                observation = self._observation(observation_row)
                if (
                    observation.feeder != ASSEMBLY_BASE_PROFILE_FEEDER
                    or observation.scope_key != ASSEMBLY_BASE_PROFILE_SCOPE
                    or observation.semantic_scope != ASSEMBLY_BASE_PROFILE_SEMANTIC_SCOPE
                ):
                    raise MaterializationError(
                        "review item is outside the Assembly current-roster scope"
                    )
                source, policy = self._assembly_review_source_context(session, observation)

                if review_row.status == IdentityReviewStatus.RESOLVED.value:
                    return self._existing_assembly_reviewed_result(
                        session, review_row, observation, source, policy
                    )
                if review_row.status != IdentityReviewStatus.OPEN.value:
                    raise MaterializationError("Assembly review item is not open")
                if review_row.reason_code != MaterializationDecisionClass.EXACT_BIRTH_DATE_CONFLICT.value:
                    raise MaterializationError(
                        "Assembly distinct resolution accepts only an exact birth-date conflict"
                    )
                details = review_row.details_json
                if not isinstance(details, dict) or (
                    details.get("action") != MaterializationAction.HARD_CONFLICT.value
                    or details.get("feeder") != ASSEMBLY_BASE_PROFILE_FEEDER
                    or details.get("provider_record_key") != observation.provider_record_key
                ):
                    raise MaterializationError("Assembly review item details do not match its observation")
                if review_row.candidate_person_id is None:
                    raise MaterializationError("Assembly exact conflict lacks its candidate Person")
                candidate_person_id = UUID(review_row.candidate_person_id)

                canonical_name = observation.normalized.get("canonical_name")
                provider_member_code = observation.normalized.get("member_code")
                external_ids = observation.identity_hints.get("external_ids")
                if (
                    not isinstance(canonical_name, str)
                    or not canonical_name.strip()
                    or provider_member_code != observation.provider_record_key
                    or not isinstance(external_ids, dict)
                    or external_ids.get("assembly_mona_cd") != observation.provider_record_key
                ):
                    raise MaterializationError(
                        "Assembly review observation lacks an exact provider identity contract"
                    )
                canonical_name = canonical_name.strip()
                birth_date_value = observation.normalized.get("birth_date")
                if not isinstance(birth_date_value, str) or not birth_date_value.strip():
                    raise MaterializationError(
                        "Assembly distinct resolution requires an exact observed birth date"
                    )
                try:
                    birth_date = date.fromisoformat(birth_date_value)
                except ValueError:
                    raise MaterializationError("Assembly observation birth date is invalid") from None

                candidate_row = session.get(PersonRow, str(candidate_person_id))
                if candidate_row is None:
                    raise MaterializationError("Assembly exact conflict candidate Person does not exist")
                candidate = self._person(candidate_row)
                if (
                    candidate.identity_status != IdentityStatus.RESOLVED
                    or candidate.superseded_at is not None
                    or candidate.canonical_name != canonical_name
                    or candidate.birth_date is None
                    or candidate.birth_date == birth_date
                ):
                    raise MaterializationError(
                        "Assembly review no longer represents a current exact birth-date conflict"
                    )

                self._assert_current_assembly_review_observation(session, observation)
                provider_links = list(
                    session.scalars(
                        select(PersonObservationLinkRow)
                        .join(
                            FeederObservationRow,
                            FeederObservationRow.id == PersonObservationLinkRow.observation_id,
                        )
                        .where(
                            FeederObservationRow.feeder == observation.feeder,
                            FeederObservationRow.scope_key == observation.scope_key,
                            FeederObservationRow.provider_record_key
                            == observation.provider_record_key,
                        )
                    )
                )
                if provider_links:
                    raise MaterializationError(
                        "Assembly provider record already has a Person observation link"
                    )

                person = Person(
                    canonical_name=canonical_name,
                    birth_date=birth_date,
                    identity_status=IdentityStatus.RESOLVED,
                    valid_from=observation.recorded_at,
                    recorded_at=observation.recorded_at,
                )
                published_claim, evidence = _build_assembly_reviewed_role_claim(
                    person, observation, source, review_item_id
                )
                gate = validate_claim_publication(
                    published_claim,
                    person,
                    [evidence],
                    {source.id: source},
                    {policy.id: policy},
                )
                if not gate.publishable:
                    raise MaterializationError(
                        f"Assembly reviewed Claim failed publication gate: {gate.failures}"
                    )
                if session.get(ClaimRow, str(published_claim.id)) is not None:
                    raise MaterializationError("Assembly reviewed role Claim ID is already in use")

                link = PersonObservationLink(
                    person_id=person.id,
                    observation_id=observation.id,
                    action=MaterializationAction.REVIEWED_CREATE,
                    decision_class=MaterializationDecisionClass.REVIEWED_DISTINCT_IDENTITY,
                    review_item_id=review_item_id,
                )
                session.add(
                    PersonRow(
                        id=str(person.id),
                        canonical_name=person.canonical_name,
                        birth_date=person.birth_date,
                        identity_status=person.identity_status.value,
                        **self._temporal(person),
                    )
                )
                session.flush()
                session.add(
                    ClaimRow(
                        id=str(published_claim.id),
                        person_id=str(published_claim.person_id),
                        organization_id=None,
                        proposition=published_claim.proposition,
                        subject=published_claim.subject,
                        predicate=published_claim.predicate,
                        object_text=published_claim.object_text,
                        qualifiers=published_claim.qualifiers,
                        epistemic_status=published_claim.epistemic_status.value,
                        publication_status=published_claim.publication_status.value,
                        asserted_as_true=published_claim.asserted_as_true,
                        resolution_note=published_claim.resolution_note,
                        **self._temporal(published_claim),
                    )
                )
                session.flush()
                session.add(
                    ClaimEvidenceRow(
                        id=str(evidence.id),
                        claim_id=str(evidence.claim_id),
                        source_id=str(evidence.source_id),
                        snapshot_id=str(evidence.snapshot_id),
                        feeder_observation_id=str(evidence.feeder_observation_id),
                        stance=evidence.stance.value,
                        excerpt=evidence.excerpt,
                    )
                )
                session.add(
                    PersonObservationLinkRow(
                        id=str(link.id),
                        person_id=str(link.person_id),
                        observation_id=str(link.observation_id),
                        action=link.action.value,
                        decision_class=link.decision_class.value,
                        linked_at=link.linked_at,
                        superseded_at=None,
                        review_item_id=str(review_item_id),
                    )
                )
                resolved_details = dict(details)
                resolved_details.update(
                    {
                        "resolution_action": MaterializationAction.REVIEWED_CREATE.value,
                        "resolution_decision_class": (
                            MaterializationDecisionClass.REVIEWED_DISTINCT_IDENTITY.value
                        ),
                        "resolved_person_id": str(person.id),
                        "resolved_observation_hash": observation.content_hash,
                    }
                )
                review_row.status = IdentityReviewStatus.RESOLVED.value
                review_row.resolved_at = now_utc()
                review_row.resolution_note = note
                review_row.details_json = resolved_details
                session.commit()
                return MaterializationResult(
                    decision=self._reviewed_assembly_distinct_decision(candidate_person_id),
                    person_id=person.id,
                    claim_id=published_claim.id,
                    review_item_id=review_item_id,
                    created=True,
                )
            except Exception:
                session.rollback()
                raise

    @staticmethod
    def _person_claim_import_semantics(claim: Claim) -> dict:
        return {
            "person_id": claim.person_id,
            "organization_id": claim.organization_id,
            "proposition": claim.proposition,
            "subject": claim.subject,
            "predicate": claim.predicate,
            "object_text": claim.object_text,
            "qualifiers": claim.qualifiers,
            "epistemic_status": claim.epistemic_status,
            "publication_status": claim.publication_status,
            "asserted_as_true": claim.asserted_as_true,
            "resolution_note": claim.resolution_note,
        }

    def _import_assembly_base_profile_claims_in_session(
        self,
        session: Session,
        person: Person,
        observation: FeederObservation,
        claims: Sequence[Claim],
        evidence: Sequence[ClaimEvidence],
    ) -> tuple[Claim, ...]:
        observation_row = session.get(FeederObservationRow, str(observation.id))
        if observation_row is None:
            raise AssemblyBaseProfileError("Assembly observation does not exist")
        stored_observation = self._observation(observation_row)
        if stored_observation != observation:
            raise AssemblyBaseProfileError("Assembly observation has changed since claim build")
        if (
            stored_observation.feeder != ASSEMBLY_BASE_PROFILE_FEEDER
            or stored_observation.scope_key != ASSEMBLY_BASE_PROFILE_SCOPE
        ):
            raise AssemblyBaseProfileError("observation is outside the Assembly base-profile scope")

        person_row = session.get(PersonRow, str(person.id))
        if person_row is None:
            raise AssemblyBaseProfileError("Assembly base profile Person does not exist")
        stored_person = self._person(person_row)
        if stored_person != person or stored_person.identity_status != IdentityStatus.RESOLVED:
            raise AssemblyBaseProfileError("Assembly base profile Person is not the current resolved row")

        links = list(
            session.scalars(
                select(PersonObservationLinkRow).where(
                    PersonObservationLinkRow.observation_id == str(observation.id),
                    PersonObservationLinkRow.superseded_at.is_(None),
                )
            )
        )
        if len(links) != 1 or links[0].person_id != str(person.id):
            raise AssemblyBaseProfileError(
                "Assembly base profile requires exactly one active Person observation link"
            )

        snapshot_row = session.get(SourceSnapshotRow, str(observation.snapshot_id))
        if snapshot_row is None:
            raise AssemblyBaseProfileError("Assembly observation snapshot does not exist")
        source_row = session.get(SourceRow, snapshot_row.source_id)
        if source_row is None:
            raise AssemblyBaseProfileError("Assembly observation Source does not exist")
        policy_row = session.get(SourcePolicyRow, source_row.policy_id)
        if policy_row is None:
            raise AssemblyBaseProfileError("Assembly observation SourcePolicy does not exist")
        source = self._source(source_row)
        policy = self._policy(policy_row)

        if not claims:
            raise AssemblyBaseProfileError("Assembly base profile requires at least one present field")
        if len({claim.id for claim in claims}) != len(claims):
            raise AssemblyBaseProfileError("Assembly base profile contains duplicate Claim IDs")
        if len({item.id for item in evidence}) != len(evidence):
            raise AssemblyBaseProfileError("Assembly base profile contains duplicate Evidence IDs")
        evidence_by_claim: dict[UUID, list[ClaimEvidence]] = {}
        for item in evidence:
            evidence_by_claim.setdefault(item.claim_id, []).append(item)
        requested_fields: set[str] = set()
        for claim in claims:
            field_name = claim.qualifiers.get("field_name")
            if field_name is None or not is_assembly_base_profile_field(field_name):
                raise AssemblyBaseProfileError("Assembly base profile Claim has an unsupported field")
            if field_name in requested_fields:
                raise AssemblyBaseProfileError("Assembly base profile contains duplicate fields")
            requested_fields.add(field_name)
            if (
                claim.person_id != person.id
                or claim.organization_id is not None
                or claim.publication_status != PublicationStatus.PUBLISHED
                or claim.qualifiers.get("source_contract")
                != ASSEMBLY_BASE_PROFILE_SOURCE_CONTRACT
                or claim.qualifiers.get("source_scope") != observation.scope_key
                or claim.qualifiers.get("semantic_scope") != observation.semantic_scope
                or claim.qualifiers.get("provider_record_key")
                != observation.provider_record_key
                or claim.qualifiers.get("immutable_observation_hash")
                != observation.content_hash
            ):
                raise AssemblyBaseProfileError(
                    "Assembly base profile Claim provenance does not match observation"
                )
            claim_evidence = evidence_by_claim.get(claim.id, [])
            if len(claim_evidence) != 1:
                raise AssemblyBaseProfileError(
                    "Assembly base profile Claim requires exactly one Evidence row"
                )
            item = claim_evidence[0]
            if (
                item.source_id != source.id
                or item.snapshot_id != observation.snapshot_id
                or item.feeder_observation_id != observation.id
                or item.stance != EvidenceStance.SUPPORT
                or item.excerpt is not None
            ):
                raise AssemblyBaseProfileError(
                    "Assembly base profile Evidence provenance does not match observation"
                )
            gate = validate_claim_publication(
                claim,
                stored_person,
                claim_evidence,
                {source.id: source},
                {policy.id: policy},
            )
            if not gate.publishable:
                raise AssemblyBaseProfileError(
                    f"Assembly base profile Claim failed publication gate: {gate.failures}"
                )

        current_claim_rows = list(
            session.scalars(
                select(ClaimRow).where(
                    ClaimRow.person_id == str(person.id),
                    ClaimRow.superseded_at.is_(None),
                )
            )
        )
        existing_by_field: dict[str, ClaimRow] = {}
        for row in current_claim_rows:
            field_name = row.qualifiers.get("field_name")
            if (
                row.qualifiers.get("source_contract")
                != ASSEMBLY_BASE_PROFILE_SOURCE_CONTRACT
                or not is_assembly_base_profile_field(field_name or "")
            ):
                continue
            assert field_name is not None
            if field_name in existing_by_field:
                raise AssemblyBaseProfileError(
                    "Assembly base profile has duplicate current field Claims"
                )
            existing_by_field[field_name] = row

        results: list[Claim] = []
        for claim in claims:
            field_name = claim.qualifiers["field_name"]
            existing_row = existing_by_field.get(field_name)
            if existing_row is not None and existing_row.id != str(claim.id):
                raise AssemblyBaseProfileError(
                    "Assembly base profile field conflicts with another immutable observation version"
                )
            if existing_row is not None:
                stored_claim = self._claim(existing_row)
                stored_evidence = [
                    self._evidence(row)
                    for row in session.scalars(
                        select(ClaimEvidenceRow).where(
                            ClaimEvidenceRow.claim_id == existing_row.id
                        )
                    )
                ]
                if (
                    self._person_claim_import_semantics(stored_claim)
                    != self._person_claim_import_semantics(claim)
                    or self._evidence_import_semantics(stored_evidence)
                    != self._evidence_import_semantics(evidence_by_claim[claim.id])
                ):
                    raise AssemblyBaseProfileError(
                        "Assembly base profile Claim ID has conflicting stored semantics"
                    )
                results.append(stored_claim)
                continue
            if session.get(ClaimRow, str(claim.id)) is not None:
                raise AssemblyBaseProfileError("Assembly base profile Claim ID is already in use")
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
                    **self._temporal(claim),
                )
            )
            session.flush()
            item = evidence_by_claim[claim.id][0]
            session.add(
                ClaimEvidenceRow(
                    id=str(item.id),
                    claim_id=str(item.claim_id),
                    source_id=str(item.source_id),
                    snapshot_id=str(item.snapshot_id) if item.snapshot_id else None,
                    feeder_observation_id=(
                        str(item.feeder_observation_id)
                        if item.feeder_observation_id
                        else None
                    ),
                    stance=item.stance.value,
                    excerpt=item.excerpt,
                )
            )
            results.append(claim)

        return tuple(results)

    def import_assembly_base_profile_claims(
        self,
        person: Person,
        observation: FeederObservation,
        claims: Sequence[Claim],
        evidence: Sequence[ClaimEvidence],
    ) -> tuple[Claim, ...]:
        """Atomically import one exact Assembly observation's base-profile Claims.

        An existing field Claim from another immutable observation version is a conflict. The
        importer never supersedes or overwrites it because the provider does not declare a
        correction or replacement contract for current-roster rows.
        """

        self.assert_ready()
        with self.sessions() as session:
            try:
                results = self._import_assembly_base_profile_claims_in_session(
                    session, person, observation, claims, evidence
                )
                session.commit()
                return tuple(results)
            except Exception:
                session.rollback()
                raise

    def import_assembly_base_profile_claims_batch(
        self,
        items: Sequence[
            tuple[Person, FeederObservation, Sequence[Claim], Sequence[ClaimEvidence]]
        ],
    ) -> tuple[Claim, ...]:
        """Atomically import exact Assembly base-profile bundles in one database session."""

        self.assert_ready()
        with self.sessions() as session:
            try:
                results: list[Claim] = []
                for person, observation, claims, evidence in items:
                    results.extend(
                        self._import_assembly_base_profile_claims_in_session(
                            session, person, observation, claims, evidence
                        )
                    )
                session.commit()
                return tuple(results)
            except Exception:
                session.rollback()
                raise

    def _import_assembly_legislative_claims_in_session(
        self,
        session: Session,
        items: Sequence[
            tuple[Person, FeederObservation, Sequence[Claim], Sequence[ClaimEvidence]]
        ],
    ) -> tuple[Claim, ...]:
        if not items:
            return ()

        prepared: list[
            tuple[Person, FeederObservation, Claim, ClaimEvidence, Source, SourcePolicy]
        ] = []
        requested_claim_ids: set[UUID] = set()
        requested_evidence_ids: set[UUID] = set()
        requested_keys: set[tuple[str, str, str]] = set()

        for person, observation, claims, evidence in items:
            if len(claims) != 1 or len(evidence) != 1:
                raise AssemblyLegislativeActivityError(
                    "Assembly legislative activity requires one Claim and one Evidence per participant"
                )
            claim = claims[0]
            item = evidence[0]
            if claim.id in requested_claim_ids or item.id in requested_evidence_ids:
                raise AssemblyLegislativeActivityError(
                    "Assembly legislative activity contains duplicate deterministic IDs"
                )
            requested_claim_ids.add(claim.id)
            requested_evidence_ids.add(item.id)

            observation_row = session.get(FeederObservationRow, str(observation.id))
            if observation_row is None or self._observation(observation_row) != observation:
                raise AssemblyLegislativeActivityError(
                    "Assembly bill observation changed since Claim build"
                )
            if (
                observation.feeder != ASSEMBLY_LEGISLATIVE_FEEDER
                or observation.semantic_scope != ASSEMBLY_LEGISLATIVE_SEMANTIC_SCOPE
            ):
                raise AssemblyLegislativeActivityError(
                    "observation is outside the Assembly legislative-activity scope"
                )

            person_row = session.get(PersonRow, str(person.id))
            if person_row is None:
                raise AssemblyLegislativeActivityError(
                    "Assembly legislative activity Person does not exist"
                )
            stored_person = self._person(person_row)
            if (
                stored_person != person
                or stored_person.identity_status != IdentityStatus.RESOLVED
                or stored_person.superseded_at is not None
            ):
                raise AssemblyLegislativeActivityError(
                    "Assembly legislative activity Person is not the current resolved row"
                )

            snapshot_row = session.get(SourceSnapshotRow, str(observation.snapshot_id))
            if snapshot_row is None:
                raise AssemblyLegislativeActivityError(
                    "Assembly bill observation snapshot does not exist"
                )
            source_row = session.get(SourceRow, snapshot_row.source_id)
            if source_row is None:
                raise AssemblyLegislativeActivityError(
                    "Assembly bill observation Source does not exist"
                )
            policy_row = session.get(SourcePolicyRow, source_row.policy_id)
            if policy_row is None:
                raise AssemblyLegislativeActivityError(
                    "Assembly bill observation SourcePolicy does not exist"
                )
            source = self._source(source_row)
            policy = self._policy(policy_row)
            if snapshot_row.source_id != source_row.id or source.policy_id != policy.id:
                raise AssemblyLegislativeActivityError(
                    "Assembly bill observation provenance chain is inconsistent"
                )
            try:
                require_policy(policy, PolicyAction.STORE_METADATA)
            except PolicyDenied as exc:
                raise AssemblyLegislativeActivityError(
                    "Assembly bill SourcePolicy forbids metadata publication"
                ) from exc

            if (
                claim.person_id != person.id
                or claim.organization_id is not None
                or claim.predicate != ASSEMBLY_LEGISLATIVE_PARTICIPATION_PREDICATE
                or claim.publication_status != PublicationStatus.PUBLISHED
                or claim.epistemic_status != EpistemicStatus.FACT
                or not claim.asserted_as_true
                or claim.qualifiers.get("source_contract")
                != ASSEMBLY_LEGISLATIVE_SOURCE_CONTRACT
                or claim.qualifiers.get("source_scope") != observation.scope_key
                or claim.qualifiers.get("semantic_scope") != observation.semantic_scope
                or claim.qualifiers.get("provider_record_key")
                != observation.provider_record_key
                or claim.qualifiers.get("immutable_observation_hash")
                != observation.content_hash
                or claim.qualifiers.get("bill_id") != observation.provider_record_key
                or claim.qualifiers.get("provider_identity_namespace") != "assembly_mona_cd"
                or not claim.qualifiers.get("provider_person_key")
                or claim.qualifiers.get("participation_role")
                not in {"REPRESENTATIVE_PROPOSER", "CO_PROPOSER"}
                or claim.object_text != observation.normalized.get("bill_name")
            ):
                raise AssemblyLegislativeActivityError(
                    "Assembly legislative activity Claim provenance is invalid"
                )
            if (
                item.claim_id != claim.id
                or item.source_id != source.id
                or item.snapshot_id != observation.snapshot_id
                or item.feeder_observation_id != observation.id
                or item.stance != EvidenceStance.SUPPORT
                or item.excerpt is not None
            ):
                raise AssemblyLegislativeActivityError(
                    "Assembly legislative activity Evidence provenance is invalid"
                )

            provider_person_key = claim.qualifiers["provider_person_key"]
            identity_rows = list(
                session.execute(
                    select(PersonObservationLinkRow, FeederObservationRow, PersonRow)
                    .join(
                        FeederObservationRow,
                        FeederObservationRow.id == PersonObservationLinkRow.observation_id,
                    )
                    .join(PersonRow, PersonRow.id == PersonObservationLinkRow.person_id)
                    .where(
                        FeederObservationRow.feeder == ASSEMBLY_BASE_PROFILE_FEEDER,
                        FeederObservationRow.scope_key == ASSEMBLY_BASE_PROFILE_SCOPE,
                        FeederObservationRow.provider_record_key == provider_person_key,
                        PersonObservationLinkRow.superseded_at.is_(None),
                        PersonRow.identity_status == IdentityStatus.RESOLVED.value,
                        PersonRow.superseded_at.is_(None),
                    )
                )
            )
            identity_person_ids: set[str] = set()
            for _link_row, roster_row, linked_person_row in identity_rows:
                if (
                    not isinstance(roster_row.normalized_json, dict)
                    or roster_row.normalized_json.get("member_code")
                    != roster_row.provider_record_key
                ):
                    raise AssemblyLegislativeActivityError(
                        "Assembly current-roster identity contract is invalid"
                    )
                identity_person_ids.add(linked_person_row.id)
            if identity_person_ids != {str(person.id)}:
                raise AssemblyLegislativeActivityError(
                    "Assembly legislative activity requires an exact current-roster MONA_CD link"
                )

            gate = validate_claim_publication(
                claim,
                stored_person,
                [item],
                {source.id: source},
                {policy.id: policy},
            )
            if not gate.publishable:
                raise AssemblyLegislativeActivityError(
                    f"Assembly legislative activity Claim failed publication gate: {gate.failures}"
                )
            logical_key = (
                str(person.id),
                claim.qualifiers["bill_id"],
                claim.qualifiers["participation_role"],
            )
            if logical_key in requested_keys:
                raise AssemblyLegislativeActivityError(
                    "Assembly legislative activity contains duplicate current logical keys"
                )
            requested_keys.add(logical_key)
            prepared.append((person, observation, claim, item, source, policy))

        current_rows = list(
            session.scalars(
                select(ClaimRow).where(
                    ClaimRow.person_id.in_([str(person.id) for person, *_ in prepared]),
                    ClaimRow.superseded_at.is_(None),
                )
            )
        )
        existing_by_key: dict[tuple[str, str, str], list[ClaimRow]] = {}
        for row in current_rows:
            if (
                row.predicate != ASSEMBLY_LEGISLATIVE_PARTICIPATION_PREDICATE
                or row.qualifiers.get("source_contract")
                != ASSEMBLY_LEGISLATIVE_SOURCE_CONTRACT
            ):
                continue
            bill_id = row.qualifiers.get("bill_id")
            role = row.qualifiers.get("participation_role")
            if not isinstance(bill_id, str) or not isinstance(role, str):
                continue
            existing_by_key.setdefault((str(row.person_id), bill_id, role), []).append(row)

        results: list[Claim] = []
        for person, observation, claim, item, source, policy in prepared:
            key = (
                str(person.id),
                claim.qualifiers["bill_id"],
                claim.qualifiers["participation_role"],
            )
            matching = existing_by_key.get(key, [])
            if len(matching) > 1:
                raise AssemblyLegislativeActivityError(
                    "Assembly legislative activity has duplicate current logical Claims"
                )
            if matching:
                existing_row = matching[0]
                if existing_row.id != str(claim.id):
                    raise AssemblyLegislativeActivityError(
                        "Assembly legislative activity conflicts with another immutable observation version"
                    )
                stored_claim = self._claim(existing_row)
                stored_evidence = [
                    self._evidence(row)
                    for row in session.scalars(
                        select(ClaimEvidenceRow).where(
                            ClaimEvidenceRow.claim_id == existing_row.id
                        )
                    )
                ]
                if (
                    self._person_claim_import_semantics(stored_claim)
                    != self._person_claim_import_semantics(claim)
                    or self._evidence_import_semantics(stored_evidence)
                    != self._evidence_import_semantics([item])
                ):
                    raise AssemblyLegislativeActivityError(
                        "Assembly legislative activity Claim ID has conflicting stored semantics"
                    )
                results.append(stored_claim)
                continue
            if session.get(ClaimRow, str(claim.id)) is not None:
                raise AssemblyLegislativeActivityError(
                    "Assembly legislative activity Claim ID is already in use"
                )
            if session.get(ClaimEvidenceRow, str(item.id)) is not None:
                raise AssemblyLegislativeActivityError(
                    "Assembly legislative activity Evidence ID is already in use"
                )
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
                    **self._temporal(claim),
                )
            )
            session.flush()
            session.add(
                ClaimEvidenceRow(
                    id=str(item.id),
                    claim_id=str(item.claim_id),
                    source_id=str(item.source_id),
                    snapshot_id=str(item.snapshot_id) if item.snapshot_id else None,
                    feeder_observation_id=(
                        str(item.feeder_observation_id)
                        if item.feeder_observation_id
                        else None
                    ),
                    stance=item.stance.value,
                    excerpt=item.excerpt,
                )
            )
            results.append(claim)
        return tuple(results)

    def import_assembly_legislative_claims_batch(
        self,
        items: Sequence[
            tuple[Person, FeederObservation, Sequence[Claim], Sequence[ClaimEvidence]]
        ],
    ) -> tuple[Claim, ...]:
        """Atomically publish exact bill participation Claims or recover an identical import."""

        self.assert_ready()
        with self.sessions() as session:
            try:
                results = self._import_assembly_legislative_claims_in_session(session, items)
                session.commit()
                return results
            except Exception:
                session.rollback()
                raise

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

        with self.sessions() as session:
            try:
                run_row = session.get(SourceRunRow, str(run_id))
                if run_row is None or run_row.status != SourceRunStatus.RUNNING.value:
                    raise ValueError("source page requires a running source run")
                for observation in observations:
                    if (
                        observation.feeder != run_row.feeder
                        or observation.scope_key != run_row.scope_key
                    ):
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
                        origin_cluster_id=(
                            str(source.origin_cluster_id) if source.origin_cluster_id else None
                        ),
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
                for observation in observations:
                    existing = session.scalar(
                        select(FeederObservationRow).where(
                            FeederObservationRow.feeder == observation.feeder,
                            FeederObservationRow.scope_key == observation.scope_key,
                            FeederObservationRow.provider_record_key
                            == observation.provider_record_key,
                            FeederObservationRow.content_hash == observation.content_hash,
                        )
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
                session.commit()
                return BatchPageCommitResult(
                    snapshot_id=UUID(snapshot_row.id),
                    observation_ids=tuple(observation_ids),
                    observations_created=created,
                    observations_unchanged=unchanged,
                )
            except Exception:
                session.rollback()
                raise

    def seed_golden(self, golden: GoldenSet | None = None) -> None:
        self.assert_ready()
        with self.sessions() as session:
            if session.scalar(select(PersonRow.id).limit(1)) is not None:
                raise GoldenSeedError("Golden Set seeding requires an empty migrated database")
            self._seed(session, golden or load_golden_set())
            session.commit()

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
                    **self._temporal(person),
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
                    **self._temporal(claim),
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
                    **self._temporal(relationship),
                )
            )
        for episode in golden.episodes:
            session.add(
                DecisionEpisodeRow(
                    id=str(episode.id),
                    payload=episode.model_dump(mode="json"),
                    **self._temporal(episode),
                )
            )

    @staticmethod
    def _person(row: PersonRow) -> Person:
        return Person.model_validate(row)

    @staticmethod
    def _organization(row: OrganizationRow) -> Organization:
        return Organization.model_validate(row)

    @staticmethod
    def _claim(row: ClaimRow) -> Claim:
        return Claim.model_validate(row)

    @staticmethod
    def _evidence(row: ClaimEvidenceRow) -> ClaimEvidence:
        return ClaimEvidence.model_validate(row)

    @staticmethod
    def _source(row: SourceRow) -> Source:
        return Source.model_validate(row)

    @staticmethod
    def _policy(row: SourcePolicyRow) -> SourcePolicy:
        return SourcePolicy.model_validate(row)

    @staticmethod
    def _snapshot(row: SourceSnapshotRow) -> SourceSnapshot:
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

    def import_reviewed_person(self, bundle: ReviewedPersonBundle) -> Person:
        self.assert_ready()
        with self.sessions() as session:
            try:
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
                    sources[source_id] = self._source(source_row)

                needed_policy_ids = {source.policy_id for source in sources.values()}
                for policy_id in needed_policy_ids:
                    if policy_id in policies:
                        continue
                    policy_row = session.get(SourcePolicyRow, str(policy_id))
                    if policy_row is None:
                        raise ReviewedPersonImportError(
                            f"reviewed import references missing SourcePolicy: {policy_id}"
                        )
                    policies[policy_id] = self._policy(policy_row)

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
                        raise ReviewedPersonImportError(
                            f"snapshot {snapshot.id} references missing source"
                        )
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
                    snapshots[snapshot_id] = self._snapshot(snapshot_row)

                for evidence in bundle.evidence:
                    if evidence.feeder_observation_id is None:
                        continue
                    observation_row = session.get(
                        FeederObservationRow, str(evidence.feeder_observation_id)
                    )
                    if observation_row is None:
                        raise ReviewedPersonImportError(
                            "reviewed import references missing feeder observation: "
                            f"{evidence.feeder_observation_id}"
                        )
                    if evidence.snapshot_id is None:
                        raise ReviewedPersonImportError(
                            "ClaimEvidence with feeder observation requires a snapshot: "
                            f"{evidence.id}"
                        )
                    if str(evidence.snapshot_id) != observation_row.snapshot_id:
                        raise ReviewedPersonImportError(
                            "ClaimEvidence snapshot does not match feeder observation: "
                            f"{evidence.id}"
                        )
                    snapshot_row = session.get(
                        SourceSnapshotRow, str(evidence.snapshot_id)
                    )
                    if snapshot_row is None or snapshot_row.source_id != str(evidence.source_id):
                        raise ReviewedPersonImportError(
                            "ClaimEvidence source does not match feeder observation snapshot: "
                            f"{evidence.id}"
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
                        source.policy_id: policies[source.policy_id]
                        for source in claim_sources.values()
                    }
                    gate = validate_claim_publication(
                        claim,
                        bundle.person,
                        claim_evidence,
                        claim_sources,
                        claim_policies,
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
                        **self._temporal(bundle.person),
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
                            **self._temporal(claim),
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
                            feeder_observation_id=(
                                str(evidence.feeder_observation_id)
                                if evidence.feeder_observation_id
                                else None
                            ),
                            stance=evidence.stance.value,
                            excerpt=evidence.excerpt,
                        )
                    )
                session.commit()
            except Exception:
                session.rollback()
                raise
        return bundle.person

    @staticmethod
    def _claim_import_key(claim: Claim) -> tuple[UUID, str, str, str]:
        source_contract = claim.qualifiers.get("source_contract")
        provider_record_key = claim.qualifiers.get("provider_record_key")
        if claim.organization_id is None or not source_contract or not provider_record_key:
            raise OrganizationClaimImportError(
                "organization claim import requires source contract and provider record key"
            )
        return claim.organization_id, claim.predicate, source_contract, provider_record_key

    @staticmethod
    def _claim_import_semantics(claim: Claim) -> dict:
        return {
            "person_id": claim.person_id,
            "organization_id": claim.organization_id,
            "proposition": claim.proposition,
            "subject": claim.subject,
            "predicate": claim.predicate,
            "object_text": claim.object_text,
            "qualifiers": claim.qualifiers,
            "epistemic_status": claim.epistemic_status,
            "publication_status": claim.publication_status,
            "asserted_as_true": claim.asserted_as_true,
            "resolution_note": claim.resolution_note,
        }

    @staticmethod
    def _evidence_import_semantics(evidence: Sequence[ClaimEvidence]) -> list[tuple]:
        values = [
            (
                item.source_id,
                item.snapshot_id,
                item.feeder_observation_id,
                item.stance,
                item.excerpt,
            )
            for item in evidence
        ]
        return sorted(
            values,
            key=lambda item: tuple("" if value is None else str(value) for value in item),
        )

    def _validate_organization_claim(
        self,
        session: Session,
        organization: Organization,
        claim: Claim,
        evidence: Sequence[ClaimEvidence],
    ) -> Organization:
        if claim.person_id is not None or claim.organization_id != organization.id:
            raise OrganizationClaimImportError(
                "organization claim must target exactly the supplied Organization"
            )
        if claim.publication_status != PublicationStatus.PUBLISHED:
            raise OrganizationClaimImportError(
                "organization claim import requires PUBLISHED status"
            )
        if not evidence:
            raise OrganizationClaimImportError("organization claim requires evidence")
        if any(item.claim_id != claim.id for item in evidence):
            raise OrganizationClaimImportError("organization evidence references another claim")
        if len({item.id for item in evidence}) != len(evidence):
            raise OrganizationClaimImportError("organization claim contains duplicate evidence IDs")

        organization_row = session.get(OrganizationRow, str(organization.id))
        if organization_row is None:
            raise OrganizationClaimImportError(
                "organization claim requires an existing canonical Organization"
            )
        stored_organization = self._organization(organization_row)
        if (
            stored_organization.name != organization.name
            or stored_organization.superseded_at is not None
        ):
            raise OrganizationClaimImportError(
                "organization claim Organization is not the current canonical row"
            )

        sources: dict[UUID, Source] = {}
        policies: dict[UUID, SourcePolicy] = {}
        for item in evidence:
            source_row = session.get(SourceRow, str(item.source_id))
            if source_row is None:
                raise OrganizationClaimImportError(
                    f"organization claim references missing source: {item.source_id}"
                )
            source = self._source(source_row)
            sources[source.id] = source
            policy_row = session.get(SourcePolicyRow, str(source.policy_id))
            if policy_row is None:
                raise OrganizationClaimImportError(
                    f"organization claim references missing SourcePolicy: {source.policy_id}"
                )
            policy = self._policy(policy_row)
            policies[policy.id] = policy
            try:
                require_policy(policy, PolicyAction.STORE_METADATA)
                if item.excerpt:
                    require_policy(policy, PolicyAction.SHOW_EXCERPT)
            except PolicyDenied as exc:
                raise OrganizationClaimImportError(
                    f"SourcePolicy forbids organization claim evidence: {item.id}"
                ) from exc

            if item.snapshot_id is not None:
                snapshot_row = session.get(SourceSnapshotRow, str(item.snapshot_id))
                if snapshot_row is None or snapshot_row.source_id != str(source.id):
                    raise OrganizationClaimImportError(
                        f"organization evidence snapshot does not match source: {item.id}"
                    )
            if item.feeder_observation_id is None:
                continue
            if item.snapshot_id is None:
                raise OrganizationClaimImportError(
                    f"organization evidence with observation requires snapshot: {item.id}"
                )
            observation_row = session.get(
                FeederObservationRow, str(item.feeder_observation_id)
            )
            if observation_row is None:
                raise OrganizationClaimImportError(
                    "organization claim references missing feeder observation: "
                    f"{item.feeder_observation_id}"
                )
            if observation_row.snapshot_id != str(item.snapshot_id):
                raise OrganizationClaimImportError(
                    f"organization evidence snapshot does not match observation: {item.id}"
                )
            versions = session.scalars(
                select(FeederObservationRow).where(
                    FeederObservationRow.feeder == observation_row.feeder,
                    FeederObservationRow.scope_key == observation_row.scope_key,
                    FeederObservationRow.provider_record_key
                    == observation_row.provider_record_key,
                )
            )
            if len({row.content_hash for row in versions}) > 1:
                raise OrganizationClaimImportError(
                    "organization claim cannot publish across multiple immutable observation versions"
                )

        gate = validate_claim_publication(
            claim,
            stored_organization,
            list(evidence),
            sources,
            policies,
        )
        if not gate.publishable:
            raise OrganizationClaimImportError(
                f"organization claim failed publication gate: {gate.failures}"
            )
        return stored_organization

    @staticmethod
    def _add_organization_claim_rows(
        session: Session,
        claim: Claim,
        evidence: Sequence[ClaimEvidence],
    ) -> None:
        session.add(
            ClaimRow(
                id=str(claim.id),
                person_id=None,
                organization_id=str(claim.organization_id),
                proposition=claim.proposition,
                subject=claim.subject,
                predicate=claim.predicate,
                object_text=claim.object_text,
                qualifiers=claim.qualifiers,
                epistemic_status=claim.epistemic_status.value,
                publication_status=claim.publication_status.value,
                asserted_as_true=claim.asserted_as_true,
                resolution_note=claim.resolution_note,
                **SqlAlchemyRepository._temporal(claim),
            )
        )
        session.flush()
        for item in evidence:
            session.add(
                ClaimEvidenceRow(
                    id=str(item.id),
                    claim_id=str(item.claim_id),
                    source_id=str(item.source_id),
                    snapshot_id=(str(item.snapshot_id) if item.snapshot_id else None),
                    feeder_observation_id=(
                        str(item.feeder_observation_id)
                        if item.feeder_observation_id
                        else None
                    ),
                    stance=item.stance.value,
                    excerpt=item.excerpt,
                )
            )

    def import_organization_claim(
        self,
        organization: Organization,
        claim: Claim,
        evidence: Sequence[ClaimEvidence],
    ) -> Claim:
        """Persist one reviewed organization Claim through the canonical validation seam."""

        self.assert_ready()
        with self.sessions() as session:
            try:
                self._validate_organization_claim(session, organization, claim, evidence)
                if session.get(ClaimRow, str(claim.id)) is not None:
                    raise OrganizationClaimImportError(
                        "organization claim ID already exists; reviewed import does not upsert"
                    )
                for item in evidence:
                    if session.get(ClaimEvidenceRow, str(item.id)) is not None:
                        raise OrganizationClaimImportError(
                            f"organization evidence ID already exists: {item.id}"
                        )
                self._add_organization_claim_rows(session, claim, evidence)
                session.commit()
            except Exception:
                session.rollback()
                raise
        return claim

    def _import_organization_claim_pair_once(
        self,
        organization: Organization,
        claim_pairs: Sequence[tuple[Claim, Sequence[ClaimEvidence]]],
    ) -> tuple[Claim, Claim]:
        with self.sessions() as session:
            try:
                requested_keys = [self._claim_import_key(claim) for claim, _ in claim_pairs]
                if len(set(requested_keys)) != 2:
                    raise OrganizationClaimImportError(
                        "organization claim pair requires two distinct source record keys"
                    )

                organization_rows = list(
                    session.scalars(
                        select(ClaimRow).where(
                            ClaimRow.organization_id == str(organization.id),
                            ClaimRow.superseded_at.is_(None),
                        )
                    )
                )
                existing_by_key: dict[tuple[UUID, str, str, str], list[ClaimRow]] = {}
                for row in organization_rows:
                    stored_claim = self._claim(row)
                    try:
                        key = self._claim_import_key(stored_claim)
                    except OrganizationClaimImportError:
                        continue
                    existing_by_key.setdefault(key, []).append(row)

                results: list[Claim] = []
                for (claim, evidence), key in zip(claim_pairs, requested_keys, strict=True):
                    self._validate_organization_claim(session, organization, claim, evidence)
                    matching = existing_by_key.get(key, [])
                    if len(matching) > 1:
                        raise OrganizationClaimImportError(
                            "organization claim import found duplicate canonical source record keys"
                        )
                    if matching:
                        stored = self._claim(matching[0])
                        stored_evidence = [
                            self._evidence(row)
                            for row in session.scalars(
                                select(ClaimEvidenceRow).where(
                                    ClaimEvidenceRow.claim_id == str(stored.id)
                                )
                            )
                        ]
                        if (
                            self._claim_import_semantics(stored)
                            != self._claim_import_semantics(claim)
                            or self._evidence_import_semantics(stored_evidence)
                            != self._evidence_import_semantics(evidence)
                        ):
                            raise OrganizationClaimImportError(
                                "organization claim source record key conflicts with stored semantics"
                            )
                        results.append(stored)
                        continue

                    self._add_organization_claim_rows(session, claim, evidence)
                    results.append(claim)

                session.commit()
                return results[0], results[1]
            except Exception:
                session.rollback()
                raise

    def import_organization_claim_pair(
        self,
        organization: Organization,
        claim_pairs: Sequence[tuple[Claim, Sequence[ClaimEvidence]]],
    ) -> tuple[Claim, Claim]:
        """Atomically import or recover one exact reviewed two-Claim operation."""

        self.assert_ready()
        if len(claim_pairs) != 2:
            raise OrganizationClaimImportError("organization claim pair requires exactly two Claims")
        try:
            return self._import_organization_claim_pair_once(organization, claim_pairs)
        except (IntegrityError, OperationalError):
            # A concurrent equivalent operation can win the deterministic primary-key race.
            # Re-read once and return only if the complete stored semantics match exactly.
            try:
                return self._import_organization_claim_pair_once(organization, claim_pairs)
            except (IntegrityError, OperationalError) as retry_exc:
                raise OrganizationClaimImportError(
                    "organization claim pair collided with a non-equivalent concurrent write"
                ) from retry_exc

    @staticmethod
    def _add_organization_row(session: Session, organization: Organization) -> None:
        session.add(
            OrganizationRow(
                id=str(organization.id),
                name=organization.name,
                **SqlAlchemyRepository._temporal(organization),
            )
        )

    def import_organization_claim_batch(
        self,
        organizations: Sequence[Organization],
        items: Sequence[tuple[Organization, Claim, Sequence[ClaimEvidence]]],
    ) -> OrganizationClaimBatchResult:
        """Atomically materialize supplied Organizations and import exact Claim/Evidence rows.

        The caller owns source-specific identity decisions. This seam only persists the supplied
        current canonical rows and applies the existing organization publication validation.
        """

        self.assert_ready()
        organization_by_id = {organization.id: organization for organization in organizations}
        if len(organization_by_id) != len(organizations):
            raise OrganizationClaimImportError("organization batch contains duplicate ids")
        if any(organization.id not in organization_by_id for organization, _, _ in items):
            raise OrganizationClaimImportError("organization claim batch has an unknown subject")

        requested_keys = [self._claim_import_key(claim) for _, claim, _ in items]
        if len(set(requested_keys)) != len(requested_keys):
            raise OrganizationClaimImportError("organization claim batch contains duplicate source keys")

        with self.sessions() as session:
            try:
                created_organizations = 0
                reused_organizations = 0
                for organization in organizations:
                    organization_row = session.get(OrganizationRow, str(organization.id))
                    if organization_row is None:
                        same_name = list(
                            session.scalars(
                                select(OrganizationRow).where(
                                    OrganizationRow.name == organization.name,
                                    OrganizationRow.superseded_at.is_(None),
                                )
                            )
                        )
                        if same_name:
                            raise OrganizationClaimImportError(
                                "organization batch refuses a same-name canonical row without an exact binding"
                            )
                        self._add_organization_row(session, organization)
                        created_organizations += 1
                    else:
                        stored_organization = self._organization(organization_row)
                        if (
                            stored_organization.name != organization.name
                            or stored_organization.superseded_at is not None
                        ):
                            raise OrganizationClaimImportError(
                                "organization batch Organization is not the current canonical row"
                            )
                        reused_organizations += 1
                session.flush()

                existing_rows = list(
                    session.scalars(
                        select(ClaimRow).where(
                            ClaimRow.organization_id.is_not(None),
                            ClaimRow.superseded_at.is_(None),
                        )
                    )
                )
                existing_by_key: dict[tuple[UUID, str, str, str], list[ClaimRow]] = {}
                source_key_owners: dict[tuple[str, str, str], set[UUID]] = {}
                for claim_row in existing_rows:
                    stored_claim = self._claim(claim_row)
                    try:
                        key = self._claim_import_key(stored_claim)
                    except OrganizationClaimImportError:
                        continue
                    existing_by_key.setdefault(key, []).append(claim_row)
                    source_key_owners.setdefault(key[1:], set()).add(key[0])

                results: list[Claim] = []
                created_claims = 0
                reused_claims = 0
                for organization, claim, evidence in items:
                    key = self._claim_import_key(claim)
                    owners = source_key_owners.get(key[1:], set())
                    if owners and owners != {organization.id}:
                        raise OrganizationClaimImportError(
                            "organization claim source record key is bound to another Organization"
                        )
                    self._validate_organization_claim(session, organization, claim, evidence)
                    matching = existing_by_key.get(key, [])
                    if len(matching) > 1:
                        raise OrganizationClaimImportError(
                            "organization claim batch found duplicate canonical source record keys"
                        )
                    if matching:
                        stored = self._claim(matching[0])
                        stored_evidence = [
                            self._evidence(row)
                            for row in session.scalars(
                                select(ClaimEvidenceRow).where(
                                    ClaimEvidenceRow.claim_id == str(stored.id)
                                )
                            )
                        ]
                        if (
                            self._claim_import_semantics(stored)
                            != self._claim_import_semantics(claim)
                            or self._evidence_import_semantics(stored_evidence)
                            != self._evidence_import_semantics(evidence)
                        ):
                            raise OrganizationClaimImportError(
                                "organization claim source record key conflicts with stored semantics"
                            )
                        results.append(stored)
                        reused_claims += 1
                        continue

                    if session.get(ClaimRow, str(claim.id)) is not None:
                        raise OrganizationClaimImportError(
                            "organization claim ID already exists with different semantics"
                        )
                    for item in evidence:
                        if session.get(ClaimEvidenceRow, str(item.id)) is not None:
                            raise OrganizationClaimImportError(
                                f"organization evidence ID already exists: {item.id}"
                            )
                    self._add_organization_claim_rows(session, claim, evidence)
                    created_claim_row = session.get(ClaimRow, str(claim.id))
                    if created_claim_row is None:
                        raise OrganizationClaimImportError("organization claim row was not persisted")
                    existing_by_key.setdefault(key, []).append(created_claim_row)
                    source_key_owners.setdefault(key[1:], set()).add(organization.id)
                    results.append(claim)
                    created_claims += 1

                session.commit()
                return OrganizationClaimBatchResult(
                    claims=tuple(results),
                    organizations_created=created_organizations,
                    organizations_reused=reused_organizations,
                    claims_created=created_claims,
                    claims_reused=reused_claims,
                )
            except (IntegrityError, OperationalError) as exc:
                session.rollback()
                raise OrganizationClaimImportError(
                    "organization claim batch database commit failed"
                ) from exc
            except Exception:
                session.rollback()
                raise

    def people(self) -> list[Person]:
        with self.sessions() as session:
            return [
                self._person(row)
                for row in session.scalars(select(PersonRow).order_by(PersonRow.id))
            ]

    def public_people(self) -> list[Person]:
        """Return only current, canonical identities eligible for public publication."""

        statement = (
            select(PersonRow)
            .where(
                PersonRow.identity_status == IdentityStatus.RESOLVED.value,
                PersonRow.superseded_at.is_(None),
            )
            .order_by(PersonRow.id)
        )
        with self.sessions() as session:
            return [self._person(row) for row in session.scalars(statement)]

    def organizations(self, *, current_only: bool = False) -> list[Organization]:
        statement = select(OrganizationRow)
        if current_only:
            statement = statement.where(OrganizationRow.superseded_at.is_(None))
        with self.sessions() as session:
            return [
                self._organization(row)
                for row in session.scalars(statement.order_by(OrganizationRow.id))
            ]

    def public_organizations(self) -> list[Organization]:
        """Return current Organizations with at least one current published Claim."""

        statement = (
            select(OrganizationRow)
            .join(ClaimRow, ClaimRow.organization_id == OrganizationRow.id)
            .where(
                OrganizationRow.superseded_at.is_(None),
                ClaimRow.publication_status == PublicationStatus.PUBLISHED.value,
                ClaimRow.superseded_at.is_(None),
            )
            .distinct()
            .order_by(OrganizationRow.id)
        )
        with self.sessions() as session:
            return [self._organization(row) for row in session.scalars(statement)]

    def published_person_claim_contexts(
        self,
        person_ids: Iterable[UUID],
    ) -> dict[UUID, tuple[tuple[Claim, ...], dict[UUID, tuple[ClaimEvidence, ...]]]]:
        """Load current published Person Claim/Evidence context in two bounded reads."""

        requested_ids = tuple(sorted({str(person_id) for person_id in person_ids}))
        if not requested_ids:
            return {}

        with self.sessions() as session:
            claim_rows = list(
                session.scalars(
                    select(ClaimRow)
                    .where(
                        ClaimRow.person_id.in_(requested_ids),
                        ClaimRow.publication_status == PublicationStatus.PUBLISHED.value,
                        ClaimRow.superseded_at.is_(None),
                    )
                    .order_by(ClaimRow.person_id, ClaimRow.id)
                )
            )
            claims_by_person: dict[UUID, list[Claim]] = {
                UUID(person_id): [] for person_id in requested_ids
            }
            claims_by_id: dict[UUID, Claim] = {}
            for row in claim_rows:
                claim = self._claim(row)
                assert claim.person_id is not None
                claims_by_person[claim.person_id].append(claim)
                claims_by_id[claim.id] = claim

            evidence_by_claim: dict[UUID, list[ClaimEvidence]] = {
                claim_id: [] for claim_id in claims_by_id
            }
            if claims_by_id:
                evidence_rows = session.scalars(
                    select(ClaimEvidenceRow)
                    .where(ClaimEvidenceRow.claim_id.in_([str(item) for item in claims_by_id]))
                    .order_by(ClaimEvidenceRow.claim_id, ClaimEvidenceRow.id)
                )
                for evidence_row in evidence_rows:
                    claim_id = UUID(evidence_row.claim_id)
                    if claim_id in evidence_by_claim:
                        evidence_by_claim[claim_id].append(self._evidence(evidence_row))

        return {
            person_id: (
                tuple(claims_by_person[person_id]),
                {
                    claim_id: tuple(items)
                    for claim_id, items in evidence_by_claim.items()
                    if claim_id in {claim.id for claim in claims_by_person[person_id]}
                },
            )
            for person_id in (UUID(item) for item in requested_ids)
        }

    def published_organization_claim_contexts(
        self,
        organization_ids: Iterable[UUID],
    ) -> dict[UUID, tuple[tuple[Claim, ...], dict[UUID, tuple[ClaimEvidence, ...]]]]:
        """Load current published Organization Claim/Evidence context in two bounded reads."""

        requested_ids = tuple(sorted({str(organization_id) for organization_id in organization_ids}))
        if not requested_ids:
            return {}

        with self.sessions() as session:
            claim_rows = list(
                session.scalars(
                    select(ClaimRow)
                    .where(
                        ClaimRow.organization_id.in_(requested_ids),
                        ClaimRow.publication_status == PublicationStatus.PUBLISHED.value,
                        ClaimRow.superseded_at.is_(None),
                    )
                    .order_by(ClaimRow.organization_id, ClaimRow.id)
                )
            )
            claims_by_organization: dict[UUID, list[Claim]] = {
                UUID(organization_id): [] for organization_id in requested_ids
            }
            claims_by_id: dict[UUID, Claim] = {}
            for row in claim_rows:
                claim = self._claim(row)
                assert claim.organization_id is not None
                claims_by_organization[claim.organization_id].append(claim)
                claims_by_id[claim.id] = claim

            evidence_by_claim: dict[UUID, list[ClaimEvidence]] = {
                claim_id: [] for claim_id in claims_by_id
            }
            if claims_by_id:
                evidence_rows = session.scalars(
                    select(ClaimEvidenceRow)
                    .where(ClaimEvidenceRow.claim_id.in_([str(item) for item in claims_by_id]))
                    .order_by(ClaimEvidenceRow.claim_id, ClaimEvidenceRow.id)
                )
                for evidence_row in evidence_rows:
                    claim_id = UUID(evidence_row.claim_id)
                    if claim_id in evidence_by_claim:
                        evidence_by_claim[claim_id].append(self._evidence(evidence_row))

        return {
            organization_id: (
                tuple(claims_by_organization[organization_id]),
                {
                    claim_id: tuple(items)
                    for claim_id, items in evidence_by_claim.items()
                    if claim_id in {claim.id for claim in claims_by_organization[organization_id]}
                },
            )
            for organization_id in (UUID(item) for item in requested_ids)
        }

    def person(self, person_id: UUID) -> Person | None:
        with self.sessions() as session:
            row = session.get(PersonRow, str(person_id))
            return self._person(row) if row else None

    def organization(self, organization_id: UUID) -> Organization | None:
        with self.sessions() as session:
            row = session.get(OrganizationRow, str(organization_id))
            return self._organization(row) if row else None

    def claims(
        self,
        person_id: UUID | None = None,
        published_only: bool = False,
        current_only: bool = False,
        *,
        organization_id: UUID | None = None,
    ) -> list[Claim]:
        if person_id is not None and organization_id is not None:
            raise ValueError("claims query accepts one subject filter")
        statement = select(ClaimRow)
        if person_id is not None:
            statement = statement.where(ClaimRow.person_id == str(person_id))
        if organization_id is not None:
            statement = statement.where(ClaimRow.organization_id == str(organization_id))
        if published_only:
            statement = statement.where(ClaimRow.publication_status == "PUBLISHED")
        if current_only:
            statement = statement.where(ClaimRow.superseded_at.is_(None))
        with self.sessions() as session:
            return [self._claim(row) for row in session.scalars(statement.order_by(ClaimRow.id))]

    def evidence_for(self, claim_id: UUID) -> list[ClaimEvidence]:
        with self.sessions() as session:
            rows = session.scalars(
                select(ClaimEvidenceRow).where(ClaimEvidenceRow.claim_id == str(claim_id))
            )
            return [self._evidence(row) for row in rows]

    def sources(self, source_ids: Iterable[UUID] | None = None) -> dict[UUID, Source]:
        statement = select(SourceRow)
        if source_ids is not None:
            statement = statement.where(SourceRow.id.in_([str(item) for item in source_ids]))
        with self.sessions() as session:
            items = [self._source(row) for row in session.scalars(statement)]
            return {item.id: item for item in items}

    def source(self, source_id: UUID) -> Source | None:
        return self.sources([source_id]).get(source_id)

    def public_source(self, source_id: UUID) -> Source | None:
        """Return a Source only through a currently publishable public Claim/Evidence path."""

        with self.sessions() as session:
            source_row = session.get(SourceRow, str(source_id))
            if source_row is None:
                return None
            evidence_rows = list(
                session.scalars(
                    select(ClaimEvidenceRow).where(
                        ClaimEvidenceRow.source_id == str(source_id)
                    )
                )
            )
            for claim_id in {row.claim_id for row in evidence_rows}:
                claim_row = session.get(ClaimRow, claim_id)
                if (
                    claim_row is None
                    or claim_row.publication_status != PublicationStatus.PUBLISHED.value
                    or claim_row.superseded_at is not None
                ):
                    continue
                claim = self._claim(claim_row)
                subject: Person | Organization
                if claim.person_id is not None:
                    person_row = session.get(PersonRow, str(claim.person_id))
                    if (
                        person_row is None
                        or person_row.identity_status != IdentityStatus.RESOLVED.value
                        or person_row.superseded_at is not None
                    ):
                        continue
                    subject = self._person(person_row)
                elif claim.organization_id is not None:
                    organization_row = session.get(
                        OrganizationRow, str(claim.organization_id)
                    )
                    if organization_row is None or organization_row.superseded_at is not None:
                        continue
                    subject = self._organization(organization_row)
                else:
                    continue

                claim_evidence = [
                    self._evidence(row)
                    for row in session.scalars(
                        select(ClaimEvidenceRow).where(
                            ClaimEvidenceRow.claim_id == claim_id
                        )
                    )
                ]
                source_items = [
                    self._source(row)
                    for row in session.scalars(
                        select(SourceRow).where(
                            SourceRow.id.in_(
                                [str(item.source_id) for item in claim_evidence]
                            )
                        )
                    )
                ]
                sources = {item.id: item for item in source_items}
                policy_items = [
                    self._policy(row)
                    for row in session.scalars(
                        select(SourcePolicyRow).where(
                            SourcePolicyRow.id.in_(
                                [str(item.policy_id) for item in sources.values()]
                            )
                        )
                    )
                ]
                policies = {item.id: item for item in policy_items}
                if validate_claim_publication(
                    claim,
                    subject,
                    claim_evidence,
                    sources,
                    policies,
                ).publishable:
                    return self._source(source_row)
            return None

    def source_snapshot(self, snapshot_id: UUID) -> SourceSnapshot | None:
        with self.sessions() as session:
            row = session.get(SourceSnapshotRow, str(snapshot_id))
            return self._snapshot(row) if row else None

    def policies(self, policy_ids: Iterable[UUID] | None = None) -> dict[UUID, SourcePolicy]:
        statement = select(SourcePolicyRow)
        if policy_ids is not None:
            statement = statement.where(SourcePolicyRow.id.in_([str(item) for item in policy_ids]))
        with self.sessions() as session:
            items = [self._policy(row) for row in session.scalars(statement)]
            return {item.id: item for item in items}

    def relationships(self, person_id: UUID) -> list[dict]:
        with self.sessions() as session:
            rows = session.scalars(
                select(RelationshipRow)
                .where(RelationshipRow.superseded_at.is_(None))
                .order_by(RelationshipRow.id)
            )
            return [row.payload for row in rows if row.payload["person_id"] == str(person_id)]

    def decision_episodes(self, person_id: UUID) -> list[dict]:
        with self.sessions() as session:
            rows = session.scalars(
                select(DecisionEpisodeRow)
                .where(DecisionEpisodeRow.superseded_at.is_(None))
                .order_by(DecisionEpisodeRow.id)
            )
            return [row.payload for row in rows if row.payload["person_id"] == str(person_id)]


def bootstrap_repository(
    target: SqlAlchemyRepository, mode: str | None = None
) -> SqlAlchemyRepository:
    selected = (mode or os.getenv("CIVIC_BOOTSTRAP_MODE") or "runtime").strip().casefold()
    if selected == "runtime":
        target.assert_ready()
        return target
    if selected == "golden":
        target.seed_golden()
        return target
    raise DatabaseNotReady(
        f"Unsupported CIVIC_BOOTSTRAP_MODE {selected!r}; expected 'runtime' or 'golden'"
    )


repository = SqlAlchemyRepository()
