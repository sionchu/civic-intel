from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from alembic import command as alembic_command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError
from test_alio_organization_activation import commit_prepared, enumerated_repository

from apps.api.admin import sign_preview, verify_preview
from apps.api.main import create_app
from packages.domain import db
from packages.domain.admin import AdminCommand
from packages.persistence.admin_workflow import AdminError

TOKEN = "operator-preview-tests-" + "x" * 40
ACTOR = "test-reviewer"
REASON = "테스트 공식 공시 원문과 기관·직책 문맥을 직접 검토했습니다."


@pytest.fixture
def repository(tmp_path: Path):
    repo, _ = enumerated_repository(tmp_path / "admin.db")
    commit_prepared(repo)
    yield repo
    repo.engine.dispose()


def command(action, *ids, **kwargs):
    return AdminCommand(
        request_id=uuid4(),
        action=action,
        record_ids=tuple(UUID(str(i)) for i in ids),
        reason=REASON,
        **kwargs,
    )


def apply(repo, request):
    preview = repo.admin_preview(request)
    return repo.admin_commit(request, ACTOR, preview["state_hash"])


def first_observation(repo):
    return repo.admin_queue(state="ALL")["items"][0]["id"]


def registered(repo):
    result = apply(repo, command("REGISTER_PERSON", first_observation(repo), human_verified=True))
    return result["result"]["outcomes"][0]


def evidence_for(repo, claim_id):
    return tuple(item.id for item in repo.evidence_for(UUID(str(claim_id))))


def counts(repo):
    with repo.sessions() as session:
        return {
            model.__tablename__: session.scalar(select(func.count()).select_from(model))
            for model in (
                db.PersonRow,
                db.ClaimRow,
                db.ClaimEvidenceRow,
                db.FeederObservationRow,
                db.AdminOperationRow,
                db.IdentityReviewItemRow,
                db.PersonObservationLinkRow,
            )
        }


def test_real_work_queue_includes_unregistered_records_not_only_open_items(repository):
    queue = repository.admin_queue()
    assert queue["named_record_total"] == 3
    assert queue["counts"]["UNREVIEWED"] == 3
    assert len(queue["items"]) == 3
    assert counts(repository)["identity_review_items"] == 0
    assert all(item["fields"]["canonical_name"] for item in queue["items"])
    assert queue["semantics"] == "NAMED_SOURCE_RECORDS_NOT_DEDUPLICATED_PEOPLE"


def test_hold_reopen_and_exclude_are_durable_audited_decisions(repository):
    identifiers = [item["id"] for item in repository.admin_queue()["items"][:2]]
    original = counts(repository)
    preview = repository.admin_preview(command("HOLD", *identifiers))
    assert preview["write_performed"] is False
    assert counts(repository) == original
    apply(repository, command("HOLD", *identifiers))
    assert repository.admin_queue(state="HELD")["total"] == 2
    apply(repository, command("REOPEN", identifiers[0]))
    apply(repository, command("EXCLUDE", identifiers[1]))
    queue = repository.admin_queue(state="ALL")
    assert queue["counts"]["EXCLUDED"] == 1
    assert queue["counts"]["UNREVIEWED"] == 2
    assert counts(repository)["feeder_observations"] == original["feeder_observations"]
    assert repository.admin_history()["total"] == 3


def test_register_person_creates_draft_claim_and_exact_link_not_auto_publication(repository):
    result = registered(repository)
    assert counts(repository)["people"] == 1
    person = repository.person(UUID(result["person_id"]))
    assert person.identity_status.value == "RESOLVED"
    claim = repository.claims(person_id=person.id)[0]
    assert claim.publication_status.value == "DRAFT"
    assert claim.epistemic_status.value == "CLAIM"
    assert claim.asserted_as_true is False
    assert repository.admin_queue(state="REGISTERED")["total"] == 1
    assert repository.admin_history()["items"][0]["actor"] == ACTOR
    with pytest.raises(AdminError, match="이미 인물"):
        apply(repository, command("REGISTER_PERSON", result["observation_id"], human_verified=True))


