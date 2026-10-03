from __future__ import annotations

import hashlib
from datetime import UTC, date, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import event, func, select, text

from apps.api.main import create_app
from packages.connectors.gukgam_witness_packet import canonical_hash
from packages.domain.admin import AdminCommand
from packages.domain.contracts import Claim, ClaimEvidence, Person, Source, SourcePolicy
from packages.domain.enums import IdentityStatus
from packages.persistence import models as db
from packages.persistence.admin_workflow import AdminError
from packages.rendering.gukgam_witness_claim import GUKGAM_WITNESS_LISTING_PREDICATE
from packages.rendering.gukgam_witness_review import load_current_gukgam_witness_documents
from tests.test_gukgam_reviewed_plan_import import migrated_repository
from tests.test_gukgam_witness import ARTIFACT, capture, synthetic_packet
from workers.gukgam_witness_import import persist_capture

ACTOR = "synthetic-witness-reviewer"
TOKEN = "synthetic-test-token-" + "x" * 40


@pytest.fixture
def scenario(tmp_path):
    repository = migrated_repository(tmp_path / "synthetic-witness-admin.db")
    persist_capture(repository, capture())
    with repository(read_only=True) as uow:
        document = load_current_gukgam_witness_documents(uow.acquisition)[0]
    people = tuple(
        Person(canonical_name=row.printed_name, identity_status=IdentityStatus.RESOLVED)
        for row in document.packet.rows
    )
    policy = SourcePolicy(
        domain="synthetic.example.gov", source_class="official_biography", collection_mode="API",
        can_fetch=True, can_store_metadata=True, can_store_fulltext=False, can_send_to_ai=False,
        can_show_excerpt=False, can_commercialize=False,
    )
    source = Source(
        url="https://synthetic.example.gov/biography", title="Synthetic identity bridge",
        publisher="Synthetic fixture", policy_id=policy.id,
    )
    bridge_claims = tuple(
        Claim(
            person_id=person.id, subject=person.canonical_name, predicate="SYNTHETIC_BIOGRAPHY",
            proposition="Synthetic official continuity fixture, never a real identity attestation.",
            object_text="Synthetic official continuity",
            epistemic_status="CLAIM", publication_status="DRAFT", asserted_as_true=False,
        )
        for person in people
    )
    bridges = tuple(
        ClaimEvidence(claim_id=claim.id, source_id=source.id, stance="SUPPORT")
        for claim in bridge_claims
    )
    with repository() as uow:
        for person in people:
            uow.identity.add_person(person)
        uow._session.add(db.SourcePolicyRow(**{**policy.model_dump(), "id": str(policy.id)}))
        uow._session.flush()
        uow._session.add(db.SourceRow(
            **{**source.model_dump(), "id": str(source.id), "url": str(source.url),
               "policy_id": str(policy.id)},
        ))
        uow._session.flush()
        for claim in bridge_claims:
            uow._session.add(db.ClaimRow(
                **{**claim.model_dump(), "id": str(claim.id), "person_id": str(claim.person_id)},
            ))
        uow._session.flush()
        for bridge in bridges:
            uow._session.add(db.ClaimEvidenceRow(
                **{**bridge.model_dump(), "id": str(bridge.id), "claim_id": str(bridge.claim_id),
                   "source_id": str(source.id)},
            ))
        uow.commit()
    yield repository, document, people, bridges, policy, source
    repository.close()


def request(scenario, index=0, **changes):
    _, document, people, bridges, _, _ = scenario
    values = {
        "request_id": uuid4(), "action": "LINK_PERSON",
        "record_ids": (document.contexts[index][0].id,),
        "target_person_id": people[index].id, "evidence_ids": (bridges[index].id,),
        "identity_basis": "OFFICIAL_BIOGRAPHY_CONTINUITY", "human_verified": True,
        "reason": "SYNTHETIC ONLY: explicit official continuity review; no real human attestation.",
    }
    values.update(changes)
    return AdminCommand(**values)


def state(repository):
    with repository(read_only=True) as uow:
        return {
            table.name: uow._session.scalar(select(func.count()).select_from(table))
            for table in db.Base.metadata.sorted_tables
        }


def immutable_rows(repository):
    with repository(read_only=True) as uow:
        return {
            model.__tablename__: [
                tuple(getattr(row, column.key) for column in model.__table__.columns)
                for row in uow._session.scalars(select(model).order_by(model.id))
            ]
            for model in (
                db.SourcePolicyRow, db.SourceRow, db.SourceSnapshotRow,
                db.FeederObservationRow, db.SourceRunRow, db.SourceCheckpointRow, db.PersonRow,
            )
        }


