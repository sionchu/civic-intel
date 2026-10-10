"""Scoped synthetic self-housing receipts, never live/private detail contents."""
import json
from uuid import uuid4

import pytest

from packages.domain import db
from packages.domain.admin import AdminCommand
from packages.domain.contracts import IdentityReviewItem, Person, PersonObservationLink
from packages.verification.assembly_asset_import import (
    PETI_HOUSING_POLICY_SCOPE,
    build_peti_housing_capture,
    build_peti_housing_claim,
    normalize_peti_housing_receipt,
    peti_asset_record_key,
)
from tests.test_peti_asset_projection import policy, receipt
from workers.assembly_asset_import import main


def housing_policy():
    return policy().model_copy(update={"policy_note": PETI_HOUSING_POLICY_SCOPE})


def housing_receipt():
    total = receipt()
    return {key: total[key] for key in ("source_page_url", "detail_route", "publication_date",
        "registration_date", "institution", "office", "printed_name")} | {
        "self_scope_coverage": "PARTIAL", "absence_basis": None, "absence_evidence": None,
        "items": [{"holder": "SELF", "dwelling_type": "APARTMENT",
            "right_type": "SHARED_OWNERSHIP", "count": 1}]}


def prepared(raw=None):
    governing = housing_policy()
    source, snapshot, observation = build_peti_housing_capture(raw or housing_receipt(),
        policy=governing, run_id=uuid4())
    person = Person(canonical_name="합성의원갑", identity_status="RESOLVED")
    review = IdentityReviewItem(observation_id=observation.id, candidate_person_id=person.id,
        reason_code="SYNTHETIC_OWNER_REVIEW", status="RESOLVED", resolution_note="Synthetic exact source review")
    link = PersonObservationLink(person_id=person.id, observation_id=observation.id,
        action="REVIEWED_LINK", decision_class="REVIEWED_SOURCE_CONTEXT", review_item_id=review.id)
    return governing, source, snapshot, observation, person, review, link


def claim_for(parts):
    p, source, snapshot, observation, person, review, link = parts
    return build_peti_housing_claim(source, snapshot, observation, policy=p,
        person=person, review=review, link=link)


def test_explicit_shared_self_ownership_positive_is_declared_not_residence():
    claim, evidence = claim_for(prepared())
    assert claim.qualifiers["housing_status"] == "DISCLOSED_OWNED"
    assert claim.qualifiers["owned_housing_count"] == "1"
    assert claim.qualifiers["shared_housing_count"] == "1"
    assert claim.qualifiers["self_scope_coverage"] == "PARTIAL"
    assert claim.publication_status == "DRAFT" and not claim.asserted_as_true
    assert claim.qualifiers["value_semantics"] == "DECLARED_OWNERSHIP_NOT_RESIDENCE"
    assert evidence.excerpt is None


@pytest.mark.parametrize("coverage", ["PARTIAL", "UNKNOWN", "WITHHELD", "COMPLETE_SELF_HOUSING"])
def test_empty_or_even_supplied_complete_scope_does_not_establish_absence(coverage):
    raw = housing_receipt() | {"items": [], "self_scope_coverage": coverage}
    claim, _ = claim_for(prepared(raw))
    assert claim.qualifiers["housing_status"] == "UNKNOWN"
    assert claim.qualifiers["owned_housing_count"] == "UNKNOWN"
    assert claim.epistemic_status == "UNKNOWN" and not claim.asserted_as_true


def test_negative_requires_exact_source_absence_evidence_not_flag():
    raw = housing_receipt() | {"items": [], "self_scope_coverage": "UNKNOWN",
        "absence_basis": "EXPLICIT_SOURCE_NO_SELF_HOUSING"}
    with pytest.raises(ValueError): prepared(raw)
    raw["absence_evidence"] = {"selector_record_key": peti_asset_record_key(raw),
        "source_statement": "본인 소유 주택 없음"}
    claim, _ = claim_for(prepared(raw))
    assert claim.qualifiers["housing_status"] == "DISCLOSED_NONE"
    raw["absence_evidence"]["selector_record_key"] = "unrelated"
    with pytest.raises(ValueError): prepared(raw)


@pytest.mark.parametrize("field", ["address", "residence", "family", "market_value", "fulltext", "HUMAN_REVIEWED"])
def test_private_or_inferred_fields_rejected_before_snapshot(field):
    with pytest.raises(ValueError): prepared(housing_receipt() | {field: "FORBIDDEN_SYNTHETIC"})


