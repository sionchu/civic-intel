from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from packages.application.context import Application
from packages.domain.contracts import (
    Claim,
    ClaimEvidence,
    FeederObservation,
    Organization,
    Source,
    SourcePolicy,
    SourceSnapshot,
)
from packages.persistence import OrganizationClaimImportError
from packages.rendering.gukgam_organization_binding_review import (
    GukgamOrganizationBindingPreflight,
    build_gukgam_organization_binding_preflight,
)
from packages.rendering.gukgam_organization_claim import (
    GUKGAM_AUDIT_TARGET_PREDICATE,
    build_gukgam_audit_target_claim,
)
from packages.rendering.gukgam_schedule_review import load_current_gukgam_schedule_review
from packages.verification.gukgam_reviewed_plan_import import GUKGAM_REVIEWED_PLAN_FEEDER

Context = tuple[FeederObservation, SourceSnapshot, Source, SourcePolicy]


@dataclass(frozen=True)
class ReviewedGukgamClaimImport:
    organization: Organization
    preflight: GukgamOrganizationBindingPreflight
    observation: FeederObservation
    snapshot: SourceSnapshot
    source: Source
    policy: SourcePolicy
    claim: Claim
    evidence: ClaimEvidence
    existing_claim: Claim | None = None


def _current_context_for_preflight(
    repository: Application, preflight: GukgamOrganizationBindingPreflight
) -> Context:
    contexts = repository.acquisition.feeder_observation_contexts([preflight.observation_id])
    if set(contexts) != {preflight.observation_id}:
        raise ValueError(
            "Gukgam reviewed Claim import requires exact current observation provenance"
        )
    context = contexts[preflight.observation_id]
    observation = context[0]
    if (
        observation.feeder != GUKGAM_REVIEWED_PLAN_FEEDER
        or observation.provider_record_key != preflight.provider_record_key
    ):
        raise ValueError("Gukgam reviewed Claim import preflight observation identity changed")
    versions = repository.acquisition.feeder_observations(
        GUKGAM_REVIEWED_PLAN_FEEDER, observation.scope_key, observation.provider_record_key
    )
    if len({item.content_hash for item in versions}) > 1:
        raise ValueError(
            "Gukgam reviewed Claim import refuses multiple immutable observation versions"
        )
    if len(versions) != 1 or versions[0].id != observation.id:
        raise ValueError(
            "Gukgam reviewed Claim import requires one exact current observation version"
        )
    return context


def _claim_semantics(claim: Claim) -> dict[str, object]:
    return {
        "person_id": claim.person_id,
        "organization_id": claim.organization_id,
        "proposition": claim.proposition,
        "subject": claim.subject,
        "predicate": claim.predicate,
        "object_text": claim.object_text,
        "qualifiers": claim.qualifiers,
        "epistemic_status": claim.epistemic_status,
        "publication_status": claim.publication_status,
        "asserted_as_true": claim.asserted_as_true,
        "resolution_note": claim.resolution_note,
    }


def _evidence_semantics(evidence: ClaimEvidence) -> tuple[object, ...]:
    return (
        evidence.source_id,
        evidence.snapshot_id,
        evidence.feeder_observation_id,
        evidence.stance,
        evidence.excerpt,
    )


def _existing_exact_claim(
    repository: Application, prepared_claim: Claim, prepared_evidence: ClaimEvidence
) -> Claim | None:
    assert prepared_claim.organization_id is not None
    matching = [
        claim
        for claim in repository.public.claims(
            organization_id=prepared_claim.organization_id, current_only=True
        )
        if claim.predicate == prepared_claim.predicate
        and claim.qualifiers.get("source_contract")
        == prepared_claim.qualifiers.get("source_contract")
        and (
            claim.qualifiers.get("provider_record_key")
            == prepared_claim.qualifiers.get("provider_record_key")
        )
    ]
    if len(matching) > 1:
        raise OrganizationClaimImportError(
            "Gukgam reviewed Claim import found duplicate canonical source keys"
        )
    if not matching:
        return None
    stored = matching[0]
    evidence = repository.public.evidence_for(stored.id)
    if (
        _claim_semantics(stored) != _claim_semantics(prepared_claim)
        or len(evidence) != 1
        or _evidence_semantics(evidence[0]) != _evidence_semantics(prepared_evidence)
    ):
        raise OrganizationClaimImportError(
            "Gukgam reviewed Claim source key conflicts with stored semantics"
        )
    return stored


def prepare_reviewed_gukgam_claim_import(
    repository: Application, *, organization_id: UUID, review_key: str
) -> ReviewedGukgamClaimImport:
    """Preflight one explicit Gukgam Organization Claim without writing."""
    repository.uows.assert_ready()
    organization = repository.public.organization(organization_id)
    if organization is None or organization.superseded_at is not None:
        raise ValueError("Gukgam reviewed Claim import requires an existing current Organization")
    schedule = load_current_gukgam_schedule_review(repository.acquisition)
    preflight = build_gukgam_organization_binding_preflight(
        schedule,
        repository.public.organizations(current_only=True),
        review_key=review_key,
        organization_id=organization_id,
    )
    context = _current_context_for_preflight(repository, preflight)
    observation, snapshot, source, policy = context
    claim, evidence = build_gukgam_audit_target_claim(
        preflight,
        organization,
        observation=observation,
        snapshot=snapshot,
        source=source,
        policy=policy,
    )
    existing = _existing_exact_claim(repository, claim, evidence)
    return ReviewedGukgamClaimImport(
        organization=organization,
        preflight=preflight,
        observation=observation,
        snapshot=snapshot,
        source=source,
        policy=policy,
        claim=claim,
        evidence=evidence,
        existing_claim=existing,
    )


def _receipt(
    prepared: ReviewedGukgamClaimImport, *, status: str, stored_claim: Claim
) -> dict[str, object]:
    return {
        "status": status,
        "organization_id": str(prepared.organization.id),
        "organization_name": prepared.organization.name,
        "review_key": prepared.preflight.review_key,
        "predicate": GUKGAM_AUDIT_TARGET_PREDICATE,
        "committee_name": prepared.preflight.committee_name,
        "audit_date": prepared.preflight.audit_date,
        "audited_target": prepared.preflight.audited_target,
        "claim_id": str(stored_claim.id),
        "evidence_id": str(prepared.evidence.id),
        "observation_id": str(prepared.observation.id),
        "snapshot_id": str(prepared.snapshot.id),
        "source_id": str(prepared.source.id),
        "binding_committed": False,
        "organization_created": False,
        "claim_persisted": status in {"COMMITTED", "REUSED"},
        "claim_created": status == "COMMITTED",
        "network_fetch": False,
    }
