"""Deterministic Person↔Organization affiliations and Person↔Person relation projection.

Canonical truth stays Person/Organization + published Claim + ClaimEvidence. This module reads
those inputs and computes, at read time, two things that are never stored as a second truth:

1. ``Affiliation``: one Person ↔ one *via entity* (committee, party, institution, company, bill,
   school …) extracted from exactly one published Claim of a known source contract.
2. ``DerivedRelation``: two Persons sharing one via entity under a versioned rule. Every relation
   carries the input Claim and Evidence ids, the rule id/version and its temporal basis.

A via entity is bindable across People only by an exact canonical id or an exact source-scoped
provider value (``binding``). A school or campaign written in free biography text has no such
binding yet, so relations through it are ``CANDIDATE`` and stay out of the default public output.
A shared organization is structural overlap only; it never means friendship, influence or motive.
"""

from __future__ import annotations

import re
from collections import defaultdict, deque
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid5

from packages.domain.contracts import Claim, ClaimEvidence, Organization
from packages.domain.enums import EpistemicStatus, EvidenceStance, PublicationStatus
from packages.rendering.relationship_bindings import (
    OrganizationRegistry,
    campaign_key,
    transition_key,
    university_key,
)

RELATION_PROJECTION_SEMANTICS = "DETERMINISTIC_READ_TIME_PROJECTION_FROM_PUBLISHED_CLAIMS"
RULESET_VERSION = "1.0"
INTERPRETATION_NOTE = (
    "공개 공식자료에 기재된 같은 조직·명단·의안 참여를 기계적으로 비교한 구조적 연결이다. "
    "친분, 영향력, 유착, 인과관계를 뜻하지 않는다."
)
_RELATION_NAMESPACE = UUID("0b6f2f52-5d2a-4f43-9c39-2a1f3e7c9d10")

# Exact source contracts this projection understands. Any other contract fails closed (ignored).
ASSEMBLY_ROSTER_CONTRACT = "assembly_member_roster"
COMMITTEE_MEMBERSHIP_PREDICATE = "ASSEMBLY_COMMITTEE_MEMBERSHIP"
COMMITTEE_MEMBERSHIP_CONTRACT = "assembly_committee_member_list_membership"
PARTY_PREDICATE = "ASSEMBLY_PARTY"
ALIO_ROLE_PREDICATE = "ALIO_REVIEWED_PERSON_ROLE"
ALIO_ROLE_CONTRACT = "alio_reviewed_person_role"
DART_ROLE_PREDICATE = "OPENDART_DISCLOSED_EXECUTIVE_ROLE"
DART_ROLE_CONTRACT = "opendart_reviewed_executive_role"
WITNESS_PREDICATE = "LISTED_AS_GUKGAM_WITNESS"
WITNESS_CONTRACT = "gukgam_witness_reviewed_person_link"
BILL_PREDICATE = "ASSEMBLY_BILL_PARTICIPATION"
BILL_CONTRACT = "assembly_term_bill_participation"
BIOGRAPHY_EDUCATION_PREDICATE = "ASSEMBLY_BIOGRAPHY_EDUCATION"
BIOGRAPHY_CAREER_PREDICATE = "ASSEMBLY_BIOGRAPHY_CAREER"
BIOGRAPHY_CONTRACT = "assembly_member_profile_biography"
NEC_EDUCATION_PREDICATE = "NEC_CANDIDATE_EDUCATION"
NEC_CAREER_PREDICATE = "NEC_CANDIDATE_CAREER"
NEC_CONTRACT = "nec_assembly_candidate_submission"
# Self-reported text lanes sharing one parser and the same registry bindings.
EDUCATION_TEXT_LANES = {(BIOGRAPHY_EDUCATION_PREDICATE, BIOGRAPHY_CONTRACT), (NEC_EDUCATION_PREDICATE, NEC_CONTRACT)}
CAREER_TEXT_LANES = {(BIOGRAPHY_CAREER_PREDICATE, BIOGRAPHY_CONTRACT), (NEC_CAREER_PREDICATE, NEC_CONTRACT)}
AUDIT_TARGET_PREDICATE = "LISTED_AS_GUKGAM_AUDIT_TARGET"
HISTORICAL_TERM_PREDICATE = "ASSEMBLY_HISTORICAL_TERM"
HISTORICAL_TERM_CONTRACT = "assembly_historical_member_term"

PERSON_AFFILIATION_PREDICATES = frozenset(
    {
        COMMITTEE_MEMBERSHIP_PREDICATE,
        PARTY_PREDICATE,
        ALIO_ROLE_PREDICATE,
        DART_ROLE_PREDICATE,
        WITNESS_PREDICATE,
        BIOGRAPHY_EDUCATION_PREDICATE,
        BIOGRAPHY_CAREER_PREDICATE,
        HISTORICAL_TERM_PREDICATE,
        NEC_EDUCATION_PREDICATE,
        NEC_CAREER_PREDICATE,
    }
)
REPEATED_COSPONSORSHIP_MIN_BILLS = 10


class Layer(StrEnum):
    POLITICAL = "POLITICAL"
    LEGISLATIVE = "LEGISLATIVE"
    PUBLIC_INSTITUTION = "PUBLIC_INSTITUTION"
    BUSINESS = "BUSINESS"
    OVERSIGHT = "OVERSIGHT"
    EDUCATION = "EDUCATION"
    CAREER = "CAREER"
    CAMPAIGN = "CAMPAIGN"
    GOVERNMENT = "GOVERNMENT"


class Binding(StrEnum):
    """How a via entity is identified across People."""

    CANONICAL_ORGANIZATION = "CANONICAL_ORGANIZATION"
    PROVIDER_CODE = "PROVIDER_CODE"
    SOURCE_SCOPED_EXACT_VALUE = "SOURCE_SCOPED_EXACT_VALUE"
    EXACT_OFFICIAL_COMMITTEE_NAME_CROSSWALK = "EXACT_OFFICIAL_COMMITTEE_NAME_CROSSWALK"
    # Biography text whose span equals exactly one registry entity (Organization, DART, MOIS).
    EXACT_REGISTRY_NAME = "EXACT_REGISTRY_NAME"
    # Exact full domestic university name or reviewed short-form alias.
    EXACT_UNIVERSITY_NAME = "EXACT_UNIVERSITY_NAME"
    # Reviewed NEC election + exact party name (campaign) or presidential transition committee.
    ELECTION_PARTY_CAMPAIGN = "ELECTION_PARTY_CAMPAIGN"
    # Free text in one source (biography line). Not bindable: relations stay CANDIDATE.
    SOURCE_TEXT_UNBOUND = "SOURCE_TEXT_UNBOUND"


