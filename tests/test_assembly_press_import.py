"""Synthetic records only: canonical capture/review/publication, no live contents."""
import json
from dataclasses import replace
from datetime import date
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy import func, select

from packages.connectors.base import ConnectorDocument
from packages.connectors.open_assembly import national_assembly_member_policy as policy
from packages.connectors.open_assembly_press_releases import OpenAssemblyPressReleaseConnector
from packages.domain import db
from packages.domain.admin import AdminCommand
from packages.domain.contracts import IdentityReviewItem, Person, PersonObservationLink
from packages.persistence.admin_workflow import AdminError
from packages.verification.assembly_base_profile import AssemblyBaseProfilePublisher
from packages.verification.assembly_press_import import (
    PRESS_CONTRACT,
    PRESS_PREDICATE,
    build_press_capture,
    build_press_claim,
)
from tests.test_assembly_asset_disclosure import migrated_repository
from tests.test_assembly_base_profile import SinglePageRoster, member_row
from workers.assembly_press_import import main
from workers.assembly_roster import AssemblyRosterEnumerator


def page():
    return {"written_date": "2099-10-09", "page_index": 1, "page_size": 5,
        "list_total_count": 17, "records": [{"record_key": "777", "title": "합성 정책 안내",
            "written_date": "2099-10-09", "category": "합성 기관",
            "source_url": OpenAssemblyPressReleaseConnector.BASE_URL + "?Type=json&NUM=777"}]}


def prepared():
    raw = page()
    governing = policy().model_copy(update={"can_send_to_ai": False})
    document = ConnectorDocument(url=OpenAssemblyPressReleaseConnector(policy=governing,
        written_on=date(2099, 10, 9), page_size=5).discover()[0], title="합성", publisher="합성",
        published_at=None, body=json.dumps(raw["records"]), metadata={"source_contract": PRESS_CONTRACT,
            "list_total_count": "17", "row_count": "1"})
    source, snapshot, rows = build_press_capture(document, policy=governing,
        written_on=date(2099, 10, 9), page_index=1, page_size=5, run_id=uuid4())
    person = Person(canonical_name="합성의원갑", identity_status="RESOLVED")
    review = IdentityReviewItem(observation_id=rows[0].id, candidate_person_id=person.id,
        reason_code="SYNTHETIC_OWNER_REVIEW", status="RESOLVED",
        resolution_note="Owner reviewed actual relevance; no title-name match")
    link = PersonObservationLink(person_id=person.id, observation_id=rows[0].id,
        action="REVIEWED_LINK", decision_class="REVIEWED_SOURCE_CONTEXT", review_item_id=review.id)
    return governing, source, snapshot, rows[0], person, review, link, document


def test_capture_is_selected_page_no_person_inference_ai_or_fulltext():
    p, source, snapshot, observation, person, review, link, _ = prepared()
    claim, evidence = build_press_claim(source, snapshot, observation, policy=p,
        person=person, review=review, link=link)
    assert claim.publication_status == "DRAFT" and claim.epistemic_status == "CLAIM"
    assert not claim.asserted_as_true and not p.can_send_to_ai
    assert snapshot.fulltext is None and evidence.excerpt is None
    assert observation.identity_hints == {} and "canonical_name" not in observation.normalized
    assert snapshot.metadata["coverage"] == "SELECTED_PAGE_ONLY"
    assert claim.qualifiers["written_date"] == "2099-10-09"
    assert source.published_at is None


@pytest.mark.parametrize("field", ["CONTENT", "CONTENT_URL", "MONA_CD", "address", "KEY"])
def test_forbidden_record_fields_fail_closed(field):
    p, _, _, _, _, _, _, document = prepared()
    rows = json.loads(document.body)
    rows[0][field] = "SYNTHETIC_FORBIDDEN"
    with pytest.raises(ValueError):
        build_press_capture(replace(document, body=json.dumps(rows)), policy=p,
            written_on=date(2099, 10, 9), page_index=1, page_size=5, run_id=uuid4())


@pytest.mark.parametrize("part", ["snapshot", "observation", "link", "review", "person"])
def test_tampered_provenance_or_identity_rejected(part):
    p, source, snapshot, observation, person, review, link, _ = prepared()
    if part == "snapshot": snapshot = snapshot.model_copy(update={"content_hash": "0" * 64})
    if part == "observation": observation = observation.model_copy(update={"scope_key": "other"})
    if part == "link": link = link.model_copy(update={"person_id": uuid4()})
    if part == "review": review = review.model_copy(update={"status": "OPEN"})
    if part == "person": person = person.model_copy(update={"identity_status": "REVIEW"})
    with pytest.raises(ValueError):
        build_press_claim(source, snapshot, observation, policy=p, person=person, review=review, link=link)


