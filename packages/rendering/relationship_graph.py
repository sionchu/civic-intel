"""Load the public relationship projection inputs through the canonical repository.

Reads only current published Claims of public RESOLVED People that pass the normal Claim
publication gate. Builds exact lookups (committee-name crosswalk, witness source Organization,
source-run capture keys) and returns Affiliations plus Organization links for path search.
"""

from __future__ import annotations

import time
import weakref
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from typing import TYPE_CHECKING, Any
from uuid import UUID

from packages.domain.contracts import Organization, Person
from packages.rendering.relationship_bindings import (
    OrganizationRegistry,
    RegistryEntity,
    registry_from_rows,
)
from packages.rendering.relationship_projection import (
    AUDIT_TARGET_PREDICATE,
    BINDABLE,
    INTERPRETATION_NOTE,
    PERSON_AFFILIATION_PREDICATES,
    RELATION_PROJECTION_SEMANTICS,
    RULES,
    RULESET_VERSION,
    WITNESS_PREDICATE,
    Affiliation,
    AffiliationContext,
    CosponsorshipPair,
    OrganizationLink,
    RelationStatus,
    career_transitions,
    derive_pair,
    eligible_relation_claim,
    extract_affiliation,
    index_by_via,
    relations_for_person,
    shortest_evidence_path,
)
from packages.verification.claims import validate_claim_publication

if TYPE_CHECKING:
    from packages.persistence.repository import SqlAlchemyRepository

COMMITTEE_ORGANIZATION_PREFIX = "국회 "


@dataclass(frozen=True)
class RelationshipGraphInputs:
    people: dict[UUID, Person]
    organizations: dict[UUID, Organization]
    affiliations: tuple[Affiliation, ...]
    organization_links: tuple[OrganizationLink, ...]
    committee_crosswalk: dict[str, UUID]
    gate_rejections: int

    def affiliations_of(self, person_id: UUID) -> tuple[Affiliation, ...]:
        return tuple(item for item in self.affiliations if item.person_id == person_id)


def committee_crosswalk(organizations: dict[UUID, Organization]) -> dict[str, UUID]:
    """Official committee name → Organization id when exactly one current ``국회 {name}`` exists."""

    by_name: dict[str, list[UUID]] = {}
    for organization in organizations.values():
        if organization.superseded_at is None and organization.name.startswith(
            COMMITTEE_ORGANIZATION_PREFIX
        ):
            name = organization.name[len(COMMITTEE_ORGANIZATION_PREFIX):].strip()
            if name.endswith("위원회"):
                by_name.setdefault(name, []).append(organization.id)
    return {name: ids[0] for name, ids in by_name.items() if len(ids) == 1}


MOIS_GOVERNMENT_TYPES = frozenset({
    "국가행정기관", "자치행정조직", "교육행정조직", "헌법조직", "사법조직", "입법조직", "국군조직",
    "대한민국정부", "경제자유구역청(조합)", "위원회",
})
MOIS_PUBLIC_INSTITUTION_TYPES = frozenset({"산하기관", "정부투자기관 및 기타"})
MOIS_UNIVERSITY_TYPES = frozenset({"고등교육기관"})


REGISTRY_CACHE_SECONDS = 600
_registry_cache: weakref.WeakKeyDictionary[SqlAlchemyRepository, tuple[float, OrganizationRegistry]] = (
    weakref.WeakKeyDictionary()
)


def build_registry(repository: SqlAlchemyRepository) -> OrganizationRegistry:
    """Canonical ALIO institutions (0) > OpenDART listed companies (1) > MOIS codes (2/3).

    The registry is read-only reference data (about 135k names); it is cached per repository
    for ``REGISTRY_CACHE_SECONDS`` so a relationship request does not rebuild it.
    """

    cached = _registry_cache.get(repository)
    now = time.monotonic()
    if cached is not None and now - cached[0] < REGISTRY_CACHE_SECONDS:
        return cached[1]
    registry = _build_registry(repository)
    _registry_cache[repository] = (now, registry)
    return registry