BINDABLE = frozenset(
    {
        Binding.CANONICAL_ORGANIZATION,
        Binding.PROVIDER_CODE,
        Binding.SOURCE_SCOPED_EXACT_VALUE,
        Binding.EXACT_OFFICIAL_COMMITTEE_NAME_CROSSWALK,
        Binding.EXACT_REGISTRY_NAME,
        Binding.EXACT_UNIVERSITY_NAME,
        Binding.ELECTION_PARTY_CAMPAIGN,
    }
)


class RelationStatus(StrEnum):
    DERIVED = "DERIVED"
    CANDIDATE = "CANDIDATE"


class Overlap(StrEnum):
    VERIFIED = "VERIFIED"
    NOT_OVERLAPPING = "NOT_OVERLAPPING"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class ViaEntity:
    key: str
    kind: str
    label: str
    binding: Binding
    organization_id: UUID | None = None
    attributes: tuple[tuple[str, str], ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "key": self.key,
            "kind": self.kind,
            "label": self.label,
            "binding": self.binding.value,
            "organization_id": str(self.organization_id) if self.organization_id else None,
            "attributes": dict(self.attributes),
        }


@dataclass(frozen=True)
class Period:
    """Valid time of one affiliation. Missing parts stay None; nothing is guessed."""

    start: date | None = None
    end: date | None = None
    precision: str = "UNKNOWN"  # DAY / MONTH / YEAR / UNKNOWN for start/end
    as_of: date | None = None  # date the source listed the affiliation
    ongoing: bool | None = None
    # Identifies one complete source enumeration/filing. Two affiliations sharing it were listed
    # together, which verifies co-listing as of that capture.
    capture_keys: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "start": self.start.isoformat() if self.start else None,
            "end": self.end.isoformat() if self.end else None,
            "precision": self.precision,
            "as_of": self.as_of.isoformat() if self.as_of else None,
            "ongoing": self.ongoing,
        }


@dataclass(frozen=True)
class Affiliation:
    person_id: UUID
    via: ViaEntity
    layer: Layer
    affiliation_type: str
    role: str | None
    period: Period
    claim_id: UUID
    evidence_ids: tuple[UUID, ...]
    source_ids: tuple[UUID, ...]
    predicate: str
    epistemic_status: str
    source_conflict: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "person_id": str(self.person_id),
            "via": self.via.to_dict(),
            "layer": self.layer.value,
            "affiliation_type": self.affiliation_type,
            "role": self.role,
            "period": self.period.to_dict(),
            "claim_id": str(self.claim_id),
            "evidence_ids": [str(item) for item in self.evidence_ids],
            "source_ids": [str(item) for item in self.source_ids],
            "predicate": self.predicate,
            "epistemic_status": self.epistemic_status,
            "source_conflict": self.source_conflict,
        }


@dataclass(frozen=True)
class DerivationRule:
    rule_id: str
    version: str
    relation_type: str
    layer: Layer
    via_kinds: tuple[str, ...]
    inputs: tuple[str, ...]
    conditions: str
    outputs: str
    false_positive_conditions: tuple[str, ...]
    # Relation type used when temporal overlap is VERIFIED, if it means something stronger.
    overlap_relation_type: str | None = None
    # Whether the via kind may be traversed by default path search (hubs and events may not).
    path_default: bool = True

    def to_dict(self) -> dict[str, object]:
        return {
            "rule_id": self.rule_id,
            "rule_version": self.version,
            "relation_type": self.relation_type,
            "overlap_relation_type": self.overlap_relation_type,
            "layer": self.layer.value,
            "via_kinds": list(self.via_kinds),
            "inputs": list(self.inputs),
            "conditions": self.conditions,
            "outputs": self.outputs,
            "false_positive_conditions": list(self.false_positive_conditions),
            "path_default": self.path_default,
        }


