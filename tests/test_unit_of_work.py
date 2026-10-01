from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, text

from apps.api.main import create_app
from packages.application.context import Application
from packages.application.publication import publish_claim
from packages.domain.enums import PublicationStatus, SourceRunStatus
from packages.persistence.database import Database, expected_schema_revision
from tests.support import ScenarioDatabase
from tests.test_materialization import OnePageRoster, enumerate_rows, member_row
from tests.test_repository import migrate


def migrated(tmp_path: Path) -> Database:
    return Database(migrate(tmp_path / "uow.db"))


def test_write_requires_commit_and_rolls_back_exception(tmp_path):
    db = migrated(tmp_path)
    with db() as uow:
        run = uow.acquisition.start_source_run("fixture", "rollback")
    with db(read_only=True) as uow:
        assert uow.acquisition.source_run(run.id) is None
    with pytest.raises(ValueError, match="fixture failure"), db() as uow:
        failed = uow.acquisition.start_source_run("fixture", "failure")
        raise ValueError("fixture failure")
    with db(read_only=True) as uow:
        assert uow.acquisition.source_run(failed.id) is None
    with db() as uow:
        committed = uow.acquisition.start_source_run("fixture", "committed")
        uow.commit()
    with db(read_only=True) as uow:
        assert uow.acquisition.source_run(committed.id).status == SourceRunStatus.RUNNING


def test_read_only_uow_rejects_write_and_commit(tmp_path):
    db = migrated(tmp_path)
    with db(read_only=True) as uow:
        with pytest.raises(RuntimeError, match="cannot commit"):
            uow.commit()
        with pytest.raises(RuntimeError, match="cannot write"):
            uow.acquisition.start_source_run("fixture", "forbidden")
    with db(read_only=True) as uow:
        assert uow.acquisition.source_runs() == []


def test_read_only_uow_rejects_direct_sql_without_poisoning_write_connections(tmp_path):
    db = migrated(tmp_path)
    with db(read_only=True) as uow, pytest.raises(RuntimeError, match="cannot write"):
        uow.public._session.execute(text("DELETE FROM source_runs"))
    with db() as uow:
        run = uow.acquisition.start_source_run("fixture", "write-after-read")
        uow.commit()
    with db(read_only=True) as uow:
        assert uow.acquisition.source_run(run.id) is not None


def test_all_repositories_share_one_session_and_repeatable_sqlite_read(tmp_path):
    db = migrated(tmp_path)
    Application(db).onboarding.seed_golden()
    with db.engine.connect() as connection:
        connection.execute(text("PRAGMA journal_mode=WAL"))
    with db(read_only=True) as uow:
        assert uow.public._session is uow.acquisition._session is uow.administration._session
        source = next(iter(uow.public.sources().values()))
        with db.engine.begin() as writer:
            writer.execute(
                text("UPDATE sources SET title = :title WHERE id = :id"),
                {"title": "changed fixture title", "id": str(source.id)},
            )
        assert uow.public.source(source.id).title == source.title
    with db(read_only=True) as fresh:
        assert fresh.public.source(source.id).title == "changed fixture title"


def test_public_response_uses_one_engine_checkout(tmp_path):
    db = migrated(tmp_path)
    Application(db).onboarding.seed_golden()
    with TestClient(create_app(db)) as client:
        checkouts = []

        def checkout(*_args):
            checkouts.append(1)

        event.listen(db.engine, "checkout", checkout)
        try:
            response = client.get("/people")
            assert response.status_code == 200
            assert len(response.json()) == 10
            assert len(checkouts) == 1
        finally:
            event.remove(db.engine, "checkout", checkout)


def test_identity_materialization_requires_separate_publication(tmp_path):
    db = ScenarioDatabase(migrate(tmp_path / "identity.db"))
    observation = enumerate_rows(db, OnePageRoster([member_row("M-001", "한명의원")]))[0]
    result = db.application.identity.materialize_feeder_observation(observation.id)
    with db(read_only=True) as uow:
        assert uow.public.claim(result.claim_id).publication_status == PublicationStatus.DRAFT
        assert uow.public.claims(published_only=True) == []
    published = publish_claim(db, result.claim_id)
    assert published.publication_status == PublicationStatus.PUBLISHED
    with db(read_only=True) as uow:
        assert len(uow.public.public_people()) == 1


def test_installed_schema_contract_is_not_source_tree_dependent():
    assert expected_schema_revision() == "0008"
