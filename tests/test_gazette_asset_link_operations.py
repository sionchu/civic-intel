"""Reviewed Gazette member-total identity link; disposable SYNTHETIC canonical DB only."""
import csv
import json
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import func, select

from apps.api.main import create_app
from packages.domain import db
from packages.domain.admin import AdminCommand
from packages.persistence.admin_workflow import AdminError
from packages.verification.assembly_asset_import import (
    ASSEMBLY_ASSET_FEEDER,
    RECORD_KIND_ITEM,
    RECORD_KIND_MEMBER_TOTAL,
    gazette_asset_policy,
)
from packages.verification.assembly_base_profile import AssemblyBaseProfilePublisher
from tests.test_assembly_asset_disclosure import SCOPE, cli, migrated_repository, write_inputs
from tests.test_assembly_base_profile import SinglePageRoster, member_row
from tests.test_peti_asset_operations import store_policy
from workers.assembly_asset_gazette_link import main as link_main
from workers.assembly_asset_import import main as gazette_main
from workers.assembly_roster import AssemblyRosterEnumerator

REASON = "SYNTHETIC owner reviewed the exact Gazette total and current roster context"
FIRST, SECOND = "합성의원갑", "합성의원을"


def setup(tmp_path, capsys, *, roster_name=FIRST, roster_code="SYNTH001", licensed=True):
    repository, url = migrated_repository(tmp_path / "gazette-link.db")
    policy = gazette_asset_policy()
    if licensed:
        policy = policy.model_copy(update={
            "license": "SYNTHETIC_TEST_ONLY", "terms_checked_at": datetime.now(UTC)})
    store_policy(repository, policy)
    packet, artifact = write_inputs(tmp_path)
    assert gazette_main(cli(packet, artifact, "--commit", "--database-url", url)) == 0
    capsys.readouterr()
    roster = SinglePageRoster(member_row(roster_code, roster_name))
    enumeration = AssemblyRosterEnumerator(roster.connector(), repository).enumerate_and_materialize()
    AssemblyBaseProfilePublisher(repository).publish_latest_successful()
    person = enumeration.materializations[0].person_id
    claim = next(item for item in repository.claims(person, published_only=True)
        if item.predicate == "ASSEMBLY_PARTY")
    evidence = repository.evidence_for(claim.id)[0]
    observations = repository.feeder_observations(ASSEMBLY_ASSET_FEEDER, SCOPE)
    return repository, url, person, evidence.id, observations


def total_for(observations, name):
    return next(item for item in observations
        if item.normalized["record_kind"] == RECORD_KIND_MEMBER_TOTAL
        and item.normalized["printed_member_name"] == name)


def link_command(observation_id, person, evidence_id, **updates):
    raw = {"request_id": uuid4(), "action": "LINK_PERSON", "record_ids": (observation_id,),
        "target_person_id": person, "evidence_ids": (evidence_id,), "reason": REASON,
        "identity_basis": "PUBLIC_DISCLOSURE_SOURCE_CONTEXT", "human_verified": True}
    return AdminCommand.model_validate(raw | updates)


def counts(repository):
    with repository.sessions() as session:
        return {model.__tablename__: session.scalar(select(func.count()).select_from(model))
            for model in (db.IdentityReviewItemRow, db.PersonObservationLinkRow, db.ClaimRow,
                db.ClaimEvidenceRow, db.AdminOperationRow, db.AssetDisclosureRow, db.AssetItemRow)}


def asset_claims(repository, person):
    return [item for item in repository.claims(person) if item.predicate == "ASSEMBLY_DECLARED_ASSET_TOTAL"]


def commit(repository, command):
    preview = repository.admin_preview(command)
    assert preview["write_performed"] is False
    return repository.admin_commit(command, actor="SYNTHETIC_OWNER", state_hash=preview["state_hash"])


def publish_command(claim_id):
    return AdminCommand(request_id=uuid4(), action="PUBLISH", record_ids=(claim_id,),
        reason="SYNTHETIC separate publication review of Gazette total closure")


