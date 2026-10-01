from __future__ import annotations

import os
from typing import Self

from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import sessionmaker

from packages.application.errors import ConcurrentWrite
from packages.persistence.database_url import normalize_database_url
from packages.persistence.errors import DatabaseNotReady

EXPECTED_SCHEMA_REVISION = "0008"
READ_COMPATIBLE_SCHEMA_REVISIONS = frozenset({"0006", "0007", EXPECTED_SCHEMA_REVISION})


def expected_schema_revision() -> str:
    """The installed runtime contract never depends on checkout/migration paths."""
    return EXPECTED_SCHEMA_REVISION


class Database:
    """The canonical engine/session factory. Startup checks; Alembic changes schema."""

    def __init__(self, database_url: str | None = None, *, pool_pre_ping: bool = False):
        url = database_url or os.getenv("DATABASE_URL") or "sqlite:///./civic_intel.db"
        self.engine = create_engine(normalize_database_url(url), pool_pre_ping=pool_pre_ping)
        self.sessions = sessionmaker(self.engine, expire_on_commit=False)

    def schema_revision(self) -> str:
        with self.engine.connect() as connection:
            return str(connection.scalar(text("SELECT version_num FROM alembic_version")))

    def assert_ready(self) -> None:
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
        missing = sorted(required - set(inspect(self.engine).get_table_names()))
        if missing:
            raise DatabaseNotReady(
                "Database is not migrated; run `python -m alembic upgrade head` "
                f"before starting the API (missing: {', '.join(missing)})"
            )
        current = self.schema_revision()
        if current not in READ_COMPATIBLE_SCHEMA_REVISIONS:
            raise DatabaseNotReady(
                f"Database schema revision is {current!r}; expected "
                f"{EXPECTED_SCHEMA_REVISION!r}. Run `python -m alembic upgrade head`."
            )

    def __call__(self, *, read_only: bool = False) -> SqlAlchemyUnitOfWork:
        return SqlAlchemyUnitOfWork(self.sessions, read_only=read_only)

    def ping(self) -> None:
        with self.engine.connect() as connection:
            connection.execute(text("SELECT 1"))

    def close(self) -> None:
        self.engine.dispose()


class SqlAlchemyUnitOfWork:
    def __init__(self, sessions, *, read_only: bool = False):
        self._sessions = sessions
        self._read_only = read_only

    def __enter__(self) -> Self:
        from packages.persistence.acquisition import AcquisitionRepository
        from packages.persistence.administration import AdministrationRepository
        from packages.persistence.identity import IdentityRepository
        from packages.persistence.onboarding import OnboardingRepository
        from packages.persistence.organizations import OrganizationsRepository
        from packages.persistence.profiles import ProfilesRepository
        from packages.persistence.public import PublicRepository
        from packages.persistence.review import ReviewRepository

        self._session = self._sessions()
        try:
            dialect = self._session.get_bind().dialect.name
            if self._read_only:
                event.listen(self._session, "before_flush", self._reject_read_write)
                if dialect == "postgresql":
                    self._session.connection(
                        execution_options={"isolation_level": "REPEATABLE READ"}
                    )
                    self._session.execute(text("SET TRANSACTION READ ONLY"))
                elif dialect == "sqlite":
                    self._session.execute(text("BEGIN"))
                else:
                    raise DatabaseNotReady("Coherent reads require SQLite or PostgreSQL")
                self._read_connection = self._session.connection()
                event.listen(
                    self._read_connection, "before_cursor_execute", self._reject_non_read_sql
                )
            elif dialect == "sqlite":
                self._session.execute(text("BEGIN IMMEDIATE"))
            self.acquisition = AcquisitionRepository(self._session)
            self.identity = IdentityRepository(self._session)
            self.profiles = ProfilesRepository(self._session)
            self.review = ReviewRepository(self._session)
            self.onboarding = OnboardingRepository(self._session)
            self.organizations = OrganizationsRepository(self._session)
            self.public = PublicRepository(self._session)
            self.administration = AdministrationRepository(self._session)
        except Exception:
            self._session.close()
            raise
        return self

    @staticmethod
    def _reject_read_write(*_args) -> None:
        raise RuntimeError("read-only Unit of Work cannot write")

    @staticmethod
    def _reject_non_read_sql(connection, cursor, statement, *args) -> None:
        # Canonical read adapters emit SELECT. Fail closed for raw SQL and Core writes too.
        if not statement.lstrip().upper().startswith("SELECT"):
            raise RuntimeError("read-only Unit of Work cannot write")

    def commit(self) -> None:
        if self._read_only:
            raise RuntimeError("read-only Unit of Work cannot commit")
        self._session.commit()

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        try:
            self._session.rollback()
        finally:
            self._session.close()
        if isinstance(exc_value, (IntegrityError, OperationalError)):
            raise ConcurrentWrite("transaction collision") from None
