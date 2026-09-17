from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any
from urllib.parse import parse_qs, urlparse
from uuid import UUID, uuid5

from packages.connectors.alio_disclosures import (
    POLICY_ID,
    AlioExecutiveDisclosureConnector,
)
from packages.domain.contracts import (
    Claim,
    ClaimEvidence,
    FeederObservation,
    Organization,
    Source,
    SourcePolicy,
    SourceSnapshot,
)
from packages.domain.enums import EpistemicStatus, EvidenceStance, PublicationStatus
from packages.verification.claims import validate_claim_publication
from packages.verification.policy import PolicyAction, PolicyDenied, require_policy

ALIO_EXECUTIVE_FEEDER = "alio_public_institution_executives"
ALIO_EXECUTIVE_SCOPE = "item_4_current_all_institutions"
ALIO_EXECUTIVE_SEMANTIC_SCOPE = "public_institution_executive_disclosure"
ALIO_EXECUTIVE_SOURCE_CONTRACT = "alio_item_4_current_executive_roster"
ALIO_EXECUTIVE_PREDICATE = "ALIO_CURRENT_EXECUTIVE_DISCLOSURE"
ALIO_CLASSIFICATION_PREDICATE = "ALIO_INSTITUTION_CLASSIFICATION"
ALIO_ORGANIZATION_NAMESPACE = UUID("b2a88d7e-02fd-4ad1-a2ec-4ee42b2ed3f4")
ALIO_CLAIM_NAMESPACE = UUID("dba4f4f7-94ee-4ad1-9258-5df9fd6ae8bc")


class AlioOrganizationContentError(ValueError):
    pass


def organization_id_for_alio_apba_id(apba_id: str) -> UUID:
    normalized = _required_text(apba_id, "alio_apba_id")
    return uuid5(ALIO_ORGANIZATION_NAMESPACE, normalized)


def _required_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise AlioOrganizationContentError(f"ALIO organization field is missing: {field}")
    return value.strip()


def _optional_text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _date_text(value: Any, field: str) -> str:
    text = _required_text(value, field)
    try:
        datetime.fromisoformat(text).date()
    except ValueError:
        raise AlioOrganizationContentError(f"ALIO organization date is invalid: {field}") from None
    return text


def _valid_source_url(source: Source, disclosure_no: str, institution_code: str) -> None:
    parsed = urlparse(str(source.url))
    if (
        parsed.scheme != "https"
        or parsed.netloc != AlioExecutiveDisclosureConnector.HOST
        or parsed.path != AlioExecutiveDisclosureConnector.REPORT_PATH
    ):
        raise AlioOrganizationContentError("ALIO executive Source URL is outside item-4 contract")
    query = parse_qs(parsed.query, keep_blank_values=True)
    if set(query) != {"seq", "disclosureNo"} or any(len(values) != 1 for values in query.values()):
        raise AlioOrganizationContentError("ALIO executive Source URL has an invalid query")
    if query["seq"][0] != disclosure_no or query["disclosureNo"][0] != disclosure_no:
        raise AlioOrganizationContentError("ALIO executive Source disclosure identity is inconsistent")
    if not institution_code.isalnum() or not disclosure_no.isdigit():
        raise AlioOrganizationContentError("ALIO executive source identity is invalid")


