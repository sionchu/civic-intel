"""Deterministic OpenDART executive ↔ Person links from a three-anchor constellation.

OpenDART executive-status rows carry no provider Person ID. The reviewed LINK_PERSON path stays
the default. This lane adds one narrow, owner-approvable rule (``--publish`` only after approval):

- ``FORMER_OR_CURRENT_MEMBER``: exact listed name = Person name, disclosed birth year/month = the
  Person's known birth date (current-roster birth date, or the NEC-submitted birth date of a
  former member's exactly matched candidacy), and the company-disclosed career states 국회의원.
- ``PUBLIC_INSTITUTION_EXECUTIVE``: exact name = a published ALIO role Person, and that Person's ALIO
  institution is the disclosing company or appears in the company-disclosed career.

A row must satisfy a rule for exactly one Person and no birth-month conflict; otherwise nothing is
linked. Name + birth year/month without a third anchor goes to the identity review queue.
The resulting Claim is the existing source-attributed ``OPENDART_DISCLOSED_EXECUTIVE_ROLE`` CLAIM
("this company disclosed this Person in this role"), never an independent career FACT.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid5

from packages.domain.contracts import Claim, ClaimEvidence, IdentityReviewItem, Person
from packages.domain.enums import EvidenceStance, PublicationStatus
from packages.verification.claims import validate_claim_publication
from packages.verification.person_record_links import (
    OPENDART_EXECUTIVE_FEEDER,
    birth_year_month,
    birth_year_month_conflict,
    build_opendart_role_claim,
    listed_name,
)

if TYPE_CHECKING:
    from packages.persistence.repository import SqlAlchemyRepository

CONSTELLATION_IDENTITY_SCOPE = "DETERMINISTIC_DART_CONSTELLATION"
RULE_MEMBER = "FORMER_OR_CURRENT_MEMBER"
RULE_ALIO = "PUBLIC_INSTITUTION_EXECUTIVE"
REVIEW_REASON = "DART_NAME_AND_BIRTH_YEAR_MONTH_ONLY"
_NAMESPACE = UUID("e1b7c4a9-2d5f-4a83-9e60-7c3b1f8d2a46")
_MEMBER_CAREER = re.compile(r"국회의원|국회\s*\(?\s*제?\s*\d+\s*대")


def _compact(value: str) -> str:
    return re.sub(r"\((?:주|株)\)|（주）|㈜|주식회사|\s", "", value)


@dataclass(frozen=True)
class KnownPerson:
    person: Person
    birth_date: date | None
    kind: str  # MEMBER / FORMER / ALIO
    institutions: tuple[str, ...] = ()


@dataclass
class ConstellationPlan:
    claims: list[tuple[Claim, ClaimEvidence]] = field(default_factory=list)
    reviews: list[IdentityReviewItem] = field(default_factory=list)
    by_rule: dict[str, int] = field(default_factory=dict)
    refused_birth_conflict: int = 0
    ambiguous: int = 0


def classify(row: dict[str, Any], candidates: list[KnownPerson]) -> tuple[str | None, KnownPerson | None, bool]:
    """(rule, person, review_only) for one disclosure row and its same-name People."""

    disclosed = row.get("birth_year_month")
    career = str(row.get("reported_main_career") or "")
    corp = _compact(str(row.get("corp_name") or ""))
    matches: list[tuple[str, KnownPerson]] = []
    review: list[KnownPerson] = []
    for known in candidates:
        if birth_year_month_conflict(known.birth_date, disclosed):
            continue
        ym_agrees = known.birth_date is not None and birth_year_month(disclosed) is not None
        if known.kind in {"MEMBER", "FORMER"}:
            if ym_agrees and _MEMBER_CAREER.search(career):
                matches.append((RULE_MEMBER, known))
            elif ym_agrees:
                review.append(known)
        elif known.kind == "ALIO":
            institutions = [_compact(item) for item in known.institutions if len(_compact(item)) >= 2]
            if any(item == corp or item in _compact(career) for item in institutions):
                matches.append((RULE_ALIO, known))
    if len({known.person.id for _, known in matches}) == 1:
        rule, known = matches[0]
        return rule, known, False
    if len(matches) > 1:
        return None, None, False
    if len({known.person.id for known in review}) == 1:
        return None, review[0], True
    return None, None, False


class OpendartConstellationLinker:
    def __init__(self, repository: SqlAlchemyRepository) -> None:
        self.repository = repository

    def plan(self) -> ConstellationPlan:
        people = self.repository.dart_link_people()
        by_name: dict[str, list[KnownPerson]] = defaultdict(list)
        for known in people:
            by_name[known.person.canonical_name].append(known)
        linked = self.repository.opendart_linked_observation_ids()
        plan = ConstellationPlan()
        rows = self.repository.feeder_observations_by_feeder(OPENDART_EXECUTIVE_FEEDER)
        contexts = self.repository.assembly_legislative_source_contexts(
            [item.id for item in rows if str(item.id) not in linked]
        )
        for observation in rows:
            if str(observation.id) in linked:
                continue
            name = listed_name(str(observation.normalized.get("canonical_name") or ""))
            candidates = by_name.get(name, [])
            if not candidates:
                continue
            if all(
                birth_year_month_conflict(item.birth_date, observation.normalized.get("birth_year_month"))
                for item in candidates
            ):
                plan.refused_birth_conflict += 1
                continue
            rule, known, review_only = classify(observation.normalized, candidates)
            if known is None:
                plan.ambiguous += 1 if rule is None and not review_only else 0
                continue
            if review_only:
                plan.reviews.append(IdentityReviewItem(
                    id=uuid5(_NAMESPACE, f"review:{observation.id}:{known.person.id}"),
                    observation_id=observation.id,
                    candidate_person_id=known.person.id,
                    reason_code=REVIEW_REASON,
                    details={"feeder": OPENDART_EXECUTIVE_FEEDER,
                             "anchors": ["EXACT_NAME", "BIRTH_YEAR_MONTH_AGREES"],
                             "missing": "third anchor (career/institution)"},
                ))
                continue
            assert rule is not None
            source, policy = contexts[observation.id]
            claim = build_opendart_role_claim(
                claim_id=uuid5(_NAMESPACE, f"claim:{observation.id}:{known.person.id}:{observation.content_hash}"),
                person_id=known.person.id,
                person_name=known.person.canonical_name,
                normalized=observation.normalized,
                observation_id=str(observation.id),
                observation_hash=observation.content_hash,
                provider_observed_at=observation.provider_observed_at,
                review_id=f"rule:{rule}",
                recorded_at=observation.recorded_at,
            )
            claim = claim.model_copy(update={
                "publication_status": PublicationStatus.PUBLISHED,
                "qualifiers": {**claim.qualifiers, "identity_scope": CONSTELLATION_IDENTITY_SCOPE,
                               "identity_rule": rule},
            })
            evidence = ClaimEvidence(
                id=uuid5(claim.id, f"{source.id}|{observation.snapshot_id}|{observation.id}|SUPPORT"),
                claim_id=claim.id, source_id=source.id, snapshot_id=observation.snapshot_id,
                feeder_observation_id=observation.id, stance=EvidenceStance.SUPPORT,
            )
            gate = validate_claim_publication(claim, known.person, [evidence], {source.id: source}, {policy.id: policy})
            if not gate.publishable:
                continue
            plan.claims.append((claim, evidence))
            plan.by_rule[rule] = plan.by_rule.get(rule, 0) + 1
        return plan

    def publish(self, *, dry_run: bool = True) -> dict[str, object]:
        plan = self.plan()
        if not dry_run:
            self.repository.insert_attributed_person_claims(plan.claims)
            self.repository.insert_identity_review_items(plan.reviews)
        return {
            "dry_run": dry_run,
            "linked_claims": len(plan.claims),
            "by_rule": plan.by_rule,
            "review_queue": len(plan.reviews),
            "refused_birth_conflict_rows": plan.refused_birth_conflict,
            "ambiguous_rows": plan.ambiguous,
            "people": len({claim.person_id for claim, _ in plan.claims}),
            "sample": [
                f"{claim.subject} · {claim.object_text} · {claim.qualifiers.get('identity_rule')}"
                for claim, _ in plan.claims[:15]
            ],
        }