_SHARED = "두 인물의 소속 기록이 같은 기관·단체를 가리킨다. 정확한 내부 식별자 또는 같은 출처의 식별값으로 확인한다"
RULES: tuple[DerivationRule, ...] = (
    DerivationRule(
        "shared_parliamentary_committee", "1.0", "SAME_PARLIAMENTARY_COMMITTEE", Layer.LEGISLATIVE,
        ("PARLIAMENTARY_COMMITTEE",), (COMMITTEE_MEMBERSHIP_PREDICATE,),
        _SHARED + "; 같은 전체 위원명단 수집본에 함께 기재된 경우만 동시 소속을 확인한다",
        "두 인물의 같은 국회 위원회 소속을 위원회 코드로 확인",
        ("위원명단에는 시작·종료일이 없어 수집 시점 동시 기재만 확인한다",
         "위원회 명칭이 같아도 코드가 다르면 다른 위원회다"),
    ),
    DerivationRule(
        "shared_special_committee", "1.0", "SAME_SPECIAL_COMMITTEE", Layer.LEGISLATIVE,
        ("SPECIAL_COMMITTEE",), (COMMITTEE_MEMBERSHIP_PREDICATE,),
        _SHARED + "; 위원회 명칭이 '특별위원회'로 끝나는 위원명단 행",
        "두 인물의 같은 특별위원회 소속을 위원회 코드로 확인",
        ("특별위원회는 활동기한이 있으므로 수집 시점 이후 존속을 가정하지 않는다",),
    ),
    DerivationRule(
        "shared_party", "1.0", "SAME_PARTY", Layer.POLITICAL,
        ("PARTY",), (PARTY_PREDICATE,),
        _SHARED + "; 같은 현직 의원 명부 수집본의 정당 값이 정확히 같다",
        "두 인물의 같은 정당 소속을 의원 명부상 정당명으로 확인",
        ("명부 외 다른 출처의 정당명과 문자열로 결합하지 않는다", "같은 정당은 계파·친분이 아니다"),
        path_default=False,
    ),
    DerivationRule(
        "shared_legislative_term", "1.0", "SAME_LEGISLATIVE_TERM", Layer.LEGISLATIVE,
        ("LEGISLATIVE_TERM",), (HISTORICAL_TERM_PREDICATE,),
        "두 전직 의원의 역대 의원 이력이 같은 대수이고 임기 기간이 실제로 겹친다",
        "같은 대수의 의원 이력과 임기 중첩을 확인",
        ("같은 대수 의원은 동료 관계를 뜻하지 않는다", "현직 의원의 과거 대수는 제공되지 않아 포함하지 않는다"),
        path_default=False,
    ),
    DerivationRule(
        "shared_public_institution", "1.0", "SAME_PUBLIC_INSTITUTION", Layer.PUBLIC_INSTITUTION,
        ("PUBLIC_INSTITUTION",), (ALIO_ROLE_PREDICATE,),
        _SHARED + "; 공공기관 경영공시의 기관 식별자가 같다",
        "같은 공공기관 소속을 확인하며, 같은 공시 수집본인 경우에만 동시 재직을 확인",
        ("공시 기준일이 다르면 동시 재직으로 보지 않는다",),
        overlap_relation_type="PUBLIC_INSTITUTION_OVERLAP",
    ),
    DerivationRule(
        "shared_company_board", "1.0", "SAME_COMPANY_BOARD", Layer.BUSINESS,
        ("COMPANY",), (DART_ROLE_PREDICATE,),
        _SHARED + "; 전자공시의 회사 고유번호가 같다",
        "같은 회사 임원 공시를 확인하며, 같은 사업보고서 접수번호에 함께 기재된 경우만 동시 임원 기재를 확인",
        ("회사명 문자열이 아니라 회사 고유번호로만 결합한다",
         "계열사·기업집단은 별개 기관이며 자동 결합하지 않는다",
         "다른 연도 보고서의 임원은 동시 재직으로 보지 않는다"),
        overlap_relation_type="BOARD_INTERLOCK",
    ),
    DerivationRule(
        "committee_witness_request", "1.0", "COMMITTEE_WITNESS_REQUEST", Layer.OVERSIGHT,
        ("PARLIAMENTARY_COMMITTEE", "SPECIAL_COMMITTEE"),
        (COMMITTEE_MEMBERSHIP_PREDICATE, WITNESS_PREDICATE),
        "한 인물은 위원회 위원명단에, 다른 인물은 정확한 공식 명칭으로 확인된 같은 위원회의 국정감사 증인 명단에 기재",
        "위원회 명단의 위원과 같은 위원회 증인 명단의 인물을 연결",
        ("증인 명단 등재는 출석요구이며 위법·책임을 뜻하지 않는다",
         "같은 명단의 증인끼리는 관계를 만들지 않는다(동시 등장 금지)",
         "위원 명단 수집일과 증인 채택일이 달라 동시점 관계는 미확인"),
    ),
    DerivationRule(
        "bill_cosponsorship", "1.0", "BILL_COSPONSORSHIP", Layer.LEGISLATIVE,
        ("BILL",), (BILL_PREDICATE,),
        f"두 인물이 같은 의안 식별자의 대표·공동발의자로 기재되며, {REPEATED_COSPONSORSHIP_MIN_BILLS}건 이상이면 반복 공동발의로 표시",
        "같은 법안의 발의 참여 기록과 공동발의 건수를 확인",
        ("공동발의는 법안 단위 참여이며 정치적 동맹이 아니다", "이름 문자열이 아니라 공식 의원 식별자로만 결합한다"),
        path_default=False,
    ),
    DerivationRule(
        "shared_school", "1.1", "SAME_UNIVERSITY", Layer.EDUCATION,
        ("EDUCATIONAL_INSTITUTION",), (BIOGRAPHY_EDUCATION_PREDICATE,),
        "약력 학력 행의 국내 대학 정식명 또는 검토된 약칭이 같으면 근거에서 도출한 관계로 표시한다. 고교·해외 학교·검토되지 않은 약칭은 이름이 같아도 검토 후보로 남긴다",
        "같은 대학·대학원·고교·학과를 구분하며, 두 인물의 재학기간이 모두 확인되면 기간 중첩을 확인",
        ("같은 학교는 친분이 아니다", "출생연도 차이로 선후배를 추정하지 않는다",
         "대학교와 부속·부설 고등학교는 별개 학교다", "동명 고등학교가 여러 지역에 있어 고교는 동일 학교로 확정하지 않는다",
         "기간 정보가 없으면 동시 활동 기간을 추정하지 않는다"),
        overlap_relation_type="EDUCATION_TIME_OVERLAP",
        path_default=False,
    ),
    DerivationRule(
        "shared_government_body", "1.0", "SAME_GOVERNMENT_BODY", Layer.GOVERNMENT,
        ("GOVERNMENT_BODY",), (BIOGRAPHY_CAREER_PREDICATE,),
        "약력 경력 행이 행정표준코드 대표기관명과 정확히 하나로 일치",
        "같은 행정기관 경력을 확인하며, 두 인물의 근무기간이 모두 확인되면 기간 중첩을 확인",
        ("같은 부처 근무 경력은 같은 부서·같은 시기를 뜻하지 않는다", "기간 정보가 없으면 동시 활동 기간을 추정하지 않는다"),
        overlap_relation_type="GOVERNMENT_OVERLAP",
    ),
    DerivationRule(
        "shared_career_org", "1.1", "SAME_CAREER_ORGANIZATION", Layer.CAREER,
        ("CAREER_ORGANIZATION", "CAMPAIGN", "TRANSITION_COMMITTEE", "GOVERNMENT_COMMITTEE",
         "UNIVERSITY_EMPLOYER"),
        (BIOGRAPHY_CAREER_PREDICATE,),
        "선거 캠프는 공식 선거 회차와 정확한 정당명, 인수위원회는 대통령선거 회차가 같을 때만 근거에서 도출한 관계로 표시한다. 그 밖의 경력 문자열은 검토 후보로 남긴다",
        "같은 선거 캠프·인수위원회·정부 위원회·근무기관을 구분하며, 확인된 기간이 겹치는 경우에만 기간 중첩을 표시",
        ("캠프 인연으로 임명됐다는 인과를 만들지 않는다", "경선캠프와 본선 선대위를 시기 구분 없이 같은 캠프로 묶으므로 역할 시기는 보장하지 않는다",
         "기간 정보가 없으면 동시 활동 기간을 추정하지 않는다"),
        overlap_relation_type="CAREER_PERIOD_OVERLAP",
    ),
)
RULES_BY_KIND: dict[str, DerivationRule] = {}
for _rule in RULES:
    if _rule.rule_id == "committee_witness_request":
        continue
    for _kind in _rule.via_kinds:
        RULES_BY_KIND.setdefault(_kind, _rule)
RULES_BY_ID = {rule.rule_id: rule for rule in RULES}
CAREER_RELATION_TYPES = {
    "CAMPAIGN": "SAME_CAMPAIGN",
    "TRANSITION_COMMITTEE": "SAME_TRANSITION_COMMITTEE",
    "GOVERNMENT_COMMITTEE": "SAME_GOVERNMENT_COMMITTEE",
    "CAREER_ORGANIZATION": "SAME_EMPLOYER",
    "UNIVERSITY_EMPLOYER": "SAME_EMPLOYER",
}
NON_PATH_KINDS = frozenset({"PARTY", "BILL", "LEGISLATIVE_TERM"})
NON_RELATION_CAREER_CATEGORIES = frozenset({"LEGISLATURE", "PARTY", "OTHER"})


# --------------------------------------------------------------------------------------------
# Affiliation extraction