@pytest.mark.parametrize("index", [0, 1, 2])
def test_reviewed_link_is_atomic_listing_only_and_reusable_by_claim_inspection(scenario, index):
    repository, document, people, _, _, _ = scenario
    command = request(scenario, index)
    before = state(repository)
    originals = immutable_rows(repository)
    statements = []
    listener = lambda connection, cursor, statement, *args: statements.append(statement)
    event.listen(repository.engine, "before_cursor_execute", listener)
    try:
        preview = repository.admin_preview(command)
    finally:
        event.remove(repository.engine, "before_cursor_execute", listener)
    assert statements and all(sql.lstrip().upper().startswith(("SELECT", "BEGIN")) for sql in statements)
    assert preview["write_performed"] is False and state(repository) == before
    outcome = preview["outcomes"][0]
    assert outcome["category"] == document.packet.rows[index].category
    assert outcome["attendance_state"] == "NOT_VERIFIED"
    receipt = repository.admin_commit(command, ACTOR, preview["state_hash"])
    assert receipt["write_performed"] and not receipt["replayed"]
    after = state(repository)
    for table in after:
        expected = 1 if table in {
            "claims", "claim_evidence", "identity_review_items",
            "person_observation_links", "admin_operations",
        } else 0
        assert after[table] == before[table] + expected
    assert immutable_rows(repository) == originals
    observation = document.contexts[index][0]
    prepared = repository.onboarding.prepare_gukgam_witness_claim(
        person_id=people[index].id, observation_id=observation.id,
        expected_observation_hash=observation.content_hash,
        expected_packet_hash=document.packet.content_hash,
    )
    claim = next(item for item in repository.claims(person_id=people[index].id)
                 if str(item.id) == outcome["claim_id"])
    # SQLite's DateTime adapter returns UTC timestamps without tzinfo.
    assert claim.valid_from.replace(tzinfo=UTC) == prepared.claim.valid_from
    assert claim.model_dump(exclude={"valid_from"}) == prepared.claim.model_dump(exclude={"valid_from"})
    assert claim.predicate == GUKGAM_WITNESS_LISTING_PREDICATE
    assert claim.publication_status.value == "DRAFT" and claim.epistemic_status.value == "CLAIM"
    assert not claim.asserted_as_true and "organization_id" not in claim.qualifiers
    assert repository.evidence_for(claim.id) == [prepared.evidence]
    with repository(read_only=True) as uow:
        link = uow._session.get(db.PersonObservationLinkRow, str(prepared.identity_link_id))
        review = uow._session.get(db.IdentityReviewItemRow, link.review_item_id)
        assert review.status == "RESOLVED" and review.candidate_person_id == str(people[index].id)
        assert review.details_json["review_evidence_ids"] == [str(scenario[3][index].id)]
        assert review.details_json["reviewed_packet_hash"] == document.packet.content_hash
    with repository.engine.connect() as connection:
        assert connection.execute(text("PRAGMA foreign_key_check")).all() == []
    with TestClient(create_app(repository), base_url="http://127.0.0.1") as client:
        profile = client.get(f"/people/{people[index].id}")
        assert profile.status_code == 200
        assert outcome["claim_id"] not in profile.text
        assert client.get(f"/sources/{prepared.evidence.source_id}").status_code == 404


@pytest.mark.parametrize("change", ["unverified", "missing_evidence", "name_only_basis"])
def test_explicit_human_identity_inputs_are_required(scenario, change):
    repository = scenario[0]
    before = state(repository)
    values = {
        "unverified": {"human_verified": False},
        "missing_evidence": {"evidence_ids": ()},
        "name_only_basis": {"identity_basis": None},
    }[change]
    with pytest.raises(ValidationError):
        request(scenario, **values)
    assert state(repository) == before


def test_witness_registration_cannot_create_a_person(scenario):
    repository = scenario[0]
    before = state(repository)
    command = request(scenario, action="REGISTER_PERSON", target_person_id=None,
                      evidence_ids=(), identity_basis=None)
    with pytest.raises(AdminError) as error:
        repository.admin_preview(command)
    assert error.value.code == "WITNESS_LINK_ONLY"
    assert state(repository) == before


