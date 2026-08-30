from __future__ import annotations

import os
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from uuid import UUID

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.orm import Session, sessionmaker

from packages.domain.contracts import (
    Claim,
    ClaimEvidence,
    FeederObservation,
    IdentityReviewItem,
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
    PublicationStatus,
    SourceRunStatus,
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


class GoldenSeedError(RuntimeError):
    pass


@dataclass(frozen=True)
class BatchPageCommitResult:
    snapshot_id: UUID
    observation_ids: tuple[UUID, ...]
    observations_created: int
    observations_unchanged: int


def _expected_schema_revision() -> str:
    root = Path(__file__).resolve().parents[2]
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "migrations"))
    revision = ScriptDirectory.from_config(config).get_current_head()
    if revision is None:
        raise DatabaseNotReady("Alembic has no current schema head")
    return revision


class SqlAlchemyRepository:
    def __init__(self, database_url: str | None = None):
        url = database_url or os.getenv("DATABASE_URL") or "sqlite:///./civic_intel.db"
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

    def person_observation_links(
        self, person_id: UUID | None = None
    ) -> list[PersonObservationLink]:
        statement = select(PersonObservationLinkRow)
        if person_id is not None:
            statement = statement.where(PersonObservationLinkRow.person_id == str(person_id))
        with self.sessions() as session:
            rows = session.scalars(statement.order_by(PersonObservationLinkRow.linked_at))
            return [self._person_observation_link(row) for row in rows]

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
                session.add(
                    ClaimRow(
                        id=str(published_claim.id),
                        person_id=str(published_claim.person_id),
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
        for source in golden.sources:
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
        for cluster in golden.origin_clusters:
            session.add(
                SourceOriginClusterRow(
                    id=str(cluster.id),
                    canonical_source_id=str(cluster.canonical_source_id),
                    member_source_ids=[str(item) for item in cluster.member_source_ids],
                    reason=cluster.reason,
                )
            )
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
        for claim in golden.claims:
            session.add(
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
                    **self._temporal(claim),
                )
            )
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
                for claim in bundle.claims:
                    session.add(
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
                            **self._temporal(claim),
                        )
                    )
                for evidence in bundle.evidence:
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
                session.commit()
            except Exception:
                session.rollback()
                raise
        return bundle.person

    def people(self) -> list[Person]:
        with self.sessions() as session:
            return [
                self._person(row)
                for row in session.scalars(select(PersonRow).order_by(PersonRow.id))
            ]

    def person(self, person_id: UUID) -> Person | None:
        with self.sessions() as session:
            row = session.get(PersonRow, str(person_id))
            return self._person(row) if row else None

    def claims(self, person_id: UUID | None = None, published_only: bool = False) -> list[Claim]:
        statement = select(ClaimRow)
        if person_id is not None:
            statement = statement.where(ClaimRow.person_id == str(person_id))
        if published_only:
            statement = statement.where(ClaimRow.publication_status == "PUBLISHED")
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

    def policies(self, policy_ids: Iterable[UUID] | None = None) -> dict[UUID, SourcePolicy]:
        statement = select(SourcePolicyRow)
        if policy_ids is not None:
            statement = statement.where(SourcePolicyRow.id.in_([str(item) for item in policy_ids]))
        with self.sessions() as session:
            items = [self._policy(row) for row in session.scalars(statement)]
            return {item.id: item for item in items}

    def relationships(self, person_id: UUID) -> list[dict]:
        with self.sessions() as session:
            rows = session.scalars(select(RelationshipRow).order_by(RelationshipRow.id))
            return [row.payload for row in rows if row.payload["person_id"] == str(person_id)]

    def decision_episodes(self, person_id: UUID) -> list[dict]:
        with self.sessions() as session:
            rows = session.scalars(select(DecisionEpisodeRow).order_by(DecisionEpisodeRow.id))
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