@dataclass(frozen=True)
class AffiliationContext:
    """Exact lookups the loader resolves before projection.

    committee_orgs_by_name: official committee name → canonical Organization id, only when exactly
    one current Organization is named ``국회 {name}``.
    witness_committee_org: witness Person Claim id → committee Organization id of the source
    Organization Claim it was copied from.
    capture_keys: Claim id → ids of the complete source run(s) behind its evidence.
    """

    committee_orgs_by_name: Mapping[str, UUID] = field(default_factory=dict)
    witness_committee_org: Mapping[UUID, UUID] = field(default_factory=dict)
    capture_keys: Mapping[UUID, tuple[str, ...]] = field(default_factory=dict)
    organizations: Mapping[UUID, Organization] = field(default_factory=dict)
    registry: OrganizationRegistry | None = None


_REGISTRY_LAYERS = {
    "COMPANY": Layer.BUSINESS,
    "PUBLIC_INSTITUTION": Layer.PUBLIC_INSTITUTION,
    "GOVERNMENT_BODY": Layer.GOVERNMENT,
}
CAREER_REGISTRY_KINDS = frozenset({*_REGISTRY_LAYERS, "UNIVERSITY"})
UNIVERSITY_KINDS = frozenset({"UNIVERSITY"})


def _career_via(
    kind: str, organization_text: str, line: str, context: AffiliationContext
) -> tuple[ViaEntity, Layer]:
    """Bind one biography career line to a campaign, transition committee or registry entity."""

    if kind == "CAMPAIGN":
        campaign = campaign_key(line)
        if campaign is not None:
            key, label, election = campaign
            return (
                ViaEntity(key, "CAMPAIGN", label, Binding.ELECTION_PARTY_CAMPAIGN, None,
                          (("election_code", election.code),)),
                Layer.CAMPAIGN,
            )
    if kind == "TRANSITION_COMMITTEE":
        transition = transition_key(line)
        if transition is not None:
            key, label = transition
            return (
                ViaEntity(key, "TRANSITION_COMMITTEE", label, Binding.ELECTION_PARTY_CAMPAIGN),
                Layer.CAMPAIGN,
            )
    if kind == "GOVERNMENT_COMMITTEE" and context.registry is not None:
        entity = context.registry.bind(organization_text, frozenset({"GOVERNMENT_BODY"}))
        if entity is not None:
            return (
                ViaEntity(entity.key, "GOVERNMENT_COMMITTEE", entity.label,
                          Binding(entity.binding), entity.organization_id),
                Layer.GOVERNMENT,
            )
    if kind == "CAREER_ORGANIZATION" and context.registry is not None:
        entity = context.registry.bind(organization_text, CAREER_REGISTRY_KINDS)
        if entity is not None:
            if entity.kind == "UNIVERSITY":
                # Teaching/research at a university: the university node, as an employer.
                return (
                    ViaEntity(entity.key, "UNIVERSITY_EMPLOYER", entity.label,
                              Binding(entity.binding), entity.organization_id),
                    Layer.CAREER,
                )
            return (
                ViaEntity(entity.key, entity.kind, entity.label, Binding(entity.binding),
                          entity.organization_id),
                _REGISTRY_LAYERS[entity.kind],
            )
    layer = (
        Layer.CAMPAIGN if kind in {"CAMPAIGN", "TRANSITION_COMMITTEE"}
        else Layer.GOVERNMENT if kind == "GOVERNMENT_COMMITTEE" else Layer.CAREER
    )
    return (
        ViaEntity(f"career_text:{kind}:{normalize_institution_text(organization_text)}",
                  kind, organization_text, Binding.SOURCE_TEXT_UNBOUND),
        layer,
    )


def eligible_relation_claim(claim: Claim, evidence: Sequence[ClaimEvidence]) -> bool:
    """Same edge gate as the ontology: current PUBLISHED FACT or attributable CLAIM with support."""

    return (
        claim.publication_status == PublicationStatus.PUBLISHED
        and claim.superseded_at is None
        and claim.epistemic_status in {EpistemicStatus.FACT, EpistemicStatus.CLAIM}
        and any(item.stance == EvidenceStance.SUPPORT for item in evidence)
    )


def _parse_date(value: object) -> date | None:
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def _tenure_start(value: object) -> date | None:
    """Start day of an OpenDART tenure text such as ``2024.04.22.~``; anything else is None."""

    if not isinstance(value, str):
        return None
    match = re.match(r"^\s*(\d{4})\.\s*(\d{1,2})\.\s*(\d{1,2})", value)
    if match is None:
        return None
    try:
        return date(*(int(part) for part in match.groups()))
    except ValueError:
        return None


def _unit_end(value: date, precision: str) -> date:
    if precision == "YEAR":
        return date(value.year, 12, 31)
    if precision == "MONTH":
        following = date(value.year + (value.month == 12), value.month % 12 + 1, 1)
        return following - timedelta(days=1)
    return value


def _biography_bounds(q: Mapping[str, str]) -> tuple[date | None, date | None, str]:
    """Conservative interval from stated biography dates.

    The start is moved to the *end* of its stated unit and the end to the *start* of its unit,
    so "2020.5 ~ 2020.5" or two adjacent year-only ranges never produce a false overlap.
    """

    start, end = _parse_date(q.get("period_start")), _parse_date(q.get("period_end"))
    start_precision = q.get("period_start_precision", "UNKNOWN")
    if start is not None:
        start = _unit_end(start, start_precision)
    if start is not None and end is not None and end < start:
        return None, None, "UNKNOWN"
    precision = start_precision if start is not None else "UNKNOWN"
    return start, end, precision


def _as_date(value: datetime | None) -> date | None:
    return value.date() if value is not None else None


def _committee_kind(name: str) -> str:
    return "SPECIAL_COMMITTEE" if name.endswith("특별위원회") else "PARLIAMENTARY_COMMITTEE"


def _committee_via(code: str, name: str, context: AffiliationContext) -> ViaEntity:
    organization_id = context.committee_orgs_by_name.get(name)
    kind = _committee_kind(name)
    if organization_id is not None:
        return ViaEntity(
            f"organization:{organization_id}", kind, name,
            Binding.EXACT_OFFICIAL_COMMITTEE_NAME_CROSSWALK, organization_id,
            (("committee_code", code),),
        )
    return ViaEntity(
        f"assembly_committee:{code}", kind, name, Binding.PROVIDER_CODE, None,
        (("committee_code", code),),
    )


def normalize_institution_text(value: str) -> str:
    """Whitespace/marker-insensitive key for unbound biography text. Never merges entities."""

    text = re.sub(r"[\s·・ㆍ]+", "", value)
    return re.sub(r"\((?:주|株)\)|㈜|주식회사", "", text)