@pytest.mark.parametrize("change", [
    "unresolved", "inactive", "wrong_name", "fetch_denied", "nonofficial", "discovery",
    "witness_evidence",
])
def test_target_and_official_bridge_fail_closed(scenario, change):
    repository, document, people, bridges, policy, _ = scenario
    command = request(scenario)
    with repository() as uow:
        target = uow._session.get(db.PersonRow, str(people[0].id))
        policy_row = uow._session.get(db.SourcePolicyRow, str(policy.id))
        if change == "unresolved":
            target.identity_status = "REVIEW"
        elif change == "inactive":
            target.superseded_at = datetime.now(UTC)
        elif change == "wrong_name":
            target.canonical_name = "명백히 다른 합성인물"
        elif change == "fetch_denied":
            policy_row.can_fetch = False
        elif change == "nonofficial":
            policy_row.source_class = "synthetic_unofficial"
        elif change == "discovery":
            policy_row.collection_mode = "DISCOVERY_ONLY"
        elif change == "witness_evidence":
            # A witness listing is metadata-only, so it cannot be its own identity bridge.
            evidence = uow._session.get(db.ClaimEvidenceRow, str(bridges[0].id))
            evidence.source_id = str(document.contexts[0][2].id)
        uow.commit()
    before = state(repository)
    with pytest.raises(AdminError):
        repository.admin_preview(command)
    assert state(repository) == before


@pytest.mark.parametrize("change", ["person", "alias", "bridge", "source", "snapshot", "run"])
def test_valid_dependency_change_invalidates_preview_without_partial_write(scenario, change):
    repository, document, people, bridges, _, source = scenario
    command = request(scenario)
    preview = repository.admin_preview(command)
    with repository() as uow:
        if change == "person":
            uow._session.get(db.PersonRow, str(people[0].id)).birth_date = date(1970, 1, 1)
        elif change == "alias":
            uow._session.add(db.PersonAliasRow(
                id=str(uuid4()), person_id=str(people[0].id), name="다른 합성 별칭",
                valid_from=datetime.now(UTC), recorded_at=datetime.now(UTC),
            ))
        elif change == "bridge":
            uow._session.get(db.ClaimEvidenceRow, str(bridges[0].id)).stance = "NEUTRAL"
        elif change == "source":
            uow._session.get(db.SourceRow, str(source.id)).title = "Updated synthetic bridge title"
        elif change == "snapshot":
            snapshot = uow._session.get(db.SourceSnapshotRow, str(document.contexts[0][1].id))
            snapshot.metadata_json = {**snapshot.metadata_json, "synthetic_revision": 2}
        elif change == "run":
            checkpoint = uow._session.scalars(select(db.SourceCheckpointRow)).one()
            checkpoint.updated_at = datetime.now(UTC)
        uow.commit()
    before = state(repository)
    with pytest.raises(AdminError) as error:
        repository.admin_commit(command, ACTOR, preview["state_hash"])
    assert error.value.code == "STALE_PREVIEW"
    assert state(repository) == before


@pytest.mark.parametrize("change", ["checkpoint", "policy", "observation", "run"])
def test_invalid_current_provenance_cannot_be_linked(scenario, change):
    repository, document, _, _, _, _ = scenario
    with repository() as uow:
        if change == "checkpoint":
            uow._session.scalars(select(db.SourceCheckpointRow)).one().cursor = "broken"
        elif change == "policy":
            uow._session.get(db.SourcePolicyRow, str(document.contexts[0][3].id)).can_send_to_ai = True
        elif change == "observation":
            row = uow._session.get(db.FeederObservationRow, str(document.contexts[0][0].id))
            row.content_hash = "f" * 64
        elif change == "run":
            uow._session.scalars(select(db.SourceRunRow)).one().status = "FAILED"
        uow.commit()
    before = state(repository)
    with pytest.raises(AdminError) as error:
        repository.admin_preview(request(scenario))
    assert error.value.code == "WITNESS_SOURCE_INVALID"
    assert state(repository) == before


@pytest.mark.parametrize("replacement", ["bytes", "subset"])
def test_replaced_or_excluded_row_cannot_resurrect_old_identity(scenario, replacement):
    repository = scenario[0]
    command = request(scenario)
    preview = repository.admin_preview(command)
    raw = synthetic_packet()
    artifact = ARTIFACT
    if replacement == "bytes":
        artifact += b"replacement"
        raw["attachment_sha256"] = hashlib.sha256(artifact).hexdigest()
    else:
        raw["selection"] = "EXPLICIT_REVIEW_SUBSET"
        raw["rows"] = raw["rows"][1:]
    persist_capture(repository, capture(raw, artifact))
    before = state(repository)
    with pytest.raises(AdminError) as error:
        repository.admin_commit(command, ACTOR, preview["state_hash"])
    assert error.value.code == "WITNESS_NOT_CURRENT"
    assert state(repository) == before