def test_register_requires_explicit_human_review():
    with pytest.raises(ValueError):
        command("REGISTER_PERSON", uuid4())
    with pytest.raises(ValueError):
        command("MERGE_PERSON", uuid4(), target_person_id=uuid4(), human_verified=True)
    with pytest.raises(ValueError):
        command("HOLD", uuid4(), value="an ignored edit")


def test_existing_same_name_stops_registration_without_linking(repository):
    observation = first_observation(repository)
    name = repository.admin_queue(state="ALL")["items"][0]["fields"]["canonical_name"]
    now = datetime.now(UTC)
    with repository.sessions() as session:
        session.add(
            db.PersonRow(
                id=str(uuid4()),
                canonical_name=name,
                identity_status="RESOLVED",
                birth_date=None,
                valid_from=now,
                valid_to=None,
                recorded_at=now,
                superseded_at=None,
            )
        )
        session.commit()
    before = counts(repository)
    with pytest.raises(AdminError) as error:
        apply(repository, command("REGISTER_PERSON", observation, human_verified=True))
    assert error.value.code == "IDENTITY_REVIEW_REQUIRED"
    assert counts(repository) == before
    assert repository.admin_queue(state="HAS_CANDIDATE")["total"] == 1


def test_idempotent_retry_and_conflicting_request_id(repository):
    request = command("HOLD", first_observation(repository))
    preview = repository.admin_preview(request)
    first = repository.admin_commit(request, ACTOR, preview["state_hash"])
    second = repository.admin_commit(request, ACTOR, preview["state_hash"])
    assert first["write_performed"] is True
    assert second["replayed"] is True
    assert repository.admin_history()["total"] == 1
    changed = request.model_copy(
        update={"reason": "다른 내용으로 같은 요청 ID를 재사용하면 거절해야 합니다."}
    )
    with pytest.raises(AdminError) as error:
        repository.admin_commit(changed, ACTOR, preview["state_hash"])
    assert error.value.code == "IDEMPOTENCY_CONFLICT"


def test_stale_preview_rejected_without_partial_write(repository):
    observation = first_observation(repository)
    request = command("REGISTER_PERSON", observation, human_verified=True)
    preview = repository.admin_preview(request)
    apply(repository, command("HOLD", observation))
    before = counts(repository)
    with pytest.raises(AdminError) as error:
        repository.admin_commit(request, ACTOR, preview["state_hash"])
    assert error.value.code == "STALE_PREVIEW"
    assert counts(repository) == before


def test_batch_failure_is_all_or_nothing(repository):
    ids = [item["id"] for item in repository.admin_queue()["items"]]
    apply(repository, command("REGISTER_PERSON", ids[-1], human_verified=True))
    before = counts(repository)
    with pytest.raises(AdminError):
        apply(repository, command("REGISTER_PERSON", *ids, human_verified=True))
    assert counts(repository) == before


def test_review_publish_withdraw_retains_epistemic_and_evidence(repository):
    result = registered(repository)
    claim_id = result["claim_id"]
    apply(repository, command("SUBMIT_REVIEW", claim_id))
    apply(repository, command("PUBLISH", claim_id))
    claim = repository.claims(person_id=UUID(result["person_id"]))[0]
    assert claim.publication_status.value == "PUBLISHED" and claim.epistemic_status.value == "CLAIM"
    before = counts(repository)
    apply(repository, command("WITHDRAW", claim_id))
    assert (
        repository.claims(person_id=UUID(result["person_id"]))[0].publication_status.value
        == "WITHHELD"
    )
    assert counts(repository)["claim_evidence"] == before["claim_evidence"]


