from __future__ import annotations

import os
from pathlib import Path
from uuid import UUID

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from test_alio_item12_money import (
    AlioBusinessExpenseEnumerator,
    FakeAlioMoneyProvider,
    insert_organization,
)

from apps.api.main import create_app
from packages.persistence import SqlAlchemyRepository
from packages.verification.postgresql import verify_restored_database
from workers.alio_reviewed_claim_import import main as reviewed_claim_import_main

POSTGRES_TEST_URL = os.getenv("POSTGRES_TEST_URL")
ORGANIZATION_ID = UUID("60000000-0000-0000-0000-000000000016")


@pytest.mark.skipif(not POSTGRES_TEST_URL, reason="POSTGRES_TEST_URL is not configured")
def test_postgresql_migration_load_and_public_api_contracts() -> None:
    assert POSTGRES_TEST_URL is not None
    config = Config(str(Path("alembic.ini")))
    config.set_main_option("sqlalchemy.url", POSTGRES_TEST_URL)
    command.upgrade(config, "head")
    command.downgrade(config, "0004")
    command.upgrade(config, "head")

    repository = SqlAlchemyRepository(POSTGRES_TEST_URL)
    repository.seed_golden()
    provider = FakeAlioMoneyProvider()
    AlioBusinessExpenseEnumerator(provider.connector(), repository).enumerate()
    insert_organization(repository, ORGANIZATION_ID, "테스트정보기관")
    assert (
        reviewed_claim_import_main(
            [
                "--organization-id",
                str(ORGANIZATION_ID),
                "--institution-code",
                "C0908",
                "--earlier-fiscal-year",
                "2024",
                "--later-fiscal-year",
                "2025",
                "--database-url",
                POSTGRES_TEST_URL,
                "--commit",
            ]
        )
        == 0
    )

    with TestClient(create_app(repository)) as client:
        assert len(client.get("/people").json()) == 10
        money = client.get(f"/organizations/{ORGANIZATION_ID}/money")
        assert money.status_code == 200
        assert len(money.json()["claim_ids"]) == 2
        assert len(money.json()["evidence_ids"]) == 2
        assert len(money.json()["snapshot_ids"]) == 1

    report = verify_restored_database(
        POSTGRES_TEST_URL,
        expected_people=10,
        expected_organization_claims=2,
    )
    assert report["alembic_revision"] == "0007"