def extract_affiliation(
    claim: Claim, evidence: Sequence[ClaimEvidence], context: AffiliationContext
) -> Affiliation | None:
    """Map one eligible Person Claim of a known contract to an Affiliation, else None."""

    if claim.person_id is None or not eligible_relation_claim(claim, evidence):
        return None
    q = claim.qualifiers
    contract = q.get("source_contract")
    supports = [item for item in evidence if item.stance == EvidenceStance.SUPPORT]
    common: dict[str, Any] = {
        "person_id": claim.person_id,
        "claim_id": claim.id,
        "evidence_ids": tuple(item.id for item in evidence),
        "source_ids": tuple(dict.fromkeys(item.source_id for item in supports)),
        "predicate": claim.predicate,
        "epistemic_status": claim.epistemic_status.value,
        "source_conflict": any(item.stance == EvidenceStance.REFUTE for item in evidence),
    }
    captures = tuple(context.capture_keys.get(claim.id, ()))

    if claim.predicate == COMMITTEE_MEMBERSHIP_PREDICATE and contract == COMMITTEE_MEMBERSHIP_CONTRACT:
        code, name = q.get("committee_code"), q.get("committee_name")
        if not code or not name:
            return None
        return Affiliation(
            via=_committee_via(code, name, context), layer=Layer.LEGISLATIVE,
            affiliation_type="COMMITTEE_MEMBER", role=q.get("committee_role"),
            period=Period(as_of=_as_date(claim.valid_from), precision="DAY", ongoing=None,
                          capture_keys=captures),
            **common,
        )
    if claim.predicate == PARTY_PREDICATE and contract == ASSEMBLY_ROSTER_CONTRACT:
        if q.get("field_name") != "party" or not claim.object_text.strip():
            return None
        value = claim.object_text.strip()
        return Affiliation(
            via=ViaEntity(f"assembly_roster_party:{value}", "PARTY", value,
                          Binding.SOURCE_SCOPED_EXACT_VALUE),
            layer=Layer.POLITICAL, affiliation_type="PARTY_LISTED", role=None,
            period=Period(as_of=_as_date(claim.valid_from), precision="DAY", capture_keys=captures),
            **common,
        )
    if claim.predicate == ALIO_ROLE_PREDICATE and contract == ALIO_ROLE_CONTRACT:
        raw = q.get("organization_id")
        try:
            organization_id = UUID(str(raw))
        except ValueError:
            return None
        organization = context.organizations.get(organization_id)
        if organization is None or organization.superseded_at is not None:
            return None
        as_of = _parse_date(q.get("as_of"))
        return Affiliation(
            via=ViaEntity(f"organization:{organization_id}", "PUBLIC_INSTITUTION",
                          organization.name, Binding.CANONICAL_ORGANIZATION, organization_id),
            layer=Layer.PUBLIC_INSTITUTION, affiliation_type="DISCLOSED_EXECUTIVE",
            role=q.get("position_text"),
            period=Period(as_of=as_of, precision="DAY" if as_of else "UNKNOWN",
                          capture_keys=(f"alio_as_of:{organization_id}:{as_of}",) if as_of else ()),
            **common,
        )
    if claim.predicate == DART_ROLE_PREDICATE and contract == DART_ROLE_CONTRACT:
        corp_code, receipt = q.get("corp_code"), q.get("receipt_no")
        if not corp_code:
            return None
        start = _tenure_start(q.get("tenure_text"))
        registered = q.get("registered_status")
        role = " · ".join(item for item in (q.get("position"), registered) if item)
        return Affiliation(
            via=ViaEntity(f"opendart_corp:{corp_code}", "COMPANY", q.get("corp_name") or corp_code,
                          Binding.PROVIDER_CODE, None, (("corp_code", corp_code),)),
            layer=Layer.BUSINESS,
            affiliation_type="OUTSIDE_DIRECTOR" if registered == "사외이사" else "DISCLOSED_EXECUTIVE",
            role=role or None,
            period=Period(start=start, as_of=_parse_date(q.get("settlement_date")),
                          precision="DAY" if start else "UNKNOWN",
                          capture_keys=(f"opendart_receipt:{receipt}",) if receipt else ()),
            **common,
        )
    if claim.predicate == WITNESS_PREDICATE and contract == WITNESS_CONTRACT:
        committee_id = context.witness_committee_org.get(claim.id)
        name = q.get("committee_name")
        if committee_id is None or not name:
            return None
        return Affiliation(
            via=ViaEntity(f"organization:{committee_id}", _committee_kind(name), name,
                          Binding.CANONICAL_ORGANIZATION, committee_id),
            layer=Layer.OVERSIGHT, affiliation_type="AUDIT_WITNESS_LISTED",
            role=" · ".join(item for item in (q.get("category"), q.get("affiliation_title")) if item) or None,
            period=Period(as_of=_parse_date(q.get("adoption_date")), precision="DAY"),
            **common,
        )
    if (claim.predicate, contract) in EDUCATION_TEXT_LANES:
        institution = q.get("institution_name")
        if not institution:
            return None
        start, end, precision = _biography_bounds(q)
        attributes = tuple(
            (key, q[key]) for key in ("institution_level", "department_text") if q.get(key)
        )
        bound = university_key(institution, q.get("institution_level"), q.get("country_text"))
        school_entity = (
            context.registry.lookup(bound, UNIVERSITY_KINDS)
            if bound and context.registry is not None
            else None
        )
        if school_entity is not None:
            via = ViaEntity(school_entity.key, "EDUCATIONAL_INSTITUTION", school_entity.label,
                            Binding.EXACT_REGISTRY_NAME, None, attributes)
        elif bound:
            via = ViaEntity(f"university:{bound}", "EDUCATIONAL_INSTITUTION", bound,
                            Binding.EXACT_UNIVERSITY_NAME, None, attributes)
        else:
            via = ViaEntity(f"school_text:{normalize_institution_text(institution)}",
                            "EDUCATIONAL_INSTITUTION", institution, Binding.SOURCE_TEXT_UNBOUND,
                            None, attributes)
        return Affiliation(
            via=via,
            layer=Layer.EDUCATION, affiliation_type="EDUCATION", role=q.get("degree_text"),
            period=Period(start=start, end=end, precision=precision),
            **common,
        )
    if (claim.predicate, contract) in CAREER_TEXT_LANES:
        organization_text = q.get("organization_text")
        category = q.get("career_category", "OTHER")
        # Legislature/party lines duplicate official roster facts; OTHER is unclassified text.
        if not organization_text or category in NON_RELATION_CAREER_CATEGORIES:
            return None
        kind = category if category in CAREER_RELATION_TYPES else "CAREER_ORGANIZATION"
        start, end, precision = _biography_bounds(q)
        line = q.get("line_text", organization_text)
        via, layer = _career_via(kind, organization_text, line, context)
        return Affiliation(
            via=via,
            layer=layer,
            affiliation_type=f"BIOGRAPHY_{category}", role=q.get("role_text"),
            period=Period(start=start, end=end, precision=precision,
                          as_of=_as_date(claim.valid_from),
                          ongoing=q.get("period_ongoing") == "true" or None),
            **common,
        )
    return None