def test_correction_is_draft_then_replaces_original_on_approval(repository):
    result = registered(repository)
    original_id = result["claim_id"]
    apply(repository, command("PUBLISH", original_id))
    request = command(
        "CORRECT_CLAIM",
        original_id,
        value="검토한 원문의 직책 표기를 정정한 기록이다.",
        evidence_ids=evidence_for(repository, original_id),
    )
    corrected = apply(repository, request)["result"]["outcomes"][0]["correction_claim_id"]
    originals = {str(row.id): row for row in repository.claims(person_id=UUID(result["person_id"]))}
    assert originals[original_id].publication_status.value == "PUBLISHED"
    assert originals[corrected].publication_status.value == "DRAFT"
    apply(repository, command("PUBLISH", corrected))
    current = repository.claims(person_id=UUID(result["person_id"]), current_only=True)
    assert [str(row.id) for row in current] == [corrected]
    assert repository.evidence_for(UUID(original_id))


def test_policy_denial_blocks_publication_and_rolls_back(repository):
    result = registered(repository)
    row = repository.evidence_for(UUID(result["claim_id"]))[0]
    with repository.sessions() as session:
        source = session.get(db.SourceRow, str(row.source_id))
        session.get(db.SourcePolicyRow, source.policy_id).can_store_metadata = False
        session.commit()
    before = counts(repository)
    from packages.rendering.alio_organization_content import AlioOrganizationContentError

    with pytest.raises((PermissionError, AdminError, AlioOrganizationContentError)):
        apply(repository, command("PUBLISH", result["claim_id"]))
    assert counts(repository) == before


def test_rename_and_deactivation_preserve_sources_and_alias_history(repository):
    result = registered(repository)
    person_id = result["person_id"]
    before = counts(repository)
    apply(
        repository,
        command(
            "RENAME_PERSON",
            person_id,
            value="검토된 정정 이름",
            evidence_ids=evidence_for(repository, result["claim_id"]),
        ),
    )
    assert repository.person(UUID(person_id)).canonical_name == "검토된 정정 이름"
    with repository.sessions() as session:
        assert session.scalar(select(func.count()).select_from(db.PersonAliasRow)) == 1
    apply(repository, command("DEACTIVATE_PERSON", person_id))
    assert repository.person(UUID(person_id)).superseded_at is not None
    assert counts(repository)["feeder_observations"] == before["feeder_observations"]
    assert repository.admin_queue(state="EXCLUDED")["total"] == 1


def test_merge_requires_reviewed_bridge_and_preserves_source_records(repository):
    result = registered(repository)
    source_id = result["person_id"]
    source = repository.person(UUID(source_id))
    target_id = str(uuid4())
    now = datetime.now(UTC)
    with repository.sessions() as session:
        session.add(
            db.PersonRow(
                id=target_id,
                canonical_name=source.canonical_name,
                identity_status="RESOLVED",
                birth_date=None,
                valid_from=now,
                valid_to=None,
                recorded_at=now,
                superseded_at=None,
            )
        )
        session.commit()
    apply(repository, command("PUBLISH", result["claim_id"]))
    before = counts(repository)
    merged = apply(
        repository,
        command(
            "MERGE_PERSON",
            source_id,
            target_person_id=UUID(target_id),
            human_verified=True,
            identity_basis="OFFICIAL_BIOGRAPHY_CONTINUITY",
            evidence_ids=evidence_for(repository, result["claim_id"]),
        ),
    )
    assert merged["result"]["outcomes"][0]["surviving_person_id"] == target_id
    assert repository.person(UUID(source_id)).superseded_at is not None
    assert len(repository.claims(person_id=UUID(target_id), current_only=True)) == 1
    assert repository.claims(person_id=UUID(source_id), current_only=True) == []
    assert counts(repository)["people"] == before["people"]
    assert counts(repository)["feeder_observations"] == before["feeder_observations"]


