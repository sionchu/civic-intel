from datetime import UTC, datetime
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text


def test_clean_database_migrates_through_batch_foundation(tmp_path: Path) -> None:
    database = tmp_path / "migration.db"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database.as_posix()}")
    command.upgrade(config, "head")
    engine = create_engine(f"sqlite:///{database.as_posix()}")
    columns = {item["name"] for item in inspect(engine).get_columns("claims")}
    assert {
        "subject",
        "predicate",
        "object_text",
        "qualifiers",
        "publication_status",
        "asserted_as_true",
        "resolution_note",
    } <= columns
    assert "published" not in columns
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "0004"
    tables = set(inspect(engine).get_table_names())
    assert {
        "source_runs",
        "source_checkpoints",
        "feeder_observations",
        "person_observation_links",
        "identity_review_items",
    } <= tables
    evidence_columns = {
        item["name"] for item in inspect(engine).get_columns("claim_evidence")
    }
    assert "feeder_observation_id" in evidence_columns
    command.downgrade(config, "0003")
    identity_downgraded_tables = set(inspect(engine).get_table_names())
    assert "person_observation_links" not in identity_downgraded_tables
    assert "identity_review_items" not in identity_downgraded_tables
    assert "feeder_observation_id" not in {
        item["name"] for item in inspect(engine).get_columns("claim_evidence")
    }
    command.downgrade(config, "0002")
    downgraded_tables = set(inspect(engine).get_table_names())
    assert "source_runs" not in downgraded_tables
    assert "source_checkpoints" not in downgraded_tables
    assert "feeder_observations" not in downgraded_tables
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO people "
                "(id, canonical_name, birth_date, identity_status, valid_from, valid_to, "
                "recorded_at, superseded_at) "
                "VALUES (:id, :name, NULL, 'RESOLVED', :now, NULL, :now, NULL)"
            ),
            {
                "id": "00000000-0000-0000-0000-000000000003",
                "name": "migration populated person",
                "now": datetime(2026, 8, 31, tzinfo=UTC),
            },
        )
    command.downgrade(config, "0001")
    downgraded = {item["name"] for item in inspect(engine).get_columns("claims")}
    assert "published" in downgraded
    assert "publication_status" not in downgraded
    command.upgrade(config, "head")
    upgraded = {item["name"] for item in inspect(engine).get_columns("claims")}
    assert "publication_status" in upgraded
    assert "published" not in upgraded
    final_tables = set(inspect(engine).get_table_names())
    assert {
        "source_runs",
        "source_checkpoints",
        "feeder_observations",
        "person_observation_links",
        "identity_review_items",
    } <= final_tables
    assert "feeder_observation_id" in {
        item["name"] for item in inspect(engine).get_columns("claim_evidence")
    }
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT COUNT(*) FROM people")) == 1
