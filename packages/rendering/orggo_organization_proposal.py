from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from urllib.parse import urlencode
from uuid import UUID

from packages.connectors.orggo_top_level_organizations import (
    OrgGoTopLevelOrganizationConnector,
    OrgGoTopLevelOrganizationRecord,
)
from packages.domain.contracts import Organization
from packages.rendering.gukgam_organization_binding_review import (
    NO_EXACT,
    GukgamOrganizationBindingReviewReport,
)

ORGGO_ORGANIZATION_PROPOSAL_SEMANTICS = "REVIEW_ONLY_ORGGO_ORGANIZATION_PROPOSAL_V1"


class OrgGoOrganizationProposalError(ValueError):
    pass


@dataclass(frozen=True)
class OrgGoGukgamOccurrenceRef:
    review_key: str
    committee_name: str
    audit_date: str
    provider_record_key: str
    observation_id: UUID
    audited_target: str

    def to_dict(self) -> dict[str, str]:
        return {
            "review_key": self.review_key,
            "committee_name": self.committee_name,
            "audit_date": self.audit_date,
            "provider_record_key": self.provider_record_key,
            "observation_id": str(self.observation_id),
            "audited_target": self.audited_target,
        }


@dataclass(frozen=True)
class OrgGoOrganizationProposalItem:
    organization_name: str
    category: str
    org_code: str
    chart_id: str
    source_locator: str
    occurrences: tuple[OrgGoGukgamOccurrenceRef, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "proposal_status": "REVIEW_REQUIRED_NO_WRITE",
            "organization_name": self.organization_name,
            "provider": {
                "org_code": self.org_code,
                "category": self.category,
                "chart_id": self.chart_id,
                "source_locator": self.source_locator,
            },
            "current_exact_canonical_match_count": 0,
            "occurrence_count": len(self.occurrences),
            "gukgam_occurrences": [item.to_dict() for item in self.occurrences],
        }


@dataclass(frozen=True)
class OrgGoOrganizationProposalReport:
    provider_row_count: int
    current_organization_count: int
    items: tuple[OrgGoOrganizationProposalItem, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "semantics": ORGGO_ORGANIZATION_PROPOSAL_SEMANTICS,
            "status": "REVIEW_ONLY",
            "match_rule": "EXACT_PROVIDER_NAME_TO_GUKGAM_NO_EXACT_LABEL_ONLY",
            "provider_row_count": self.provider_row_count,
            "current_organization_count": self.current_organization_count,
            "proposal_count": len(self.items),
            "gukgam_occurrence_count": sum(len(item.occurrences) for item in self.items),
            "canonical_name_conflict_count": 0,
            "items": [item.to_dict() for item in self.items],
            "limitations": [
                "Exact provider-name equality is a review proposal only and does not create an Organization.",
                "Current canonical Organization names are rechecked and any exact conflict fails closed.",
                "No alias expansion, fuzzy similarity, ranking, embeddings, or organizational proximity is used.",
                "No Gukgam binding, Claim, ClaimEvidence, or public publication is performed.",
            ],
        }


def _detail_locator(record: OrgGoTopLevelOrganizationRecord) -> str:
    query = urlencode(
        {
            "codeNum": record.category,
            "orgCode": record.org_code,
            "chartId": record.chart_id,
        }
    )
    return f"https://{OrgGoTopLevelOrganizationConnector.HOST}/cop/bbs/getInstiChartDetail.do?{query}"


def build_orggo_organization_proposal(
    provider_rows: Sequence[OrgGoTopLevelOrganizationRecord],
    gukgam_review: GukgamOrganizationBindingReviewReport,
    organizations: Sequence[Organization],
) -> OrgGoOrganizationProposalReport:
    current = [item for item in organizations if item.superseded_at is None]
    if gukgam_review.organization_universe_count != len(current):
        raise OrgGoOrganizationProposalError(
            "Gukgam review Organization universe does not match current Organizations"
        )
    current_names: dict[str, list[Organization]] = defaultdict(list)
    for organization in current:
        current_names[organization.name.strip()].append(organization)

    by_provider_name: dict[str, list[OrgGoTopLevelOrganizationRecord]] = defaultdict(list)
    seen_codes: set[str] = set()
    for row in provider_rows:
        name = row.organization_name.strip()
        if not name:
            raise OrgGoOrganizationProposalError("org.go row has empty organization_name")
        if row.org_code in seen_codes:
            raise OrgGoOrganizationProposalError("org.go provider rows contain duplicate org_code")
        seen_codes.add(row.org_code)
        by_provider_name[name].append(row)

    for name, rows in by_provider_name.items():
        if len(rows) != 1:
            raise OrgGoOrganizationProposalError(
                f"org.go provider name is not unique: {name}"
            )

    occurrences_by_name: dict[str, list[OrgGoGukgamOccurrenceRef]] = defaultdict(list)
    for item in gukgam_review.items:
        if item.match_class != NO_EXACT:
            continue
        name = item.audited_target.strip()
        if name not in by_provider_name:
            continue
        if item.candidates:
            raise OrgGoOrganizationProposalError(
                "NO_EXACT Gukgam review item unexpectedly contains candidates"
            )
        occurrences_by_name[name].append(
            OrgGoGukgamOccurrenceRef(
                review_key=item.review_key,
                committee_name=item.committee_name,
                audit_date=item.audit_date,
                provider_record_key=item.provider_record_key,
                observation_id=item.observation_id,
                audited_target=item.audited_target,
            )
        )

    proposals: list[OrgGoOrganizationProposalItem] = []
    for name in sorted(occurrences_by_name):
        if current_names.get(name):
            raise OrgGoOrganizationProposalError(
                f"current canonical Organization already uses exact name: {name}"
            )
        provider_row = by_provider_name[name][0]
        occurrences = tuple(
            sorted(occurrences_by_name[name], key=lambda item: item.review_key)
        )
        proposals.append(
            OrgGoOrganizationProposalItem(
                organization_name=provider_row.organization_name,
                category=provider_row.category,
                org_code=provider_row.org_code,
                chart_id=provider_row.chart_id,
                source_locator=_detail_locator(provider_row),
                occurrences=occurrences,
            )
        )

    return OrgGoOrganizationProposalReport(
        provider_row_count=len(provider_rows),
        current_organization_count=len(current),
        items=tuple(proposals),
    )
