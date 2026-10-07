"""Read-only coverage audit of Person dimensions and relationship layers.

Measures, over current public RESOLVED People, which profile dimensions have at least one
current published, gate-passing Claim, and which relation layers have bindable affiliations.
A dimension is AVAILABLE (asserted FACT), PARTIAL (source-attributed CLAIM only), CONFLICTING
(REFUTE evidence present) or UNKNOWN (no published Claim). UNKNOWN is a collection gap, not a
negative finding. No row is written.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from collections.abc import Callable
from uuid import UUID

from sqlalchemy import func, select

from packages.domain.contracts import Claim
from packages.domain.db import ClaimEvidenceRow, ClaimRow, PersonAliasRow
from packages.domain.enums import EvidenceStance, PublicationStatus
from packages.persistence import SqlAlchemyRepository
from packages.rendering.relationship_graph import load_relationship_graph
from packages.rendering.relationship_projection import (
    BINDABLE,
    relations_for_person,
)

Matcher = Callable[[Claim], bool]


def _pred(*names: str) -> Matcher:
    wanted = set(names)
    return lambda claim: claim.predicate in wanted


def _q(predicate: str, key: str, *values: str) -> Matcher:
    wanted = set(values)
    return lambda claim: claim.predicate == predicate and claim.qualifiers.get(key) in wanted


def _text(predicate: str, key: str, *needles: str) -> Matcher:
    return lambda claim: claim.predicate == predicate and any(
        needle in str(claim.qualifiers.get(key, "")) for needle in needles
    )


def _any(*matchers: Matcher) -> Matcher:
    return lambda claim: any(matcher(claim) for matcher in matchers)


EDU = "ASSEMBLY_BIOGRAPHY_EDUCATION"
CAREER = "ASSEMBLY_BIOGRAPHY_CAREER"
DART = "OPENDART_DISCLOSED_EXECUTIVE_ROLE"
ALIO = "ALIO_REVIEWED_PERSON_ROLE"
COMMITTEE = ("ASSEMBLY_COMMITTEES", "ASSEMBLY_COMMITTEE_MEMBERSHIP", "ASSEMBLY_COMMITTEE_ROLE")

DIMENSIONS: dict[str, Matcher] = {
    "education": _pred(EDU),
    "high_school": _q(EDU, "institution_level", "HIGH_SCHOOL"),
    "university": _q(EDU, "institution_level", "UNIVERSITY"),
    "graduate_school": _q(EDU, "institution_level", "GRADUATE_SCHOOL"),
    "department": lambda c: c.predicate == EDU and bool(c.qualifiers.get("department_text")),
    "education_dates": lambda c: c.predicate == EDU
    and bool(c.qualifiers.get("period_start") or c.qualifiers.get("period_end") or c.qualifiers.get("period_point")),
    "career": _any(_pred(CAREER, DART, ALIO), _q("HELD_ROLE", "source_scope", "current_member_roster")),
    "employment": _any(_pred(DART, ALIO), _q(CAREER, "career_category", "BUSINESS", "ACADEMIA", "LEGAL_PRACTICE", "CIVIC")),
    "company_role": _any(_pred(DART), _q(CAREER, "career_category", "BUSINESS")),
    "public_institution_role": _pred(ALIO),
    "political_party": _any(_pred("ASSEMBLY_PARTY"), _q(CAREER, "career_category", "PARTY")),
    "elected_office": _any(_pred("HELD_ROLE", "ASSEMBLY_DISTRICT"), _q(CAREER, "career_category", "LOCAL_GOVERNMENT")),
    "parliamentary_term": _pred("ASSEMBLY_REELECTION"),
    "committee": _pred(*COMMITTEE),
    "special_committee": lambda c: c.predicate in COMMITTEE and "특별위원회" in c.object_text,
    "campaign": _q(CAREER, "career_category", "CAMPAIGN"),
    "campaign_role": lambda c: c.predicate == CAREER and c.qualifiers.get("career_category") == "CAMPAIGN"
    and bool(c.qualifiers.get("role_text")),
    "transition_committee": _q(CAREER, "career_category", "TRANSITION_COMMITTEE"),
    "government_role": _q(CAREER, "career_category", "PUBLIC_SERVICE", "PRESIDENTIAL_OFFICE", "GOVERNMENT_COMMITTEE"),
    "presidential_office": _q(CAREER, "career_category", "PRESIDENTIAL_OFFICE"),
    "ministry": _q(CAREER, "career_category", "PUBLIC_SERVICE"),
    "government_committee": _q(CAREER, "career_category", "GOVERNMENT_COMMITTEE"),
    "advisory_committee": _text(CAREER, "role_text", "자문위원", "고문"),
    "corporate_role": _pred(DART),
    "board_membership": _any(_pred(DART), _text(ALIO, "position_text", "이사")),
    "outside_director": _any(_q(DART, "registered_status", "사외이사"), _text(ALIO, "position_text", "비상임이사")),
    "audit_role": _any(_text(DART, "position", "감사"), _text(ALIO, "position_text", "감사")),
    "ownership": _pred("DISCLOSED_OWNERSHIP"),
    "major_shareholder": _pred("DISCLOSED_MAJOR_SHAREHOLDER"),
    "association": _text(CAREER, "organization_text", "협회", "연합회", "협의회"),
    "foundation": _text(CAREER, "organization_text", "재단"),
    "think_tank": _text(CAREER, "organization_text", "연구원", "연구소", "싱크탱크"),
    "professional_association": _text(CAREER, "organization_text", "변호사회", "의사회", "회계사회", "학회"),
    "family": _pred("DISCLOSED_FAMILY_RELATION"),
    "spouse": _pred("DISCLOSED_SPOUSE"),
    "parent": _pred("DISCLOSED_PARENT"),
    "child": _pred("DISCLOSED_CHILD"),
    "explicit_public_kinship": _pred("DISCLOSED_KINSHIP"),
    "public_religious_affiliation": _pred("PUBLIC_RELIGIOUS_ROLE"),
    "asset_disclosure": _pred("DECLARED_TOTAL_ASSETS", "DISCLOSED_BUSINESS_EXPENSE"),
    "real_estate_disclosure": _pred("DECLARED_REAL_ESTATE"),
    "securities_disclosure": _pred("DECLARED_SECURITIES"),
    "tax_disclosure": _pred("DECLARED_TAX_PAID"),
    "executive_compensation": _pred("DISCLOSED_EXECUTIVE_COMPENSATION"),
    "military_service": _q(CAREER, "career_category", "MILITARY"),
}
# Counted in SQL (too many Claims to load): bill_sponsorship, cosponsorship.
# Dimensions computed outside Claims.
STRUCTURAL = ("identity", "aliases", "birth", "birthplace", "vote", "source_provenance", "external_identifiers")


def _person_external_id(claim: Claim) -> bool:
    """A provider Person identifier (Assembly MONA_CD, NEC candidate id) — not an Organization code."""

    q = claim.qualifiers
    return bool(
        q.get("provider_person_key")
        or q.get("candidate_id")
        or (q.get("source_contract") == "assembly_member_roster" and q.get("provider_record_key"))
    )


def _predicates(repository: SqlAlchemyRepository, ids: list[str]) -> list[tuple[str]]:
    with repository.sessions() as session:
        return [
            (str(predicate),)
            for predicate in session.scalars(
                select(ClaimRow.predicate)
                .where(
                    ClaimRow.person_id.in_(ids),
                    ClaimRow.publication_status == PublicationStatus.PUBLISHED.value,
                    ClaimRow.superseded_at.is_(None),
                )
                .distinct()
            )
        ]


def _bill_roles(repository: SqlAlchemyRepository, ids: list[str]) -> dict[str, set[UUID]]:
    role = ClaimRow.qualifiers["participation_role"].as_string()
    result: dict[str, set[UUID]] = defaultdict(set)
    with repository.sessions() as session:
        for person, value in session.execute(
            select(ClaimRow.person_id, role)
            .where(
                ClaimRow.person_id.in_(ids),
                ClaimRow.predicate == "ASSEMBLY_BILL_PARTICIPATION",
                ClaimRow.publication_status == PublicationStatus.PUBLISHED.value,
                ClaimRow.superseded_at.is_(None),
            )
            .distinct()
        ):
            result[str(value)].add(UUID(str(person)))
    return result


def audit(repository: SqlAlchemyRepository) -> dict[str, object]:
    people = {person.id: person for person in repository.public_people()}
    ids = [str(item) for item in people]
    with repository.sessions() as session:
        votes = Counter(
            {
                UUID(person): count
                for person, count in session.execute(
                    select(ClaimRow.person_id, func.count())
                    .where(
                        ClaimRow.person_id.in_(ids),
                        ClaimRow.predicate == "ASSEMBLY_PLENARY_VOTE",
                        ClaimRow.publication_status == PublicationStatus.PUBLISHED.value,
                        ClaimRow.superseded_at.is_(None),
                    )
                    .group_by(ClaimRow.person_id)
                )
            }
        )
        aliases = {
            UUID(person)
            for person in session.scalars(
                select(PersonAliasRow.person_id).where(PersonAliasRow.person_id.in_(ids))
            )
        }
        refuted = {
            claim_id
            for claim_id in session.scalars(
                select(ClaimEvidenceRow.claim_id).where(
                    ClaimEvidenceRow.stance == EvidenceStance.REFUTE.value
                )
            )
        }
    # Votes and bill participation are counted in SQL; every other dimension reads its Claims.
    claim_predicates = {
        row[0]
        for row in _predicates(repository, ids)
        if row[0] not in {"ASSEMBLY_PLENARY_VOTE", "ASSEMBLY_BILL_PARTICIPATION"}
    }
    contexts = repository.published_person_claim_contexts(people, predicates=claim_predicates)
    status: dict[str, dict[UUID, str]] = defaultdict(dict)
    provenance: set[UUID] = set()
    external: set[UUID] = set()
    for person_id, (claims, evidence) in contexts.items():
        for claim in claims:
            if claim.predicate == "ASSEMBLY_PLENARY_VOTE":
                continue
            if evidence.get(claim.id):
                provenance.add(person_id)
            if _person_external_id(claim):
                external.add(person_id)
            for name, matcher in DIMENSIONS.items():
                if not matcher(claim):
                    continue
                value = (
                    "CONFLICTING" if str(claim.id) in refuted
                    else "AVAILABLE" if claim.asserted_as_true else "PARTIAL"
                )
                previous = status[name].get(person_id)
                rank = {"PARTIAL": 0, "AVAILABLE": 1, "CONFLICTING": 2}
                if previous is None or rank[value] > rank[previous]:
                    status[name][person_id] = value
    total = len(people)

    def row(name: str, values: dict[UUID, str]) -> dict[str, object]:
        counts = Counter(values.values())
        covered = counts["AVAILABLE"] + counts["PARTIAL"] + counts["CONFLICTING"]
        return {
            "dimension": name,
            "AVAILABLE": counts["AVAILABLE"],
            "PARTIAL": counts["PARTIAL"],
            "CONFLICTING": counts["CONFLICTING"],
            "UNKNOWN": total - covered,
            "coverage_pct": round(100 * covered / total, 1) if total else 0.0,
        }

    structural = {
        "identity": {pid: "AVAILABLE" for pid in people},
        "aliases": {pid: "AVAILABLE" for pid in aliases},
        "birth": {pid: "AVAILABLE" for pid, person in people.items() if person.birth_date},
        "birthplace": {},
        "vote": {pid: "AVAILABLE" for pid in votes},
        "source_provenance": {pid: "AVAILABLE" for pid in provenance},
        "external_identifiers": {pid: "AVAILABLE" for pid in external},
    }
    bills = _bill_roles(repository, ids)
    status["bill_sponsorship"] = {pid: "AVAILABLE" for pid in bills.get("REPRESENTATIVE_PROPOSER", set())}
    status["cosponsorship"] = {pid: "AVAILABLE" for pid in bills.get("CO_PROPOSER", set())}
    matrix = [row(name, structural[name]) for name in STRUCTURAL]
    matrix += [
        row(name, status.get(name, {}))
        for name in (*DIMENSIONS, "bill_sponsorship", "cosponsorship")
    ]

    graph = load_relationship_graph(repository)
    populations = {
        "assembly_member": {a.person_id for a in graph.affiliations if a.via.kind == "PARTY"},
        "public_institution_executive": {a.person_id for a in graph.affiliations if a.predicate == "ALIO_REVIEWED_PERSON_ROLE"},
        "former_assembly_member": {
            a.person_id for a in graph.affiliations if a.predicate == "ASSEMBLY_HISTORICAL_TERM"
        },
        "company_executive": {a.person_id for a in graph.affiliations if a.predicate == "OPENDART_DISCLOSED_EXECUTIVE_ROLE"},
        "audit_witness": {a.person_id for a in graph.affiliations if a.affiliation_type == "AUDIT_WITNESS_LISTED"},
    }
    layer_people: dict[str, set[UUID]] = defaultdict(set)
    for item in graph.affiliations:
        layer_people[f"{item.layer.value}:{item.via.binding.value in BINDABLE and 'BOUND' or 'TEXT'}"].add(item.person_id)
    relation_counts: Counter[str] = Counter()
    people_with_relation: Counter[str] = Counter()
    for person_id in people:
        relations = relations_for_person(person_id, graph.affiliations, include_candidates=True)
        kinds = set()
        for relation in relations:
            key = f"{relation.relation_type}:{relation.status.value}"
            relation_counts[key] += 1
            kinds.add(key)
        for key in kinds:
            people_with_relation[key] += 1
    layer_coverage = {
        population: {
            layer: round(100 * len(members & layer_people[layer]) / len(members), 1) if members else 0.0
            for layer in sorted(layer_people)
        }
        for population, members in populations.items()
    }
    return {
        "public_people": total,
        "coverage_matrix": matrix,
        "population_sizes": {key: len(value) for key, value in populations.items()},
        "relation_layer_coverage_pct": layer_coverage,
        # Each undirected relation is counted from both endpoints; halve for unique pairs.
        "relation_endpoint_counts": dict(sorted(relation_counts.items())),
        "people_with_relation_type": dict(sorted(people_with_relation.items())),
        "affiliations": len(graph.affiliations),
        "organization_links": len(graph.organization_links),
        "claims_rejected_by_gate": graph.gate_rejections,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url")
    args = parser.parse_args(argv)
    print(json.dumps(audit(SqlAlchemyRepository(args.database_url)), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