def validate_alio_item4_observation(
    observation: FeederObservation,
    *,
    snapshot: SourceSnapshot,
    source: Source,
    policy: SourcePolicy,
) -> dict[str, str]:
    """Validate the persisted item-4 contract and return only safe scalar fields."""

    if observation.feeder != ALIO_EXECUTIVE_FEEDER:
        raise AlioOrganizationContentError("observation is outside the ALIO item-4 feeder")
    if observation.scope_key != ALIO_EXECUTIVE_SCOPE:
        raise AlioOrganizationContentError("observation is outside the ALIO item-4 scope")
    if observation.semantic_scope != ALIO_EXECUTIVE_SEMANTIC_SCOPE:
        raise AlioOrganizationContentError("observation is outside the ALIO item-4 semantic scope")
    if snapshot.id != observation.snapshot_id or snapshot.source_id != source.id:
        raise AlioOrganizationContentError("ALIO executive observation provenance is inconsistent")
    if source.policy_id != policy.id or policy.id != POLICY_ID or policy.domain != "alio.go.kr":
        raise AlioOrganizationContentError("ALIO executive SourcePolicy provenance is inconsistent")
    try:
        require_policy(policy, PolicyAction.STORE_METADATA)
    except PolicyDenied as exc:
        raise AlioOrganizationContentError("ALIO executive SourcePolicy forbids metadata storage") from exc
    if snapshot.fulltext is not None:
        raise AlioOrganizationContentError("ALIO executive snapshot must not retain fulltext")
    metadata = snapshot.metadata
    if (
        metadata.get("source_contract") != "alio_item_4_executive_report"
        or metadata.get("report_form_no") != AlioExecutiveDisclosureConnector.REPORT_FORM_NO
        or not isinstance(metadata.get("document_path"), str)
        or not metadata["document_path"].startswith("/upload/disclosure/")
    ):
        raise AlioOrganizationContentError("ALIO executive snapshot is outside item-4 contract")

    normalized = observation.normalized
    institution_code = _required_text(normalized.get("institution_code"), "institution_code")
    institution_name = _required_text(normalized.get("institution_name"), "institution_name")
    disclosure_no = _required_text(normalized.get("disclosure_no"), "disclosure_no")
    classification = _required_text(normalized.get("classification"), "classification")
    classification_text = _required_text(
        normalized.get("classification_text"), "classification_text"
    )
    name_status = _required_text(normalized.get("name_status"), "name_status")
    executive_row_key = _required_text(normalized.get("executive_row_key"), "executive_row_key")
    if metadata.get("institution_code") != institution_code or metadata.get("disclosure_no") != disclosure_no:
        raise AlioOrganizationContentError("ALIO executive snapshot institution identity is inconsistent")
    if observation.provider_record_key != executive_row_key:
        raise AlioOrganizationContentError("ALIO executive provider row key is inconsistent")
    if not disclosure_no.isdigit() or ":" not in executive_row_key:
        raise AlioOrganizationContentError("ALIO executive provider row key is invalid")
    _valid_source_url(source, disclosure_no, institution_code)
    _date_text(normalized.get("as_of"), "as_of")
    if name_status not in {"PUBLIC", "MASKED_OR_VACANT", "NOT_PUBLISHED"}:
        raise AlioOrganizationContentError("ALIO executive name status is unsupported")
    if name_status == "PUBLIC":
        _required_text(normalized.get("canonical_name"), "canonical_name")
        _required_text(normalized.get("position_text"), "position_text")
        _required_text(normalized.get("executive_kind"), "executive_kind")
    elif normalized.get("canonical_name") is not None:
        raise AlioOrganizationContentError("ALIO non-public executive row contains a name")

    return {
        "alio_apba_id": institution_code,
        "institution_name": institution_name,
        "classification": classification,
        "classification_text": classification_text,
        "disclosure_no": disclosure_no,
        "executive_row_key": executive_row_key,
        "name_status": name_status,
        "canonical_name": _optional_text(normalized.get("canonical_name")),
        "position_text": _optional_text(normalized.get("position_text")),
        "executive_kind": _optional_text(normalized.get("executive_kind")),
        "title": _optional_text(normalized.get("title")),
        "term_start": _optional_text(normalized.get("term_start")),
        "term_end": _optional_text(normalized.get("term_end")),
        "as_of": _required_text(normalized.get("as_of"), "as_of"),
    }


def _claim_qualifiers(fields: Mapping[str, str], observation: FeederObservation) -> dict[str, str]:
    return {
        "alio_apba_id": fields["alio_apba_id"],
        "source_contract": ALIO_EXECUTIVE_SOURCE_CONTRACT,
        "source_scope": observation.scope_key,
        "semantic_scope": observation.semantic_scope,
        "provider_record_key": observation.provider_record_key,
        "immutable_observation_hash": observation.content_hash,
        "disclosure_no": fields["disclosure_no"],
        "executive_kind": fields["executive_kind"],
        "position_text": fields["position_text"],
        "canonical_name": fields["canonical_name"],
        "title": fields["title"],
        "term_start": fields["term_start"],
        "term_end": fields["term_end"],
        "as_of": fields["as_of"],
        "classification": fields["classification"],
        "classification_text": fields["classification_text"],
    }


def _claim_id(organization: Organization, predicate: str, observation: FeederObservation) -> UUID:
    return uuid5(
        ALIO_CLAIM_NAMESPACE,
        "|".join(
            (
                str(organization.id),
                predicate,
                ALIO_EXECUTIVE_SOURCE_CONTRACT,
                observation.provider_record_key,
                observation.content_hash,
            )
        ),
    )