def test_additional_series_version_invalidates_preview_even_if_selection_is_unchanged(scenario):
    repository, document, _, _, _, _ = scenario
    command = request(scenario)
    preview = repository.admin_preview(command)
    with repository() as uow:
        current = uow._session.get(db.FeederObservationRow, str(document.contexts[0][0].id))
        values = {column.key: getattr(current, column.key) for column in db.FeederObservationRow.__table__.columns}
        normalized = {**current.normalized_json, "printed_role": "다른 합성 원문 버전"}
        values.update(id=str(uuid4()), normalized_json=normalized, content_hash=canonical_hash(normalized))
        uow._session.add(db.FeederObservationRow(**values))
        uow.commit()
    before = state(repository)
    with pytest.raises(AdminError) as error:
        repository.admin_commit(command, ACTOR, preview["state_hash"])
    assert error.value.code == "STALE_PREVIEW"
    assert state(repository) == before


def test_link_validation_is_scoped_to_the_selected_attachment(scenario):
    repository = scenario[0]
    with repository() as uow:
        uow._session.add(db.SourceCheckpointRow(
            id=str(uuid4()), feeder="gukgam_reviewed_witness",
            scope_key="2026:unrelated:synthetic", cursor="invalid", last_run_id=None,
            updated_at=datetime.now(UTC), metadata_json={},
        ))
        uow.commit()
    before = state(repository)
    preview = repository.admin_preview(request(scenario))
    assert preview["write_performed"] is False and state(repository) == before


def test_exact_replay_and_duplicate_link_do_not_duplicate_claims(scenario):
    repository = scenario[0]
    command = request(scenario)
    preview = repository.admin_preview(command)
    first = repository.admin_commit(command, ACTOR, preview["state_hash"])
    before = state(repository)
    replay = repository.admin_commit(command, ACTOR, preview["state_hash"])
    assert replay["replayed"] and not replay["write_performed"] and replay["id"] == first["id"]
    with pytest.raises(AdminError) as error:
        repository.admin_preview(request(scenario))
    assert error.value.code == "ALREADY_LINKED"
    with pytest.raises(AdminError) as error:
        repository.admin_commit(command, "different-actor", preview["state_hash"])
    assert error.value.code == "IDEMPOTENCY_CONFLICT"
    assert state(repository) == before


def test_evidence_failure_rolls_back_review_link_claim_and_audit(scenario):
    repository = scenario[0]
    command = request(scenario)
    preview = repository.admin_preview(command)
    before = state(repository)

    def fail_insert(*args):
        raise RuntimeError("synthetic evidence insertion failure")

    event.listen(db.ClaimEvidenceRow, "before_insert", fail_insert)
    try:
        with pytest.raises(RuntimeError, match="synthetic evidence insertion"):
            repository.admin_commit(command, ACTOR, preview["state_hash"])
    finally:
        event.remove(db.ClaimEvidenceRow, "before_insert", fail_insert)
    assert state(repository) == before


@pytest.mark.parametrize("action", ["PUBLISH", "CORRECT_CLAIM"])
def test_new_witness_draft_cannot_enter_generic_release_or_correction_path(scenario, action):
    repository = scenario[0]
    command = request(scenario)
    preview = repository.admin_preview(command)
    result = repository.admin_commit(command, ACTOR, preview["state_hash"])
    claim_id = UUID(result["result"]["outcomes"][0]["claim_id"])
    values = {"value": "Synthetic correction", "evidence_ids": (scenario[3][0].id,)} if (
        action == "CORRECT_CLAIM"
    ) else {}
    release = AdminCommand(
        request_id=uuid4(), action=action, record_ids=(claim_id,),
        reason="Synthetic release boundary probe; no real publication approval.", **values,
    )
    before = state(repository)
    with pytest.raises(AdminError) as error:
        repository.admin_preview(release)
    assert error.value.code == "WITNESS_RELEASE_NOT_ENABLED"
    assert state(repository) == before


