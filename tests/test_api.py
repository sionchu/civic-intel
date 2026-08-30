from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient

from apps.api.main import create_app
from packages.persistence import DatabaseNotReady, SqlAlchemyRepository

PERSON_ID = "00000000-0000-0000-0000-000000000002"
HA_JUNGWOO_ID = "00000000-0000-0000-0000-000000000009"
SOURCE_ID = "20000000-0000-0000-0000-000000000001"
HA_ROLE_SOURCE_ID = "20000000-0000-0000-0000-000000000006"


def migrated_repository(database: Path) -> SqlAlchemyRepository:
    database_url = f"sqlite:///{database.as_posix()}"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(config, "head")
    return SqlAlchemyRepository(database_url)


@pytest.fixture()
def client(tmp_path: Path):
    repository = migrated_repository(tmp_path / "api.db")
    repository.seed_golden()
    with TestClient(create_app(repository)) as api_client:
        yield api_client


def test_health_and_real_roster(client: TestClient) -> None:
    assert client.get("/health").json() == {"status": "ok"}
    people = client.get("/people").json()
    assert len(people) == 10
    assert {item["canonical_name"] for item in people} >= {"이형일", "홍지선", "이해민"}


def test_published_fact_is_traceable_through_source_policy(client: TestClient) -> None:
    claims = client.get("/people/00000000-0000-0000-0000-000000000001/claims").json()
    fact = next(item for item in claims if item["epistemic_status"] == "FACT")
    assert fact["asserted_as_true"] is True
    assert fact["evidence"][0]["stance"] == "SUPPORT"
    source = client.get(f"/sources/{fact['source_ids'][0]}").json()
    assert source["id"] == SOURCE_ID
    assert source["policy"]["can_store_metadata"] is True
    assert source["policy"]["can_show_excerpt"] is True


def test_api_renders_explicit_unknown_without_fact_promotion(client: TestClient) -> None:
    profile = client.get(f"/people/{PERSON_ID}").json()
    unknown = next(item for item in profile["claims"] if item["epistemic_status"] == "UNKNOWN")
    assert unknown["publication_status"] == "PUBLISHED"
    assert unknown["asserted_as_true"] is False
    assert unknown["resolution_note"]
    assert unknown["evidence"] == []


def test_ha_jungwoo_profile_projection_preserves_enrichment_semantics(
    client: TestClient,
) -> None:
    payload = client.get(f"/people/{HA_JUNGWOO_ID}").json()
    profile = payload["profile"]
    sections = {item["id"]: item for item in profile["sections"]}

    assert profile["section_order"] == [
        "identity",
        "summary",
        "career_timeline",
        "current_power_tasks",
        "appointment_logic",
        "decision_episodes",
        "repeated_patterns",
        "stakeholders",
        "controversies",
        "hearing_questions",
        "forecast",
        "limitations",
    ]
    assert sections["identity"]["status"] == "AVAILABLE"
    assert sections["summary"]["status"] == "AVAILABLE"
    nomination = sections["summary"]["entries"][0]
    assert nomination["details"]["predicate"] == "NOMINATED_AS"
    assert nomination["claim_id"] == "30000000-0000-0000-0000-000000000009"
    assert nomination["source_ids"] == [SOURCE_ID]

    assert sections["career_timeline"]["status"] == "AVAILABLE"
    timeline_predicates = [entry["details"]["predicate"] for entry in sections["career_timeline"]["entries"]]
    assert timeline_predicates == ["HELD_ROLE", "NOMINATED_AS"]
    held_role = sections["career_timeline"]["entries"][0]
    assert held_role["date"] == "2026-01-27"
    assert held_role["source_ids"] == [HA_ROLE_SOURCE_ID]

    assert sections["appointment_logic"]["status"] == "PARTIAL"
    rationale = sections["appointment_logic"]["entries"][0]
    assert rationale["details"]["predicate"] == "APPOINTMENT_RATIONALE"
    assert rationale["epistemic_status"] == "CLAIM"
    assert rationale["source_ids"] == [SOURCE_ID]

    assert sections["current_power_tasks"]["status"] == "UNKNOWN"
    assert sections["current_power_tasks"]["entries"] == []
    assert sections["stakeholders"]["status"] == "AVAILABLE"
    assert sections["stakeholders"]["entries"][0]["details"]["evidence_types"] == [
        "APPOINTMENT"
    ]
    assert sections["forecast"]["status"] == "UNKNOWN"
    assert sections["limitations"]["status"] == "AVAILABLE"


def test_profile_projection_keeps_flat_claims_for_backward_compatibility(
    client: TestClient,
) -> None:
    payload = client.get(f"/people/{HA_JUNGWOO_ID}").json()
    assert payload["claims"]
    assert payload["profile"]["semantics"] == "DERIVED_READ_MODEL_FROM_CANONICAL_EVIDENCE"


def test_review_surface_reports_source_conflict(client: TestClient) -> None:
    report = client.get("/admin/review").json()
    assert "30000000-0000-0000-0000-000000000013" in report["contradictions"]
    assert report["unpublishable_claims"] == []
    assert client.get("/people/00000000-0000-0000-0000-999999999999").status_code == 404


def test_api_startup_fails_on_unmigrated_database(tmp_path: Path) -> None:
    repository = SqlAlchemyRepository(f"sqlite:///{(tmp_path / 'missing.db').as_posix()}")
    with pytest.raises(DatabaseNotReady, match="not migrated"), TestClient(create_app(repository)):
        pass