@pytest.mark.parametrize("change", [
    {"holder": "SPOUSE"}, {"dwelling_type": "BUILDING"}, {"dwelling_type": "OFFICETEL"},
    {"right_type": "LEASE"}, {"right_type": "PRESALE_RIGHT"}, {"count": True},
    {"count": 0}, {"address": "FORBIDDEN_SYNTHETIC"},
])
def test_family_generic_building_lease_or_bad_count_never_prove_ownership(change):
    raw = housing_receipt()
    raw["items"][0].update(change)
    with pytest.raises(ValueError): prepared(raw)


def test_total_policy_does_not_silently_grant_housing_scope():
    with pytest.raises(ValueError): normalize_peti_housing_receipt(housing_receipt(), policy=policy())
    with pytest.raises(PermissionError): normalize_peti_housing_receipt(housing_receipt(),
        policy=housing_policy().model_copy(update={"can_store_metadata": False}))


@pytest.mark.parametrize("part", ["source", "snapshot", "observation", "person", "review", "link"])
def test_exact_identity_and_immutable_provenance_required(part):
    values = list(prepared())
    changes = {"source": (1, {"policy_id": uuid4()}), "snapshot": (2, {"content_hash": "0" * 64}),
        "observation": (3, {"identity_hints": {"name": "unsafe"}}),
        "person": (4, {"identity_status": "REVIEW"}), "review": (5, {"candidate_person_id": uuid4()}),
        "link": (6, {"action": "AUTO_LINK"})}
    i, change = changes[part]
    values[i] = values[i].model_copy(update=change)
    with pytest.raises(ValueError): claim_for(values)


def test_worker_housing_default_no_write_and_no_contents(tmp_path, monkeypatch, capsys):
    raw_path, policy_path = tmp_path / "housing.json", tmp_path / "policy.json"
    raw_path.write_text(json.dumps(housing_receipt(), ensure_ascii=False), encoding="utf-8")
    policy_path.write_text(housing_policy().model_dump_json(), encoding="utf-8")
    monkeypatch.delenv("CIVIC_DATABASE_URL", raising=False)
    assert main(["--peti-housing-receipt", str(raw_path), "--peti-policy", str(policy_path)]) == 0
    stdout = capsys.readouterr().out
    assert "합성" not in stdout and "APARTMENT" not in stdout
    result = json.loads(stdout)
    assert result["feeder"] == "peti_public_self_housing"
    assert not result["write_performed"] and not result["claim_publication"]
    assert "amount_unit" not in result


@pytest.mark.parametrize("empty", [False, True])
def test_canonical_housing_capture_review_draft_separate_publish(tmp_path, monkeypatch, capsys, empty):
    from uuid import UUID

    from tests.test_peti_asset_operations import setup
    repository, _args, total_command = setup(tmp_path, monkeypatch, capsys)
    policy_path = tmp_path / "policy.json"
    from packages.domain.contracts import SourcePolicy
    governing = SourcePolicy.model_validate_json(policy_path.read_text(encoding="utf-8"))
    governing = governing.model_copy(update={"policy_note": PETI_HOUSING_POLICY_SCOPE})
    # Disposable fixture only: operational policy replacement is never performed by the worker.
    with repository.sessions() as session:
        session.get(db.SourcePolicyRow, str(governing.id)).policy_note = governing.policy_note
        session.commit()
    policy_path.write_text(governing.model_dump_json(), encoding="utf-8")
    raw_path = tmp_path / "housing.json"
    raw = housing_receipt() | ({"items": [], "self_scope_coverage": "WITHHELD"} if empty else {})
    raw_path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
    house_args = ["--peti-housing-receipt", str(raw_path), "--peti-policy", str(policy_path)]
    assert main(house_args + ["--commit"]) == 0
    captured = json.loads(capsys.readouterr().out)
    command = total_command.model_copy(update={"request_id": uuid4(),
        "record_ids": (UUID(captured["observation_ids"][0]),)})
    preview = repository.admin_preview(command)
    assert not preview["write_performed"]
    repository.admin_commit(command, actor="SYNTHETIC_OWNER", state_hash=preview["state_hash"])
    claim = next(c for c in repository.claims(command.target_person_id) if c.predicate == "PETI_DECLARED_SELF_HOUSING")
    assert claim.publication_status == "DRAFT"
    publish = AdminCommand(request_id=uuid4(), action="PUBLISH", record_ids=(claim.id,),
        reason="SYNTHETIC separate reviewed self-housing publication")
    repository.admin_commit(publish, actor="SYNTHETIC_OWNER",
        state_hash=repository.admin_preview(publish)["state_hash"])
    actual = next(c for c in repository.claims(command.target_person_id) if c.id == claim.id)
    assert actual.publication_status == "PUBLISHED" and not actual.asserted_as_true
    assert actual.epistemic_status == ("UNKNOWN" if empty else "CLAIM")
    assert actual.qualifiers["housing_status"] == ("UNKNOWN" if empty else "DISCLOSED_OWNED")