def test_witness_private_api_retains_signed_preview_auth_and_explicit_confirmation(scenario):
    repository = scenario[0]
    command = request(scenario)
    body = command.model_dump(mode="json")
    headers = {"x-civic-operator-token": TOKEN}
    before = state(repository)
    app = create_app(repository, enable_review_surface=True, operator_token=TOKEN,
                     operator_writes=True, operator_actor=ACTOR)
    with TestClient(app, base_url="http://127.0.0.1") as client:
        assert client.post("/admin/operations/preview", json=body).status_code == 403
        preview = client.post("/admin/operations/preview", json=body, headers=headers)
        assert preview.status_code == 200
        commit = {"command": body, "preview_token": preview.json()["preview_token"], "confirmed": False}
        assert client.post("/admin/operations/commit", json=commit, headers=headers).status_code == 403
        commit["confirmed"] = True
        commit["preview_token"] += "tampered"
        assert client.post("/admin/operations/commit", json=commit, headers=headers).status_code == 409
        commit["preview_token"] = preview.json()["preview_token"]
        assert client.post("/admin/operations/commit", json=commit,
                           headers={**headers, "origin": "http://attacker"}).status_code == 403
        assert state(repository) == before
        result = client.post("/admin/operations/commit", json=commit, headers=headers)
        assert result.status_code == 200 and result.json()["write_performed"]


def linked_claim(scenario, index=0):
    repository = scenario[0]
    command = request(scenario, index)
    preview = repository.admin_preview(command)
    result = repository.admin_commit(command, ACTOR, preview["state_hash"])
    return UUID(result["result"]["outcomes"][0]["claim_id"])


def review_request(*claim_ids):
    return AdminCommand(
        request_id=uuid4(), action="SUBMIT_REVIEW", record_ids=claim_ids,
        reason="Synthetic review queue request; never a human review or publication approval.",
    )


@pytest.mark.parametrize("index", [0, 1, 2])
def test_witness_review_preflight_is_read_only_and_commit_only_requests_review(scenario, index):
    repository, document, people, _, _, _ = scenario
    claim_id = linked_claim(scenario, index)
    command = review_request(claim_id)
    before = state(repository)
    originals = immutable_rows(repository)
    statements = []
    listener = lambda connection, cursor, statement, *args: statements.append(statement)
    event.listen(repository.engine, "before_cursor_execute", listener)
    try:
        preview = repository.admin_preview(command)
    finally:
        event.remove(repository.engine, "before_cursor_execute", listener)
    assert all(sql.lstrip().upper().startswith(("SELECT", "BEGIN")) for sql in statements)
    assert not preview["write_performed"] and state(repository) == before
    outcome = preview["outcomes"][0]
    assert outcome["witness_preflight"] == "CURRENT_SOURCE_IDENTITY_CLAIM_EVIDENCE_VERIFIED"
    assert outcome["packet_hash"] == document.packet.content_hash
    assert outcome["observation_hash"] == document.contexts[index][0].content_hash
    assert outcome["after"] == "REVIEW" and outcome["publication_enabled"] is False
    assert outcome["attendance_state"] == "NOT_VERIFIED"
    result = repository.admin_commit(command, ACTOR, preview["state_hash"])
    assert result["write_performed"] and result["result"]["human_verified"] is False
    assert result["result"]["review_evidence_ids"] == []
    after = state(repository)
    assert after == {table: count + (table == "admin_operations") for table, count in before.items()}
    assert immutable_rows(repository) == originals
    claim = next(item for item in repository.claims(person_id=people[index].id) if item.id == claim_id)
    assert claim.publication_status.value == "REVIEW"
    assert claim.epistemic_status.value == "CLAIM" and not claim.asserted_as_true
    replay = repository.admin_commit(command, ACTOR, preview["state_hash"])
    assert replay["replayed"] and not replay["write_performed"] and state(repository) == after
    with TestClient(create_app(repository), base_url="http://127.0.0.1") as client:
        assert str(claim_id) not in client.get(f"/people/{people[index].id}").text
    release = AdminCommand(request_id=uuid4(), action="PUBLISH", record_ids=(claim_id,),
                           reason="Synthetic release boundary probe.")
    with pytest.raises(AdminError, match="증인 명단 Claim") as error:
        repository.admin_preview(release)
    assert error.value.code == "WITNESS_RELEASE_NOT_ENABLED"


def test_withheld_witness_can_request_review_without_truth_promotion(scenario):
    repository = scenario[0]
    claim_id = linked_claim(scenario)
    withdraw = AdminCommand(request_id=uuid4(), action="WITHDRAW", record_ids=(claim_id,),
                            reason="Synthetic withholding fixture.")
    preview = repository.admin_preview(withdraw)
    repository.admin_commit(withdraw, ACTOR, preview["state_hash"])
    command = review_request(claim_id)
    preview = repository.admin_preview(command)
    assert preview["outcomes"][0]["before"] == "WITHHELD"
    repository.admin_commit(command, ACTOR, preview["state_hash"])
    with repository(read_only=True) as uow:
        row = uow._session.get(db.ClaimRow, str(claim_id))
        assert (row.publication_status, row.epistemic_status, row.asserted_as_true) == (
            "REVIEW", "CLAIM", False,
        )


