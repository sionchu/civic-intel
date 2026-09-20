from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
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


GUKGAM_PUBLIC_TARGET_PROJECTION_SEMANTICS = "PUBLIC_CLAIM_BACKED_GUKGAM_AUDIT_TARGETS_V1"
GUKGAM_PUBLIC_TARGET_COVERAGE = "BOUNDED_INCOMPLETE_PUBLISHED_CLAIMS_ONLY"


@dataclass(frozen=True)
class GukgamAuditTargetProjectionItem:
    organization_id: UUID
    organization_name: str
    committee_name: str
    audit_date: str
    time_text: str | None
    venue: str | None
    section: str
    page_number: int
    source_published_date: str
    claim_id: UUID
    evidence_ids: tuple[UUID, ...]
    source_ids: tuple[UUID, ...]
    snapshot_ids: tuple[UUID, ...]
    observation_ids: tuple[UUID, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "organization": {
                "id": str(self.organization_id),
                "name": self.organization_name,
            },
            "committee_name": self.committee_name,
            "audit_date": self.audit_date,
            "time_text": self.time_text,
            "venue": self.venue,
            "section": self.section,
            "page_number": self.page_number,
            "source_published_date": self.source_published_date,
            "claim_id": str(self.claim_id),
            "evidence_ids": [str(item) for item in self.evidence_ids],
            "source_ids": [str(item) for item in self.source_ids],
            "snapshot_ids": [str(item) for item in self.snapshot_ids],
            "observation_ids": [str(item) for item in self.observation_ids],
        }


@dataclass(frozen=True)
class GukgamAuditTargetProjection:
    year: int
    items: tuple[GukgamAuditTargetProjectionItem, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "semantics": GUKGAM_PUBLIC_TARGET_PROJECTION_SEMANTICS,
            "coverage": GUKGAM_PUBLIC_TARGET_COVERAGE,
            "year": self.year,
            "target_count": len(self.items),
            "committee_count": len({item.committee_name for item in self.items}),
            "items": [item.to_dict() for item in self.items],
            "limitations": [
                "Only current published reviewed Gukgam Claims are included.",
                "Coverage is bounded and incomplete; absence is not evidence of no audit.",
                "Review observations and name-overlap candidates are never used as a public fallback.",
                "A listed target is a plan fact, not evidence that an audit occurred or established an outcome.",
            ],
        }


def _required_claim_qualifier(claim: Claim, key: str) -> str:
    value = claim.qualifiers.get(key)
    if not isinstance(value, str) or not value.strip():
        raise GukgamOrganizationClaimError(
            f"Gukgam public projection Claim qualifier is invalid: {key}"
        )
    return value.strip()


