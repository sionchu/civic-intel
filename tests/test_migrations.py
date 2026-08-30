from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text


def test_clean_database_migrates_to_publication_semantics(tmp_path: Path) -> None:
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
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "0002"
    command.downgrade(config, "0001")
    downgraded = {item["name"] for item in inspect(engine).get_columns("claims")}
    assert "published" in downgraded
    assert "publication_status" not in downgraded
    command.upgrade(config, "head")
    upgraded = {item["name"] for item in inspect(engine).get_columns("claims")}
    assert "publication_status" in upgraded
    assert "published" not in upgraded