def _build_registry(repository: SqlAlchemyRepository) -> OrganizationRegistry:
    entries: list[tuple[str, RegistryEntity, int]] = []
    for name, kind, key, organization_id in repository.organization_registry_rows():
        if kind == "ALIO_INSTITUTION":
            entries.append((name, RegistryEntity(
                f"organization:{key}", "PUBLIC_INSTITUTION", name, "CANONICAL_ORGANIZATION",
                UUID(organization_id) if organization_id else None), 0))
        elif kind == "OPENDART_CORP":
            entries.append((name, RegistryEntity(
                f"opendart_corp:{key}", "COMPANY", name, "EXACT_REGISTRY_NAME"), 1))
        elif kind.startswith(("MOIS:", "MOIS_UNIT:")):
            unit = kind.startswith("MOIS_UNIT:")
            type_big = kind.split(":", 1)[1]
            if unit and (type_big not in MOIS_GOVERNMENT_TYPES or len(name) < 5):
                continue
            mapped = (
                "GOVERNMENT_BODY" if type_big in MOIS_GOVERNMENT_TYPES
                else "PUBLIC_INSTITUTION" if type_big in MOIS_PUBLIC_INSTITUTION_TYPES
                else "UNIVERSITY" if type_big in MOIS_UNIVERSITY_TYPES
                else None
            )
            if mapped is not None:
                entries.append((name, RegistryEntity(
                    f"mois_org:{key}", mapped, name, "EXACT_REGISTRY_NAME"), 3 if unit else 2))
    return registry_from_rows(entries)


def load_relationship_graph(repository: SqlAlchemyRepository) -> RelationshipGraphInputs:
    people = {person.id: person for person in repository.public_people()}
    organizations = {item.id: item for item in repository.organizations(current_only=True)}
    contexts = repository.published_person_claim_contexts(
        people, predicates=PERSON_AFFILIATION_PREDICATES
    )
    all_evidence = [
        item
        for _, evidence_by_claim in contexts.values()
        for evidence in evidence_by_claim.values()
        for item in evidence
    ]
    sources = repository.sources({item.source_id for item in all_evidence})
    policies = repository.policies({item.policy_id for item in sources.values()})
    run_ids = repository.evidence_run_ids(all_evidence)

    eligible = []
    rejected = 0
    for person_id, (claims, evidence_by_claim) in contexts.items():
        for claim in claims:
            evidence = list(evidence_by_claim.get(claim.id, ()))
            gate = validate_claim_publication(claim, people[person_id], evidence, sources, policies)
            if not gate.publishable or not eligible_relation_claim(claim, evidence):
                rejected += 1
                continue
            eligible.append((claim, evidence))

    witness_sources = repository.current_claims_by_ids(
        UUID(str(claim.qualifiers["source_claim_id"]))
        for claim, _ in eligible
        if claim.predicate == WITNESS_PREDICATE and claim.qualifiers.get("source_claim_id")
    )
    witness_org: dict[UUID, UUID] = {}
    for claim, _ in eligible:
        if claim.predicate != WITNESS_PREDICATE:
            continue
        try:
            source_claim = witness_sources.get(UUID(str(claim.qualifiers.get("source_claim_id"))))
        except ValueError:
            continue
        if (
            source_claim is not None
            and source_claim.organization_id is not None
            and source_claim.organization_id in organizations
        ):
            witness_org[claim.id] = source_claim.organization_id

    crosswalk = committee_crosswalk(organizations)
    context = AffiliationContext(
        committee_orgs_by_name=crosswalk,
        witness_committee_org=witness_org,
        capture_keys={
            claim.id: tuple(
                sorted({f"run:{run_ids[item.id]}" for item in evidence if item.id in run_ids})
            )
            for claim, evidence in eligible
        },
        organizations=organizations,
        registry=build_registry(repository),
    )
    affiliations = tuple(
        affiliation
        for claim, evidence in eligible
        if (affiliation := extract_affiliation(claim, evidence, context)) is not None
    )

    public_org_ids = [item.id for item in repository.public_organizations()]
    org_contexts = repository.published_organization_claim_contexts(
        public_org_ids, predicates=[AUDIT_TARGET_PREDICATE]
    )
    org_evidence = [
        item for _, by_claim in org_contexts.values() for ev in by_claim.values() for item in ev
    ]
    org_sources = repository.sources({item.source_id for item in org_evidence})
    org_policies = repository.policies({item.policy_id for item in org_sources.values()})
    links = []
    for organization_id, (claims, by_claim) in org_contexts.items():
        organization = organizations.get(organization_id)
        if organization is None:
            continue
        for claim in claims:
            evidence = list(by_claim.get(claim.id, ()))
            committee = crosswalk.get(str(claim.qualifiers.get("committee_name", "")))
            if committee is None or not eligible_relation_claim(claim, evidence):
                continue
            if not validate_claim_publication(
                claim, organization, evidence, org_sources, org_policies
            ).publishable:
                continue
            audit_date = claim.qualifiers.get("audit_date")
            links.append(
                OrganizationLink(
                    source_organization_id=organization_id,
                    target_via_key=f"organization:{committee}",
                    target_label=str(claim.qualifiers.get("committee_name")),
                    relation_type="LISTED_AS_AUDIT_TARGET_OF",
                    claim_id=claim.id,
                    evidence_ids=tuple(item.id for item in evidence),
                    as_of=_iso_date(audit_date),
                )
            )
    return RelationshipGraphInputs(
        people=people,
        organizations=organizations,
        affiliations=affiliations,
        organization_links=tuple(links),
        committee_crosswalk=crosswalk,
        gate_rejections=rejected,
    )


