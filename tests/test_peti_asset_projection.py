from datetime import UTC, datetime
from uuid import uuid4

import pytest

from packages.domain.contracts import (
    IdentityReviewItem,
    Person,
    PersonObservationLink,
    SourcePolicy,
)
from packages.domain.enums import (
    IdentityReviewStatus,
    IdentityStatus,
    MaterializationAction,
    MaterializationDecisionClass,
    SourceCollectionMode,
)
from packages.rendering.money_projection import (
    AssetSourceVersionConflict,
    build_assembly_declared_assets_from_claims,
)
from packages.verification.assembly_asset_import import (
    AMOUNT_UNIT,
    PETI_ASSET_DETAIL,
    PETI_ASSET_PAGE,
    PETI_ASSET_TOTALS_SCOPE,
    PETI_TOTAL_HEADERS,
    AssemblyAssetImportError,
    build_peti_asset_capture,
    build_peti_asset_total_claim,
    normalize_peti_asset_receipt,
)
from packages.verification.policy import PolicyDenied


def policy():
    return SourcePolicy(domain="www.peti.go.kr", source_class="SYNTHETIC_POLICY_DECISION",
        collection_mode=SourceCollectionMode.BROWSER, can_fetch=False, can_store_metadata=True,
        can_store_fulltext=False, can_send_to_ai=False, can_show_excerpt=False,
        can_commercialize=False, license=None)


def receipt():
    return {"source_page_url": PETI_ASSET_PAGE, "detail_route": PETI_ASSET_DETAIL,
        "publication_date": "2099-03-26", "registration_date": "2098-12-31",
        "institution": "국회", "office": "국회의원", "printed_name": "합성의원갑",
        "column_headers": list(PETI_TOTAL_HEADERS), "amount_unit": AMOUNT_UNIT,
        "prior_value": 1470897, "increase": 105310, "decrease": 252013,
        "current_value": 1324194, "report_type": "UNKNOWN", "report_type_label": None,
        "declared_totals_scope": PETI_ASSET_TOTALS_SCOPE}


def prepared(raw=None):
    governing = policy()
    source, snapshot, observation = build_peti_asset_capture(
        raw or receipt(), policy=governing, run_id=uuid4())
    person = Person(canonical_name="합성의원갑", identity_status=IdentityStatus.RESOLVED)
    review = IdentityReviewItem(observation_id=observation.id, candidate_person_id=person.id,
        reason_code="SYNTHETIC_SOURCE_CONTEXT", status=IdentityReviewStatus.RESOLVED,
        resolution_note="SYNTHETIC reviewed source-context linkage", resolved_at=datetime.now(UTC))
    link = PersonObservationLink(person_id=person.id, observation_id=observation.id,
        action=MaterializationAction.REVIEWED_LINK,
        decision_class=MaterializationDecisionClass.REVIEWED_SOURCE_CONTEXT,
        review_item_id=review.id)
    return governing, source, snapshot, observation, person, review, link


def claim_for(parts, *, published=False):
    governing, source, snapshot, observation, person, review, link = parts
    return build_peti_asset_total_claim(source, snapshot, observation, policy=governing,
        person=person, review=review, link=link, publication_approved=published)


def project(parts, claim, evidence, *, siblings=()):
    governing, source, snapshot, observation, person, _, link = parts
    return build_assembly_declared_assets_from_claims(person, [claim], {claim.id: [evidence]},
        observations={o.id: o for o in (observation, *siblings)},
        snapshots={snapshot.id: snapshot}, sources={source.id: source},
        policies={governing.id: governing}, links=[link])


def test_public_fact_metadata_needs_no_gazette_human_flag_or_media_license():
    parts = prepared()
    governing, source, snapshot, observation, _, _, _ = parts
    assert governing.license is None
    assert source.published_at is None  # route publication time is not the record's disclosure date
    assert snapshot.fulltext is None
    assert "review_status" not in snapshot.metadata
    assert observation.identity_hints == {}
    assert "canonical_name" not in observation.normalized
    claim, evidence = claim_for(parts)
    assert project(parts, claim, evidence) == []
    claim, evidence = claim_for(parts, published=True)
    row = project(parts, claim, evidence)[0]
    assert row["amount_thousand_krw"] == 1324194
    assert type(row["amount_thousand_krw"]) is int
    assert row["report_type"] == "UNKNOWN"
    assert row["declared_totals_scope"] == PETI_ASSET_TOTALS_SCOPE
    assert row["epistemic_status"] == "CLAIM" and row["asserted_as_true"] is False


