from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from uuid import UUID

from packages.domain.contracts import FeederObservation, Organization
from packages.rendering.gukgam_organization_binding_review import (
    NO_EXACT,
    GukgamOrganizationBindingReviewReport,
)

MOIS_ORGANIZATION_PROPOSAL_SEMANTICS = "REVIEW_ONLY_MOIS_ORGANIZATION_PROPOSAL_V1"
MOIS_FEEDER = "mois_standard_organization_codes"
MOIS_SCOPE_KEY = "current:stop_selt=0"
MOIS_SEMANTIC_SCOPE = "current_organization_code_registry"
MOIS_IDENTITY_SEMANTICS = "PROVIDER_ORGANIZATION_KEY_NOT_CANONICAL_ORGANIZATION"


class MoisOrganizationProposalError(ValueError):
    pass


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise MoisOrganizationProposalError("MOIS normalized text field has invalid type")
    normalized = value.strip()
    return normalized or None


@dataclass(frozen=True)
class MoisOrganizationProposalProviderRow:
    observation_id: UUID
    provider_record_key: str
    org_code: str
    full_name: str
    lowest_name: str | None
    type_big: str | None
    type_mid: str | None
    parent_org_code: str | None
    top_org_code: str | None
    representative_org_code: str | None
    base_date: str | None
    changed_date: str | None

    def to_dict(self) -> dict[str, object]:
        return {
            "observation_id": str(self.observation_id),
            "provider_record_key": self.provider_record_key,
            "org_code": self.org_code,
            "full_name": self.full_name,
            "lowest_name": self.lowest_name,
            "type_big": self.type_big,
            "type_mid": self.type_mid,
            "parent_org_code": self.parent_org_code,
            "top_org_code": self.top_org_code,
            "representative_org_code": self.representative_org_code,
            "base_date": self.base_date,
            "changed_date": self.changed_date,
        }


def mois_organization_proposal_provider_row(
    observation: FeederObservation,
) -> MoisOrganizationProposalProviderRow:
    if (
        observation.feeder != MOIS_FEEDER
        or observation.scope_key != MOIS_SCOPE_KEY
        or observation.semantic_scope != MOIS_SEMANTIC_SCOPE
    ):
        raise MoisOrganizationProposalError("unexpected MOIS observation scope")

    normalized = observation.normalized
    org_code = normalized.get("org_code")
    full_name = normalized.get("full_name")
    if not isinstance(org_code, str) or not re.fullmatch(r"[A-Z0-9]{7}", org_code):
        raise MoisOrganizationProposalError("MOIS observation org_code is invalid")
    if observation.provider_record_key != org_code:
        raise MoisOrganizationProposalError(
            "MOIS provider_record_key does not match normalized org_code"
        )
    if not isinstance(full_name, str) or not full_name.strip():
        raise MoisOrganizationProposalError(
            "MOIS proposal requires a non-empty provider full_name"
        )
    if normalized.get("stop_selector") != "0":
        raise MoisOrganizationProposalError("MOIS proposal requires current stop_selector=0")
    if normalized.get("identity_semantics") != MOIS_IDENTITY_SEMANTICS:
        raise MoisOrganizationProposalError("MOIS identity semantics changed unexpectedly")

    hints = observation.identity_hints
    if (
        hints.get("record_kind") != "organization_registry_record"
        or hints.get("materialization") != "REVIEW_ONLY"
        or not isinstance(hints.get("external_ids"), dict)
        or hints["external_ids"].get("mois_org_cd") != org_code
    ):
        raise MoisOrganizationProposalError("MOIS identity hints changed unexpectedly")

    return MoisOrganizationProposalProviderRow(
        observation_id=observation.id,
        provider_record_key=observation.provider_record_key,
        org_code=org_code,
        full_name=full_name.strip(),
        lowest_name=_optional_text(normalized.get("lowest_name")),
        type_big=_optional_text(normalized.get("type_big")),
        type_mid=_optional_text(normalized.get("type_mid")),
        parent_org_code=_optional_text(normalized.get("parent_org_code")),
        top_org_code=_optional_text(normalized.get("top_org_code")),
        representative_org_code=_optional_text(
            normalized.get("representative_org_code")
        ),
        base_date=_optional_text(normalized.get("base_date")),
        changed_date=_optional_text(normalized.get("changed_date")),
    )


@dataclass(frozen=True)
class MoisGukgamOccurrenceRef:
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
class MoisOrganizationProposalItem:
    organization_name: str
    provider: MoisOrganizationProposalProviderRow
    occurrences: tuple[MoisGukgamOccurrenceRef, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "proposal_status": "REVIEW_REQUIRED_NO_WRITE",
            "organization_name": self.organization_name,
            "provider": self.provider.to_dict(),
            "current_exact_canonical_match_count": 0,
            "occurrence_count": len(self.occurrences),
            "gukgam_occurrences": [item.to_dict() for item in self.occurrences],
        }


@dataclass(frozen=True)
class MoisOrganizationAmbiguousItem:
    audited_target: str
    provider_org_codes: tuple[str, ...]
    occurrence_count: int

    def to_dict(self) -> dict[str, object]:
        return {
            "audited_target": self.audited_target,
            "provider_org_codes": list(self.provider_org_codes),
            "occurrence_count": self.occurrence_count,
        }