# --------------------------------------------------------------------------------------------
# Temporal comparison


def extract_affiliations(
    claim: Claim, evidence: Sequence[ClaimEvidence], context: AffiliationContext
) -> list[Affiliation]:
    """All affiliations of one Claim: a historical term yields the term and its party."""

    single = extract_affiliation(claim, evidence, context)
    if single is not None:
        return [single]
    q = claim.qualifiers
    if (
        claim.person_id is None
        or claim.predicate != HISTORICAL_TERM_PREDICATE
        or q.get("source_contract") != HISTORICAL_TERM_CONTRACT
        or not eligible_relation_claim(claim, evidence)
    ):
        return []
    unit, label = q.get("profile_unit_code"), q.get("profile_unit_name")
    start, end = _parse_date(q.get("term_start")), _parse_date(q.get("term_end"))
    if not unit or not label or start is None or end is None:
        return []
    supports = [item for item in evidence if item.stance == EvidenceStance.SUPPORT]
    common: dict[str, Any] = {
        "person_id": claim.person_id,
        "claim_id": claim.id,
        "evidence_ids": tuple(item.id for item in evidence),
        "source_ids": tuple(dict.fromkeys(item.source_id for item in supports)),
        "predicate": claim.predicate,
        "epistemic_status": claim.epistemic_status.value,
        "source_conflict": any(item.stance == EvidenceStance.REFUTE for item in evidence),
    }
    period = Period(start=start, end=end, precision="DAY")
    found = [
        Affiliation(
            via=ViaEntity(f"assembly_term:{unit}", "LEGISLATIVE_TERM", f"{label} 국회",
                          Binding.PROVIDER_CODE),
            layer=Layer.LEGISLATIVE, affiliation_type="FORMER_MEMBER_TERM",
            role=q.get("district"), period=period, **common,
        )
    ]
    party = q.get("party")
    if party:
        found.append(
            Affiliation(
                via=ViaEntity(f"assembly_term_party:{unit}:{party}", "PARTY", f"{label} {party}",
                              Binding.SOURCE_SCOPED_EXACT_VALUE),
                layer=Layer.POLITICAL, affiliation_type="PARTY_LISTED", role=None,
                period=period, **common,
            )
        )
    return found


def _interval(period: Period) -> tuple[date, date] | None:
    if period.start is None:
        return None
    if period.end is not None:
        return period.start, period.end
    if period.ongoing and period.as_of is not None:
        return period.start, period.as_of
    return None


def temporal_overlap(left: Period, right: Period) -> tuple[Overlap, str]:
    """Overlap is VERIFIED only from shared capture or two fully known intervals."""

    shared = set(left.capture_keys) & set(right.capture_keys)
    if shared:
        return Overlap.VERIFIED, "SAME_SOURCE_CAPTURE"
    a, b = _interval(left), _interval(right)
    if a and b:
        if a[0] <= b[1] and b[0] <= a[1]:
            return Overlap.VERIFIED, "KNOWN_INTERVALS_OVERLAP"
        return Overlap.NOT_OVERLAPPING, "KNOWN_INTERVALS_DISJOINT"
    for interval, other in ((a, right), (b, left)):
        if interval and other.as_of and interval[0] <= other.as_of <= interval[1]:
            return Overlap.VERIFIED, "AS_OF_WITHIN_KNOWN_INTERVAL"
    return Overlap.UNKNOWN, "INSUFFICIENT_PERIOD_EVIDENCE"


# --------------------------------------------------------------------------------------------
# Derived relations


@dataclass(frozen=True)
class DerivedRelation:
    relation_id: UUID
    rule: DerivationRule
    relation_type: str
    status: RelationStatus
    subject: Affiliation
    counterpart: Affiliation
    overlap: Overlap
    overlap_basis: str

    @property
    def via(self) -> ViaEntity:
        return self.subject.via

    @property
    def layer(self) -> Layer:
        """Career-text relations keep the affiliation's layer (campaign, government, career)."""

        if self.rule.rule_id == "shared_career_org":
            return self.subject.layer
        return self.rule.layer

    def to_dict(self) -> dict[str, object]:
        confidence = (
            "HIGH" if {self.subject.epistemic_status, self.counterpart.epistemic_status} == {"FACT"}
            else "ATTRIBUTED"
        )
        if self.status == RelationStatus.CANDIDATE:
            confidence = "UNBOUND_TEXT"
        proximity = 1 + (self.overlap == Overlap.VERIFIED) + (
            self.subject.role is not None and self.subject.role == self.counterpart.role
        )
        return {
            "relation_id": str(self.relation_id),
            "relation_type": self.relation_type,
            "status": self.status.value,
            "layer": self.layer.value,
            "rule_id": self.rule.rule_id,
            "rule_version": self.rule.version,
            "subject_person_id": str(self.subject.person_id),
            "object_person_id": str(self.counterpart.person_id),
            "via": self.via.to_dict(),
            "subject_role": self.subject.role,
            "object_role": self.counterpart.role,
            "temporal": {
                "overlap": self.overlap.value,
                "basis": self.overlap_basis,
                "subject_period": self.subject.period.to_dict(),
                "object_period": self.counterpart.period.to_dict(),
            },
            "source_claim_ids": [str(self.subject.claim_id), str(self.counterpart.claim_id)],
            "evidence_ids": [str(item) for item in (*self.subject.evidence_ids, *self.counterpart.evidence_ids)],
            "source_ids": [str(item) for item in dict.fromkeys((*self.subject.source_ids, *self.counterpart.source_ids))],
            "source_conflict": self.subject.source_conflict or self.counterpart.source_conflict,
            "scores": {
                "evidence_confidence": confidence,
                "structural_proximity": proximity,
                "temporal_currency_as_of": _latest_iso(
                    self.subject.period.as_of, self.counterpart.period.as_of
                ),
            },
            "interpretation_note": INTERPRETATION_NOTE,
        }


def _latest_iso(*values: date | None) -> str | None:
    known = [item for item in values if item is not None]
    return max(known).isoformat() if known else None


def _relation_id(rule: DerivationRule, left: Affiliation, right: Affiliation) -> UUID:
    first, second = sorted((left, right), key=lambda item: (str(item.person_id), str(item.claim_id)))
    return uuid5(
        _RELATION_NAMESPACE,
        "|".join((rule.rule_id, rule.version, first.via.key, str(first.claim_id), str(second.claim_id))),
    )


