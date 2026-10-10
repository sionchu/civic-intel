"""Disposable canonical DB coverage; no real source acquisition or production writes."""
import json
from datetime import UTC, datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy import func, select

from packages.domain import db
from packages.domain.admin import AdminCommand
from packages.domain.enums import SourceCollectionMode
from packages.persistence.admin_workflow import AdminError
from packages.verification.assembly_base_profile import AssemblyBaseProfilePublisher
from tests.test_assembly_asset_disclosure import migrated_repository
from tests.test_assembly_base_profile import SinglePageRoster, member_row
from tests.test_peti_asset_projection import policy, receipt
from workers.assembly_asset_import import main
from workers.assembly_roster import AssemblyRosterEnumerator


def inputs(tmp_path):
    receipt_path, policy_path = tmp_path / "receipt.json", tmp_path / "policy.json"
    receipt_path.write_text(json.dumps(receipt(), ensure_ascii=False), encoding="utf-8")
    policy_path.write_text(policy().model_dump_json(), encoding="utf-8")
    return ["--peti-receipt", str(receipt_path), "--peti-policy", str(policy_path)]


def setup(tmp_path, monkeypatch, capsys):
    repository, url = migrated_repository(tmp_path / "peti.db")
    args = inputs(tmp_path)
    governing = policy_from(args)
    with repository.sessions() as session:
        values = governing.model_dump(mode="python")
        values["id"] = str(governing.id)
        session.add(db.SourcePolicyRow(**values))
        session.commit()
    monkeypatch.setenv("CIVIC_DATABASE_URL", url)
    assert main(args + ["--commit"]) == 0
    captured = json.loads(capsys.readouterr().out)
    roster = SinglePageRoster(member_row("SYNTHETIC-M-001", "합성의원갑"))
    enumeration = AssemblyRosterEnumerator(roster.connector(), repository).enumerate_and_materialize()
    AssemblyBaseProfilePublisher(repository).publish_latest_successful()
    person = enumeration.materializations[0].person_id
    claim = next(item for item in repository.claims(person, published_only=True)
        if item.predicate == "ASSEMBLY_PARTY")
    evidence = repository.evidence_for(claim.id)[0]
    command = AdminCommand(request_id=uuid4(), action="LINK_PERSON",
        record_ids=(UUID(captured["observation_ids"][0]),), target_person_id=person,
        reason="SYNTHETIC owner reviewed the exact disclosure and current roster context",
        evidence_ids=(evidence.id,), identity_basis="PUBLIC_DISCLOSURE_SOURCE_CONTEXT",
        human_verified=True)
    return repository, args, command


def policy_from(args):
    from pathlib import Path

    from packages.domain.contracts import SourcePolicy
    return SourcePolicy.model_validate_json(Path(args[3]).read_text(encoding="utf-8"))