@dataclass(frozen=True)
class MoisOrganizationProposalReport:
    provider_universe_count: int
    candidate_provider_row_count: int
    current_organization_count: int
    gukgam_no_exact_distinct_target_count: int
    unmatched_distinct_target_count: int
    items: tuple[MoisOrganizationProposalItem, ...]
    ambiguous_items: tuple[MoisOrganizationAmbiguousItem, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "semantics": MOIS_ORGANIZATION_PROPOSAL_SEMANTICS,
            "status": "REVIEW_ONLY",
            "match_rule": "EXACT_MOIS_FULL_NAME_TO_GUKGAM_NO_EXACT_LABEL_ONLY",
            "provider_universe_count": self.provider_universe_count,
            "candidate_provider_row_count": self.candidate_provider_row_count,
            "current_organization_count": self.current_organization_count,
            "gukgam_no_exact_distinct_target_count": (
                self.gukgam_no_exact_distinct_target_count
            ),
            "proposal_count": len(self.items),
            "gukgam_occurrence_count": sum(len(item.occurrences) for item in self.items),
            "ambiguous_distinct_target_count": len(self.ambiguous_items),
            "unmatched_distinct_target_count": self.unmatched_distinct_target_count,
            "canonical_name_conflict_count": 0,
            "items": [item.to_dict() for item in self.items],
            "ambiguous_items": [item.to_dict() for item in self.ambiguous_items],
            "limitations": [
                "Exact MOIS full_name equality is a review proposal only and does not create an Organization.",
                "MOIS org_code remains a provider identity and is never treated as a canonical Organization ID.",
                "Multiple exact provider full_name matches are withheld from proposals and remain review-required.",
                "No alias expansion, fuzzy similarity, ranking, embeddings, or organizational proximity is used.",
                "No Gukgam binding, Claim, ClaimEvidence, or public publication is performed.",
            ],
        }


def build_mois_organization_proposal(
    provider_rows: Sequence[MoisOrganizationProposalProviderRow],
    *,
    provider_universe_count: int,
    gukgam_review: GukgamOrganizationBindingReviewReport,
    organizations: Sequence[Organization],
) -> MoisOrganizationProposalReport:
    if provider_universe_count < 1 or provider_universe_count < len(provider_rows):
        raise MoisOrganizationProposalError("MOIS provider universe count is invalid")

    current = [item for item in organizations if item.superseded_at is None]
    if gukgam_review.organization_universe_count != len(current):
        raise MoisOrganizationProposalError(
            "Gukgam review Organization universe does not match current Organizations"
        )

    current_names: dict[str, list[Organization]] = defaultdict(list)
    for organization in current:
        current_names[organization.name.strip()].append(organization)

    by_name: dict[str, list[MoisOrganizationProposalProviderRow]] = defaultdict(list)
    seen_provider_keys: set[str] = set()
    seen_org_codes: set[str] = set()
    for row in provider_rows:
        if row.provider_record_key in seen_provider_keys:
            raise MoisOrganizationProposalError(
                "MOIS candidate rows contain duplicate provider_record_key"
            )
        if row.org_code in seen_org_codes:
            raise MoisOrganizationProposalError(
                "MOIS candidate rows contain duplicate org_code"
            )
        if row.provider_record_key != row.org_code:
            raise MoisOrganizationProposalError(
                "MOIS candidate provider_record_key does not match org_code"
            )
        seen_provider_keys.add(row.provider_record_key)
        seen_org_codes.add(row.org_code)
        by_name[row.full_name.strip()].append(row)

    occurrences_by_name: dict[str, list[MoisGukgamOccurrenceRef]] = defaultdict(list)
    no_exact_names: set[str] = set()
    for item in gukgam_review.items:
        if item.match_class != NO_EXACT:
            continue
        if item.candidates:
            raise MoisOrganizationProposalError(
                "NO_EXACT Gukgam review item unexpectedly contains candidates"
            )
        name = item.audited_target.strip()
        no_exact_names.add(name)
        if current_names.get(name):
            raise MoisOrganizationProposalError(
                f"current canonical Organization already uses NO_EXACT name: {name}"
            )
        if name not in by_name:
            continue
        occurrences_by_name[name].append(
            MoisGukgamOccurrenceRef(
                review_key=item.review_key,
                committee_name=item.committee_name,
                audit_date=item.audit_date,
                provider_record_key=item.provider_record_key,
                observation_id=item.observation_id,
                audited_target=item.audited_target,
            )
        )

    proposals: list[MoisOrganizationProposalItem] = []
    ambiguous: list[MoisOrganizationAmbiguousItem] = []
    for name in sorted(occurrences_by_name):
        matches = by_name[name]
        occurrences = tuple(
            sorted(occurrences_by_name[name], key=lambda item: item.review_key)
        )
        if len(matches) != 1:
            ambiguous.append(
                MoisOrganizationAmbiguousItem(
                    audited_target=name,
                    provider_org_codes=tuple(sorted(row.org_code for row in matches)),
                    occurrence_count=len(occurrences),
                )
            )
            continue
        proposals.append(
            MoisOrganizationProposalItem(
                organization_name=name,
                provider=matches[0],
                occurrences=occurrences,
            )
        )

    matched_names = {item.organization_name for item in proposals}
    ambiguous_names = {item.audited_target for item in ambiguous}
    unmatched_count = len(no_exact_names - matched_names - ambiguous_names)

    return MoisOrganizationProposalReport(
        provider_universe_count=provider_universe_count,
        candidate_provider_row_count=len(provider_rows),
        current_organization_count=len(current),
        gukgam_no_exact_distinct_target_count=len(no_exact_names),
        unmatched_distinct_target_count=unmatched_count,
        items=tuple(proposals),
        ambiguous_items=tuple(ambiguous),
    )
