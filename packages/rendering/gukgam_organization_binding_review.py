from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from uuid import UUID

from packages.domain.contracts import Organization
from packages.rendering.gukgam_schedule_review import (
    GukgamScheduleReviewReport,
    GukgamScheduleReviewSource,
)

GUKGAM_ORGANIZATION_BINDING_REVIEW_SEMANTICS = (
    "REVIEW_ONLY_EXACT_CANONICAL_NAME_OVERLAP_DISCOVERY"
)
EXACT_ONE = "EXACT_CANONICAL_NAME_OVERLAP_DISCOVERY_ONLY"
NO_EXACT = "NO_EXACT_CANONICAL_NAME_OVERLAP"
EXACT_MULTIPLE = "MULTIPLE_EXACT_CANONICAL_NAME_OVERLAPS_REVIEW_REQUIRED"


@dataclass(frozen=True)
class OrganizationBindingCandidate:
    organization_id: UUID
    name: str

    def to_dict(self) -> dict[str, str]:
        return {
            "organization_id": str(self.organization_id),
            "name": self.name,
        }


@dataclass(frozen=True)
class GukgamOrganizationBindingReviewItem:
    review_key: str
    committee_name: str
    audit_date: str
    provider_record_key: str
    observation_id: UUID
    audited_target: str
    match_class: str
    candidates: tuple[OrganizationBindingCandidate, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "review_key": self.review_key,
            "committee_name": self.committee_name,
            "audit_date": self.audit_date,
            "provider_record_key": self.provider_record_key,
            "observation_id": str(self.observation_id),
            "audited_target": self.audited_target,
            "match_class": self.match_class,
            "candidates": [candidate.to_dict() for candidate in self.candidates],
        }


@dataclass(frozen=True)
class GukgamOrganizationBindingReviewReport:
    organization_universe_count: int
    items: tuple[GukgamOrganizationBindingReviewItem, ...]

    def to_dict(self) -> dict[str, object]:
        occurrence_counts = Counter(item.match_class for item in self.items)
        distinct: dict[str, GukgamOrganizationBindingReviewItem] = {}
        for item in self.items:
            prior = distinct.get(item.audited_target)
            if prior is None:
                distinct[item.audited_target] = item
                continue
            if (
                prior.match_class != item.match_class
                or prior.candidates != item.candidates
            ):
                raise ValueError(
                    "same audited target produced inconsistent Organization candidates"
                )
        distinct_counts = Counter(item.match_class for item in distinct.values())
        return {
            "semantics": GUKGAM_ORGANIZATION_BINDING_REVIEW_SEMANTICS,
            "match_rule": "EXACT_CANONICAL_NAME_EQUALITY_DISCOVERY_ONLY",
            "organization_universe_count": self.organization_universe_count,
            "mention_count": len(self.items),
            "distinct_target_count": len(distinct),
            "mention_match_classes": dict(sorted(occurrence_counts.items())),
            "distinct_match_classes": dict(sorted(distinct_counts.items())),
            "items": [item.to_dict() for item in self.items],
            "limitations": [
                "Exact name overlap is a discovery candidate only and never authorizes binding.",
                "No alias expansion, fuzzy similarity, score, rank, embedding, or organizational proximity is used.",
                "No Organization, Claim, ClaimEvidence, or identity link is created by this report.",
                "Targets without one exact current canonical-name overlap remain unresolved.",
            ],
        }


def build_gukgam_organization_binding_review(
    schedule: GukgamScheduleReviewReport,
    organizations: Sequence[Organization],
) -> GukgamOrganizationBindingReviewReport:
    current = [organization for organization in organizations if organization.superseded_at is None]
    by_name: dict[str, list[Organization]] = defaultdict(list)
    for organization in current:
        by_name[organization.name.strip()].append(organization)

    items: list[GukgamOrganizationBindingReviewItem] = []
    for committee in schedule.committees:
        for row in committee.rows:
            for target_index, target in enumerate(row.audited_targets, start=1):
                candidates = tuple(
                    OrganizationBindingCandidate(
                        organization_id=organization.id,
                        name=organization.name,
                    )
                    for organization in sorted(
                        by_name.get(target.strip(), ()),
                        key=lambda item: str(item.id),
                    )
                )
                match_class = (
                    NO_EXACT
                    if not candidates
                    else EXACT_ONE
                    if len(candidates) == 1
                    else EXACT_MULTIPLE
                )
                items.append(
                    GukgamOrganizationBindingReviewItem(
                        review_key=(
                            f"{row.provider_record_key}:audited-target:{target_index}"
                        ),
                        committee_name=committee.committee_name,
                        audit_date=row.audit_date,
                        provider_record_key=row.provider_record_key,
                        observation_id=row.observation_id,
                        audited_target=target,
                        match_class=match_class,
                        candidates=candidates,
                    )
                )

    return GukgamOrganizationBindingReviewReport(
        organization_universe_count=len(current),
        items=tuple(items),
    )