def derive_pair(left: Affiliation, right: Affiliation) -> DerivedRelation | None:
    """Apply the single matching rule to two affiliations of different People, else None."""

    if left.person_id == right.person_id or left.via.key != right.via.key:
        return None
    witness = {left.affiliation_type, right.affiliation_type} & {"AUDIT_WITNESS_LISTED"}
    if witness:
        # Only member ↔ witness of the same committee. Witness ↔ witness is co-listing only.
        member = [item for item in (left, right) if item.affiliation_type == "COMMITTEE_MEMBER"]
        if len(member) != 1:
            return None
        rule = RULES_BY_ID["committee_witness_request"]
        subject = member[0]
        other = right if subject is left else left
        return DerivedRelation(
            _relation_id(rule, subject, other), rule, rule.relation_type, RelationStatus.DERIVED,
            subject, other, Overlap.UNKNOWN, "MEMBER_LIST_AND_WITNESS_LIST_DATES_DIFFER",
        )
    matched = RULES_BY_KIND.get(left.via.kind)
    if matched is None or left.via.kind != right.via.kind or left.layer != right.layer:
        return None
    rule = matched
    overlap, basis = temporal_overlap(left.period, right.period)
    relation_type = rule.relation_type
    if left.via.kind in CAREER_RELATION_TYPES:
        relation_type = CAREER_RELATION_TYPES[left.via.kind]
    disclosed = {"DISCLOSED_EXECUTIVE", "OUTSIDE_DIRECTOR"}
    if rule.rule_id == "shared_company_board" and not (
        left.affiliation_type in disclosed and right.affiliation_type in disclosed
    ):
        # A biography employment line is not a board seat.
        relation_type = "SAME_EMPLOYER"
    if rule.rule_id == "shared_school":
        levels = {dict(item.via.attributes).get("institution_level") for item in (left, right)}
        if levels == {"GRADUATE_SCHOOL"}:
            relation_type = "SAME_GRADUATE_SCHOOL"
        elif levels <= {"HIGH_SCHOOL"}:
            relation_type = "SAME_HIGH_SCHOOL"
        elif levels & {"MIDDLE_SCHOOL", "ELEMENTARY_SCHOOL"}:
            relation_type = "SAME_SCHOOL"
    if overlap == Overlap.VERIFIED and rule.overlap_relation_type:
        if rule.rule_id == "shared_career_org":
            relation_type = f"{relation_type}_OVERLAP"
        elif relation_type == "SAME_EMPLOYER":
            relation_type = "EMPLOYMENT_OVERLAP"
        else:
            relation_type = rule.overlap_relation_type
    if rule.rule_id == "shared_school" and overlap != Overlap.VERIFIED:
        left_dept = dict(left.via.attributes).get("department_text")
        if left_dept and left_dept == dict(right.via.attributes).get("department_text"):
            relation_type = "SAME_DEPARTMENT"
    bindable = left.via.binding in BINDABLE and right.via.binding in BINDABLE
    status = RelationStatus.DERIVED if bindable else RelationStatus.CANDIDATE
    subject, other = sorted((left, right), key=lambda item: str(item.person_id))
    return DerivedRelation(
        _relation_id(rule, left, right), rule, relation_type, status, subject, other, overlap, basis,
    )


def index_by_via(affiliations: Iterable[Affiliation]) -> dict[str, list[Affiliation]]:
    """Candidate pairs come from shared via entities only (no N² Person comparison)."""

    index: dict[str, list[Affiliation]] = defaultdict(list)
    for item in affiliations:
        index[item.via.key].append(item)
    return index


def relations_for_person(
    person_id: UUID,
    affiliations: Sequence[Affiliation],
    *,
    include_candidates: bool = False,
    layers: Iterable[str] | None = None,
) -> list[DerivedRelation]:
    wanted = set(layers) if layers else None
    index = index_by_via(affiliations)
    relations: dict[UUID, DerivedRelation] = {}
    for own in (item for item in affiliations if item.person_id == person_id):
        for other in index.get(own.via.key, ()):
            relation = derive_pair(own, other)
            if relation is None:
                continue
            if relation.status == RelationStatus.CANDIDATE and not include_candidates:
                continue
            if wanted and relation.layer.value not in wanted:
                continue
            relations[relation.relation_id] = relation
    return sorted(
        relations.values(),
        key=lambda item: (item.layer.value, item.via.label, item.relation_type, str(item.relation_id)),
    )


@dataclass(frozen=True)
class CosponsorshipPair:
    person_id: UUID
    other_person_id: UUID
    bill_ids: tuple[str, ...]
    claim_ids: tuple[UUID, ...]

    def to_dict(self, *, claim_limit: int = 20) -> dict[str, object]:
        count = len(self.bill_ids)
        return {
            "relation_type": "REPEATED_COSPONSORSHIP"
            if count >= REPEATED_COSPONSORSHIP_MIN_BILLS else "BILL_COSPONSORSHIP",
            "status": RelationStatus.DERIVED.value,
            "layer": Layer.LEGISLATIVE.value,
            "rule_id": "bill_cosponsorship",
            "rule_version": RULES_BY_ID["bill_cosponsorship"].version,
            "subject_person_id": str(self.person_id),
            "object_person_id": str(self.other_person_id),
            "shared_bill_count": count,
            "source_claim_ids": [str(item) for item in self.claim_ids[:claim_limit]],
            "source_claim_ids_truncated": len(self.claim_ids) > claim_limit,
            "interpretation_note": INTERPRETATION_NOTE,
        }


def cosponsorship_pairs(
    person_id: UUID,
    bill_participants: Mapping[str, Sequence[tuple[UUID, UUID]]],
) -> list[CosponsorshipPair]:
    """bill_participants: BILL_ID → [(person_id, participation claim id)] from published Claims."""

    shared: dict[UUID, list[tuple[str, UUID, UUID]]] = defaultdict(list)
    for bill_id, participants in bill_participants.items():
        own = [claim for person, claim in participants if person == person_id]
        if not own:
            continue
        for other, claim in participants:
            if other != person_id:
                shared[other].append((bill_id, own[0], claim))
    pairs = [
        CosponsorshipPair(
            person_id, other, tuple(sorted({bill for bill, _, _ in rows})),
            tuple(dict.fromkeys(item for _, mine, theirs in sorted(rows) for item in (mine, theirs))),
        )
        for other, rows in shared.items()
    ]
    return sorted(pairs, key=lambda item: (-len(item.bill_ids), str(item.other_person_id)))


# --------------------------------------------------------------------------------------------
# Path search


@dataclass(frozen=True)
class OrganizationLink:
    """Organization ↔ Organization edge from a published Organization Claim (e.g. audit target)."""

    source_organization_id: UUID
    target_via_key: str
    target_label: str
    relation_type: str
    claim_id: UUID
    evidence_ids: tuple[UUID, ...]
    as_of: date | None


