from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import event, func, select, text
from sqlalchemy.exc import OperationalError

from apps.api.main import create_app
from apps.api.operator import configure_read_only, documented_catalog, manifest_inspection
from packages.domain import db
from packages.persistence import SqlAlchemyRepository
from packages.persistence.operator_queries import MODELS, safe_url

TOKEN = "test-operator-token-" + "a" * 32


@pytest.fixture
def repository(tmp_path: Path):
    url = f"sqlite:///{(tmp_path / 'operator.db').as_posix()}"
    configuration = Config("alembic.ini")
    configuration.set_main_option("sqlalchemy.url", url)
    command.upgrade(configuration, "head")
    repository = SqlAlchemyRepository(url)
    repository.seed_golden()
    yield repository
    repository.engine.dispose()


def temporal():
    return {
        "valid_from": datetime.now(UTC),
        "valid_to": None,
        "recorded_at": datetime.now(UTC),
        "superseded_at": None,
    }


def insert_lane(repository):
    now = datetime.now(UTC)
    policy_id, source_id, snapshot_id, run_id = [str(uuid4()) for _ in range(4)]
    ids = [str(uuid4()) for _ in range(3)]
    with repository.sessions() as session:
        session.add(
            db.SourcePolicyRow(
                id=policy_id,
                domain="operator.example",
                source_class="test",
                collection_mode="API",
                can_fetch=True,
                can_store_metadata=True,
                can_store_fulltext=False,
                can_send_to_ai=False,
                can_show_excerpt=False,
                can_commercialize=False,
            )
        )
        session.flush()
        session.add(
            db.SourceRow(
                id=source_id,
                url="https://operator.example/item?id=17&ServiceKey=NEVER_LEAK",
                title="검증용 수집 출처",
                publisher="fixture",
                policy_id=policy_id,
            )
        )
        session.add(
            db.SourceRunRow(
                id=run_id,
                feeder="test_lane",
                scope_key="bounded",
                started_at=now,
                finished_at=now,
                status="PARTIAL",
                records_seen=3,
                observations_created=3,
                observations_unchanged=0,
                error_summary="NEVER_LEAK",
                metadata_json={"token": "NEVER_LEAK"},
            )
        )
        session.flush()
        session.add(
            db.SourceSnapshotRow(
                id=snapshot_id,
                source_id=source_id,
                fetched_at=now,
                content_hash="a" * 64,
                metadata_json={"token": "NEVER_LEAK"},
                fulltext="NEVER_LEAK",
            )
        )
        session.flush()
        for index, record_id in enumerate(ids):
            session.add(
                db.FeederObservationRow(
                    id=record_id,
                    feeder="test_lane",
                    scope_key="bounded",
                    provider_record_key="one" if index < 2 else "two",
                    snapshot_id=snapshot_id,
                    run_id=run_id,
                    recorded_at=now,
                    semantic_scope="test_only",
                    identity_hints_json={"email": "NEVER_LEAK"},
                    normalized_json={
                        "canonical_name": "수집된 이름",
                        "position_text": "기록된 직책",
                        "email": "NEVER_LEAK",
                        "nested": {"password": "NEVER_LEAK"},
                    },
                    content_hash=str(index) * 64,
                )
            )
        session.add(
            db.SourceCheckpointRow(
                id=str(uuid4()),
                feeder="test_lane",
                scope_key="bounded",
                cursor="NEVER_LEAK",
                metadata_json={"password": "NEVER_LEAK"},
                updated_at=now,
                last_run_id=run_id,
            )
        )
        session.commit()
    return ids, source_id


def test_operator_counts_are_real_and_versions_are_not_identities(repository):
    insert_lane(repository)
    summary = repository.operator_summary()
    assert summary["counts"]["observations"] == 3
    assert summary["counts"]["observation_keys"] == 2
    assert summary["counts"]["current_people"] == 10
    lane = next(item for item in summary["lanes"] if item["feeder"] == "test_lane")
    assert lane["latest_run_status"] == "PARTIAL"
    assert lane["last_success_at"] is None
    assert lane["provider_keys"] == 2
    assert lane["observation_versions"] == 3
    assert "coverage_percent" not in lane
    assert "NEVER_LEAK" not in str(summary)


