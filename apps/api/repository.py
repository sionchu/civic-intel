from __future__ import annotations

import os
from collections.abc import Iterable
from pathlib import Path
from uuid import UUID

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.orm import Session, sessionmaker

from packages.domain.contracts import Claim, ClaimEvidence, Person, Source, SourcePolicy
from packages.domain.db import (
    ClaimEvidenceRow,
    ClaimRow,
    DecisionEpisodeRow,
    PersonRow,
    RelationshipRow,
    SourceOriginClusterRow,
    SourcePolicyRow,
    SourceRow,
    SourceSnapshotRow,
)
from packages.verification.golden import GoldenSet, load_golden_set


class DatabaseNotReady(RuntimeError):
    pass


class GoldenSeedError(RuntimeError):
    pass


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
        required = {"alembic_version", "people", "claims", "claim_evidence", "sources"}
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