@pytest.mark.parametrize("field", ["fulltext", "family", "address", "pdf", "session_url", "HUMAN_REVIEWED"])
def test_receipt_rejects_unapproved_fields_without_echoing_values(field):
    raw = receipt() | {field: "SYNTHETIC_PRIVATE_CANARY"}
    with pytest.raises(AssemblyAssetImportError) as error:
        normalize_peti_asset_receipt(raw, policy=policy())
    assert "SYNTHETIC_PRIVATE_CANARY" not in str(error.value)


@pytest.mark.parametrize("update", [
    {"amount_unit": "KRW"}, {"current_value": 0}, {"current_value": 1324194.0},
    {"increase": True}, {"prior_value": 2**53}, {"report_type": "정기"},
    {"report_type": []}, {"report_type_label": "정기"},
    {"registration_date": "2099-03-27"}, {"publication_date": "20990326"},
    {"column_headers": list(reversed(PETI_TOTAL_HEADERS))},
    {"detail_route": PETI_ASSET_DETAIL + "?session=SYNTHETIC_PRIVATE_CANARY"},
    {"declared_totals_scope": "PERSONAL_SELF_WEALTH"},
])
def test_source_unit_column_date_amount_and_unknown_semantics_fail_closed(update):
    with pytest.raises(AssemblyAssetImportError):
        normalize_peti_asset_receipt(receipt() | update, policy=policy())


@pytest.mark.parametrize("update", [
    {"can_store_metadata": False}, {"can_fetch": True}, {"can_store_fulltext": True},
    {"can_show_excerpt": True}, {"domain": "www.assembly.go.kr"},
])
def test_explicit_policy_is_first_and_never_opens_fetch(update):
    with pytest.raises(PolicyDenied):
        build_peti_asset_capture({}, policy=policy().model_copy(update=update), run_id=uuid4())


@pytest.mark.parametrize("part,update", [
    (4, {"identity_status": IdentityStatus.REVIEW}),
    (5, {"status": IdentityReviewStatus.OPEN}),
    (5, {"candidate_person_id": uuid4()}),
    (6, {"action": MaterializationAction.AUTO_LINK}),
    (6, {"review_item_id": None}),
])
def test_person_output_requires_supplied_exact_reviewed_link(part, update):
    parts = list(prepared())
    parts[part] = parts[part].model_copy(update=update)
    with pytest.raises(AssemblyAssetImportError):
        claim_for(parts)


def test_source_route_is_reused_across_records_without_a_second_raw_store():
    first = prepared()
    second = prepared(receipt() | {"printed_name": "합성의원을"})
    assert first[1].id == second[1].id
    assert first[3].provider_record_key != second[3].provider_record_key
    assert first[2].content_hash == first[3].content_hash
    assert first[2].metadata["receipt"] == first[3].normalized


@pytest.mark.parametrize("amount", [0, -12])
def test_printed_zero_or_signed_total_is_preserved_without_absence_inference(amount):
    parts = prepared(receipt() | {"prior_value": amount, "increase": 0,
        "decrease": 0, "current_value": amount})
    claim, evidence = claim_for(parts, published=True)
    assert project(parts, claim, evidence)[0]["amount_thousand_krw"] == amount


def test_unpublished_sibling_correction_blocks_current_published_total():
    parts = prepared()
    claim, evidence = claim_for(parts, published=True)
    correction = parts[3].model_copy(update={"id": uuid4(), "content_hash": "f" * 64})
    with pytest.raises(AssetSourceVersionConflict):
        project(parts, claim, evidence, siblings=[correction])


@pytest.mark.parametrize("part,update", [
    (1, {"policy_id": uuid4()}), (2, {"content_hash": "f" * 64}),
    (3, {"snapshot_id": uuid4()}), (3, {"identity_hints": {"canonical_name": "합성의원갑"}}),
])
def test_claim_builder_rejects_mismatched_immutable_provenance(part, update):
    parts = list(prepared())
    parts[part] = parts[part].model_copy(update=update)
    with pytest.raises(AssemblyAssetImportError):
        claim_for(parts)


def test_public_reader_rejects_claim_text_and_unknown_type_promotion():
    parts = prepared()
    claim, evidence = claim_for(parts, published=True)
    for invalid in (
        claim.model_copy(update={"proposition": "합성의원갑의 개인 순자산은 1천원이다."}),
        claim.model_copy(update={"qualifiers": claim.qualifiers | {"report_type": "정기"}}),
    ):
        with pytest.raises(ValueError):
            project(parts, invalid, evidence)


def test_publication_builder_rejects_wrong_record_scope_before_marking_published():
    parts = list(prepared())
    parts[3] = parts[3].model_copy(update={"scope_key": "peti:2099-03-27:selected-public-records"})
    with pytest.raises(AssemblyAssetImportError):
        claim_for(parts, published=True)
