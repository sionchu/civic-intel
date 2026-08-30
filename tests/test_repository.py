from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text

from apps.api.repository import (
    DatabaseNotReady,
    GoldenSeedError,
    SqlAlchemyRepository,
    bootstrap_repository,
)
from packages.domain.enums import EpistemicStatus, PublicationStatus


def migrate(database: Path) -> str:
    database_url = f"sqlite:///{database.as_posix()}"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(config, "head")
    return database_url


def test_runtime_repository_requires_migrated_database(tmp_path: Path) -> None:
    repository = SqlAlchemyRepository(f"sqlite:///{(tmp_path / 'unmigrated.db').as_posix()}")
    with pytest.raises(DatabaseNotReady, match="not migrated"):
        bootstrap_repository(repository, "runtime")
    assert inspect(repository.engine).get_table_names() == []


def test_explicit_golden_seed_populates_migrated_database(tmp_path: Path) -> None:
    database = tmp_path / "runtime.db"
    repository = SqlAlchemyRepository(migrate(database))

    bootstrap_repository(repository, "runtime")
    assert repository.people() == []

    repository.seed_golden()
    assert len(repository.people()) == 10
    unknowns = [
        item
        for item in repository.claims(published_only=True)
        if item.epistemic_status == EpistemicStatus.UNKNOWN
    ]
    assert len(unknowns) == 1
    assert unknowns[0].publication_status == PublicationStatus.PUBLISHED
    assert unknowns[0].asserted_as_true is False
    assert "people" in inspect(repository.engine).get_table_names()
    with repository.engine.connect() as connection:
        assert connection.scalar(text("SELECT COUNT(*) FROM people")) == 10


def test_golden_bootstrap_is_explicit_and_refuses_nonempty_database(tmp_path: Path) -> None:
    database = tmp_path / "golden.db"
    repository = SqlAlchemyRepository(migrate(database))

    bootstrap_repository(repository, "golden")
    assert len(repository.people()) == 10
    with pytest.raises(GoldenSeedError, match="empty migrated database"):
        bootstrap_repository(repository, "golden")


def test_unknown_bootstrap_mode_fails_closed(tmp_path: Path) -> None:
    repository = SqlAlchemyRepository(migrate(tmp_path / "mode.db"))
    with pytest.raises(DatabaseNotReady, match="Unsupported CIVIC_BOOTSTRAP_MODE"):
        bootstrap_repository(repository, "surprise")