def _iso_date(value: object) -> date | None:
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


# --------------------------------------------------------------------------------------------
# Public payloads

RELATIONSHIP_LIMITATIONS = (
    "관계는 공개 공식자료의 같은 조직·명단·의안 기재를 결정적 규칙으로 비교한 결과다. 친분·영향력·유착·인과를 뜻하지 않는다.",
    "현재 수집 범위(국회 위원명단·명부, ALIO·OpenDART 검토 연결, 국정감사 증인·피감기관 명단, 의안 공동발의)에 없는 관계는 없는 것이 아니라 UNKNOWN이다.",
    "기간이 확인되지 않은 소속은 겹침(overlap)을 만들지 않는다.",
    "약력(의원 본인 관리 텍스트)의 학교·기관·기업·캠프는 공식 registry(행정표준코드, ALIO, OpenDART, NEC 선거)와 정확히 하나로 일치할 때만 연결한다. 일치하지 않거나 동명 고교처럼 모호하면 CANDIDATE로 두고 기본 응답에서 뺀다.",
)


def _person_label(inputs: RelationshipGraphInputs, person_id: UUID) -> dict[str, object]:
    person = inputs.people.get(person_id)
    return {"id": str(person_id), "name": person.canonical_name if person else None}


def person_relationships_payload(
    inputs: RelationshipGraphInputs,
    person_id: UUID,
    *,
    layers: Sequence[str] | None = None,
    relation_types: Sequence[str] | None = None,
    include_candidates: bool = False,
    cosponsorship: Sequence[CosponsorshipPair] = (),
    limit_per_via: int = 50,
) -> dict[str, object]:
    relations = relations_for_person(
        person_id, inputs.affiliations, include_candidates=include_candidates, layers=layers
    )
    if relation_types:
        wanted = set(relation_types)
        relations = [item for item in relations if item.relation_type in wanted]
    groups: dict[str, dict[str, Any]] = {}
    for relation in relations:
        counterpart = relation.counterpart if relation.subject.person_id == person_id else relation.subject
        group = groups.setdefault(
            relation.via.key,
            {"via": relation.via.to_dict(), "layer": relation.layer.value, "relations": []},
        )
        records = group["relations"]
        assert isinstance(records, list)
        if len(records) < limit_per_via:
            records.append(
                relation.to_dict() | {"counterpart": _person_label(inputs, counterpart.person_id)}
            )
        group["relation_count"] = int(group.get("relation_count", 0)) + 1
    own = inputs.affiliations_of(person_id)
    if not include_candidates:
        own = tuple(item for item in own if item.via.binding in BINDABLE)
    return {
        "person": _person_label(inputs, person_id),
        "semantics": RELATION_PROJECTION_SEMANTICS,
        "ruleset_version": RULESET_VERSION,
        "affiliations": [item.to_dict() for item in own],
        "groups": sorted(groups.values(), key=lambda item: (str(item["layer"]), str(item["via"]["label"]))),  # type: ignore[index]
        "relation_count": len(relations),
        "career_transitions": career_transitions(
            inputs.affiliations_of(person_id), include_candidates=include_candidates
        ),
        "cosponsorship": [
            item.to_dict() | {"counterpart": _person_label(inputs, item.other_person_id)}
            for item in cosponsorship[:limit_per_via]
        ],
        "limitations": list(RELATIONSHIP_LIMITATIONS),
    }