@pytest.mark.parametrize("change", [
    "person_unresolved", "person_inactive", "link_inactive", "link_person", "link_action",
    "link_class", "link_review", "second_link", "review_status", "review_person",
    "review_note", "review_time", "review_hash", "review_request", "review_evidence",
    "review_basis", "new_review", "bridge_policy", "bridge_name",
])
def test_review_preflight_rejects_broken_identity_review_audit_and_bridge(scenario, change):
    repository, document, people, _, policy, _ = scenario
    claim_id = linked_claim(scenario)
    with repository() as uow:
        link = uow._session.scalars(select(db.PersonObservationLinkRow)).one()
        review = uow._session.get(db.IdentityReviewItemRow, link.review_item_id)
        person = uow._session.get(db.PersonRow, str(people[0].id))
        if change == "person_unresolved":
            person.identity_status = "REVIEW"
        elif change == "person_inactive":
            person.superseded_at = datetime.now(UTC)
        elif change == "link_inactive":
            link.superseded_at = datetime.now(UTC)
        elif change == "link_person":
            link.person_id = str(people[1].id)
        elif change == "link_action":
            link.action = "AUTO_LINK"
        elif change == "link_class":
            link.decision_class = "DETERMINISTIC_SOURCE_CONTEXT"
        elif change == "link_review":
            link.review_item_id = None
        elif change == "second_link":
            values = {column.key: getattr(link, column.key)
                      for column in db.PersonObservationLinkRow.__table__.columns}
            values.update(id=str(uuid4()), person_id=str(people[1].id))
            uow._session.add(db.PersonObservationLinkRow(**values))
        elif change == "review_status":
            review.status = "OPEN"
        elif change == "review_person":
            review.candidate_person_id = str(people[1].id)
        elif change == "review_note":
            review.resolution_note += " changed"
        elif change == "review_time":
            review.resolved_at += timedelta(seconds=1)
        elif change.startswith("review_"):
            field, value = {
                "review_hash": ("reviewed_packet_hash", "f" * 64),
                "review_request": ("operator_request_id", str(uuid4())),
                "review_evidence": ("review_evidence_ids", []),
                "review_basis": ("identity_basis", "NAME_ONLY"),
            }[change]
            review.details_json = {**review.details_json, field: value}
        elif change == "new_review":
            uow._session.add(db.IdentityReviewItemRow(
                id=str(uuid4()), observation_id=str(document.contexts[0][0].id),
                candidate_person_id=None, reason_code="SYNTHETIC_RECHECK", details_json={},
                status="OPEN", created_at=review.created_at + timedelta(seconds=1),
                resolved_at=None, resolution_note=None,
            ))
        elif change == "bridge_policy":
            uow._session.get(db.SourcePolicyRow, str(policy.id)).can_fetch = False
        elif change == "bridge_name":
            person.canonical_name = "다른 합성 이름"
        uow.commit()
    before = state(repository)
    with pytest.raises(AdminError):
        repository.admin_preview(review_request(claim_id))
    assert state(repository) == before


@pytest.mark.parametrize("change", [
    "proposition", "object", "subject", "predicate", "qualifiers", "fact", "valid_from",
    "evidence_extra", "evidence_missing", "evidence_source", "evidence_snapshot",
    "evidence_observation", "evidence_stance", "evidence_excerpt",
])
def test_review_preflight_rejects_tampered_claim_or_evidence(scenario, change):
    repository, document, _, _, _, source = scenario
    claim_id = linked_claim(scenario)
    with repository() as uow:
        claim = uow._session.get(db.ClaimRow, str(claim_id))
        evidence = uow._session.scalars(select(db.ClaimEvidenceRow).where(
            db.ClaimEvidenceRow.claim_id == str(claim_id),
        )).one()
        if change == "proposition":
            claim.proposition += " actually attended"
        elif change == "object":
            claim.object_text = "Synthetic attendance assertion"
        elif change == "subject":
            claim.subject = "Different synthetic subject"
        elif change == "predicate":
            claim.predicate = "TAMPERED_GENERIC_PREDICATE"
            # Observation provenance still identifies a witness if its marker is removed.
            claim.qualifiers = {key: value for key, value in claim.qualifiers.items()
                                if key != "source_contract"}
        elif change == "qualifiers":
            claim.qualifiers = {**claim.qualifiers, "category": "REFERENCE_PERSON"}
        elif change == "fact":
            claim.epistemic_status, claim.asserted_as_true = "FACT", True
        elif change == "valid_from":
            claim.valid_from += timedelta(days=1)
        elif change == "evidence_extra":
            values = {column.key: getattr(evidence, column.key)
                      for column in db.ClaimEvidenceRow.__table__.columns}
            uow._session.add(db.ClaimEvidenceRow(**{**values, "id": str(uuid4())}))
        elif change == "evidence_missing":
            uow._session.delete(evidence)
        elif change == "evidence_source":
            evidence.source_id = str(source.id)
        elif change == "evidence_snapshot":
            evidence.snapshot_id = None
        elif change == "evidence_observation":
            evidence.feeder_observation_id = str(document.contexts[1][0].id)
        elif change == "evidence_stance":
            evidence.stance = "NEUTRAL"
        elif change == "evidence_excerpt":
            evidence.excerpt = "Synthetic forbidden raw excerpt"
        uow.commit()
    before = state(repository)
    with pytest.raises(AdminError):
        repository.admin_preview(review_request(claim_id))
    if change == "predicate":
        release = AdminCommand(request_id=uuid4(), action="PUBLISH", record_ids=(claim_id,),
                               reason="Synthetic predicate bypass probe.")
        with pytest.raises(AdminError) as error:
            repository.admin_preview(release)
        assert error.value.code == "WITNESS_RELEASE_NOT_ENABLED"
    assert state(repository) == before


