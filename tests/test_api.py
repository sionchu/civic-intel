from datetime import UTC, date, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient

from apps.api.main import create_app
from packages.domain.contracts import (
    FeederObservation,
    Source,
    SourcePolicy,
    SourceSnapshot,
)
from packages.domain.db import ClaimRow, DecisionEpisodeRow, PersonRow, RelationshipRow
from packages.domain.enums import IdentityStatus, SourceCollectionMode, SourceRunStatus
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
def seeded_repository(tmp_path: Path) -> SqlAlchemyRepository:
    repository = migrated_repository(tmp_path / "api.db")
    repository.seed_golden()

    return repository


@pytest.fixture()
def client(seeded_repository: SqlAlchemyRepository):
    repository = seeded_repository
    with TestClient(create_app(repository, enable_review_surface=True)) as api_client:
        yield api_client


def insert_person(
    repository: SqlAlchemyRepository,
    person_id: str,
    canonical_name: str,
    identity_status: IdentityStatus,
    birth_date: date | None = None,
) -> None:
    timestamp = datetime.now(UTC)
    with repository.sessions() as session:
        session.add(
            PersonRow(
                id=person_id,
                canonical_name=canonical_name,
                birth_date=birth_date,
                identity_status=identity_status.value,
                valid_from=timestamp,
                valid_to=None,
                recorded_at=timestamp,
                superseded_at=None,
            )
        )
        session.commit()


def stage_observation(
    repository: SqlAlchemyRepository,
    *,
    feeder: str,
    semantic_scope: str,
    provider_record_key: str,
    canonical_name: str,
    birth_date: str | None = None,
) -> FeederObservation:
    suffix = uuid4().hex
    policy = SourcePolicy(
        domain=f"review-{suffix}.example",
        source_class="test_review_source",
        collection_mode=SourceCollectionMode.API,
        can_fetch=True,
        can_store_metadata=True,
        can_store_fulltext=False,
        can_send_to_ai=False,
        can_show_excerpt=False,
        can_commercialize=False,
        license="test-only",
    )
    source = Source(
        url=f"https://{policy.domain}/records/{provider_record_key}",
        title="Review source",
        publisher="Test publisher",
        policy_id=policy.id,
    )
    snapshot = SourceSnapshot(
        source_id=source.id,
        content_hash=("a" * 64),
        metadata={"fixture": True},
    )
    scope_key = f"scope-{suffix}"
    run = repository.start_source_run(feeder, scope_key, metadata={"fixture": True})
    normalized = {"canonical_name": canonical_name}
    if birth_date is not None:
        normalized["birth_date"] = birth_date
    observation = FeederObservation(
        feeder=feeder,
        scope_key=scope_key,
        provider_record_key=provider_record_key,
        snapshot_id=snapshot.id,
        run_id=run.id,
        semantic_scope=semantic_scope,
        normalized=normalized,
        content_hash=("b" * 64),
    )
    repository.commit_source_page(
        run_id=run.id,
        policy=policy,
        source=source,
        snapshot=snapshot,
        observations=[observation],
        cursor="1",
        checkpoint_metadata={"fixture": True},
    )
    repository.finish_source_run(run.id, SourceRunStatus.SUCCESS)
    return observation


def test_health_and_real_roster(client: TestClient) -> None:
    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/ready").json() == {"status": "ready"}
    people = client.get("/people").json()
    assert len(people) == 10
    assert {item["canonical_name"] for item in people} >= {"이형일", "홍지선", "이해민"}


