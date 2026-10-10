from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from apps.api.main import create_app
from packages.connectors.assembly_asset_packet import parse_reviewed_assembly_asset_packet
from packages.domain.contracts import IdentityReviewItem, Person, PersonObservationLink
from packages.domain.enums import (
    IdentityReviewStatus,
    IdentityStatus,
    MaterializationAction,
    MaterializationDecisionClass,
)
from packages.rendering.money_projection import build_assembly_declared_assets_from_claims
from packages.verification.assembly_asset_import import (
    AssemblyAssetImportError,
    build_assembly_asset_capture,
    build_assembly_asset_total_claim,
    gazette_asset_policy,
)
from tests.test_assembly_asset_disclosure import ARTIFACT_BYTES, migrated_repository, payload


def prepared():
    policy = gazette_asset_policy().model_copy(update={
        "license": "SYNTHETIC_TEST_ONLY", "terms_checked_at": datetime.now(UTC),
    })
    capture = build_assembly_asset_capture(
        parse_reviewed_assembly_asset_packet(payload()), artifact_bytes=ARTIFACT_BYTES,
        policy=policy,
    )
    observation = capture.observations(uuid4())[0]
    person = Person(canonical_name="합성의원갑", identity_status=IdentityStatus.RESOLVED)
    review = IdentityReviewItem(observation_id=observation.id, candidate_person_id=person.id,
        reason_code="SYNTHETIC", status=IdentityReviewStatus.RESOLVED,
        resolution_note="SYNTHETIC reviewed exact official provider identity")
    link = PersonObservationLink(person_id=person.id, observation_id=observation.id,
        action=MaterializationAction.REVIEWED_LINK,
        decision_class=MaterializationDecisionClass.REVIEWED_SOURCE_CONTEXT,
        review_item_id=review.id)
    return capture, observation, person, review, link


def project(capture, observation, person, link, claim, evidence):
    return build_assembly_declared_assets_from_claims(person, [claim], {claim.id: [evidence]},
        observations={observation.id: observation}, snapshots={capture.snapshot.id: capture.snapshot},
        sources={capture.source.id: capture.source}, policies={capture.policy.id: capture.policy},
        links=[link])


def test_draft_default_is_absent_and_published_integer_total_is_exact():
    capture, observation, person, review, link = prepared()
    claim, evidence = build_assembly_asset_total_claim(capture, observation, person=person,
        link=link, review=review, official_member_code="SYNTH001")
    assert project(capture, observation, person, link, claim, evidence) == []
    claim, evidence = build_assembly_asset_total_claim(capture, observation, person=person,
        link=link, review=review, official_member_code="SYNTH001", publication_approved=True)
    rows = project(capture, observation, person, link, claim, evidence)
    assert rows[0]["amount_thousand_krw"] == 195000
    assert type(rows[0]["amount_thousand_krw"]) is int
    assert rows[0]["asserted_as_true"] is False
    assert rows[0]["declared_totals_scope"] == observation.normalized["declared_totals_scope"]


@pytest.mark.parametrize("bad", ["code", "person", "link", "review"])
def test_staging_requires_exact_reviewed_identity(bad):
    capture, observation, person, review, link = prepared()
    code = "WRONG" if bad == "code" else "SYNTH001"
    if bad == "person":
        person = person.model_copy(update={"identity_status": IdentityStatus.REVIEW})
    if bad == "link":
        link = link.model_copy(update={"person_id": uuid4()})
    if bad == "review":
        review = review.model_copy(update={"status": IdentityReviewStatus.OPEN})
    with pytest.raises(AssemblyAssetImportError):
        build_assembly_asset_total_claim(capture, observation, person=person,
            link=link, review=review, official_member_code=code)


