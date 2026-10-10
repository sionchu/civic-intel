import json
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from apps.api.main import create_app
from packages.connectors.open_assembly import (
    OpenAssemblyMemberConnector,
    national_assembly_member_policy,
)
from packages.domain import db
from packages.domain.admin import AdminCommand
from packages.domain.contracts import SourcePolicy
from packages.domain.enums import EvidenceStance
from packages.rendering.public_disclosure_records import validate_public_disclosure_records
from packages.verification.assembly_asset_import import (
    assembly_asset_observation_hash,
    build_peti_housing_claim,
)
from packages.verification.assembly_press_import import build_press_claim
from tests.test_assembly_press_import import prepared as press_parts
from tests.test_peti_housing_import import housing_receipt
from tests.test_peti_housing_import import prepared as housing_parts


@pytest.mark.parametrize("lane", ["press", "housing"])
@pytest.mark.parametrize(
    "mutation",
    [
        None,
        "admin_evidence_id",
        "second_person",
        "sibling",
        "claim",
        "review",
        "missing_bridge",
        "withdrawn_roster",
        "stale_checkpoint",
        "failed_roster_run",
        "second_roster_person",
        "withdrawn_person",
    ],
)
def test_public_reader_revalidates_full_source_identity_and_claim(lane, mutation):
    parts = press_parts() if lane == "press" else housing_parts()
    policy, source, snapshot, observation, person, review, link = parts[:7]
    factory = build_press_claim if lane == "press" else build_peti_housing_claim
    claim, proof = factory(
        source,
        snapshot,
        observation,
        policy=policy,
        person=person,
        review=review,
        link=link,
        publication_approved=True,
    )
    active = {person.id} if mutation != "second_person" else {person.id, uuid4()}
    sibling = observation.model_copy(update={"id": uuid4(), "content_hash": "0" * 64})
    normalized = {"canonical_name": person.canonical_name, "member_code": "SYNTHETIC-M-001"}
    roster_policy = national_assembly_member_policy()
    roster_source = source.model_copy(
        update={
            "id": uuid4(),
            "policy_id": roster_policy.id,
            "url": OpenAssemblyMemberConnector.BASE_URL + "?Type=json&pIndex=1&pSize=100",
        }
    )
    roster_snapshot = snapshot.model_copy(update={"id": uuid4(), "source_id": roster_source.id})
    roster_observation = observation.model_copy(
        update={
            "id": uuid4(),
            "snapshot_id": roster_snapshot.id,
            "feeder": "national_assembly_members",
            "scope_key": "current_member_roster",
            "semantic_scope": "legislative_member_roster",
            "provider_record_key": "SYNTHETIC-M-001",
            "normalized": normalized,
            "content_hash": assembly_asset_observation_hash(normalized),
        }
    )
    anchor = claim.model_copy(
        update={
            "id": uuid4(),
            "predicate": "ASSEMBLY_PARTY",
            "proposition": "합성 명부 사실.",
            "epistemic_status": "FACT",
            "asserted_as_true": True,
            "qualifiers": {
                "source_contract": "assembly_member_roster",
                "provider_record_key": roster_observation.provider_record_key,
                "immutable_observation_hash": roster_observation.content_hash,
            },
        }
    )
    original = proof.model_copy(
        update={
            "id": uuid4(),
            "claim_id": anchor.id,
            "source_id": roster_source.id,
            "snapshot_id": roster_snapshot.id,
            "feeder_observation_id": roster_observation.id,
        }
    )
    bridge = original.model_copy(
        update={"id": uuid4(), "claim_id": claim.id, "stance": EvidenceStance.NEUTRAL}
    )
    repository = SimpleNamespace(
        feeder_observation_contexts=lambda _: {
            observation.id: (observation, snapshot, source, policy),
            roster_observation.id: (
                roster_observation,
                roster_snapshot,
                roster_source,
                roster_policy,
            ),
        },
        active_person_ids_by_observation=lambda _: {
            observation.id: frozenset(active),
            roster_observation.id: frozenset(
                {person.id, uuid4()} if mutation == "second_roster_person" else {person.id}
            ),
        },
        person_observation_links=lambda _: [link],
        identity_review_items=lambda _: [] if mutation == "review" else [review],
        feeder_observations=lambda *_: (
            [observation, sibling] if mutation == "sibling" else [observation]
        ),
        published_person_claim_contexts=lambda *_, **__: (
            {person.id: ([], {})}
            if mutation == "withdrawn_roster"
            else {person.id: ([anchor], {anchor.id: [original]})}
        ),
        source_checkpoint=lambda *_: SimpleNamespace(
            last_run_id=uuid4(),
            cursor="1",
            metadata={
                "source_contract": "assembly_member_roster",
                "list_total_count": 1,
                "expected_pages": 1,
                "seen_provider_hashes": {
                    roster_observation.provider_record_key: "0" * 64
                    if mutation == "stale_checkpoint"
                    else roster_observation.content_hash
                },
            },
        ),
        source_run=lambda _: SimpleNamespace(
            status="FAILED" if mutation == "failed_roster_run" else "SUCCESS",
            feeder=roster_observation.feeder,
            scope_key=roster_observation.scope_key,
            records_seen=1,
        ),
        sources=lambda _: {source.id: source, roster_source.id: roster_source},
        policies=lambda _: {policy.id: policy, roster_policy.id: roster_policy},
    )
    if mutation == "claim":
        claim = claim.model_copy(update={"object_text": "different public statement"})
    if mutation == "admin_evidence_id":
        proof = proof.model_copy(update={"id": uuid4()})
    if mutation == "withdrawn_person":
        person = person.model_copy(update={"superseded_at": observation.recorded_at})
    evidence = [proof] if mutation == "missing_bridge" else [proof, bridge]
    if mutation not in {None, "admin_evidence_id"}:
        with pytest.raises(ValueError):
            validate_public_disclosure_records(repository, person, [claim], {claim.id: evidence})
    else:
        assert validate_public_disclosure_records(
            repository, person, [claim], {claim.id: evidence}
        ) == [claim]


