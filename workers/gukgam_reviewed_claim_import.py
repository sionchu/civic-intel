from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from uuid import UUID

from packages.domain.contracts import (
    Claim,
    ClaimEvidence,
    FeederObservation,
    Organization,
    Source,
    SourcePolicy,
    SourceSnapshot,
)
from packages.persistence import OrganizationClaimImportError, SqlAlchemyRepository
from packages.rendering.gukgam_organization_binding_review import (
    GukgamOrganizationBindingPreflight,
    GukgamOrganizationBindingPreflightError,
    build_gukgam_organization_binding_preflight,
    parse_gukgam_review_key,
)
from packages.rendering.gukgam_organization_claim import (
    GUKGAM_AUDIT_TARGET_PREDICATE,
    GukgamOrganizationClaimError,
    build_gukgam_audit_target_claim,
)
from packages.rendering.gukgam_schedule_review import build_gukgam_schedule_review
from packages.verification.gukgam_reviewed_plan_import import (
    GUKGAM_REVIEWED_PLAN_FEEDER,
)

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


def _current_context_for_review_key(
    repository: SqlAlchemyRepository,
    review_key: str,
) -> Context:
    try:
        provider_record_key, _ = parse_gukgam_review_key(review_key)
    except ValueError as exc:
        raise ValueError("Gukgam reviewed Claim import review_key is invalid") from exc

    matches: list[Context] = []
    for checkpoint in repository.source_checkpoints(GUKGAM_REVIEWED_PLAN_FEEDER):
        if not checkpoint.scope_key.startswith("2026:"):
            continue
        attachment_hash = checkpoint.metadata.get("attachment_sha256")
        expected_rows = checkpoint.metadata.get("schedule_row_count")
        if not isinstance(attachment_hash, str) or not isinstance(expected_rows, int):
            raise TypeError("Gukgam reviewed Claim checkpoint metadata is incomplete")

        observations = repository.feeder_observations(
            GUKGAM_REVIEWED_PLAN_FEEDER,
            checkpoint.scope_key,
            provider_record_key,
        )
        if not observations:
            continue
        if len({item.content_hash for item in observations}) > 1:
            raise ValueError(
                "Gukgam reviewed Claim import refuses multiple immutable observation versions"
            )
        contexts = repository.feeder_observation_contexts(item.id for item in observations)
        current = [
            contexts[item.id]
            for item in observations
            if item.id in contexts and contexts[item.id][1].content_hash == attachment_hash
        ]
        if len(current) != 1:
            raise ValueError(
                "Gukgam reviewed Claim import requires one current observation version"
            )
        matches.extend(current)

    if len(matches) != 1:
        raise ValueError(
            "Gukgam reviewed Claim import review_key does not resolve to one current observation"
        )
    return matches[0]


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
    repository: SqlAlchemyRepository,
    prepared_claim: Claim,
    prepared_evidence: ClaimEvidence,
) -> Claim | None:
    assert prepared_claim.organization_id is not None
    matching = [
        claim
        for claim in repository.claims(
            organization_id=prepared_claim.organization_id,
            current_only=True,
        )
        if claim.predicate == prepared_claim.predicate
        and claim.qualifiers.get("source_contract")
        == prepared_claim.qualifiers.get("source_contract")
        and claim.qualifiers.get("provider_record_key")
        == prepared_claim.qualifiers.get("provider_record_key")
    ]
    if len(matching) > 1:
        raise OrganizationClaimImportError(
            "Gukgam reviewed Claim import found duplicate canonical source keys"
        )
    if not matching:
        return None

    stored = matching[0]
    evidence = repository.evidence_for(stored.id)
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
    repository: SqlAlchemyRepository,
    *,
    organization_id: UUID,
    review_key: str,
) -> ReviewedGukgamClaimImport:
    """Preflight one explicit Gukgam Organization Claim without writing."""

    repository.assert_ready()
    organization = repository.organization(organization_id)
    if organization is None or organization.superseded_at is not None:
        raise ValueError(
            "Gukgam reviewed Claim import requires an existing current Organization"
        )

    context = _current_context_for_review_key(repository, review_key)
    observation, snapshot, source, policy = context
    schedule = build_gukgam_schedule_review([context])
    preflight = build_gukgam_organization_binding_preflight(
        schedule,
        repository.organizations(current_only=True),
        review_key=review_key,
        organization_id=organization_id,
    )
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
    prepared: ReviewedGukgamClaimImport,
    *,
    status: str,
    stored_claim: Claim,
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Import one explicitly reviewed Gukgam audit-target Claim for an existing Organization."
        )
    )
    parser.add_argument("--organization-id", required=True, type=UUID)
    parser.add_argument("--review-key", required=True)
    parser.add_argument("--database-url")
    parser.add_argument(
        "--commit",
        action="store_true",
        help="Persist the preflighted Claim/Evidence; without this flag the command is a dry run.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    repository = SqlAlchemyRepository(args.database_url)
    try:
        prepared = prepare_reviewed_gukgam_claim_import(
            repository,
            organization_id=args.organization_id,
            review_key=args.review_key,
        )
        if not args.commit:
            status = "DRY_RUN"
            stored_claim = prepared.claim
        elif prepared.existing_claim is not None:
            status = "REUSED"
            stored_claim = prepared.existing_claim
        else:
            try:
                stored_claim = repository.import_organization_claim(
                    prepared.organization,
                    prepared.claim,
                    [prepared.evidence],
                )
                status = "COMMITTED"
            except OrganizationClaimImportError:
                stored = _existing_exact_claim(
                    repository,
                    prepared.claim,
                    prepared.evidence,
                )
                if stored is None:
                    raise
                stored_claim = stored
                status = "REUSED"
    except (
        GukgamOrganizationBindingPreflightError,
        GukgamOrganizationClaimError,
        OrganizationClaimImportError,
        TypeError,
        ValueError,
    ) as exc:
        parser.error(str(exc))

    print(
        json.dumps(
            _receipt(prepared, status=status, stored_claim=stored_claim),
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