def test_readiness_masks_database_failure(
    seeded_repository: SqlAlchemyRepository,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_ready() -> None:
        raise RuntimeError("database detail must remain private")

    with TestClient(create_app(seeded_repository), raise_server_exceptions=False) as api_client:
        monkeypatch.setattr(seeded_repository, "assert_ready", fail_ready)
        response = api_client.get("/ready")

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "SERVICE_UNAVAILABLE"
    assert response.json()["error"]["request_id"] == response.headers["x-request-id"]
    assert "database detail" not in response.text


def test_public_roster_and_profiles_exclude_unresolved_identities(
    client: TestClient, seeded_repository: SqlAlchemyRepository
) -> None:
    review_id = "00000000-0000-0000-0000-000000000011"
    unresolved_id = "00000000-0000-0000-0000-000000000012"
    insert_person(seeded_repository, review_id, "검토 중인 사람", IdentityStatus.REVIEW)
    insert_person(seeded_repository, unresolved_id, "미해결 사람", IdentityStatus.UNRESOLVED)

    people = client.get("/people").json()

    assert all(item["identity_status"] == "RESOLVED" for item in people)
    assert review_id not in {item["id"] for item in people}
    assert unresolved_id not in {item["id"] for item in people}
    assert client.get(f"/people/{review_id}").status_code == 404
    assert client.get(f"/people/{unresolved_id}/claims").status_code == 404


def test_review_surface_is_disabled_by_default(seeded_repository: SqlAlchemyRepository) -> None:
    with TestClient(create_app(seeded_repository)) as public_client:
        response = public_client.get("/admin/review")
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "PUBLIC_RECORD_NOT_FOUND"
        assert response.json()["error"]["request_id"] == response.headers["x-request-id"]


def test_public_profile_does_not_publish_unlinked_decision_episodes(client: TestClient) -> None:
    payload = client.get("/people/00000000-0000-0000-0000-000000000007").json()
    episodes = next(
        section for section in payload["profile"]["sections"] if section["id"] == "decision_episodes"
    )
    assert episodes["status"] == "UNKNOWN"
    assert episodes["entries"] == []


def test_public_profiles_exclude_superseded_temporal_records(
    client: TestClient, seeded_repository: SqlAlchemyRepository
) -> None:
    with seeded_repository.sessions() as session:
        session.get(ClaimRow, "30000000-0000-0000-0000-000000000013").superseded_at = datetime.now(
            UTC
        )
        session.get(RelationshipRow, "50000000-0000-0000-0000-000000000001").superseded_at = (
            datetime.now(UTC)
        )
        session.get(DecisionEpisodeRow, "70000000-0000-0000-0000-000000000002").superseded_at = (
            datetime.now(UTC)
        )
        session.commit()

    profile = client.get("/people/00000000-0000-0000-0000-000000000007").json()
    assert all(claim["id"] != "30000000-0000-0000-0000-000000000013" for claim in profile["claims"])
    assert next(
        section for section in profile["profile"]["sections"] if section["id"] == "decision_episodes"
    )["entries"] == []

    relationship_profile = client.get("/people/00000000-0000-0000-0000-000000000009").json()
    assert relationship_profile["relationship_ids"] == []


def test_published_fact_is_traceable_through_source_policy(client: TestClient) -> None:
    claims = client.get("/people/00000000-0000-0000-0000-000000000001/claims").json()
    fact = next(item for item in claims if item["epistemic_status"] == "FACT")
    assert fact["asserted_as_true"] is True
    assert fact["evidence"][0]["stance"] == "SUPPORT"
    source = client.get(f"/sources/{fact['source_ids'][0]}").json()
    assert source["id"] == SOURCE_ID
    assert set(source) == {
        "id",
        "url",
        "title",
        "publisher",
        "published_at",
        "source_class",
        "license",
        "terms_checked_at",
        "policy_summary",
    }
    assert "policy" not in source
    assert source["policy_summary"] == {
        "collection": "NOT_PERMITTED",
        "metadata_storage": "PERMITTED",
        "fulltext_storage": "NOT_PERMITTED",
        "excerpt_display": "PERMITTED",
    }


def test_public_source_requires_reachable_published_claim(
    client: TestClient,
    seeded_repository: SqlAlchemyRepository,
) -> None:
    observation = stage_observation(
        seeded_repository,
        feeder="test_private_source",
        semantic_scope="review_only",
        provider_record_key="private-001",
        canonical_name="검토 전 후보",
    )
    snapshot = seeded_repository.source_snapshot(observation.snapshot_id)
    assert snapshot is not None

    response = client.get(f"/sources/{snapshot.source_id}")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "PUBLIC_RECORD_NOT_FOUND"
    assert response.json()["error"]["request_id"] == response.headers["x-request-id"]
    assert "review" not in response.text.casefold()


def test_public_api_uses_safe_error_contract(client: TestClient) -> None:
    response = client.get("/people/00000000-0000-0000-0000-999999999999")

    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "PUBLIC_RECORD_NOT_FOUND",
            "message": "The public record was not found.",
            "request_id": response.headers["x-request-id"],
        }
    }
    assert "detail" not in response.json()