def _evidence(claim: Claim, source: Source, observation: FeederObservation) -> ClaimEvidence:
    return ClaimEvidence(
        id=uuid5(
            claim.id,
            "|".join(
                (
                    str(source.id),
                    str(observation.snapshot_id),
                    str(observation.id),
                    EvidenceStance.SUPPORT.value,
                )
            ),
        ),
        claim_id=claim.id,
        source_id=source.id,
        snapshot_id=observation.snapshot_id,
        feeder_observation_id=observation.id,
        stance=EvidenceStance.SUPPORT,
    )


def build_alio_executive_claim(
    organization: Organization,
    observation: FeederObservation,
    *,
    source: Source,
    snapshot: SourceSnapshot,
    policy: SourcePolicy,
) -> tuple[Claim, ClaimEvidence]:
    fields = validate_alio_item4_observation(
        observation,
        snapshot=snapshot,
        source=source,
        policy=policy,
    )
    if fields["name_status"] != "PUBLIC":
        raise AlioOrganizationContentError("non-public ALIO executive row cannot create a named claim")
    if organization.name != fields["institution_name"]:
        raise AlioOrganizationContentError("Organization name does not match ALIO institution")
    claim = Claim(
        id=_claim_id(organization, ALIO_EXECUTIVE_PREDICATE, observation),
        organization_id=organization.id,
        proposition=(
            f"{organization.name}는 ALIO 임원현황에서 {fields['position_text']} 직위의 "
            f"{fields['canonical_name']}을 공개한다."
        ),
        subject=organization.name,
        predicate=ALIO_EXECUTIVE_PREDICATE,
        object_text=f"{fields['position_text']} · {fields['canonical_name']}",
        qualifiers=_claim_qualifiers(fields, observation),
        epistemic_status=EpistemicStatus.FACT,
        publication_status=PublicationStatus.PUBLISHED,
        asserted_as_true=True,
        valid_from=_observation_time(observation),
        recorded_at=observation.recorded_at,
    )
    evidence = _evidence(claim, source, observation)
    gate = validate_claim_publication(claim, organization, [evidence], {source.id: source}, {policy.id: policy})
    if not gate.publishable:
        raise AlioOrganizationContentError(f"ALIO executive Claim failed publication gate: {gate.failures}")
    return claim, evidence


def build_alio_classification_claim(
    organization: Organization,
    observation: FeederObservation,
    *,
    source: Source,
    snapshot: SourceSnapshot,
    policy: SourcePolicy,
) -> tuple[Claim, ClaimEvidence]:
    fields = validate_alio_item4_observation(
        observation,
        snapshot=snapshot,
        source=source,
        policy=policy,
    )
    if organization.name != fields["institution_name"]:
        raise AlioOrganizationContentError("Organization name does not match ALIO institution")
    claim = Claim(
        id=_claim_id(organization, ALIO_CLASSIFICATION_PREDICATE, observation),
        organization_id=organization.id,
        proposition=(
            f"{organization.name}은 ALIO 기관분류에서 {fields['classification_text']}으로 분류된다."
        ),
        subject=organization.name,
        predicate=ALIO_CLASSIFICATION_PREDICATE,
        object_text=fields["classification_text"],
        qualifiers={
            "alio_apba_id": fields["alio_apba_id"],
            "source_contract": ALIO_EXECUTIVE_SOURCE_CONTRACT,
            "source_scope": observation.scope_key,
            "semantic_scope": observation.semantic_scope,
            "provider_record_key": observation.provider_record_key,
            "immutable_observation_hash": observation.content_hash,
            "classification": fields["classification"],
            "classification_text": fields["classification_text"],
            "disclosure_no": fields["disclosure_no"],
            "as_of": fields["as_of"],
        },
        epistemic_status=EpistemicStatus.FACT,
        publication_status=PublicationStatus.PUBLISHED,
        asserted_as_true=True,
        valid_from=_observation_time(observation),
        recorded_at=observation.recorded_at,
    )
    evidence = _evidence(claim, source, observation)
    gate = validate_claim_publication(claim, organization, [evidence], {source.id: source}, {policy.id: policy})
    if not gate.publishable:
        raise AlioOrganizationContentError(
            f"ALIO classification Claim failed publication gate: {gate.failures}"
        )
    return claim, evidence


def _observation_time(observation: FeederObservation) -> datetime:
    if observation.provider_observed_at is not None:
        return observation.provider_observed_at
    return observation.recorded_at.astimezone(UTC)