def test_preview_signature_rejects_tampering_wrong_actor_and_expiry(repository, monkeypatch):
    request = command("HOLD", first_observation(repository))
    preview = repository.admin_preview(request)
    token = sign_preview(request, ACTOR, preview["state_hash"], TOKEN)
    assert verify_preview(token, request, ACTOR, TOKEN) == preview["state_hash"]
    for token_value, actor in ((token + "x", ACTOR), (token, "someone-else")):
        with pytest.raises(AdminError):
            verify_preview(token_value, request, actor, TOKEN)
    monkeypatch.setattr("apps.api.admin.time.time", lambda: 99999999999)
    with pytest.raises(AdminError):
        verify_preview(token, request, ACTOR, TOKEN)


def test_private_commit_requires_token_write_optin_and_confirmation(repository):
    request = command("HOLD", first_observation(repository))
    app = create_app(
        repository,
        enable_review_surface=True,
        operator_token=TOKEN,
        operator_writes=True,
        operator_actor=ACTOR,
    )
    headers = {"x-civic-operator-token": TOKEN}
    with TestClient(app, base_url="http://127.0.0.1") as client:
        assert (
            client.post(
                "/admin/operations/preview", json=request.model_dump(mode="json")
            ).status_code
            == 403
        )
        preview = client.post(
            "/admin/operations/preview", headers=headers, json=request.model_dump(mode="json")
        )
        assert preview.status_code == 200, preview.text
        body = {
            "command": request.model_dump(mode="json"),
            "preview_token": preview.json()["preview_token"],
            "confirmed": False,
        }
        assert (
            client.post("/admin/operations/commit", headers=headers, json=body).status_code == 403
        )
        body["confirmed"] = True
        response = client.post("/admin/operations/commit", headers=headers, json=body)
        assert response.status_code == 200, response.text
        assert response.json()["write_performed"] is True
        assert (
            client.post(
                "/admin/operations/commit",
                headers={**headers, "origin": "http://attacker"},
                json=body,
            ).status_code
            == 403
        )
    read_app = create_app(repository, enable_review_surface=True, operator_token=TOKEN)
    with TestClient(read_app, base_url="http://127.0.0.1") as client:
        assert (
            client.post("/admin/operations/commit", headers=headers, json=body).status_code == 403
        )


def test_append_only_audit_and_populated_migration_roundtrip(repository):
    apply(repository, command("HOLD", first_observation(repository)))
    with pytest.raises(DBAPIError), repository.engine.begin() as connection:
        connection.execute(text("UPDATE admin_operations SET actor='tampered'"))
    with pytest.raises(DBAPIError), repository.engine.begin() as connection:
        connection.execute(text("DELETE FROM admin_operations"))
    url = str(repository.engine.url)
    domain_before = counts(repository)
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", url)
    alembic_command.downgrade(config, "0006")
    repository.assert_ready()  # Additive rollout supports old read schema.
    assert repository.admin_schema_ready() is False
    assert repository.admin_queue()["named_record_total"] == 3
    alembic_command.upgrade(config, "head")
    assert repository.admin_schema_ready() is True
    assert counts(repository)["feeder_observations"] == domain_before["feeder_observations"]
    assert counts(repository)["claims"] == domain_before["claims"]


def test_registered_role_graph_is_publish_gated_and_bidirectional(repository):
    result = registered(repository)
    person_id = result["person_id"]
    claim = repository.claims(person_id=UUID(person_id))[0]
    organization_id = claim.qualifiers["organization_id"]
    with TestClient(create_app(repository)) as client:
        before = client.get(f"/ontology/people/{person_id}").json()
        assert not any(edge["relation_type"] == "DISCLOSED_ROLE_AT" for edge in before["edges"])
        apply(repository, command("PUBLISH", result["claim_id"]))
        for path in (f"/ontology/people/{person_id}", f"/ontology/organizations/{organization_id}"):
            response = client.get(path)
            assert response.status_code == 200, response.text
            role = [
                edge
                for edge in response.json()["edges"]
                if edge["relation_type"] == "DISCLOSED_ROLE_AT"
            ]
            assert len(role) == 1
            assert role[0]["source"] == f"person:{person_id}"
            assert role[0]["target"] == f"organization:{organization_id}"
            assert role[0]["evidence_ids"]
        apply(repository, command("WITHDRAW", result["claim_id"]))
        assert not client.get(f"/ontology/people/{person_id}").json()["edges"]


