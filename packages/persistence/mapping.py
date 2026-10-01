from __future__ import annotations

from packages.domain.contracts import (
    Claim,
    ClaimEvidence,
    FeederObservation,
    IdentityReviewItem,
    Organization,
    Person,
    PersonObservationLink,
    Source,
    SourceCheckpoint,
    SourcePolicy,
    SourceRun,
    SourceSnapshot,
)
from packages.persistence.models import (
    ClaimEvidenceRow,
    ClaimRow,
    FeederObservationRow,
    IdentityReviewItemRow,
    OrganizationRow,
    PersonObservationLinkRow,
    PersonRow,
    SourceCheckpointRow,
    SourcePolicyRow,
    SourceRow,
    SourceRunRow,
    SourceSnapshotRow,
)


def _source_run(row: SourceRunRow) -> SourceRun:
    return SourceRun.model_validate(
        {
            "id": row.id,
            "feeder": row.feeder,
            "scope_key": row.scope_key,
            "started_at": row.started_at,
            "finished_at": row.finished_at,
            "status": row.status,
            "checkpoint_before": row.checkpoint_before,
            "checkpoint_after": row.checkpoint_after,
            "records_seen": row.records_seen,
            "observations_created": row.observations_created,
            "observations_unchanged": row.observations_unchanged,
            "error_code": row.error_code,
            "error_summary": row.error_summary,
            "metadata": row.metadata_json,
        }
    )


def _checkpoint(row: SourceCheckpointRow) -> SourceCheckpoint:
    return SourceCheckpoint.model_validate(
        {
            "id": row.id,
            "feeder": row.feeder,
            "scope_key": row.scope_key,
            "cursor": row.cursor,
            "metadata": row.metadata_json,
            "updated_at": row.updated_at,
            "last_run_id": row.last_run_id,
        }
    )


def _observation(row: FeederObservationRow) -> FeederObservation:
    return FeederObservation.model_validate(
        {
            "id": row.id,
            "feeder": row.feeder,
            "scope_key": row.scope_key,
            "provider_record_key": row.provider_record_key,
            "snapshot_id": row.snapshot_id,
            "run_id": row.run_id,
            "recorded_at": row.recorded_at,
            "provider_observed_at": row.provider_observed_at,
            "semantic_scope": row.semantic_scope,
            "identity_hints": row.identity_hints_json,
            "normalized": row.normalized_json,
            "content_hash": row.content_hash,
        }
    )


def _person_observation_link(row: PersonObservationLinkRow) -> PersonObservationLink:
    return PersonObservationLink.model_validate(row)


def _identity_review_item(row: IdentityReviewItemRow) -> IdentityReviewItem:
    return IdentityReviewItem.model_validate(
        {
            "id": row.id,
            "observation_id": row.observation_id,
            "candidate_person_id": row.candidate_person_id,
            "reason_code": row.reason_code,
            "details": row.details_json,
            "status": row.status,
            "created_at": row.created_at,
            "resolved_at": row.resolved_at,
            "resolution_note": row.resolution_note,
        }
    )


def _temporal(contract) -> dict:
    return {
        "valid_from": contract.valid_from,
        "valid_to": contract.valid_to,
        "recorded_at": contract.recorded_at,
        "superseded_at": contract.superseded_at,
    }


def _person(row: PersonRow) -> Person:
    return Person.model_validate(row)


def _organization(row: OrganizationRow) -> Organization:
    return Organization.model_validate(row)


def _claim(row: ClaimRow) -> Claim:
    return Claim.model_validate(row)


def _evidence(row: ClaimEvidenceRow) -> ClaimEvidence:
    return ClaimEvidence.model_validate(row)


def _source(row: SourceRow) -> Source:
    return Source.model_validate(row)


def _policy(row: SourcePolicyRow) -> SourcePolicy:
    return SourcePolicy.model_validate(row)


def _snapshot(row: SourceSnapshotRow) -> SourceSnapshot:
    return SourceSnapshot.model_validate(
        {
            "id": row.id,
            "source_id": row.source_id,
            "fetched_at": row.fetched_at,
            "content_hash": row.content_hash,
            "metadata": row.metadata_json,
            "fulltext": row.fulltext,
        }
    )
