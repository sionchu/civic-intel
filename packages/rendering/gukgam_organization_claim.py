from __future__ import annotations

from datetime import UTC, date, datetime, time
from uuid import UUID, uuid5

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
from packages.rendering.gukgam_organization_binding_review import (
    GukgamOrganizationBindingPreflight,
    parse_gukgam_review_key,
)
from packages.rendering.gukgam_schedule_review import build_gukgam_schedule_review
from packages.verification.claims import validate_claim_publication
from packages.verification.gukgam_reviewed_plan_import import (
    GUKGAM_REVIEWED_PLAN_SOURCE_CONTRACT,
)

GUKGAM_AUDIT_TARGET_PREDICATE = "LISTED_AS_GUKGAM_AUDIT_TARGET"
GUKGAM_AUDIT_TARGET_CLAIM_NAMESPACE = UUID("bfa45c99-9fcf-447e-99e8-49d1713ce0a5")


class GukgamOrganizationClaimError(ValueError):
    pass


def _claim_id(
    organization: Organization,
    review_key: str,
    observation: FeederObservation,
) -> UUID:
    return uuid5(
        GUKGAM_AUDIT_TARGET_CLAIM_NAMESPACE,
        "|".join(
            (
                str(organization.id),
                GUKGAM_AUDIT_TARGET_PREDICATE,
                GUKGAM_REVIEWED_PLAN_SOURCE_CONTRACT,
                review_key,
                observation.content_hash,
            )
        ),
    )


def _evidence_id(
    claim_id: UUID,
    source: Source,
    observation: FeederObservation,
) -> UUID:
    return uuid5(
        claim_id,
        "|".join(
            (
                str(source.id),
                str(observation.snapshot_id),
                str(observation.id),
                EvidenceStance.SUPPORT.value,
            )
        ),
    )


def build_gukgam_audit_target_claim(
    preflight: GukgamOrganizationBindingPreflight,
    organization: Organization,
    *,
    observation: FeederObservation,
    snapshot: SourceSnapshot,
    source: Source,
    policy: SourcePolicy,
) -> tuple[Claim, ClaimEvidence]:
    """Build one reviewed Organization Claim for one exact Gukgam target occurrence."""

    if organization.superseded_at is not None:
        raise GukgamOrganizationClaimError("Gukgam Claim requires a current Organization")
    if (
        preflight.organization.organization_id != organization.id
        or preflight.organization.name != organization.name
        or preflight.audited_target != organization.name
    ):
        raise GukgamOrganizationClaimError(
            "Gukgam preflight does not match the supplied Organization"
        )

    try:
        provider_record_key, target_index = parse_gukgam_review_key(preflight.review_key)
    except ValueError as exc:
        raise GukgamOrganizationClaimError("Gukgam review_key is invalid") from exc
    if (
        observation.id != preflight.observation_id
        or observation.provider_record_key != provider_record_key
    ):
        raise GukgamOrganizationClaimError(
            "Gukgam preflight does not match the selected observation"
        )

    schedule = build_gukgam_schedule_review(
        [(observation, snapshot, source, policy)]
    )
    if len(schedule.committees) != 1 or len(schedule.committees[0].rows) != 1:
        raise GukgamOrganizationClaimError(
            "Gukgam Claim requires exactly one reviewed schedule row"
        )
    committee = schedule.committees[0]
    row = committee.rows[0]
    if (
        committee.committee_name != preflight.committee_name
        or row.audit_date != preflight.audit_date
        or row.provider_record_key != preflight.provider_record_key
        or row.observation_id != preflight.observation_id
    ):
        raise GukgamOrganizationClaimError(
            "Gukgam preflight schedule semantics changed"
        )
    if target_index > len(row.audited_targets):
        raise GukgamOrganizationClaimError(
            "Gukgam review_key target index is outside the reviewed row"
        )
    if row.audited_targets[target_index - 1] != preflight.audited_target:
        raise GukgamOrganizationClaimError(
            "Gukgam review_key does not identify the preflight audited target"
        )
    if (
        preflight.source.source_id != source.id
        or preflight.source.snapshot_id != snapshot.id
        or preflight.source.url != str(source.url)
        or preflight.source.attachment_sha256 != snapshot.content_hash
    ):
        raise GukgamOrganizationClaimError(
            "Gukgam preflight provenance changed before Claim build"
        )

    qualifiers = {
        "source_contract": GUKGAM_REVIEWED_PLAN_SOURCE_CONTRACT,
        "source_scope": observation.scope_key,
        "semantic_scope": observation.semantic_scope,
        "provider_record_key": preflight.review_key,
        "observation_provider_record_key": observation.provider_record_key,
        "immutable_observation_hash": observation.content_hash,
        "committee_name": committee.committee_name,
        "source_published_date": committee.source_published_date,
        "audit_date": row.audit_date,
        "audited_target": preflight.audited_target,
        "audited_target_index": str(target_index),
        "section": row.section,
        "page_number": str(row.page_number),
        "event_semantics": "OFFICIAL_PLAN_LISTING_NOT_COMPLETED_AUDIT",
    }
    if row.time_text is not None:
        qualifiers["time_text"] = row.time_text
    if row.venue is not None:
        qualifiers["venue"] = row.venue

    valid_from = datetime.combine(
        date.fromisoformat(committee.source_published_date),
        time.min,
        tzinfo=UTC,
    )
    claim = Claim(
        id=_claim_id(organization, preflight.review_key, observation),
        organization_id=organization.id,
        proposition=(
            f"{organization.name}는 {committee.committee_name} 2026년도 국정감사계획서의 "
            f"{row.audit_date} 감사일정에서 피감대상으로 기재되어 있다."
        ),
        subject=organization.name,
        predicate=GUKGAM_AUDIT_TARGET_PREDICATE,
        object_text=f"{committee.committee_name} · {row.audit_date} 피감대상",
        qualifiers=qualifiers,
        epistemic_status=EpistemicStatus.FACT,
        publication_status=PublicationStatus.PUBLISHED,
        asserted_as_true=True,
        valid_from=valid_from,
        recorded_at=observation.recorded_at,
    )
    evidence = ClaimEvidence(
        id=_evidence_id(claim.id, source, observation),
        claim_id=claim.id,
        source_id=source.id,
        snapshot_id=snapshot.id,
        feeder_observation_id=observation.id,
        stance=EvidenceStance.SUPPORT,
        excerpt=None,
    )
    gate = validate_claim_publication(
        claim,
        organization,
        [evidence],
        {source.id: source},
        {policy.id: policy},
    )
    if not gate.publishable:
        raise GukgamOrganizationClaimError(
            f"Gukgam Claim failed publication gate: {gate.failures}"
        )
    return claim, evidence