def test_initial_migration_does_not_precreate_future_audit_table(tmp_path):
    from sqlalchemy import create_engine, inspect

    database_url = f"sqlite:///{(tmp_path / 'pre-audit.db').as_posix()}"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)
    alembic_command.upgrade(config, "0006")
    engine = create_engine(database_url)
    assert "admin_operations" not in inspect(engine).get_table_names()
    alembic_command.upgrade(config, "head")
    assert "admin_operations" in inspect(engine).get_table_names()
    engine.dispose()


def test_successful_registration_obeys_database_foreign_keys(repository):
    from sqlalchemy import event

    @event.listens_for(repository.engine, "connect")
    def enforce(dbapi_connection, _):
        dbapi_connection.execute("PRAGMA foreign_keys = ON")

    repository.engine.dispose()
    result = registered(repository)
    apply(repository, command("PUBLISH", result["claim_id"]))
    apply(repository, command("DEACTIVATE_PERSON", result["person_id"]))
    with repository.engine.connect() as connection:
        assert list(connection.execute(text("PRAGMA foreign_key_check"))) == []


def test_stored_alias_is_a_review_candidate_not_an_unseen_new_person(repository):
    observed = repository.admin_queue()["items"][0]
    person_id = str(uuid4())
    now = datetime.now(UTC)
    with repository.sessions() as session:
        session.add(
            db.PersonRow(
                id=person_id,
                canonical_name="이미 정정된 이름",
                birth_date=None,
                identity_status="RESOLVED",
                valid_from=now,
                valid_to=None,
                recorded_at=now,
                superseded_at=None,
            )
        )
        session.flush()
        session.add(
            db.PersonAliasRow(
                id=str(uuid4()),
                person_id=person_id,
                name=observed["fields"]["canonical_name"],
                valid_from=now,
                valid_to=None,
                recorded_at=now,
                superseded_at=None,
            )
        )
        session.commit()
    result = repository.admin_queue(state="HAS_CANDIDATE")
    assert result["total"] == 1
    assert result["items"][0]["candidates"][0]["id"] == person_id
    with pytest.raises(AdminError) as error:
        apply(repository, command("REGISTER_PERSON", observed["id"], human_verified=True))
    assert error.value.code == "IDENTITY_REVIEW_REQUIRED"


def test_reviewed_link_uses_explicit_bridge_without_creating_another_person(repository):
    observed = repository.admin_queue()["items"][0]
    person_id = str(uuid4())
    now = datetime.now(UTC)
    with repository.sessions() as session:
        session.add(
            db.PersonRow(
                id=person_id,
                canonical_name=observed["fields"]["canonical_name"],
                birth_date=None,
                identity_status="RESOLVED",
                valid_from=now,
                valid_to=None,
                recorded_at=now,
                superseded_at=None,
            )
        )
        session.commit()
        evidence_id = session.scalar(
            select(db.ClaimEvidenceRow.id)
            .where(db.ClaimEvidenceRow.feeder_observation_id == observed["id"])
            .limit(1)
        )
    result = apply(
        repository,
        command(
            "LINK_PERSON",
            observed["id"],
            target_person_id=UUID(person_id),
            evidence_ids=(UUID(evidence_id),),
            identity_basis="OFFICIAL_CAREER_CONTINUITY",
            human_verified=True,
        ),
    )
    assert counts(repository)["people"] == 1
    assert result["result"]["outcomes"][0]["identity_action"] == "REVIEWED_LINK"
    assert result["result"]["review_evidence_ids"] == [evidence_id]


def test_queue_search_supports_institution_and_role(repository):
    assert repository.admin_queue(q="테스트공기업")["total"] == 2
    assert repository.admin_queue(q="상임기관장")["total"] == 1
    assert repository.admin_queue(q="이전문")["total"] == 1
