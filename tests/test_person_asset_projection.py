from fastapi.testclient import TestClient

from apps.api.main import create_app
from packages.domain.admin import AdminCommand
from tests.test_assembly_asset_disclosure import migrated_repository
from tests.test_peti_asset_projection import claim_for, prepared


def test_person_and_assets_share_validated_peti_total_and_source_trace(tmp_path, monkeypatch):
    repository, _ = migrated_repository(tmp_path / "person-assets.sqlite")
    repository.seed_golden()
    current_person = repository.public_people()[0]
    parts = list(prepared())
    parts[4] = current_person
    parts[5] = parts[5].model_copy(update={"candidate_person_id": current_person.id})
    parts[6] = parts[6].model_copy(update={"person_id": current_person.id})
    policy, source, snapshot, observation, person, _, link = parts
    claim, evidence = claim_for(parts, published=True)
    monkeypatch.setattr(repository, "published_person_claim_contexts",
                        lambda *args, **kwargs: {person.id: ([claim], {claim.id: [evidence]})})
    monkeypatch.setattr(repository, "feeder_observation_contexts",
                        lambda ids: {observation.id: (observation, snapshot, source, policy)})
    monkeypatch.setattr(repository, "active_person_ids_by_observation",
                        lambda ids: {observation.id: frozenset({person.id})})
    monkeypatch.setattr(repository, "feeder_observations", lambda *args: [observation])
    monkeypatch.setattr(repository, "person_observation_links", lambda *args: [link])
    monkeypatch.setattr(repository, "sources", lambda ids: {source.id: source})
    monkeypatch.setattr(repository, "policies", lambda ids: {policy.id: policy})
    with TestClient(create_app(repository)) as client:
        assets = client.get(f"/people/{person.id}/assets")
        response = client.get(f"/people/{person.id}")
    assert assets.status_code == response.status_code == 200
    payload = response.json()
    section = next(item for item in payload["profile"]["sections"]
                   if item["id"] == "public_declared_assets")
    entry = section["entries"][0]
    assert entry["details"]["amount_thousand_krw"] == assets.json()[0]["amount_thousand_krw"]
    assert entry["details"]["report_type"] == "UNKNOWN"
    assert entry["epistemic_status"] == "CLAIM"
    assert entry["source_ids"] == [str(source.id)]
    assert entry["evidence_ids"] == [str(evidence.id)]
    assert payload["asset_disclosure_ids"] == []  # No canonical AssetDisclosure row was created.
    assert payload["claims"][0]["id"] == str(claim.id)


def test_disposable_reviewed_peti_operation_reaches_person_and_public_source(tmp_path, monkeypatch, capsys):
    from uuid import uuid4

    from tests.test_peti_asset_operations import setup

    repository, _, link = setup(tmp_path, monkeypatch, capsys)
    preview = repository.admin_preview(link)
    repository.admin_commit(link, actor="SYNTHETIC_OWNER", state_hash=preview["state_hash"])
    claim = next(item for item in repository.claims(link.target_person_id)
                 if item.predicate == "ASSEMBLY_DECLARED_ASSET_TOTAL")
    publish = AdminCommand(request_id=uuid4(), action="PUBLISH", record_ids=(claim.id,),
                           reason="SYNTHETIC separate publication decision")
    preview = repository.admin_preview(publish)
    repository.admin_commit(publish, actor="SYNTHETIC_OWNER", state_hash=preview["state_hash"])
    with TestClient(create_app(repository)) as client:
        response = client.get(f"/people/{link.target_person_id}")
        assert response.status_code == 200
        payload = response.json()
        section = next(item for item in payload["profile"]["sections"]
                       if item["id"] == "public_declared_assets")
        entry = section["entries"][0]
        assert entry["claim_id"] == str(claim.id)
        assert entry["details"]["amount_thousand_krw"] == 1324194
        assert payload["asset_disclosure_ids"] == []
        assert all(client.get(f"/sources/{source_id}").status_code == 200
                   for source_id in entry["source_ids"])