def test_admin_published_press_reaches_profile_and_actual_evidence_ids(
    tmp_path, monkeypatch, capsys
):
    from tests.test_assembly_press_import import setup

    repository, _, command = setup(tmp_path, monkeypatch, capsys)
    repository.admin_commit(
        command, actor="SYNTHETIC_OWNER", state_hash=repository.admin_preview(command)["state_hash"]
    )
    claim = next(
        c
        for c in repository.claims(command.target_person_id)
        if c.predicate == "ASSEMBLY_OFFICIAL_PRESS_RECORD"
    )
    publish = AdminCommand(
        request_id=uuid4(),
        action="PUBLISH",
        record_ids=(claim.id,),
        reason="SYNTHETIC separate publication",
    )
    repository.admin_commit(
        publish, actor="SYNTHETIC_OWNER", state_hash=repository.admin_preview(publish)["state_hash"]
    )
    actual_proofs = repository.evidence_for(claim.id)
    assert len(actual_proofs) == 2
    current_claims, current_evidence = repository.published_person_claim_contexts(
        [command.target_person_id]
    )[command.target_person_id]
    validate_public_disclosure_records(
        repository, repository.person(command.target_person_id), current_claims, current_evidence
    )
    with TestClient(create_app(repository)) as client:
        response = client.get(f"/people/{command.target_person_id}")
        assert response.status_code == 200
        dto = response.json()
        section = next(s for s in dto["profile"]["sections"] if s["id"] == "official_press_records")
        assert section["entries"][0]["details"]["coverage"] == "REVIEWED_SELECTED_RECORD"
        embedded = next(c for c in dto["claims"] if c["id"] == str(claim.id))
        assert {p["id"] for p in embedded["evidence"]} == {str(p.id) for p in actual_proofs}
        assert client.get(f"/people/{command.target_person_id}/claims").status_code == 200


@pytest.mark.parametrize("empty", [False, True])
def test_admin_housing_publication_reaches_profile_without_zero_inference(
    tmp_path, monkeypatch, capsys, empty
):
    from packages.verification.assembly_asset_import import PETI_HOUSING_POLICY_SCOPE
    from tests.test_peti_asset_operations import setup
    from workers.assembly_asset_import import main

    repository, _, total_command = setup(tmp_path, monkeypatch, capsys)
    policy_path = tmp_path / "policy.json"
    governing = SourcePolicy.model_validate_json(policy_path.read_text(encoding="utf-8"))
    governing = governing.model_copy(update={"policy_note": PETI_HOUSING_POLICY_SCOPE})
    with repository.sessions() as session:
        session.get(db.SourcePolicyRow, str(governing.id)).policy_note = governing.policy_note
        session.commit()
    policy_path.write_text(governing.model_dump_json(), encoding="utf-8")
    raw = housing_receipt() | ({"items": [], "self_scope_coverage": "WITHHELD"} if empty else {})
    receipt = tmp_path / "housing.json"
    receipt.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
    assert (
        main(
            ["--peti-housing-receipt", str(receipt), "--peti-policy", str(policy_path), "--commit"]
        )
        == 0
    )
    capture = json.loads(capsys.readouterr().out)
    command = total_command.model_copy(
        update={"request_id": uuid4(), "record_ids": (UUID(capture["observation_ids"][0]),)}
    )
    repository.admin_commit(
        command, actor="SYNTHETIC_OWNER", state_hash=repository.admin_preview(command)["state_hash"]
    )
    claim = next(
        c
        for c in repository.claims(command.target_person_id)
        if c.predicate == "PETI_DECLARED_SELF_HOUSING"
    )
    publish = AdminCommand(
        request_id=uuid4(),
        action="PUBLISH",
        record_ids=(claim.id,),
        reason="Synthetic separate publication",
    )
    repository.admin_commit(
        publish, actor="SYNTHETIC_OWNER", state_hash=repository.admin_preview(publish)["state_hash"]
    )
    with TestClient(create_app(repository)) as client:
        response = client.get(f"/people/{command.target_person_id}")
        assert response.status_code == 200
        section = next(
            s for s in response.json()["profile"]["sections"] if s["id"] == "public_self_housing"
        )
        entry = section["entries"][0]
        assert entry["claim_id"] == str(claim.id)
        assert entry["details"]["housing_status"] == ("UNKNOWN" if empty else "DISCLOSED_OWNED")
        assert entry["details"]["owned_housing_count"] == ("UNKNOWN" if empty else "1")
        assert entry["epistemic_status"] == ("UNKNOWN" if empty else "CLAIM")