@pytest.mark.parametrize("replacement", ["bytes", "subset"])
def test_review_preflight_cannot_reuse_replaced_or_excluded_source_row(scenario, replacement):
    repository = scenario[0]
    claim_id = linked_claim(scenario)
    raw, artifact = synthetic_packet(), ARTIFACT
    if replacement == "bytes":
        artifact += b"replacement"
        raw["attachment_sha256"] = hashlib.sha256(artifact).hexdigest()
    else:
        raw["selection"], raw["rows"] = "EXPLICIT_REVIEW_SUBSET", raw["rows"][1:]
    persist_capture(repository, capture(raw, artifact))
    before = state(repository)
    with pytest.raises(AdminError) as error:
        repository.admin_preview(review_request(claim_id))
    assert error.value.code == "WITNESS_NOT_CURRENT" and state(repository) == before


@pytest.mark.parametrize("change", ["alias", "bridge", "source", "snapshot", "checkpoint", "review"])
def test_review_request_binds_current_dependencies_to_preview(scenario, change):
    repository, document, people, bridges, _, source = scenario
    claim_id = linked_claim(scenario)
    command = review_request(claim_id)
    preview = repository.admin_preview(command)
    with repository() as uow:
        if change == "alias":
            uow._session.add(db.PersonAliasRow(
                id=str(uuid4()), person_id=str(people[0].id), name="다른 합성 별칭",
                valid_from=datetime.now(UTC), recorded_at=datetime.now(UTC),
            ))
        elif change == "bridge":
            uow._session.get(db.ClaimEvidenceRow, str(bridges[0].id)).stance = "NEUTRAL"
        elif change == "source":
            uow._session.get(db.SourceRow, str(source.id)).title += " changed"
        elif change == "snapshot":
            row = uow._session.get(db.SourceSnapshotRow, str(document.contexts[0][1].id))
            row.metadata_json = {**row.metadata_json, "synthetic_revision": 2}
        elif change == "checkpoint":
            uow._session.scalars(select(db.SourceCheckpointRow)).one().updated_at = datetime.now(UTC)
        elif change == "review":
            row = uow._session.scalars(select(db.IdentityReviewItemRow)).one()
            row.details_json = {**row.details_json, "synthetic_recheck": True}
        uow.commit()
    before = state(repository)
    with pytest.raises(AdminError) as error:
        repository.admin_commit(command, ACTOR, preview["state_hash"])
    assert error.value.code == "STALE_PREVIEW" and state(repository) == before


def test_review_batch_is_atomic_when_one_claim_is_invalid(scenario):
    repository = scenario[0]
    first, second = linked_claim(scenario, 0), linked_claim(scenario, 1)
    command = review_request(first, second)
    preview = repository.admin_preview(command)
    with repository() as uow:
        uow._session.get(db.ClaimRow, str(second)).proposition += " corrupted"
        uow.commit()
    before = state(repository)
    with pytest.raises(AdminError):
        repository.admin_commit(command, ACTOR, preview["state_hash"])
    assert state(repository) == before
    with repository(read_only=True) as uow:
        assert all(uow._session.get(db.ClaimRow, str(item)).publication_status == "DRAFT"
                   for item in (first, second))


