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
from test_alio_organization_activation import commit_prepared
from test_batch_alio_executives import FakeAlioProvider

from apps.api.main import create_app
from packages.persistence import SqlAlchemyRepository
from packages.verification.postgresql import verify_restored_database
from workers.alio_reviewed_claim_import import main as reviewed_claim_import_main
from workers.public_institutions import AlioExecutiveEnumerator

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

@pytest.mark.skipif(not POSTGRES_TEST_URL, reason="POSTGRES_TEST_URL is not configured")
def test_postgresql_safe_alio_person_materialization_is_atomic_and_idempotent() -> None:
    assert POSTGRES_TEST_URL is not None
    config = Config(str(Path("alembic.ini")))
    config.set_main_option("sqlalchemy.url", POSTGRES_TEST_URL)
    command.upgrade(config, "head")

    repository = SqlAlchemyRepository(POSTGRES_TEST_URL)
    before_people = len(repository.people())
    provider = FakeAlioProvider()
    result = AlioExecutiveEnumerator(provider.connector(), repository).enumerate()
    assert result.run.status.value == "SUCCESS"
    commit_prepared(repository)

    preflight = repository.prepare_alio_person_materialization()
    assert preflight.action_counts()["CREATE"] == 3
    receipt = repository.commit_alio_person_materialization(
        expected_receipt_sha256=preflight.sha256()
    )
    assert receipt["status"] == "COMMITTED"
    assert receipt["created_people"] == 3
    assert receipt["created_claims"] == 3
    assert receipt["claim_publication"] is False
    assert len(repository.people()) == before_people + 3
    with TestClient(create_app(repository)) as client:
        assert len(client.get("/people").json()) == before_people
    created_ids = [
        item.packet.person.id
        for item in preflight.create_items
        if item.packet is not None
    ]
    assert all(repository.person(person_id).identity_status.value == "REVIEW" for person_id in created_ids)
    assert all(
        claim.publication_status.value == "DRAFT"
        for person_id in created_ids
        for claim in repository.claims(person_id=person_id)
    )

    rerun = repository.prepare_alio_person_materialization()
    assert rerun.action_counts()["CREATE"] == 0
    assert rerun.action_counts()["NOOP"] == 3
    noop = repository.commit_alio_person_materialization(
        expected_receipt_sha256=rerun.sha256()
    )
    assert noop["status"] == "NOOP"
    assert noop["write_performed"] is False
    assert len(repository.people()) == before_people + 3