def test_default_preview_no_db_no_review_no_publication(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("CIVIC_DATABASE_URL", raising=False)
    assert main(inputs(tmp_path)) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "DRY_RUN" and report["record_count"] == 1
    assert report["identity_review_confirmed"] is False
    assert report["write_performed"] is False and report["claim_publication"] is False


def test_stored_policy_mismatch_precedes_any_run(tmp_path, monkeypatch):
    repository, url = migrated_repository(tmp_path / "peti.db")
    monkeypatch.setenv("CIVIC_DATABASE_URL", url)
    with pytest.raises(SystemExit):
        main(inputs(tmp_path) + ["--commit"])
    with repository.sessions() as session:
        assert session.scalar(select(func.count()).select_from(db.SourceRunRow)) == 0
        assert session.scalar(select(func.count()).select_from(db.SourcePolicyRow)) == 0


def test_review_link_draft_then_separate_publish(tmp_path, monkeypatch, capsys):
    repository, args, command = setup(tmp_path, monkeypatch, capsys)
    preview = repository.admin_preview(command)
    assert preview["write_performed"] is False
    with repository.sessions() as session:
        assert session.scalar(select(func.count()).select_from(db.IdentityReviewItemRow)) == 0
    repository.admin_commit(command, actor="SYNTHETIC_OWNER", state_hash=preview["state_hash"])
    claims = [item for item in repository.claims(command.target_person_id)
        if item.predicate == "ASSEMBLY_DECLARED_ASSET_TOTAL"]
    assert len(claims) == 1 and claims[0].publication_status.value == "DRAFT"
    assert {item.stance.value for item in repository.evidence_for(claims[0].id)} == {"SUPPORT", "NEUTRAL"}
    publish = AdminCommand(request_id=uuid4(), action="PUBLISH", record_ids=(claims[0].id,),
        reason="SYNTHETIC separate publication review of metadata and evidence closure")
    preview = repository.admin_preview(publish)
    repository.admin_commit(publish, actor="SYNTHETIC_OWNER", state_hash=preview["state_hash"])
    assert any(item.id == claims[0].id for item in repository.claims(command.target_person_id, published_only=True))
    # Unchanged source capture remains idempotent; it does not add identity or Claim writes.
    assert main(args + ["--commit"]) == 0
    assert json.loads(capsys.readouterr().out)["observations_unchanged"] == 1


@pytest.mark.parametrize("change", [
    {"human_verified": False}, {"action": "MERGE_PERSON"},
])
def test_public_context_cannot_fake_review_or_merge(change):
    raw = {"request_id": uuid4(), "action": "LINK_PERSON", "record_ids": (uuid4(),),
        "target_person_id": uuid4(), "evidence_ids": (uuid4(),),
        "reason": "SYNTHETIC reviewed source context", "human_verified": True,
        "identity_basis": "PUBLIC_DISCLOSURE_SOURCE_CONTEXT"}
    with pytest.raises(ValidationError):
        AdminCommand.model_validate(raw | change)


@pytest.mark.parametrize("mutation", ["identity", "checkpoint", "claim_hash", "policy", "second_person"])
def test_exact_current_official_anchor_required(tmp_path, monkeypatch, capsys, mutation):
    repository, _, command = setup(tmp_path, monkeypatch, capsys)
    with repository.sessions() as session:
        evidence = session.get(db.ClaimEvidenceRow, str(command.evidence_ids[0]))
        observation = session.get(db.FeederObservationRow, evidence.feeder_observation_id)
        if mutation == "identity":
            session.get(db.PersonRow, str(command.target_person_id)).identity_status = "REVIEW"
        elif mutation == "checkpoint":
            checkpoint = session.scalar(select(db.SourceCheckpointRow).where(db.SourceCheckpointRow.feeder == observation.feeder))
            checkpoint.cursor = "0"
        elif mutation == "claim_hash":
            claim = session.get(db.ClaimRow, evidence.claim_id)
            claim.qualifiers = dict(claim.qualifiers, immutable_observation_hash="0" * 64)
        elif mutation == "policy":
            source = session.get(db.SourceRow, evidence.source_id)
            session.get(db.SourcePolicyRow, source.policy_id).can_store_metadata = False
        else:
            person = db.PersonRow(id=str(uuid4()), canonical_name="합성다른인물", identity_status="RESOLVED",
                valid_from=datetime.now(UTC), recorded_at=datetime.now(UTC))
            session.add(person)
            session.flush()
            session.add(db.PersonObservationLinkRow(id=str(uuid4()), person_id=person.id,
                observation_id=observation.id, action="AUTO_LINK", decision_class="AUTHORITATIVE_PROVIDER_IDENTIFIER",
                linked_at=datetime.now(UTC)))
        session.commit()
    with pytest.raises((AdminError, PermissionError)):
        repository.admin_preview(command)


def test_unpublished_corrected_version_blocks_link_and_publication(tmp_path, monkeypatch, capsys):
    repository, args, command = setup(tmp_path, monkeypatch, capsys)
    preview = repository.admin_preview(command)
    repository.admin_commit(command, actor="SYNTHETIC_OWNER", state_hash=preview["state_hash"])
    from pathlib import Path
    raw = receipt() | {"increase": 105311, "current_value": 1324195}
    Path(args[1]).write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
    main(args + ["--commit"])
    capsys.readouterr()
    claim = next(item for item in repository.claims(command.target_person_id) if item.predicate == "ASSEMBLY_DECLARED_ASSET_TOTAL")
    publish = AdminCommand(request_id=uuid4(), action="PUBLISH", record_ids=(claim.id,),
        reason="SYNTHETIC publication with conflicting unpublished correction")
    with pytest.raises(AdminError, match="서로 다른 버전"):
        repository.admin_preview(publish)


def test_owner_pending_preview_does_not_construct_confirmed_command(tmp_path, monkeypatch, capsys):
    repository, args, command = setup(tmp_path, monkeypatch, capsys)
    path = tmp_path / "owner-review.json"
    raw = command.model_dump(mode="json") | {"human_verified": False}
    path.write_text(json.dumps(raw), encoding="utf-8")
    assert main(args + ["--peti-operation", "link", "--command", str(path)]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "OWNER_SOURCE_CONTEXT_REVIEW_PENDING"
    assert report["identity_review_confirmed"] is False and report["write_performed"] is False
    with repository.sessions() as session:
        assert session.scalar(select(func.count()).select_from(db.IdentityReviewItemRow)) == 0


def test_cli_review_preview_commit_then_publication_is_content_free(tmp_path, monkeypatch, capsys):
    repository, args, command = setup(tmp_path, monkeypatch, capsys)
    path = tmp_path / "command.json"
    path.write_text(command.model_dump_json(), encoding="utf-8")
    owner_preview = tmp_path / "owner-preview.json"
    assert main(args + ["--peti-operation", "link", "--command", str(path),
        "--preview-output", str(owner_preview)]) == 0
    output = capsys.readouterr().out
    report = json.loads(output)
    assert "합성의원갑" not in output and "current_value" not in output
    assert owner_preview.exists() and report["write_performed"] is False
    assert main(args + ["--peti-operation", "link", "--command", str(path),
        "--commit", "--actor", "SYNTHETIC_OWNER", "--state-hash", report["state_hash"]]) == 0
    assert "합성의원갑" not in capsys.readouterr().out
    claim = next(item for item in repository.claims(command.target_person_id) if item.predicate == "ASSEMBLY_DECLARED_ASSET_TOTAL")
    publication = AdminCommand(request_id=uuid4(), action="PUBLISH", record_ids=(claim.id,),
        reason="SYNTHETIC explicit separate publication decision")
    path.write_text(publication.model_dump_json(), encoding="utf-8")
    assert main(args + ["--peti-operation", "publish", "--command", str(path)]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "ADMIN_PREVIEW" and report["write_performed"] is False
    assert report["claim_publication"] is False
    assert main(args + ["--peti-operation", "publish", "--command", str(path),
        "--commit", "--actor", "SYNTHETIC_OWNER", "--state-hash", report["state_hash"]]) == 0
    committed = json.loads(capsys.readouterr().out)
    assert committed["write_performed"] is True and committed["claim_publication"] is True


def test_stale_roster_preview_cannot_commit_identity(tmp_path, monkeypatch, capsys):
    repository, _, command = setup(tmp_path, monkeypatch, capsys)
    preview = repository.admin_preview(command)
    with repository.sessions() as session:
        checkpoint = session.scalar(select(db.SourceCheckpointRow).where(db.SourceCheckpointRow.feeder == "national_assembly_members"))
        checkpoint.cursor = "0"
        session.commit()
    with pytest.raises(AdminError):
        repository.admin_commit(command, actor="SYNTHETIC_OWNER", state_hash=preview["state_hash"])
    with repository.sessions() as session:
        assert session.scalar(select(func.count()).select_from(db.IdentityReviewItemRow)) == 0


@pytest.mark.parametrize("mutation", ["review", "subject", "lineage", "predicate", "active_link"])
def test_publication_revalidates_identity_and_claim_lineage(tmp_path, monkeypatch, capsys, mutation):
    repository, _, command = setup(tmp_path, monkeypatch, capsys)
    preview = repository.admin_preview(command)
    repository.admin_commit(command, actor="SYNTHETIC_OWNER", state_hash=preview["state_hash"])
    claim = next(item for item in repository.claims(command.target_person_id) if item.predicate == "ASSEMBLY_DECLARED_ASSET_TOTAL")
    with repository.sessions() as session:
        row = session.get(db.ClaimRow, str(claim.id))
        if mutation == "subject":
            row.subject = "합성오인인물"
        elif mutation == "predicate":
            row.predicate = "SYNTHETIC_WRONG_PREDICATE"
        elif mutation == "lineage":
            row.qualifiers = dict(row.qualifiers, source_contract="SYNTHETIC_WRONG_CONTRACT")
        else:
            link = session.scalar(select(db.PersonObservationLinkRow).where(
                db.PersonObservationLinkRow.observation_id == str(command.record_ids[0])))
            if mutation == "review":
                session.get(db.IdentityReviewItemRow, link.review_item_id).status = "OPEN"
            else:
                link.superseded_at = datetime.now(UTC)
        session.commit()
    publish = AdminCommand(request_id=uuid4(), action="PUBLISH", record_ids=(claim.id,),
        reason="SYNTHETIC publication integrity negative regression")
    with pytest.raises(AdminError):
        repository.admin_preview(publish)


def test_policy_revoked_after_precheck_rolls_back_capture(tmp_path, monkeypatch):
    repository, url = migrated_repository(tmp_path / "policy-race.db")
    args = inputs(tmp_path)
    governing = policy_from(args)
    with repository.sessions() as session:
        values = governing.model_dump(mode="python") | {"id": str(governing.id)}
        session.add(db.SourcePolicyRow(**values))
        session.commit()
    monkeypatch.setenv("CIVIC_DATABASE_URL", url)
    from packages.persistence import SqlAlchemyRepository
    original = SqlAlchemyRepository.start_source_run

    def revoke_after_precheck(self, *args, **kwargs):
        run = original(self, *args, **kwargs)
        with self.sessions() as session:
            session.get(db.SourcePolicyRow, str(governing.id)).can_store_metadata = False
            session.commit()
        return run

    monkeypatch.setattr(SqlAlchemyRepository, "start_source_run", revoke_after_precheck)
    with pytest.raises(SystemExit):
        main(args + ["--commit"])
    with repository.sessions() as session:
        for model in (db.SourceRow, db.SourceSnapshotRow, db.FeederObservationRow, db.SourceCheckpointRow):
            assert session.scalar(select(func.count()).select_from(model)) == 0
        assert session.scalar(select(db.SourceRunRow)).status == "FAILED"
        assert session.get(db.SourcePolicyRow, str(governing.id)).can_store_metadata is False


def test_policy_audit_times_compare_instants_without_assigning_unknown_timezone():
    from packages.persistence.repository import source_policy_semantics_equal
    utc = datetime(2099, 1, 1, tzinfo=UTC)
    kst = utc.astimezone(timezone(timedelta(hours=9)))
    first = policy().model_copy(update={"robots_checked_at": utc, "terms_checked_at": utc})
    assert source_policy_semantics_equal(first, first.model_copy(update={"robots_checked_at": kst}))
    # Unknown naive timestamps retain wall-clock semantics; they are not assumed KST/UTC.
    assert not source_policy_semantics_equal(first,
        first.model_copy(update={"robots_checked_at": kst.replace(tzinfo=None)}))
    assert not source_policy_semantics_equal(first, first.model_copy(update={"can_send_to_ai": True}))


def registration_policy(**updates):
    return policy().model_copy(update={
        "id": UUID("12ee6a2d-b36f-4bea-9a6e-79d0a2f65f75"),
        "source_class": "official_public_declared_asset_metadata",
        "policy_note": "SYNTHETIC explicit reviewed PETI public-total receipt metadata-only decision",
    } | updates)


def registration_command(candidate=None, **updates):
    candidate = candidate or registration_policy()
    return AdminCommand(request_id=uuid4(), action="REGISTER_SOURCE_POLICY",
        record_ids=(candidate.id,), reason="SYNTHETIC exact scoped source-policy registration review",
        value=candidate.model_dump_json(), **updates)


def store_policy(repository, candidate):
    with repository.sessions() as session:
        values = candidate.model_dump(mode="python") | {
            "id": str(candidate.id), "collection_mode": candidate.collection_mode.value}
        session.add(db.SourcePolicyRow(**values))
        session.commit()


def assert_no_capture_or_identity(repository):
    with repository.sessions() as session:
        for model in (db.SourceRunRow, db.SourceRow, db.SourceSnapshotRow, db.FeederObservationRow,
            db.SourceCheckpointRow, db.PersonRow, db.PersonObservationLinkRow, db.ClaimRow):
            assert session.scalar(select(func.count()).select_from(model)) == 0


def test_policy_registration_preview_atomic_commit_and_exact_noop(tmp_path):
    repository, _ = migrated_repository(tmp_path / "registration.db")
    command = registration_command()
    preview = repository.admin_preview(command)
    assert preview["write_performed"] is False
    assert preview["changes"][0]["after"]["can_send_to_ai"] is False
    assert repository.policies() == {}
    committed = repository.admin_commit(command, actor="SYNTHETIC_OWNER", state_hash=preview["state_hash"])
    assert committed["write_performed"] is True
    assert repository.policies()[command.record_ids[0]].can_send_to_ai is False
    assert_no_capture_or_identity(repository)
    no_op = registration_command()
    preview = repository.admin_preview(no_op)
    assert preview["outcomes"][0]["disposition"] == "ALREADY_REGISTERED_EXACT_MATCH"
    result = repository.admin_commit(no_op, actor="SYNTHETIC_OWNER", state_hash=preview["state_hash"])
    assert result["write_performed"] is False and result["changed_rows"] == 0
    with repository.sessions() as session:
        assert session.scalar(select(func.count()).select_from(db.AdminOperationRow)) == 1


@pytest.mark.parametrize("update", [
    {"can_fetch": True}, {"can_store_fulltext": True}, {"can_show_excerpt": True},
    {"can_commercialize": True}, {"license": "CC-BY-4.0"},
    {"source_class": "generic_public_source"}, {"domain": "other.example"},
    {"id": uuid4()}, {"collection_mode": SourceCollectionMode.API}, {"can_store_metadata": False},
    {"policy_note": None}, {"policy_note": "short"},
])
def test_registration_never_widens_reviewed_peti_permission_scope(tmp_path, update):
    repository, _ = migrated_repository(tmp_path / "closed-policy.db")
    with pytest.raises((AdminError, PermissionError)):
        repository.admin_preview(registration_command(registration_policy(**update)))
    assert repository.policies() == {}
    assert_no_capture_or_identity(repository)


def test_reviewed_scoped_ai_choice_is_explicit_and_false_not_defaulted(tmp_path):
    repository, _ = migrated_repository(tmp_path / "ai-choice.db")
    candidate = registration_policy(can_send_to_ai=True)
    command = registration_command(candidate)
    preview = repository.admin_preview(command)
    assert preview["changes"][0]["after"]["can_send_to_ai"] is True
    assert repository.policies() == {}
    raw = json.loads(command.value)
    del raw["can_send_to_ai"]
    with pytest.raises(ValidationError):
        AdminCommand.model_validate(command.model_dump(mode="json") | {"value": json.dumps(raw)})


@pytest.mark.parametrize("change", [
    {"record_ids": (uuid4(),)}, {"record_ids": (uuid4(), uuid4())},
    {"target_person_id": uuid4()}, {"evidence_ids": (uuid4(),)},
    {"human_verified": True}, {"value": "{}"},
])
def test_registration_command_is_one_typed_policy_without_identity_attestation(change):
    command = registration_command()
    with pytest.raises(ValidationError):
        AdminCommand.model_validate(command.model_dump(mode="python") | change)


def test_changed_candidate_cannot_use_prior_absence_state_hash(tmp_path):
    repository, _ = migrated_repository(tmp_path / "candidate-state.db")
    command = registration_command()
    preview = repository.admin_preview(command)
    changed = registration_command(registration_policy(can_send_to_ai=True))
    with pytest.raises(AdminError, match="다시 검토"):
        repository.admin_commit(changed, actor="SYNTHETIC_OWNER", state_hash=preview["state_hash"])
    assert repository.policies() == {}


def test_exact_noop_rechecks_locked_state_after_policy_revocation(tmp_path):
    repository, _ = migrated_repository(tmp_path / "noop-state.db")
    candidate = registration_policy()
    store_policy(repository, candidate)
    command = registration_command(candidate)
    preview = repository.admin_preview(command)
    with repository.sessions() as session:
        session.get(db.SourcePolicyRow, str(candidate.id)).can_store_metadata = False
        session.commit()
    with pytest.raises(AdminError):
        repository.admin_commit(command, actor="SYNTHETIC_OWNER", state_hash=preview["state_hash"])
    assert repository.policies()[candidate.id].can_store_metadata is False


def test_competing_registration_after_preview_stays_intact_and_fails_closed(tmp_path):
    repository, _ = migrated_repository(tmp_path / "competing-policy.db")
    command = registration_command()
    preview = repository.admin_preview(command)
    store_policy(repository, registration_policy())
    with pytest.raises(AdminError, match="다시 검토"):
        repository.admin_commit(command, actor="SYNTHETIC_OWNER", state_hash=preview["state_hash"])
    with repository.sessions() as session:
        assert session.scalar(select(func.count()).select_from(db.SourcePolicyRow)) == 1
        assert session.scalar(select(func.count()).select_from(db.AdminOperationRow)) == 0


def test_existing_domain_or_id_mismatch_never_overwrites_policy(tmp_path):
    repository, _ = migrated_repository(tmp_path / "different-policy.db")
    existing = registration_policy(id=uuid4(), can_store_metadata=False)
    store_policy(repository, existing)
    with pytest.raises(AdminError):
        repository.admin_preview(registration_command())
    assert repository.policies()[existing.id].can_store_metadata is False


def test_unique_conflict_rolls_back_registration_and_audit(tmp_path, monkeypatch):
    from sqlalchemy.exc import IntegrityError

    from packages.persistence.admin_workflow import Plan
    repository, _ = migrated_repository(tmp_path / "unique-conflict.db")
    command = registration_command()
    preview = repository.admin_preview(command)
    original = Plan.apply

    def inject_duplicate(self):
        candidate = registration_policy()
        values = candidate.model_dump(mode="python") | {
            "id": str(candidate.id), "collection_mode": candidate.collection_mode.value}
        self.session.add(db.SourcePolicyRow(**values))
        self.session.flush()
        original(self)

    monkeypatch.setattr(Plan, "apply", inject_duplicate)
    with pytest.raises(IntegrityError):
        repository.admin_commit(command, actor="SYNTHETIC_OWNER", state_hash=preview["state_hash"])
    assert repository.policies() == {}
    with repository.sessions() as session:
        assert session.scalar(select(func.count()).select_from(db.AdminOperationRow)) == 0


def test_registration_cli_only_preview_until_explicit_commit(tmp_path, monkeypatch, capsys):
    from pathlib import Path
    repository, url = migrated_repository(tmp_path / "cli-policy.db")
    args = inputs(tmp_path)
    Path(args[3]).write_text(registration_policy().model_dump_json(), encoding="utf-8")
    path = tmp_path / "registration-command.json"
    path.write_text(registration_command().model_dump_json(), encoding="utf-8")
    monkeypatch.setenv("CIVIC_DATABASE_URL", url)
    invocation = args + ["--peti-operation", "policy", "--command", str(path)]
    assert main(invocation) == 0
    output = capsys.readouterr().out
    preview = json.loads(output)
    assert preview["status"] == "POLICY_REGISTRATION_PREVIEW"
    assert preview["write_performed"] is False and preview["policy_registration"] is False
    assert "policy_note" not in output and "printed_name" not in output
    assert repository.policies() == {}
    assert main(invocation + ["--commit", "--actor", "SYNTHETIC_OWNER", "--state-hash", preview["state_hash"]]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["write_performed"] is True and result["policy_registration"] is True
    assert result["claim_publication"] is False and result["identity_review_confirmed"] is False
    assert_no_capture_or_identity(repository)


def test_registration_cli_rejects_receipt_route_outside_peti_allowlist(tmp_path, monkeypatch):
    from pathlib import Path
    repository, url = migrated_repository(tmp_path / "closed-route.db")
    args = inputs(tmp_path)
    Path(args[1]).write_text(json.dumps(receipt() | {"detail_route": "https://other.example/private"}), encoding="utf-8")
    Path(args[3]).write_text(registration_policy().model_dump_json(), encoding="utf-8")
    path = tmp_path / "registration-command.json"
    path.write_text(registration_command().model_dump_json(), encoding="utf-8")
    monkeypatch.setenv("CIVIC_DATABASE_URL", url)
    with pytest.raises(SystemExit):
        main(args + ["--peti-operation", "policy", "--command", str(path)])
    assert repository.policies() == {}
    assert_no_capture_or_identity(repository)
