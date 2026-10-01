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
from packages.rendering.money_projection import build_alio_head_expense_claim
from workers.alio_business_expense import (
    FEEDER,
    KNOWN_POSITIVE_INSTITUTION_CODES,
    SEMANTIC_SCOPE,
    alio_business_expense_scope_key,
)

BOUNDED_SCOPE_KEY = alio_business_expense_scope_key(KNOWN_POSITIVE_INSTITUTION_CODES)


@dataclass(frozen=True)
class ReviewedAlioClaimImport:
    organization: Organization
    institution_code: str
    fiscal_years: tuple[int, int]
    observations: tuple[FeederObservation, FeederObservation]
    claims: tuple[tuple[Claim, ClaimEvidence], tuple[Claim, ClaimEvidence]]


def _year(observation: FeederObservation) -> int:
    value = observation.normalized.get("fiscal_year")
    if not isinstance(value, int):
        raise TypeError("ALIO reviewed import observation has an invalid fiscal year")
    return value


def _preflight_observation_versions(
    observations: list[FeederObservation], selected: FeederObservation
) -> None:
    versions = [
        item for item in observations if item.provider_record_key == selected.provider_record_key
    ]
    if len({item.content_hash for item in versions}) > 1:
        raise ValueError(
            f"ALIO reviewed import refuses multiple immutable observation versions for {selected.provider_record_key}"
        )


def prepare_reviewed_import(
    repository: Application,
    *,
    organization_id: UUID,
    institution_code: str,
    earlier_fiscal_year: int,
    later_fiscal_year: int,
) -> ReviewedAlioClaimImport:
    """Preflight one explicit reviewed ALIO binding without writing to the database."""
    if institution_code not in KNOWN_POSITIVE_INSTITUTION_CODES:
        raise ValueError(
            "ALIO reviewed import requires one of the bounded known-positive institutions"
        )
    if earlier_fiscal_year >= later_fiscal_year:
        raise ValueError("ALIO reviewed import requires an earlier and a later fiscal year")
    repository.uows.assert_ready()
    organization = repository.public.organization(organization_id)
    if organization is None:
        raise ValueError("ALIO reviewed import requires an existing canonical Organization")
    if organization.superseded_at is not None:
        raise ValueError("ALIO reviewed import requires a current canonical Organization")
    observations = repository.acquisition.feeder_observations(FEEDER, BOUNDED_SCOPE_KEY)
    selected: list[FeederObservation] = []
    for fiscal_year in (earlier_fiscal_year, later_fiscal_year):
        matches = [
            item
            for item in observations
            if item.normalized.get("institution_code") == institution_code
            and item.semantic_scope == SEMANTIC_SCOPE
            and (_year(item) == fiscal_year)
        ]
        if len(matches) != 1:
            raise ValueError(
                f"ALIO reviewed import requires exactly one observation for {institution_code}/{fiscal_year}"
            )
        _preflight_observation_versions(observations, matches[0])
        selected.append(matches[0])
    snapshots: dict[UUID, SourceSnapshot] = {}
    for observation in selected:
        snapshot = repository.public.source_snapshot(observation.snapshot_id)
        if snapshot is None:
            raise ValueError(
                f"ALIO reviewed import is missing the snapshot for {observation.provider_record_key}"
            )
        snapshots[snapshot.id] = snapshot
    sources: dict[UUID, Source] = repository.public.sources(
        snapshot.source_id for snapshot in snapshots.values()
    )
    policies: dict[UUID, SourcePolicy] = repository.public.policies(
        source.policy_id for source in sources.values()
    )
    claim_pairs: list[tuple[Claim, ClaimEvidence]] = []
    for observation in selected:
        source = sources.get(snapshots[observation.snapshot_id].source_id)
        if source is None:
            raise ValueError(
                f"ALIO reviewed import is missing the source for {observation.provider_record_key}"
            )
        policy = policies.get(source.policy_id)
        if policy is None:
            raise ValueError(
                f"ALIO reviewed import is missing the SourcePolicy for {observation.provider_record_key}"
            )
        claim_pairs.append(
            build_alio_head_expense_claim(
                observation,
                organization=organization,
                policy=policy,
                snapshots=snapshots,
                sources=sources,
            )
        )
    return ReviewedAlioClaimImport(
        organization=organization,
        institution_code=institution_code,
        fiscal_years=(earlier_fiscal_year, later_fiscal_year),
        observations=(selected[0], selected[1]),
        claims=(claim_pairs[0], claim_pairs[1]),
    )