def compare_payload(
    inputs: RelationshipGraphInputs,
    left: UUID,
    right: UUID,
    *,
    include_candidates: bool = False,
    cosponsorship: Sequence[CosponsorshipPair] = (),
) -> dict[str, object]:
    left_items = inputs.affiliations_of(left)
    right_by_via = index_by_via(inputs.affiliations_of(right))
    direct = []
    for item in left_items:
        for other in right_by_via.get(item.via.key, ()):
            relation = derive_pair(item, other)
            if relation is None or (
                relation.status == RelationStatus.CANDIDATE and not include_candidates
            ):
                continue
            direct.append(relation)
    unique = {item.relation_id: item for item in direct}
    shared = sorted({item.via.key: item.via for item in unique.values()}.values(), key=lambda v: v.label)
    path = shortest_evidence_path(
        left, right, inputs.affiliations, organization_links=inputs.organization_links,
        organization_labels={key: value.name for key, value in inputs.organizations.items()},
    )
    pair = next((item for item in cosponsorship if item.other_person_id == right), None)
    layers = sorted({item.layer.value for item in unique.values()} | ({"LEGISLATIVE"} if pair else set()))
    timeline = sorted(
        (
            {
                "person_id": str(item.person_id),
                "via": item.via.to_dict(),
                "affiliation_type": item.affiliation_type,
                "role": item.role,
                "period": item.period.to_dict(),
                "claim_id": str(item.claim_id),
            }
            for item in (*left_items, *inputs.affiliations_of(right))
            if include_candidates or item.via.binding in BINDABLE
        ),
        key=lambda entry: (
            str(entry["period"]["start"] or entry["period"]["as_of"] or "9999"),  # type: ignore[index]
            str(entry["person_id"]),
        ),
    )
    return {
        "people": [_person_label(inputs, left), _person_label(inputs, right)],
        "semantics": RELATION_PROJECTION_SEMANTICS,
        "ruleset_version": RULESET_VERSION,
        "direct_relations": [item.to_dict() for item in sorted(unique.values(), key=lambda r: (r.layer.value, r.via.label))],
        "shared_organizations": [item.to_dict() for item in shared],
        "multiplex_layers": layers,
        "cosponsorship": pair.to_dict() if pair else None,
        "timeline": timeline,
        "shortest_evidence_path": path,
        "limitations": list(RELATIONSHIP_LIMITATIONS),
    }


def rules_payload(inputs: RelationshipGraphInputs | None = None) -> dict[str, object]:
    payload: dict[str, object] = {
        "semantics": RELATION_PROJECTION_SEMANTICS,
        "ruleset_version": RULESET_VERSION,
        "rules": [rule.to_dict() for rule in RULES],
        "bindable": sorted(item.value for item in BINDABLE),
        "interpretation_note": INTERPRETATION_NOTE,
    }
    if inputs is not None:
        by_kind: dict[str, int] = {}
        for item in inputs.affiliations:
            by_kind[item.via.kind] = by_kind.get(item.via.kind, 0) + 1
        payload["coverage"] = {
            "public_people": len(inputs.people),
            "people_with_bindable_affiliation": len(
                {item.person_id for item in inputs.affiliations if item.via.binding in BINDABLE}
            ),
            "affiliations_by_via_kind": dict(sorted(by_kind.items())),
            "organization_links": len(inputs.organization_links),
            "committee_crosswalk_entries": len(inputs.committee_crosswalk),
            "claims_rejected_by_gate": inputs.gate_rejections,
        }
    return payload