def test_summary_is_bounded_query_count(repository):
    queries = []
    event.listen(repository.engine, "before_cursor_execute", lambda *args: queries.append(args[2]))
    repository.operator_summary()
    assert len(queries) == 2


def test_record_browser_filters_paginates_and_escapes_wildcards(repository):
    with repository.sessions() as session:
        for name in ("표준기관", "특수%기관", "특수_기관"):
            session.add(db.OrganizationRow(id=str(uuid4()), name=name, **temporal()))
        session.commit()
    first = repository.operator_records("organizations", q="기관", limit=1)
    second = repository.operator_records("organizations", q="기관", limit=1, offset=1)
    assert first["total"] == 3
    assert first["items"][0]["id"] != second["items"][0]["id"]
    assert repository.operator_records("organizations", q="%")["total"] == 1
    assert repository.operator_records("organizations", q="_")["total"] == 1
    for kwargs in ({"limit": 101}, {"offset": -1}, {"feeder": "unsupported"}):
        with pytest.raises(ValueError):
            repository.operator_records("organizations", **kwargs)
    with pytest.raises(ValueError):
        repository.operator_records("sqlite_master")


def test_safe_observation_content_and_foreign_key_graph(repository):
    ids, source_id = insert_lane(repository)
    result = repository.operator_records("observations", q="수집된 이름", feeder="test_lane")
    assert result["total"] == 3
    assert result["items"][0]["fields"]["position_text"] == "기록된 직책"
    assert "NEVER_LEAK" not in str(result)
    graph = repository.operator_record_detail("observations", ids[0])["graph"]
    assert f"sources:{source_id}" in {node["id"] for node in graph["nodes"]}
    assert "NEVER_LEAK" not in str(graph)
    assert sum(node["kind"] == "observations" for node in graph["nodes"]) == 1
    assert all(edge["source"] != edge["target"] for edge in graph["edges"])
    assert not any(node["kind"] == "people" for node in graph["nodes"])
    source = repository.operator_record_detail("sources", source_id)["record"]
    assert source["fields"]["url"] == "https://operator.example/item?id=17"


def test_equal_names_do_not_make_a_relation(repository):
    with repository.sessions() as session:
        ids = [str(uuid4()), str(uuid4())]
        session.add_all(
            [
                db.OrganizationRow(id=identifier, name="동일 이름", **temporal())
                for identifier in ids
            ]
        )
        session.commit()
    graph = repository.operator_record_detail("organizations", ids[0])["graph"]
    assert len(graph["nodes"]) == 1
    assert graph["edges"] == []


def test_default_public_app_has_no_operator_routes(repository):
    with TestClient(create_app(repository)) as client:
        assert client.get("/admin/operations").status_code == 404
        assert client.get("/admin/operations/records?kind=people").status_code == 404


def test_private_operator_auth_denies_missing_token_external_host_and_origin(repository):
    app = create_app(repository, enable_review_surface=True, operator_token=TOKEN)
    with TestClient(app, base_url="http://127.0.0.1") as client:
        assert client.get("/admin/operations").status_code == 403
        headers = {"x-civic-operator-token": TOKEN}
        response = client.get("/admin/operations", headers=headers)
        assert response.status_code == 200
        assert response.json()["counts"]["current_people"] == 10
        assert response.headers["cache-control"] == "private, no-store"
        assert TOKEN not in response.text
        assert (
            client.get(
                "/admin/operations", headers={**headers, "Host": "attacker.example"}
            ).status_code
            == 403
        )
        assert (
            client.get(
                "/admin/operations", headers={**headers, "Origin": "http://127.0.0.1"}
            ).status_code
            == 403
        )
        assert (
            client.get("/admin/operations/records?limit=10000", headers=headers).status_code == 422
        )
        assert (
            client.get("/admin/operations/records?kind=unknown", headers=headers).status_code == 422
        )
        assert (
            client.get("/admin/operations/records/people/not-uuid", headers=headers).status_code
            == 422
        )
        assert client.get("/openapi.json").status_code == 404
        assert client.post("/admin/operations", headers=headers).status_code == 405
    with pytest.raises(ValueError):
        create_app(repository, enable_review_surface=True, operator_token="weak")


