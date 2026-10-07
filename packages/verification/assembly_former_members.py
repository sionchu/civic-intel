"""Former National Assembly members from the 역대 국회의원 의원이력 API (owner-approved AUTO_CREATE).

The service lists, per term (``PROFILE_UNIT_CD``), each *former* member's ``MONA_CD``, name, Hanja
name, term dates (``FRTO_DATE``) and a term label (``PROFILE_SJ``: 대수, 정당, 선거구). Current
members are excluded by the provider.

Identity rule (owner decision 2026-10-07): ``MONA_CD`` is the authoritative Assembly provider
identifier. For each ``MONA_CD`` of the in-scope terms:

- already linked by this lane → reuse that Person (idempotent);
- linked to a current-roster Person → AUTO_LINK to that Person;
- otherwise, if any current Person has the same canonical name → REVIEW_REQUIRED (never a merge,
  never a duplicate);
- otherwise AUTO_CREATE one RESOLVED Person (deterministic id from ``MONA_CD``).

Each term row becomes one ``ASSEMBLY_HISTORICAL_TERM`` FACT with exact term dates; party and
district are copied from the provider label only when the party is an exact known party name.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime, time
from typing import TYPE_CHECKING
from uuid import UUID, uuid5

from packages.connectors.open_assembly_historical import AssemblyHistoricalCareerRecord
from packages.domain.contracts import (
    Claim,
    ClaimEvidence,
    FeederObservation,
    IdentityReviewItem,
    Person,
    PersonAlias,
    PersonObservationLink,
    Source,
    SourcePolicy,
)
from packages.domain.enums import (
    EpistemicStatus,
    EvidenceStance,
    IdentityStatus,
    MaterializationAction,
    MaterializationDecisionClass,
    PublicationStatus,
    SourceRunStatus,
)
from packages.verification.claims import validate_claim_publication
from packages.verification.policy import PolicyAction, require_policy

if TYPE_CHECKING:
    from packages.persistence.repository import SqlAlchemyRepository

FORMER_MEMBER_FEEDER = "national_assembly_historical_members"
FORMER_MEMBER_SCOPE = "historical_member_terms:17-22"
FORMER_MEMBER_SEMANTIC_SCOPE = "legislative_historical_member_term"
FORMER_MEMBER_SOURCE_CONTRACT = "assembly_historical_member_term"
FORMER_MEMBER_PREDICATE = "ASSEMBLY_HISTORICAL_TERM"
# 제17대(2004) … 제22대: recent terms with public-interest relevance to current networks.
IN_SCOPE_PROFILE_UNITS = tuple(f"1000{n:02d}" for n in range(17, 23))
_PERSON_NAMESPACE = UUID("5f2c1d7a-3b9e-4c6d-8a1f-2e7b9c4d6a83")
_CLAIM_NAMESPACE = UUID("9d4e2b71-6c3a-4f85-b2d9-7a1e5c3b8f04")
PARTY_LABELS = (
    "더불어민주당", "국민의힘", "조국혁신당", "개혁신당", "진보당", "기본소득당", "사회민주당", "정의당",
    "미래통합당", "자유한국당", "새누리당", "한나라당", "새정치민주연합", "민주통합당", "국민의당",
    "바른미래당", "바른정당", "열린우리당", "민주평화당",
    "열린민주당", "시대전환", "민생당", "대안신당", "우리공화당", "친박신당", "자유선진당",
    "통합민주당", "대통합민주신당", "민주노동당", "선진통일당", "무소속", "새천년민주당", "자민련",
    "자유민주연합", "국민중심당", "창조한국당", "친박연대", "미래희망연대", "통합민주당",
    "더불어시민당", "미래한국당", "국민의미래", "더불어민주연합", "조국혁신당", "개혁신당",
)


class AssemblyFormerMemberError(ValueError):
    pass


def person_id_for(member_code: str) -> UUID:
    return uuid5(_PERSON_NAMESPACE, f"assembly_mona_cd:{member_code}")


def provider_record_key(record: AssemblyHistoricalCareerRecord) -> str:
    return f"{record.member_code}:{record.profile_unit_code}:{record.frto_date}"


def split_term_label(label: str) -> tuple[str | None, str | None]:
    """'제21대 미래통합당 경남 창원시성산구' → ('미래통합당', '경남 창원시성산구')."""

    body = re.sub(r"^\s*제?\s*\d+\s*대\s*", "", label).strip()
    for name in sorted(set(PARTY_LABELS), key=len, reverse=True):
        if body.startswith(name):
            return name, body[len(name):].strip() or None
    return None, None


def normalized_term(
    record: AssemblyHistoricalCareerRecord, hanja_name: str | None
) -> dict[str, object]:
    party, district = split_term_label(record.profile_sj)
    return {
        "member_code": record.member_code,
        "canonical_name": record.name_ko,
        "hanja_name": hanja_name,
        "profile_unit_code": record.profile_unit_code,
        "profile_unit_name": record.profile_unit_name,
        "profile_label": record.profile_sj,
        "frto_date": record.frto_date,
        "term_start": record.valid_from.isoformat(),
        "term_end": record.valid_to.isoformat(),
        "party": party,
        "district": district,
        "term_semantics": "official_historical_member_term_listing",
    }


@dataclass
class FormerMemberPlan:
    person: Person
    action: MaterializationAction
    decision_class: MaterializationDecisionClass
    alias: PersonAlias | None = None
    observations: list[FeederObservation] = field(default_factory=list)
    claims: list[tuple[Claim, ClaimEvidence]] = field(default_factory=list)
    review: IdentityReviewItem | None = None


def build_term_claim(
    person: Person, observation: FeederObservation, source: Source, policy: SourcePolicy
) -> tuple[Claim, ClaimEvidence]:
    require_policy(policy, PolicyAction.STORE_METADATA)
    n = observation.normalized
    start = datetime.combine(datetime.fromisoformat(str(n["term_start"])).date(), time(), UTC)
    end = datetime.combine(datetime.fromisoformat(str(n["term_end"])).date(), time(), UTC)
    qualifiers = {
        "source_contract": FORMER_MEMBER_SOURCE_CONTRACT,
        "source_scope": observation.scope_key,
        "semantic_scope": observation.semantic_scope,
        "provider_record_key": observation.provider_record_key,
        "immutable_observation_hash": observation.content_hash,
        "provider_identity_namespace": "assembly_mona_cd",
        "provider_person_key": str(n["member_code"]),
        "profile_unit_code": str(n["profile_unit_code"]),
        "profile_unit_name": str(n["profile_unit_name"]),
        "profile_label": str(n["profile_label"]),
        "term_start": str(n["term_start"]),
        "term_end": str(n["term_end"]),
    }
    for key in ("party", "district"):
        if n.get(key):
            qualifiers[key] = str(n[key])
    claim = Claim(
        id=uuid5(_CLAIM_NAMESPACE, f"{person.id}|{observation.provider_record_key}|{observation.content_hash}"),
        person_id=person.id,
        proposition=(
            f"{person.canonical_name}의 국회 역대 의원 이력에 「{n['profile_label']}」"
            f"({n['frto_date']}) 임기가 기재되어 있다."
        ),
        subject=person.canonical_name,
        predicate=FORMER_MEMBER_PREDICATE,
        object_text=str(n["profile_label"]),
        qualifiers=qualifiers,
        epistemic_status=EpistemicStatus.FACT,
        publication_status=PublicationStatus.PUBLISHED,
        asserted_as_true=True,
        valid_from=start,
        valid_to=end,
        recorded_at=observation.recorded_at,
    )
    evidence = ClaimEvidence(
        id=uuid5(claim.id, f"{source.id}|{observation.snapshot_id}|{observation.id}|SUPPORT"),
        claim_id=claim.id,
        source_id=source.id,
        snapshot_id=observation.snapshot_id,
        feeder_observation_id=observation.id,
        stance=EvidenceStance.SUPPORT,
    )
    gate = validate_claim_publication(claim, person, [evidence], {source.id: source}, {policy.id: policy})
    if not gate.publishable:
        raise AssemblyFormerMemberError(f"historical term Claim failed gate: {gate.failures}")
    return claim, evidence


@dataclass(frozen=True)
class FormerMemberResult:
    run_id: UUID
    observations: int
    members: int
    created: int
    linked_existing: int
    review_required: int
    claims: int


class AssemblyFormerMemberPublisher:
    def __init__(self, repository: SqlAlchemyRepository) -> None:
        self.repository = repository

    def _latest(self) -> tuple[UUID, list[FeederObservation]]:
        checkpoint = self.repository.source_checkpoint(FORMER_MEMBER_FEEDER, FORMER_MEMBER_SCOPE)
        if checkpoint is None or checkpoint.last_run_id is None:
            raise AssemblyFormerMemberError("former-member success checkpoint is unavailable")
        run = self.repository.source_run(checkpoint.last_run_id)
        if run is None or run.status != SourceRunStatus.SUCCESS:
            raise AssemblyFormerMemberError("former members require the latest successful enumeration")
        hashes = checkpoint.metadata.get("seen_provider_hashes")
        if not isinstance(hashes, dict) or len(hashes) != int(checkpoint.metadata.get("row_total", -1)):
            raise AssemblyFormerMemberError("former-member checkpoint coverage is incomplete")
        by_key = {
            item.provider_record_key: item
            for item in self.repository.feeder_observations(FORMER_MEMBER_FEEDER, FORMER_MEMBER_SCOPE)
            if hashes.get(item.provider_record_key) == item.content_hash
        }
        if set(by_key) != set(hashes):
            raise AssemblyFormerMemberError("former-member manifest lacks committed observations")
        return run.id, [by_key[key] for key in sorted(by_key)]

    def plan(self) -> tuple[UUID, list[FormerMemberPlan]]:
        run_id, observations = self._latest()
        by_member: dict[str, list[FeederObservation]] = {}
        for item in observations:
            by_member.setdefault(str(item.normalized["member_code"]), []).append(item)
        contexts = self.repository.assembly_legislative_source_contexts([item.id for item in observations])
        current = self.repository.assembly_current_person_contexts(sorted(by_member))
        lane_people = self.repository.person_ids_linked_to_feeder(FORMER_MEMBER_FEEDER)
        names = self.repository.current_person_ids_by_name(
            {str(items[0].normalized["canonical_name"]) for items in by_member.values()}
        )
        plans: list[FormerMemberPlan] = []
        for code, items in sorted(by_member.items()):
            items.sort(key=lambda obs: str(obs.normalized["term_start"]))
            name = str(items[-1].normalized["canonical_name"])
            if len({str(obs.normalized["canonical_name"]) for obs in items}) != 1:
                raise AssemblyFormerMemberError(f"MONA_CD {code} has different names across terms")
            own_id = person_id_for(code)
            if code in current:
                person = current[code]
                action, decision = MaterializationAction.AUTO_LINK, MaterializationDecisionClass.EXACT_PROVIDER_IDENTITY
            elif own_id in lane_people:
                person = Person(id=own_id, canonical_name=name, identity_status=IdentityStatus.RESOLVED)
                action, decision = MaterializationAction.AUTO_LINK, MaterializationDecisionClass.EXACT_PROVIDER_IDENTITY
            elif names.get(name):
                plan = FormerMemberPlan(
                    person=Person(id=own_id, canonical_name=name),
                    action=MaterializationAction.REVIEW_REQUIRED,
                    decision_class=MaterializationDecisionClass.SAME_NAME_AMBIGUITY,
                    observations=items,
                )
                plan.review = IdentityReviewItem(
                    id=uuid5(_PERSON_NAMESPACE, f"review:{code}"),
                    observation_id=items[-1].id,
                    candidate_person_id=names[name][0] if len(names[name]) == 1 else None,
                    reason_code=MaterializationDecisionClass.SAME_NAME_AMBIGUITY.value,
                    details={
                        "feeder": FORMER_MEMBER_FEEDER,
                        "provider_person_key": code,
                        "reasons": ["former_member_name_matches_existing_person_no_shared_provider_id"],
                    },
                )
                plans.append(plan)
                continue
            else:
                person = Person(id=own_id, canonical_name=name, identity_status=IdentityStatus.RESOLVED)
                action, decision = MaterializationAction.AUTO_CREATE, MaterializationDecisionClass.AUTHORITATIVE_NEW_IDENTITY
            plan = FormerMemberPlan(person=person, action=action, decision_class=decision, observations=items)
            hanja = items[-1].normalized.get("hanja_name")
            if action == MaterializationAction.AUTO_CREATE and isinstance(hanja, str) and hanja:
                plan.alias = PersonAlias(id=uuid5(own_id, f"alias:{hanja}"), person_id=own_id, name=hanja)
            for obs in items:
                context = contexts.get(obs.id)
                if context is None:
                    raise AssemblyFormerMemberError("former-member observation provenance is incomplete")
                plan.claims.append(build_term_claim(person, obs, *context))
            plans.append(plan)
        return run_id, plans

    def publish(self, *, dry_run: bool = False) -> FormerMemberResult:
        run_id, plans = self.plan()
        if not dry_run:
            self.repository.apply_former_member_plans(plans)
        return FormerMemberResult(
            run_id=run_id,
            observations=sum(len(plan.observations) for plan in plans),
            members=len(plans),
            created=sum(plan.action == MaterializationAction.AUTO_CREATE for plan in plans),
            linked_existing=sum(plan.action == MaterializationAction.AUTO_LINK for plan in plans),
            review_required=sum(plan.action == MaterializationAction.REVIEW_REQUIRED for plan in plans),
            claims=sum(len(plan.claims) for plan in plans),
        )


def link_for(plan: FormerMemberPlan, observation: FeederObservation) -> PersonObservationLink:
    return PersonObservationLink(
        id=uuid5(plan.person.id, f"link:{observation.id}"),
        person_id=plan.person.id,
        observation_id=observation.id,
        action=plan.action,
        decision_class=plan.decision_class,
    )