def test_public_api_masks_unexpected_failure(
    seeded_repository: SqlAlchemyRepository,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_people():
        raise RuntimeError("database-password=must-not-leak")

    monkeypatch.setattr(seeded_repository, "public_people", fail_people)
    with TestClient(
        create_app(seeded_repository),
        raise_server_exceptions=False,
    ) as public_client:
        response = public_client.get("/people")

    assert response.status_code == 503
    assert response.json()["error"] == {
        "code": "SERVICE_UNAVAILABLE",
        "message": "The public data service is temporarily unavailable.",
        "request_id": response.headers["x-request-id"],
    }
    assert "password" not in response.text.casefold()


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
        "assembly_base_profile",
        "summary",
        "career_timeline",
        "recent_changes",
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


def test_profile_exposes_evidence_stance_and_batch_trace(client: TestClient) -> None:
    payload = client.get(f"/people/{HA_JUNGWOO_ID}").json()
    nomination = next(
        item
        for item in payload["profile"]["sections"]
        for item in item["entries"]
        if item.get("claim_id") == "30000000-0000-0000-0000-000000000009"
    )

    assert nomination["evidence"][0]["stance"] == "SUPPORT"
    assert nomination["evidence"][0]["snapshot_id"] == "21000000-0000-0000-0000-000000000001"
    assert nomination["evidence"][0]["feeder_observation_id"] is None

    conflict_profile = client.get(
        "/people/00000000-0000-0000-0000-000000000007"
    )
    assert conflict_profile.status_code == 200
    conflict_payload = conflict_profile.json()
    conflict_claim = next(
        item
        for item in conflict_payload["claims"]
        if item["id"] == "30000000-0000-0000-0000-000000000013"
    )
    conflict_entry = next(
        item
        for section in conflict_payload["profile"]["sections"]
        for item in section["entries"]
        if item.get("claim_id") == "30000000-0000-0000-0000-000000000013"
    )
    assert conflict_claim["source_conflict"] is True
    assert conflict_entry["source_conflict"] is True
    assert {item["stance"] for item in conflict_entry["evidence"]} == {"SUPPORT", "REFUTE"}


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


def test_review_surface_exposes_materialization_action_and_provenance(
    client: TestClient, seeded_repository: SqlAlchemyRepository
) -> None:
    insert_person(
        seeded_repository,
        "00000000-0000-0000-0000-000000000013",
        "하드 충돌 후보",
        IdentityStatus.RESOLVED,
        date(1980, 1, 1),
    )
    review_observation = stage_observation(
        seeded_repository,
        feeder="test_unsupported_feeder",
        semantic_scope="test_scope",
        provider_record_key="review-001",
        canonical_name="검토 후보",
    )
    hard_conflict_observation = stage_observation(
        seeded_repository,
        feeder="national_assembly_members",
        semantic_scope="legislative_member_roster",
        provider_record_key="M-HARD-001",
        canonical_name="하드 충돌 후보",
        birth_date="1990-01-01",
    )
    seeded_repository.materialize_feeder_observation(review_observation.id)
    seeded_repository.materialize_feeder_observation(hard_conflict_observation.id)

    report = client.get("/admin/review").json()
    items = {item["observation"]["provider_record_key"]: item for item in report["review_items"]}

    assert items["review-001"]["action"] == "REVIEW_REQUIRED"
    assert items["review-001"]["provenance"]["source"]["title"] == "Review source"
    assert items["review-001"]["provenance"]["snapshot"]["id"] == str(
        seeded_repository.feeder_observation(review_observation.id).snapshot_id
    )
    assert items["M-HARD-001"]["action"] == "HARD_CONFLICT"
    assert items["M-HARD-001"]["candidate_person"]["canonical_name"] == "하드 충돌 후보"
    assert "normalized" not in items["review-001"]["observation"]
    public_candidate = client.get(
        "/people/00000000-0000-0000-0000-000000000013"
    ).json()
    assert all(
        claim["qualifiers"].get("provider_record_key") != "M-HARD-001"
        for claim in public_candidate["claims"]
    )


def test_api_startup_fails_on_unmigrated_database(tmp_path: Path) -> None:
    repository = SqlAlchemyRepository(f"sqlite:///{(tmp_path / 'missing.db').as_posix()}")
    with pytest.raises(DatabaseNotReady, match="not migrated"), TestClient(create_app(repository)):
        pass