@pytest.mark.parametrize(("name", "code", "amount"), [
    (FIRST, "SYNTH001", "195,000천원"),   # reviewer-stated code equals the roster code
    (SECOND, "SYNTH002", "311,500천원"),  # no reviewer-stated code; roster code is authority
])
def test_reviewed_link_creates_draft_claim_then_separate_publish(tmp_path, capsys, name, code, amount):
    repository, _, person, evidence_id, observations = setup(
        tmp_path, capsys, roster_name=name, roster_code=code)
    total = total_for(observations, name)
    command = link_command(total.id, person, evidence_id)
    before = counts(repository)
    preview = repository.admin_preview(command)
    assert counts(repository) == before
    repository.admin_commit(command, actor="SYNTHETIC_OWNER", state_hash=preview["state_hash"])
    after = counts(repository)
    assert after["identity_review_items"] == before["identity_review_items"] + 1
    assert after["person_observation_links"] == before["person_observation_links"] + 1
    assert after["asset_disclosures"] == after["asset_items"] == 0
    [claim] = asset_claims(repository, person)
    assert claim.publication_status.value == "DRAFT" and claim.epistemic_status.value == "CLAIM"
    assert claim.asserted_as_true is False and claim.object_text == amount
    assert claim.qualifiers | {
        "gazette_issue": "2099-1", "pdf_id": "0", "publication_date": "2099-03-26",
        "immutable_observation_hash": total.content_hash, "assembly_mona_cd": code,
        "value_semantics": "DECLARED_VALUE_NOT_MARKET_WEALTH",
        "source_contract": "assembly_asset_gazette_reviewed_packet_v1",
    } == claim.qualifiers
    assert claim.qualifiers["reporting_period_text"] == total.normalized["reporting_period_text"]
    evidence = repository.evidence_for(claim.id)
    assert {(item.stance.value, item.feeder_observation_id) for item in evidence} == {
        ("SUPPORT", total.id), ("NEUTRAL", next(
            item.feeder_observation_id for item in repository.evidence_for(
                next(c.id for c in repository.claims(person) if c.predicate == "ASSEMBLY_PARTY"))))}
    links = [link for link in repository.person_observation_links(person)
        if link.observation_id in {item.id for item in observations}]
    assert [(link.observation_id, link.action.value, link.decision_class.value) for link in links] == [
        (total.id, "REVIEWED_LINK", "REVIEWED_SOURCE_CONTEXT")]
    commit(repository, publish_command(claim.id))
    assert any(item.id == claim.id for item in repository.claims(person, published_only=True))
    with TestClient(create_app(repository)) as client:
        rows = client.get(f"/people/{person}/assets").json()
    assert [row["amount_thousand_krw"] for row in rows] == [int(amount[:-2].replace(",", ""))]


def test_item_observation_is_never_a_link_target(tmp_path, capsys):
    repository, _, person, evidence_id, observations = setup(tmp_path, capsys)
    item = next(row for row in observations if row.normalized["record_kind"] == RECORD_KIND_ITEM)
    before = counts(repository)
    with pytest.raises(AdminError) as error:
        repository.admin_preview(link_command(item.id, person, evidence_id))
    assert error.value.code == "GAZETTE_MEMBER_TOTAL_REQUIRED"
    assert counts(repository) == before


def test_printed_name_must_equal_roster_name(tmp_path, capsys):
    repository, _, person, evidence_id, observations = setup(tmp_path, capsys, roster_name="합성의원병")
    with pytest.raises(AdminError) as error:
        repository.admin_preview(link_command(total_for(observations, FIRST).id, person, evidence_id))
    assert error.value.code == "GAZETTE_IDENTITY_CONFLICT"


def test_reviewer_stated_code_must_equal_current_roster_code(tmp_path, capsys):
    repository, _, person, evidence_id, observations = setup(tmp_path, capsys, roster_code="SYNTH009")
    with pytest.raises(AdminError) as error:
        repository.admin_preview(link_command(total_for(observations, FIRST).id, person, evidence_id))
    assert error.value.code == "GAZETTE_MONA_CONFLICT"


def test_non_current_roster_anchor_fails_closed(tmp_path, capsys):
    repository, _, person, evidence_id, observations = setup(tmp_path, capsys)
    with repository.sessions() as session:
        checkpoint = session.scalar(select(db.SourceCheckpointRow).where(
            db.SourceCheckpointRow.feeder == "national_assembly_members"))
        hashes = checkpoint.metadata_json["seen_provider_hashes"]
        checkpoint.metadata_json = dict(checkpoint.metadata_json,
            seen_provider_hashes={"SYNTH999": next(iter(hashes.values()))})
        session.commit()
    with pytest.raises(AdminError) as error:
        repository.admin_preview(link_command(total_for(observations, FIRST).id, person, evidence_id))
    assert error.value.code == "GAZETTE_ROSTER_REQUIRED"


def test_human_verification_is_required():
    with pytest.raises(ValidationError):
        link_command(uuid4(), uuid4(), uuid4(), human_verified=False)


def test_publication_requires_reviewed_gazette_terms(tmp_path, capsys):
    repository, _, person, evidence_id, observations = setup(tmp_path, capsys, licensed=False)
    commit(repository, link_command(total_for(observations, FIRST).id, person, evidence_id))
    [claim] = asset_claims(repository, person)
    with pytest.raises(AdminError) as error:
        repository.admin_preview(publish_command(claim.id))
    assert error.value.code == "GAZETTE_SOURCE_INVALID"