def test_review_audit_failure_rolls_back_claim_transition(scenario):
    repository = scenario[0]
    command = review_request(linked_claim(scenario))
    preview = repository.admin_preview(command)
    before = state(repository)

    def fail_insert(*args):
        raise RuntimeError("synthetic review audit insertion failure")

    event.listen(db.AdminOperationRow, "before_insert", fail_insert)
    try:
        with pytest.raises(RuntimeError, match="synthetic review audit insertion"):
            repository.admin_commit(command, ACTOR, preview["state_hash"])
    finally:
        event.remove(db.AdminOperationRow, "before_insert", fail_insert)
    assert state(repository) == before
    with repository(read_only=True) as uow:
        assert uow._session.get(db.ClaimRow, str(command.record_ids[0])).publication_status == "DRAFT"


def test_review_request_private_api_preserves_auth_signature_and_confirmation(scenario):
    repository = scenario[0]
    command = review_request(linked_claim(scenario))
    body, headers = command.model_dump(mode="json"), {"x-civic-operator-token": TOKEN}
    before = state(repository)
    app = create_app(repository, enable_review_surface=True, operator_token=TOKEN,
                     operator_writes=True, operator_actor=ACTOR)
    with TestClient(app, base_url="http://127.0.0.1") as client:
        assert client.post("/admin/operations/preview", json=body).status_code == 403
        preview = client.post("/admin/operations/preview", json=body, headers=headers)
        assert preview.status_code == 200
        commit = {"command": body, "preview_token": preview.json()["preview_token"], "confirmed": False}
        assert client.post("/admin/operations/commit", json=commit, headers=headers).status_code == 403
        commit["confirmed"] = True
        commit["preview_token"] += "tampered"
        assert client.post("/admin/operations/commit", json=commit, headers=headers).status_code == 409
        commit["preview_token"] = preview.json()["preview_token"]
        assert client.post("/admin/operations/commit", json=commit,
                           headers={**headers, "origin": "http://attacker"}).status_code == 403
        assert state(repository) == before
        result = client.post("/admin/operations/commit", json=commit, headers=headers)
        assert result.status_code == 200 and result.json()["result"]["human_verified"] is False


@pytest.mark.parametrize("action", ["SUBMIT_REVIEW", "PUBLISH", "CORRECT_CLAIM"])
@pytest.mark.parametrize("keep_snapshot", [True, False])
def test_immutable_source_capture_prevents_compound_witness_marker_bypass(scenario, action, keep_snapshot):
    repository = scenario[0]
    claim_id = linked_claim(scenario)
    with repository() as uow:
        claim = uow._session.get(db.ClaimRow, str(claim_id))
        claim.predicate, claim.qualifiers = "TAMPERED_GENERIC_PREDICATE", {}
        evidence = uow._session.scalars(select(db.ClaimEvidenceRow).where(
            db.ClaimEvidenceRow.claim_id == str(claim_id),
        )).one()
        evidence.feeder_observation_id = None
        if not keep_snapshot:
            evidence.snapshot_id = None
        uow.commit()
    values = {"value": "Synthetic correction", "evidence_ids": (scenario[3][0].id,)} if (
        action == "CORRECT_CLAIM"
    ) else {}
    command = AdminCommand(request_id=uuid4(), action=action, record_ids=(claim_id,),
                           reason="Synthetic compound provenance corruption probe.", **values)
    before = state(repository)
    with pytest.raises(AdminError) as error:
        repository.admin_preview(command)
    expected = "WITNESS_EVIDENCE_CONFLICT" if action == "SUBMIT_REVIEW" else "WITNESS_RELEASE_NOT_ENABLED"
    assert error.value.code == expected and state(repository) == before


def test_review_cannot_borrow_another_rows_immutable_link_audit(scenario):
    repository, document, _, _, _, _ = scenario
    claim_id = linked_claim(scenario, 0)
    other = request(scenario, 1)
    preview = repository.admin_preview(other)
    repository.admin_commit(other, ACTOR, preview["state_hash"])
    with repository() as uow:
        review = uow._session.scalars(select(db.IdentityReviewItemRow).where(
            db.IdentityReviewItemRow.observation_id == str(document.contexts[0][0].id),
        )).one()
        review.details_json = {**review.details_json, "operator_request_id": str(other.request_id)}
        uow.commit()
    before = state(repository)
    with pytest.raises(AdminError) as error:
        repository.admin_preview(review_request(claim_id))
    assert error.value.code == "WITNESS_AUDIT_CONFLICT" and state(repository) == before
