from datetime import UTC, datetime
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect, text

from packages.persistence import EXPECTED_SCHEMA_REVISION


def test_runtime_schema_contract_matches_alembic_head() -> None:
    config = Config(str(Path("alembic.ini").resolve()))
    config.set_main_option("script_location", str(Path("migrations").resolve()))

    assert ScriptDirectory.from_config(config).get_current_head() == EXPECTED_SCHEMA_REVISION


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
        assert (
            connection.scalar(text("SELECT version_num FROM alembic_version"))
            == EXPECTED_SCHEMA_REVISION
        )
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

def test_data_go_policy_reconciliation_round_trips(tmp_path: Path) -> None:
    database = tmp_path / "data-go-policy.db"
    database_url = f"sqlite:///{database.as_posix()}"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(config, "0007")
    engine = create_engine(database_url)

    old_rate = (
        "Development account 10,000 requests; operational account requires review approval"
    )
    old_note = (
        "Reviewed against data.go.kr datasets 15000908 and 15000864 on 2026-08-31 for "
        "the Central Election Commission candidate and winner APIs. Civic Intel discards "
        "candidate address and stores only public-interest election metadata."
    )
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO source_policies (
                    id, domain, source_class, collection_mode,
                    can_fetch, can_store_metadata, can_store_fulltext,
                    can_send_to_ai, can_show_excerpt, can_commercialize,
                    robots_checked_at, terms_checked_at, license, rate_limit, policy_note
                ) VALUES (
                    :id, :domain, 'official_open_api', 'API',
                    1, 1, 0, 0, 0, 1,
                    NULL, :terms_checked_at, :license, :rate_limit, :policy_note
                )
                """
            ),
            {
                "id": "12000000-0000-0000-0000-000000000001",
                "domain": "apis.data.go.kr",
                "terms_checked_at": datetime(2026, 8, 31, tzinfo=UTC),
                "license": "이용허락범위 제한 없음",
                "rate_limit": old_rate,
                "policy_note": old_note,
            },
        )

    command.upgrade(config, "0008")
    with engine.connect() as connection:
        row = connection.execute(
            text(
                """
                SELECT terms_checked_at, rate_limit, policy_note
                FROM source_policies
                WHERE id = '12000000-0000-0000-0000-000000000001'
                """
            )
        ).one()
    assert "2026-09-22" in str(row.terms_checked_at)
    assert "MOIS development/operation access is automatic" in row.rate_limit
    assert "dataset 15077870" in row.policy_note
    assert "unrelated apis.data.go.kr endpoints" in row.policy_note

    command.downgrade(config, "0007")
    with engine.connect() as connection:
        row = connection.execute(
            text(
                """
                SELECT terms_checked_at, rate_limit, policy_note
                FROM source_policies
                WHERE id = '12000000-0000-0000-0000-000000000001'
                """
            )
        ).one()
    assert "2026-08-31" in str(row.terms_checked_at)
    assert row.rate_limit == old_rate
    assert row.policy_note == old_note

def test_data_go_policy_reconciliation_rejects_unexpected_policy_drift(
    tmp_path: Path,
) -> None:
    database = tmp_path / "data-go-policy-drift.db"
    database_url = f"sqlite:///{database.as_posix()}"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(config, "0007")
    engine = create_engine(database_url)

    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO source_policies (
                    id, domain, source_class, collection_mode,
                    can_fetch, can_store_metadata, can_store_fulltext,
                    can_send_to_ai, can_show_excerpt, can_commercialize,
                    robots_checked_at, terms_checked_at, license, rate_limit, policy_note
                ) VALUES (
                    :id, :domain, 'official_open_api', 'API',
                    1, 1, 0, 0, 0, 1,
                    NULL, :terms_checked_at, :license, :rate_limit, :policy_note
                )
                """
            ),
            {
                "id": "12000000-0000-0000-0000-000000000001",
                "domain": "apis.data.go.kr",
                "terms_checked_at": datetime(2026, 8, 31, tzinfo=UTC),
                "license": "이용허락범위 제한 없음",
                "rate_limit": (
                    "Development account 10,000 requests; operational account requires "
                    "review approval"
                ),
                "policy_note": "unexpected policy drift",
            },
        )

    with pytest.raises(
        RuntimeError,
        match="precondition failed for policy_note",
    ):
        command.upgrade(config, "0008")

    with engine.connect() as connection:
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "0007"
        assert (
            connection.scalar(
                text(
                    """
                    SELECT policy_note
                    FROM source_policies
                    WHERE id = '12000000-0000-0000-0000-000000000001'
                    """
                )
            )
            == "unexpected policy drift"
        )