@pytest.mark.parametrize("mutation", ["amount", "review", "roster"])
def test_publication_revalidates_claim_identity_and_roster(tmp_path, capsys, mutation):
    repository, _, person, evidence_id, observations = setup(tmp_path, capsys)
    total = total_for(observations, FIRST)
    commit(repository, link_command(total.id, person, evidence_id))
    [claim] = asset_claims(repository, person)
    with repository.sessions() as session:
        if mutation == "amount":
            row = session.get(db.ClaimRow, str(claim.id))
            row.object_text = "1천원"
        elif mutation == "review":
            link = session.scalar(select(db.PersonObservationLinkRow).where(
                db.PersonObservationLinkRow.observation_id == str(total.id)))
            session.get(db.IdentityReviewItemRow, link.review_item_id).status = "OPEN"
        else:
            checkpoint = session.scalar(select(db.SourceCheckpointRow).where(
                db.SourceCheckpointRow.feeder == "national_assembly_members"))
            checkpoint.cursor = "0"
        session.commit()
    with pytest.raises(AdminError):
        repository.admin_preview(publish_command(claim.id))


def write_matches(path, rows):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["printed_name", "mona", "person_id", "match_class"])
        writer.writeheader()
        writer.writerows(rows)


def test_operator_preview_writes_nothing_and_commit_needs_exact_aggregate_hash(tmp_path, capsys, monkeypatch):
    repository, url, person, _, _ = setup(tmp_path, capsys)
    monkeypatch.setenv("CIVIC_DATABASE_URL", url)
    matches = tmp_path / "matches.csv"
    write_matches(matches, [
        {"printed_name": FIRST, "mona": "SYNTH001", "person_id": str(person), "match_class": "UNIQUE_ROSTER_MATCH"},
        {"printed_name": SECOND, "mona": "", "person_id": "", "match_class": "NO_ROSTER_MATCH"},
    ])
    base = ["--matches", str(matches), "--scope-key", SCOPE, "--reason", REASON]
    with pytest.raises(SystemExit):
        link_main(base + ["--preview-output", str(tmp_path / "unconfirmed.json")])
    capsys.readouterr()
    base.append("--confirm-human-reviewed-matches")
    before = counts(repository)
    preview_path = tmp_path / "preview.json"
    assert link_main(base + ["--preview-output", str(preview_path)]) == 0
    output = capsys.readouterr().out
    report = json.loads(output)
    assert report["status"] == "PREVIEW" and report["write_performed"] is False
    assert report["selected_count"] == 1
    assert report["match_class_counts"] == {"NO_ROSTER_MATCH": 1, "UNIQUE_ROSTER_MATCH": 1}
    assert FIRST not in output
    assert counts(repository) == before
    saved = json.loads(preview_path.read_text(encoding="utf-8"))
    assert saved["aggregate_state_hash"] == report["aggregate_state_hash"]
    assert link_main(base + ["--commit", "--actor", "SYNTHETIC_OWNER", "--state-hash", "0" * 64]) == 1
    failed = json.loads(capsys.readouterr().out)
    assert failed["status"] == "FAILED" and failed["error_code"] == "STALE_AGGREGATE_PREVIEW"
    assert failed["write_performed"] is False
    assert counts(repository) == before
    assert link_main(base + ["--commit", "--actor", "SYNTHETIC_OWNER",
        "--state-hash", report["aggregate_state_hash"]]) == 0
    committed = json.loads(capsys.readouterr().out)
    assert committed["status"] == "COMMITTED" and committed["write_performed"] is True
    assert len(committed["committed_request_ids"]) == 1
    [claim] = asset_claims(repository, person)
    assert claim.publication_status.value == "DRAFT"


def test_operator_stops_on_first_invalid_row_without_writes(tmp_path, capsys, monkeypatch):
    repository, url, person, _, _ = setup(tmp_path, capsys)
    monkeypatch.setenv("CIVIC_DATABASE_URL", url)
    matches = tmp_path / "matches.csv"
    write_matches(matches, [
        {"printed_name": FIRST, "mona": "SYNTH001", "person_id": str(person), "match_class": "UNIQUE_ROSTER_MATCH"},
        {"printed_name": SECOND, "mona": "SYNTH002", "person_id": str(uuid4()), "match_class": "UNIQUE_ROSTER_MATCH"},
    ])
    before = counts(repository)
    assert link_main(["--matches", str(matches), "--scope-key", SCOPE, "--reason", REASON,
        "--confirm-human-reviewed-matches", "--preview-output", str(tmp_path / "p.json")]) == 1
    report = json.loads(capsys.readouterr().out)
    assert report["error_code"] == "GAZETTE_ROSTER_ANCHOR_NOT_FOUND" and report["failed_row_number"] == 3
    assert not (tmp_path / "p.json").exists()
    assert counts(repository) == before