GUKGAM_ORGANIZATION_BINDING_PREFLIGHT_SEMANTICS = (
    "REVIEW_ONLY_OPERATOR_SUPPLIED_ORGANIZATION_BINDING_PREFLIGHT"
)


class GukgamOrganizationBindingPreflightError(ValueError):
    pass


@dataclass(frozen=True)
class GukgamOrganizationBindingPreflight:
    review_key: str
    committee_name: str
    audit_date: str
    provider_record_key: str
    observation_id: UUID
    audited_target: str
    organization: OrganizationBindingCandidate
    source: GukgamScheduleReviewSource

    def to_dict(self) -> dict[str, object]:
        return {
            "status": "DRY_RUN",
            "semantics": GUKGAM_ORGANIZATION_BINDING_PREFLIGHT_SEMANTICS,
            "candidate_relationship": "EXACT_CANONICAL_NAME_OVERLAP_REVERIFIED",
            "binding_committed": False,
            "claim_publication": False,
            "review_key": self.review_key,
            "occurrence": {
                "committee_name": self.committee_name,
                "audit_date": self.audit_date,
                "provider_record_key": self.provider_record_key,
                "observation_id": str(self.observation_id),
                "audited_target": self.audited_target,
            },
            "organization": self.organization.to_dict(),
            "provenance": self.source.to_dict(),
            "limitations": [
                "This receipt validates one current review candidate and performs no binding write.",
                "Exact canonical-name equality is necessary for this preflight but is not a public fact.",
                "Claim and ClaimEvidence publication require a separate explicitly approved slice.",
            ],
        }


def build_gukgam_organization_binding_preflight(
    schedule: GukgamScheduleReviewReport,
    organizations: Sequence[Organization],
    *,
    review_key: str,
    organization_id: UUID,
) -> GukgamOrganizationBindingPreflight:
    if not review_key.strip():
        raise GukgamOrganizationBindingPreflightError("review_key must be non-empty")

    report = build_gukgam_organization_binding_review(schedule, organizations)
    matches = [item for item in report.items if item.review_key == review_key]
    if len(matches) != 1:
        raise GukgamOrganizationBindingPreflightError(
            "review_key does not identify exactly one current audited-target occurrence"
        )
    item = matches[0]
    if item.match_class != EXACT_ONE or len(item.candidates) != 1:
        raise GukgamOrganizationBindingPreflightError(
            "review occurrence does not have exactly one current exact-name candidate"
        )
    candidate = item.candidates[0]
    if candidate.organization_id != organization_id:
        raise GukgamOrganizationBindingPreflightError(
            "operator-supplied Organization is not the current exact-name candidate"
        )

    current_organizations = {
        organization.id: organization
        for organization in organizations
        if organization.superseded_at is None
    }
    organization = current_organizations.get(organization_id)
    if organization is None or organization.name != candidate.name:
        raise GukgamOrganizationBindingPreflightError(
            "operator-supplied Organization is not current"
        )

    sources = []
    for committee in schedule.committees:
        if committee.committee_name != item.committee_name:
            continue
        for row in committee.rows:
            if (
                row.observation_id == item.observation_id
                and row.provider_record_key == item.provider_record_key
            ):
                sources.append(committee.source)
    if len(sources) != 1:
        raise GukgamOrganizationBindingPreflightError(
            "review occurrence provenance is not uniquely recoverable"
        )

    return GukgamOrganizationBindingPreflight(
        review_key=item.review_key,
        committee_name=item.committee_name,
        audit_date=item.audit_date,
        provider_record_key=item.provider_record_key,
        observation_id=item.observation_id,
        audited_target=item.audited_target,
        organization=candidate,
        source=sources[0],
    )