def build_gukgam_audit_target_projection(
    organizations: Sequence[Organization],
    contexts: Mapping[
        UUID,
        tuple[Sequence[Claim], Mapping[UUID, Sequence[ClaimEvidence]]],
    ],
    *,
    sources: Mapping[UUID, Source],
    policies: Mapping[UUID, SourcePolicy],
    year: int = 2026,
) -> GukgamAuditTargetProjection:
    """Project only publishable reviewed Gukgam Organization Claims."""

    organization_by_id = {
        organization.id: organization
        for organization in organizations
        if organization.superseded_at is None
    }
    items: list[GukgamAuditTargetProjectionItem] = []
    for organization_id, (claims, evidence_by_claim) in contexts.items():
        organization = organization_by_id.get(organization_id)
        if organization is None:
            continue
        for claim in claims:
            if claim.predicate != GUKGAM_AUDIT_TARGET_PREDICATE:
                continue
            if (
                claim.qualifiers.get("source_contract")
                != GUKGAM_REVIEWED_PLAN_SOURCE_CONTRACT
            ):
                raise GukgamOrganizationClaimError(
                    "Gukgam public projection Claim source contract is invalid"
                )

            evidence = list(evidence_by_claim.get(claim.id, ()))
            gate = validate_claim_publication(
                claim,
                organization,
                evidence,
                dict(sources),
                dict(policies),
            )
            if not gate.publishable:
                raise GukgamOrganizationClaimError(
                    f"Gukgam public projection Claim failed publication gate: {gate.failures}"
                )
            if not evidence:
                raise GukgamOrganizationClaimError(
                    "Gukgam public projection Claim lacks Evidence"
                )

            committee_name = _required_claim_qualifier(claim, "committee_name")
            audit_date = _required_claim_qualifier(claim, "audit_date")
            source_published_date = _required_claim_qualifier(
                claim, "source_published_date"
            )
            audited_target = _required_claim_qualifier(claim, "audited_target")
            section = _required_claim_qualifier(claim, "section")
            page_number_text = _required_claim_qualifier(claim, "page_number")
            if (
                _required_claim_qualifier(claim, "event_semantics")
                != "OFFICIAL_PLAN_LISTING_NOT_COMPLETED_AUDIT"
            ):
                raise GukgamOrganizationClaimError(
                    "Gukgam public projection event semantics changed"
                )
            if audited_target != organization.name:
                raise GukgamOrganizationClaimError(
                    "Gukgam public projection target does not match Organization"
                )
            try:
                audit_date_value = date.fromisoformat(audit_date)
                published_date_value = date.fromisoformat(source_published_date)
                page_number = int(page_number_text)
            except ValueError as exc:
                raise GukgamOrganizationClaimError(
                    "Gukgam public projection Claim date/page qualifier is invalid"
                ) from exc
            if (
                audit_date_value.year != year
                or published_date_value.year != year
                or page_number < 1
                or claim.valid_from.date() != published_date_value
            ):
                raise GukgamOrganizationClaimError(
                    "Gukgam public projection Claim year/valid-time semantics are invalid"
                )

            evidence_ids: list[UUID] = []
            source_ids: list[UUID] = []
            snapshot_ids: list[UUID] = []
            observation_ids: list[UUID] = []
            for evidence_item in evidence:
                source = sources.get(evidence_item.source_id)
                if source is None:
                    raise GukgamOrganizationClaimError(
                        "Gukgam public projection Evidence source is missing"
                    )
                policy = policies.get(source.policy_id)
                if (
                    policy is None
                    or policy.source_class != "official_reviewed_committee_attachment"
                ):
                    raise GukgamOrganizationClaimError(
                        "Gukgam public projection source policy is invalid"
                    )
                if (
                    evidence_item.snapshot_id is None
                    or evidence_item.feeder_observation_id is None
                    or evidence_item.excerpt is not None
                ):
                    raise GukgamOrganizationClaimError(
                        "Gukgam public projection Evidence provenance is incomplete"
                    )
                evidence_ids.append(evidence_item.id)
                source_ids.append(evidence_item.source_id)
                snapshot_ids.append(evidence_item.snapshot_id)
                observation_ids.append(evidence_item.feeder_observation_id)

            items.append(
                GukgamAuditTargetProjectionItem(
                    organization_id=organization.id,
                    organization_name=organization.name,
                    committee_name=committee_name,
                    audit_date=audit_date,
                    time_text=claim.qualifiers.get("time_text"),
                    venue=claim.qualifiers.get("venue"),
                    section=section,
                    page_number=page_number,
                    source_published_date=source_published_date,
                    claim_id=claim.id,
                    evidence_ids=tuple(sorted(set(evidence_ids), key=str)),
                    source_ids=tuple(sorted(set(source_ids), key=str)),
                    snapshot_ids=tuple(sorted(set(snapshot_ids), key=str)),
                    observation_ids=tuple(sorted(set(observation_ids), key=str)),
                )
            )

    return GukgamAuditTargetProjection(
        year=year,
        items=tuple(
            sorted(
                items,
                key=lambda item: (
                    item.audit_date,
                    item.committee_name,
                    item.organization_name,
                    str(item.claim_id),
                ),
            )
        ),
    )
