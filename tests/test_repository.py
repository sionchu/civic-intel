from pathlib import Path

from sqlalchemy import inspect, text

from apps.api.repository import SqlAlchemyRepository
from packages.domain.enums import EpistemicStatus, PublicationStatus


def test_runtime_repository_uses_seeded_sqlalchemy_database(tmp_path: Path) -> None:
    database = tmp_path / "runtime.db"
    repository = SqlAlchemyRepository(f"sqlite:///{database.as_posix()}")
    repository.initialize()
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