def test_reader_rejects_tampered_amount_and_absent_link():
    capture, observation, person, review, link = prepared()
    claim, evidence = build_assembly_asset_total_claim(capture, observation, person=person,
        link=link, review=review, official_member_code="SYNTH001", publication_approved=True)
    tampered = claim.model_copy(update={"qualifiers": claim.qualifiers | {"amount_thousand_krw": "0"}})
    with pytest.raises(ValueError):
        project(capture, observation, person, link, tampered, evidence)
    with pytest.raises(ValueError):
        project(capture, observation, person, link.model_copy(update={"review_item_id": None}), claim, evidence)


def test_assets_empty_coverage_is_not_zero_or_an_error(tmp_path):
    repository, _ = migrated_repository(tmp_path / "asset-api.sqlite")
    repository.seed_golden()
    with TestClient(create_app(repository)) as client:
        person = client.get("/people").json()[0]
        response = client.get(f"/people/{person['id']}/assets")
        assert response.status_code == 200
        assert response.json() == []
        assert response.headers["X-Civic-Asset-Coverage"] == "NO_PUBLISHED_ASSET_CLAIMS"


def test_unpublished_corrected_sibling_blocks_old_published_total():
    capture, observation, person, review, link = prepared()
    claim, evidence = build_assembly_asset_total_claim(capture, observation, person=person,
        link=link, review=review, official_member_code="SYNTH001", publication_approved=True)
    correction = observation.model_copy(update={"id": uuid4(), "content_hash": "f" * 64})
    from packages.rendering.money_projection import AssetSourceVersionConflict
    with pytest.raises(AssetSourceVersionConflict):
        build_assembly_declared_assets_from_claims(person, [claim], {claim.id: [evidence]},
            observations={observation.id: observation, correction.id: correction},
            snapshots={capture.snapshot.id: capture.snapshot},
            sources={capture.source.id: capture.source}, policies={capture.policy.id: capture.policy},
            links=[link])


def test_reader_rejects_snapshot_publication_date_drift():
    capture, observation, person, review, link = prepared()
    claim, evidence = build_assembly_asset_total_claim(capture, observation, person=person,
        link=link, review=review, official_member_code="SYNTH001", publication_approved=True)
    capture = capture.__class__(capture.packet, capture.policy, capture.source,
        capture.snapshot.model_copy(update={"metadata": capture.snapshot.metadata | {"publication_date": "2099-03-27"}}))
    with pytest.raises(ValueError):
        project(capture, observation, person, link, claim, evidence)


def test_source_publication_instant_normalized_to_utc_keeps_korean_date():
    capture, observation, person, review, link = prepared()
    claim, evidence = build_assembly_asset_total_claim(capture, observation, person=person,
        link=link, review=review, official_member_code="SYNTH001", publication_approved=True)
    capture = capture.__class__(capture.packet, capture.policy,
        capture.source.model_copy(update={"published_at": capture.source.published_at.astimezone(UTC)}),
        capture.snapshot)
    rows = project(capture, observation, person, link, claim, evidence)
    assert rows[0]["publication_date"] == "2099-03-26"


def test_api_rejects_asset_observation_also_linked_to_another_person(tmp_path, monkeypatch):
    repository, _ = migrated_repository(tmp_path / "asset-link-api.sqlite")
    repository.seed_golden()
    person = repository.public_people()[0]
    capture, observation, _, review, link = prepared()
    review = review.model_copy(update={"candidate_person_id": person.id})
    link = link.model_copy(update={"person_id": person.id})
    claim, evidence = build_assembly_asset_total_claim(capture, observation, person=person,
        link=link, review=review, official_member_code="SYNTH001", publication_approved=True)
    monkeypatch.setattr(repository, "published_person_claim_contexts",
        lambda *args, **kwargs: {person.id: ([claim], {claim.id: [evidence]})})
    monkeypatch.setattr(repository, "feeder_observation_contexts",
        lambda ids: {observation.id: (observation, capture.snapshot, capture.source, capture.policy)})
    monkeypatch.setattr(repository, "active_person_ids_by_observation",
        lambda ids: {observation.id: frozenset({person.id, uuid4()})})
    with TestClient(create_app(repository)) as client:
        response = client.get(f"/people/{person.id}/assets")
        assert response.status_code == 503
        assert "195000" not in response.text