def shortest_evidence_path(
    start: UUID,
    goal: UUID,
    affiliations: Sequence[Affiliation],
    *,
    organization_links: Sequence[OrganizationLink] = (),
    organization_labels: Mapping[UUID, str] | None = None,
    include_kinds: Iterable[str] | None = None,
    max_edges: int = 8,
) -> dict[str, object] | None:
    """Breadth-first shortest path over the bipartite Person–via graph (deterministic order).

    Only bindable via entities are traversed. Hub/event kinds (party, bill) are excluded unless
    requested via ``include_kinds``. Every edge carries its supporting Claim and Evidence ids.
    """

    allowed_extra = set(include_kinds or ())
    graph: dict[str, list[tuple[str, dict[str, Any]]]] = defaultdict(list)
    labels: dict[str, str] = {}
    vias: dict[str, ViaEntity] = {}
    for item in affiliations:
        if item.via.binding not in BINDABLE:
            continue
        if item.via.kind in NON_PATH_KINDS and item.via.kind not in allowed_extra:
            continue
        person_node, via_node = f"person:{item.person_id}", f"via:{item.via.key}"
        vias[via_node] = item.via
        labels[via_node] = item.via.label
        edge: dict[str, Any] = {
            "relation_type": item.affiliation_type,
            "layer": item.layer.value,
            "role": item.role,
            "period": item.period.to_dict(),
            "claim_ids": [str(item.claim_id)],
            "evidence_ids": [str(value) for value in item.evidence_ids],
            "epistemic_status": item.epistemic_status,
        }
        graph[person_node].append((via_node, edge))
        graph[via_node].append((person_node, edge))
    for link in organization_links:
        source_node = f"via:organization:{link.source_organization_id}"
        target_node = f"via:{link.target_via_key}"
        labels.setdefault(source_node, (organization_labels or {}).get(link.source_organization_id, ""))
        labels.setdefault(target_node, link.target_label)
        link_edge: dict[str, Any] = {
            "relation_type": link.relation_type,
            "layer": Layer.OVERSIGHT.value,
            "role": None,
            "period": {"as_of": link.as_of.isoformat() if link.as_of else None},
            "claim_ids": [str(link.claim_id)],
            "evidence_ids": [str(value) for value in link.evidence_ids],
            "epistemic_status": "FACT",
        }
        graph[source_node].append((target_node, link_edge))
        graph[target_node].append((source_node, link_edge))
    origin, target = f"person:{start}", f"person:{goal}"
    if origin not in graph or target not in graph:
        return None
    for neighbors in graph.values():
        neighbors.sort(key=lambda pair: (pair[0], str(pair[1]["claim_ids"])))
    previous: dict[str, tuple[str, dict[str, Any]] | None] = {origin: None}
    queue: deque[tuple[str, int]] = deque([(origin, 0)])
    while queue:
        node, depth = queue.popleft()
        if node == target:
            break
        if depth >= max_edges:
            continue
        for neighbor, edge in graph[node]:
            if neighbor not in previous:
                previous[neighbor] = (node, edge)
                queue.append((neighbor, depth + 1))
    if target not in previous:
        return None
    chain: list[tuple[str, str, dict[str, Any]]] = []
    node = target
    while previous[node] is not None:
        step = previous[node]
        assert step is not None
        parent, step_edge = step
        chain.append((parent, node, step_edge))
        node = parent
    chain.reverse()
    node_ids = [origin] + [step[1] for step in chain]
    nodes: list[dict[str, Any]] = []
    for node_id in node_ids:
        if node_id.startswith("person:"):
            nodes.append({"id": node_id, "kind": "PERSON", "person_id": node_id.split(":", 1)[1]})
        else:
            via = vias.get(node_id)
            nodes.append({
                "id": node_id,
                "kind": via.kind if via else "ORGANIZATION",
                "label": labels.get(node_id, ""),
                "via": via.to_dict() if via else None,
            })
    edges: list[dict[str, Any]] = [
        {"source": a, "target": b, **values} for a, b, values in chain
    ]
    claim_ids = [cid for item in edges for cid in item["claim_ids"]]
    return {
        "nodes": nodes,
        "edges": edges,
        "source_claim_ids": list(dict.fromkeys(claim_ids)),
        "path_length": len(edges),
        "excluded_kinds": sorted(NON_PATH_KINDS - allowed_extra),
        "interpretation_note": INTERPRETATION_NOTE,
    }


# --------------------------------------------------------------------------------------------
# Career transitions (revolving door)

SECTOR_BY_KIND = {
    "GOVERNMENT_BODY": "GOVERNMENT",
    "PUBLIC_INSTITUTION": "PUBLIC_INSTITUTION",
    "COMPANY": "BUSINESS",
}
REVOLVING_DOOR_TYPES = {
    ("GOVERNMENT", "BUSINESS"): "GOVERNMENT_TO_BUSINESS",
    ("BUSINESS", "GOVERNMENT"): "BUSINESS_TO_GOVERNMENT",
    ("PUBLIC_INSTITUTION", "BUSINESS"): "PUBLIC_INSTITUTION_TO_PRIVATE",
    ("BUSINESS", "PUBLIC_INSTITUTION"): "PRIVATE_TO_PUBLIC",
}


def _month(value: date) -> tuple[int, int]:
    return value.year, value.month


def career_transitions(
    affiliations: Sequence[Affiliation], *, include_candidates: bool = False
) -> list[dict[str, object]]:
    """Ordered sector moves of one Person from stated periods only (rule revolving_door 1.0).

    A move A → B is emitted only when A has a stated end and B a stated start in a strictly later
    month. The output describes a sequence; it never states a reason for the move.
    """

    dated = [
        item
        for item in affiliations
        if item.via.kind in SECTOR_BY_KIND
        and (include_candidates or item.via.binding in BINDABLE)
    ]
    moves: list[dict[str, object]] = []
    for earlier in dated:
        for later in dated:
            if earlier is later or earlier.period.end is None or later.period.start is None:
                continue
            if _month(earlier.period.end) >= _month(later.period.start):
                continue
            kind = REVOLVING_DOOR_TYPES.get(
                (SECTOR_BY_KIND[earlier.via.kind], SECTOR_BY_KIND[later.via.kind])
            )
            if kind is None:
                continue
            bound = earlier.via.binding in BINDABLE and later.via.binding in BINDABLE
            moves.append({
                "transition_type": kind,
                "status": (RelationStatus.DERIVED if bound else RelationStatus.CANDIDATE).value,
                "rule_id": "revolving_door",
                "rule_version": "1.0",
                "from": earlier.via.to_dict() | {"period": earlier.period.to_dict(), "role": earlier.role},
                "to": later.via.to_dict() | {"period": later.period.to_dict(), "role": later.role},
                "source_claim_ids": [str(earlier.claim_id), str(later.claim_id)],
                "basis": "STATED_PERIODS_STRICTLY_ORDERED_BY_MONTH",
                "interpretation_note": INTERPRETATION_NOTE,
            })
    return sorted(moves, key=lambda item: (str(item["to"]["period"]["start"]), str(item["transition_type"])))  # type: ignore[index]