def inputs(tmp_path):
    metadata, governing = tmp_path / "page.json", tmp_path / "policy.json"
    metadata.write_text(json.dumps(page(), ensure_ascii=False), encoding="utf-8")
    governing.write_text(policy().model_copy(update={"can_send_to_ai": False}).model_dump_json(), encoding="utf-8")
    return ["--metadata", str(metadata), "--policy", str(governing)]


def setup(tmp_path, monkeypatch, capsys):
    repository, url = migrated_repository(tmp_path / "press.db")
    roster = SinglePageRoster(member_row("SYNTHETIC-M-001", "합성의원갑"))
    enumerated = AssemblyRosterEnumerator(roster.connector(), repository).enumerate_and_materialize()
    AssemblyBaseProfilePublisher(repository).publish_latest_successful()
    # Preserve stored exact semantics while refusing AI use in the synthetic policy.
    with repository.sessions() as session:
        session.get(db.SourcePolicyRow, str(policy().id)).can_send_to_ai = False
        session.commit()
    monkeypatch.setenv("CIVIC_DATABASE_URL", url)
    args = inputs(tmp_path)
    assert main(args + ["--commit"]) == 0
    capture = json.loads(capsys.readouterr().out)
    person = enumerated.materializations[0].person_id
    roster_claim = next(c for c in repository.claims(person, published_only=True) if c.predicate == "ASSEMBLY_PARTY")
    command = AdminCommand(request_id=uuid4(), action="LINK_PERSON",
        record_ids=(UUID(capture["observation_ids"][0]),), target_person_id=person,
        evidence_ids=(repository.evidence_for(roster_claim.id)[0].id,),
        identity_basis="OFFICIAL_PRESS_SOURCE_CONTEXT", human_verified=True,
        reason="SYNTHETIC owner inspected exact press relevance, not title-name linkage")
    return repository, args, command


def test_default_preview_outputs_no_contents_and_writes_nothing(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("CIVIC_DATABASE_URL", raising=False)
    assert main(inputs(tmp_path)) == 0
    out = capsys.readouterr().out
    assert "합성" not in out and "title" not in out
    receipt = json.loads(out)
    assert not receipt["write_performed"] and not receipt["claim_publication"]
    assert not receipt["identity_review_confirmed"] and not receipt["ai_processing"]


def test_canonical_link_draft_and_separate_publication(tmp_path, monkeypatch, capsys):
    repository, _, command = setup(tmp_path, monkeypatch, capsys)
    preview = repository.admin_preview(command)
    assert not preview["write_performed"]
    with repository.sessions() as session:
        assert session.scalar(select(func.count()).select_from(db.PersonObservationLinkRow,
            ).where(db.PersonObservationLinkRow.observation_id == str(command.record_ids[0]))) == 0
    repository.admin_commit(command, actor="SYNTHETIC_OWNER", state_hash=preview["state_hash"])
    claim = next(c for c in repository.claims(command.target_person_id) if c.predicate == PRESS_PREDICATE)
    assert claim.publication_status == "DRAFT"
    publish = AdminCommand(request_id=uuid4(), action="PUBLISH", record_ids=(claim.id,),
        reason="SYNTHETIC separate reviewed metadata publication")
    repository.admin_commit(publish, actor="SYNTHETIC_OWNER",
        state_hash=repository.admin_preview(publish)["state_hash"])
    assert next(c for c in repository.claims(command.target_person_id) if c.id == claim.id).publication_status == "PUBLISHED"
    assert not repository.policies()[policy().id].can_send_to_ai


def test_press_basis_cannot_merge_or_bypass_human_review():
    base = {"request_id": uuid4(), "action": "LINK_PERSON", "record_ids": (uuid4(),), "target_person_id": uuid4(),
        "evidence_ids": (uuid4(),), "identity_basis": "OFFICIAL_PRESS_SOURCE_CONTEXT", "human_verified": True,
        "reason": "SYNTHETIC source context review"}
    with pytest.raises(ValidationError): AdminCommand(**(base | {"action": "MERGE_PERSON"}))
    with pytest.raises(ValidationError): AdminCommand(**(base | {"human_verified": False}))


def test_press_corrected_sibling_blocks_link(tmp_path, monkeypatch, capsys):
    repository, _, command = setup(tmp_path, monkeypatch, capsys)
    observation = repository.feeder_observation(command.record_ids[0])
    assert observation is not None
    with repository.sessions() as session:
        values = observation.model_dump(mode="python")
        for k in ("id", "snapshot_id", "run_id"): values[k] = str(values[k])
        values["id"] = str(uuid4())
        values["normalized_json"] = values.pop("normalized")
        values["identity_hints_json"] = values.pop("identity_hints")
        values["content_hash"] = "0" * 64
        session.add(db.FeederObservationRow(**values))
        session.commit()
    with pytest.raises(AdminError, match="서로 다른 버전"):
        repository.admin_preview(command)