def test_operator_engine_cannot_write_and_reads_do_not_mutate(repository):
    before = repository.operator_summary()["counts"]
    readonly = SqlAlchemyRepository(str(repository.engine.url))
    configure_read_only(readonly)
    try:
        assert readonly.operator_records("people")["total"] == 10
        with pytest.raises(OperationalError), readonly.engine.begin() as connection:
            connection.execute(text("UPDATE people SET canonical_name = 'INVALID'"))
        assert readonly.operator_summary()["counts"] == before
    finally:
        readonly.engine.dispose()


def test_bounded_graph_signals_truncation(repository):
    person_id = "00000000-0000-0000-0000-000000000001"
    with repository.sessions() as session:
        for i in range(30):
            session.add(
                db.ClaimRow(
                    id=str(uuid4()),
                    person_id=person_id,
                    organization_id=None,
                    subject="fixture",
                    predicate="HELD_ROLE",
                    object_text=f"role {i}",
                    proposition="test",
                    qualifiers={},
                    epistemic_status="CLAIM",
                    publication_status="DRAFT",
                    asserted_as_true=False,
                    **temporal(),
                )
            )
        session.commit()
    graph = repository.operator_record_detail("people", person_id)["graph"]
    assert graph["truncated"] is True
    assert len(graph["nodes"]) <= 80
    assert len({node["id"] for node in graph["nodes"]}) == len(graph["nodes"])


def test_manifest_preflight_is_read_only_and_reports_baseline_conflict(repository):
    before = repository.operator_summary()["counts"]
    result = manifest_inspection(repository)
    assert result["status"] == "BASELINE_OR_IDENTITY_CONFLICT"
    assert result["item_count"] == 27
    assert result["write_performed"] is False
    assert repository.operator_summary()["counts"] == before


def test_catalog_is_documentation_not_runtime_counts():
    catalog = documented_catalog()
    assert len(catalog) > 20
    assert all(item["basis"] == "DOCUMENTED_CAPABILITY_NOT_LIVE_COVERAGE" for item in catalog)
    assert all("observations" not in item for item in catalog)


def test_urls_and_all_record_kinds_use_explicit_fields(repository):
    assert safe_url("javascript:alert(1)") is None
    assert safe_url("https://user:secret@example.com/") is None
    assert (
        safe_url("https://example.com/?token=secret&pageIndex=2")
        == "https://example.com/?pageIndex=2"
    )
    for kind, model in MODELS.items():
        page = repository.operator_records(kind, limit=2)
        with repository.sessions() as session:
            assert page["total"] == session.scalar(select(func.count()).select_from(model))
        assert all("fulltext" not in item["fields"] for item in page["items"])
        assert "identity_hints_json" not in str(page["items"])


def test_railway_tunnel_uri_is_loopback_only_and_never_rewritten():
    from workers.operator_console import _private_uri

    assert _private_uri("status: opening tunnel", 55000) is None
    uri = "postgresql://operator:secret@127.0.0.1:55000/railway"
    assert _private_uri(uri, 55000) == uri
    with pytest.raises(RuntimeError):
        _private_uri("postgresql://operator:secret@external.example:55000/db", 55000)
    with pytest.raises(RuntimeError):
        _private_uri(uri, 55001)


def test_operator_factory_masks_invalid_connection_configuration(monkeypatch):
    from apps.api.operator import create_operator_app

    monkeypatch.setenv("CIVIC_OPERATOR_ENABLED", "1")
    monkeypatch.setenv("CIVIC_OPERATOR_TOKEN", TOKEN)
    monkeypatch.setenv("CIVIC_OPERATOR_LABEL", "TEST")
    monkeypatch.setenv("DATABASE_URL", "not-a-url-with-private-secret")
    with pytest.raises(RuntimeError) as error:
        create_operator_app()
    assert "private-secret" not in str(error.value)
    assert error.value.__suppress_context__ is True
