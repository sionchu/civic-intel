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
COMMITTEE_ROLE_PREDICATE = "ASSEMBLY_COMMITTEE_ROLE"
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
AUDIT_TARGET_PREDICATE = "LISTED_AS_GUKGAM_AUDIT_TARGET"

PERSON_AFFILIATION_PREDICATES = frozenset(
    {
        COMMITTEE_MEMBERSHIP_PREDICATE,
        COMMITTEE_ROLE_PREDICATE,
        PARTY_PREDICATE,
        ALIO_ROLE_PREDICATE,
        DART_ROLE_PREDICATE,
        WITNESS_PREDICATE,
        BIOGRAPHY_EDUCATION_PREDICATE,
        BIOGRAPHY_CAREER_PREDICATE,
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
    # Free text in one source (biography line). Not bindable: relations stay CANDIDATE.
    SOURCE_TEXT_UNBOUND = "SOURCE_TEXT_UNBOUND"


BINDABLE = frozenset(
    {
        Binding.CANONICAL_ORGANIZATION,
        Binding.PROVIDER_CODE,
        Binding.SOURCE_SCOPED_EXACT_VALUE,
        Binding.EXACT_OFFICIAL_COMMITTEE_NAME_CROSSWALK,
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


_SHARED = "두 Person의 Affiliation이 같은 via entity(정확한 canonical id 또는 source-scoped 값)를 가리킨다"
RULES: tuple[DerivationRule, ...] = (
    DerivationRule(
        "shared_parliamentary_committee", "1.0", "SAME_PARLIAMENTARY_COMMITTEE", Layer.LEGISLATIVE,
        ("PARLIAMENTARY_COMMITTEE",), (COMMITTEE_MEMBERSHIP_PREDICATE,),
        _SHARED + "; 같은 전체 위원명단 수집본(capture)에 함께 기재되면 overlap VERIFIED",
        "SAME_PARLIAMENTARY_COMMITTEE(A,B,via=위원회 코드)",
        ("위원명단에는 시작·종료일이 없어 수집 시점 동시 기재만 확인한다",
         "위원회 명칭이 같아도 코드가 다르면 다른 위원회다"),
    ),
    DerivationRule(
        "shared_special_committee", "1.0", "SAME_SPECIAL_COMMITTEE", Layer.LEGISLATIVE,
        ("SPECIAL_COMMITTEE",), (COMMITTEE_MEMBERSHIP_PREDICATE,),
        _SHARED + "; 위원회 명칭이 '특별위원회'로 끝나는 위원명단 행",
        "SAME_SPECIAL_COMMITTEE(A,B,via=위원회 코드)",
        ("특별위원회는 활동기한이 있으므로 수집 시점 이후 존속을 가정하지 않는다",),
    ),
    DerivationRule(
        "shared_party", "1.0", "SAME_PARTY", Layer.POLITICAL,
        ("PARTY",), (PARTY_PREDICATE,),
        _SHARED + "; 같은 현직 의원 명부 수집본의 정당 값이 정확히 같다",
        "SAME_PARTY(A,B,via=명부상 정당명)",
        ("명부 외 다른 출처의 정당명과 문자열로 결합하지 않는다", "같은 정당은 계파·친분이 아니다"),
        path_default=False,
    ),
    DerivationRule(
        "shared_public_institution", "1.0", "SAME_PUBLIC_INSTITUTION", Layer.PUBLIC_INSTITUTION,
        ("PUBLIC_INSTITUTION",), (ALIO_ROLE_PREDICATE,),
        _SHARED + "; ALIO 공시 기관 canonical Organization id가 같다",
        "SAME_PUBLIC_INSTITUTION(A,B,via=기관); 같은 공시 수집본이면 PUBLIC_INSTITUTION_OVERLAP",
        ("공시 기준일이 다르면 동시 재직으로 보지 않는다",),
        overlap_relation_type="PUBLIC_INSTITUTION_OVERLAP",
    ),
    DerivationRule(
        "shared_company_board", "1.0", "SAME_COMPANY_BOARD", Layer.BUSINESS,
        ("COMPANY",), (DART_ROLE_PREDICATE,),
        _SHARED + "; OpenDART corp_code가 같다",
        "SAME_COMPANY_BOARD(A,B,via=회사); 같은 사업보고서 접수번호에 함께 기재되면 BOARD_INTERLOCK",
        ("회사명 문자열이 아니라 corp_code로만 결합한다",
         "계열사·기업집단은 다른 entity이며 자동 결합하지 않는다",
         "다른 연도 보고서의 임원은 동시 재직으로 보지 않는다"),
        overlap_relation_type="BOARD_INTERLOCK",
    ),
    DerivationRule(
        "committee_witness_request", "1.0", "COMMITTEE_WITNESS_REQUEST", Layer.OVERSIGHT,
        ("PARLIAMENTARY_COMMITTEE", "SPECIAL_COMMITTEE"),
        (COMMITTEE_MEMBERSHIP_PREDICATE, WITNESS_PREDICATE),
        "A는 위원회 위원명단에, B는 같은 위원회(정확한 공식 위원회명 crosswalk)의 국정감사 증인 명단에 기재",
        "COMMITTEE_WITNESS_REQUEST(위원 A, 증인 B, via=위원회)",
        ("증인 명단 등재는 출석요구이며 위법·책임을 뜻하지 않는다",
         "같은 명단의 증인끼리는 관계를 만들지 않는다(동시 등장 금지)",
         "위원 명단 수집일과 증인 채택일이 달라 overlap은 UNKNOWN"),
    ),
    DerivationRule(
        "bill_cosponsorship", "1.0", "BILL_COSPONSORSHIP", Layer.LEGISLATIVE,
        ("BILL",), (BILL_PREDICATE,),
        f"두 Person이 같은 BILL_ID의 대표·공동발의자 code로 기재; {REPEATED_COSPONSORSHIP_MIN_BILLS}건 이상이면 REPEATED_COSPONSORSHIP",
        "BILL_COSPONSORSHIP(A,B,count, bill claims)",
        ("공동발의는 법안 단위 참여이며 정치적 동맹이 아니다", "이름 문자열이 아니라 MONA_CD로만 결합한다"),
        path_default=False,
    ),
    DerivationRule(
        "shared_school_candidate", "1.0", "SAME_SCHOOL", Layer.EDUCATION,
        ("EDUCATIONAL_INSTITUTION",), (BIOGRAPHY_EDUCATION_PREDICATE,),
        "약력 텍스트의 학교명이 정규화 후 같다. canonical 학교 binding이 없어 CANDIDATE",
        "SAME_SCHOOL / SAME_DEPARTMENT candidate; 재학기간이 둘 다 있으면 EDUCATION_TIME_OVERLAP",
        ("같은 학교는 친분이 아니다", "출생연도 차이로 선후배를 추정하지 않는다",
         "대학교와 대학원·부속고등학교는 다른 entity다", "기간이 없으면 overlap을 만들지 않는다"),
        overlap_relation_type="EDUCATION_TIME_OVERLAP",
    ),
    DerivationRule(
        "shared_career_org_candidate", "1.0", "SAME_CAREER_ORGANIZATION", Layer.CAREER,
        ("CAREER_ORGANIZATION", "CAMPAIGN", "TRANSITION_COMMITTEE", "GOVERNMENT_COMMITTEE"),
        (BIOGRAPHY_CAREER_PREDICATE,),
        "약력 경력 행의 조직 문자열이 정규화 후 같다. canonical binding이 없어 CANDIDATE",
        "SAME_CAMPAIGN / SAME_GOVERNMENT_COMMITTEE / SAME_EMPLOYER candidate; 기간 중첩 시 *_OVERLAP",
        ("캠프 인연으로 임명됐다는 인과를 만들지 않는다", "기간이 없으면 overlap을 만들지 않는다"),
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
}
NON_PATH_KINDS = frozenset({"PARTY", "BILL"})


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
    if claim.predicate == BIOGRAPHY_EDUCATION_PREDICATE and contract == BIOGRAPHY_CONTRACT:
        institution = q.get("institution_name")
        if not institution:
            return None
        start, end, precision = _biography_bounds(q)
        return Affiliation(
            via=ViaEntity(f"school_text:{normalize_institution_text(institution)}",
                          "EDUCATIONAL_INSTITUTION", institution, Binding.SOURCE_TEXT_UNBOUND,
                          None, tuple((key, q[key]) for key in ("institution_level", "department_text") if q.get(key))),
            layer=Layer.EDUCATION, affiliation_type="EDUCATION", role=q.get("degree_text"),
            period=Period(start=start, end=end, precision=precision),
            **common,
        )
    if claim.predicate == BIOGRAPHY_CAREER_PREDICATE and contract == BIOGRAPHY_CONTRACT:
        organization_text = q.get("organization_text")
        category = q.get("career_category", "CAREER_ORGANIZATION")
        if not organization_text:
            return None
        kind = category if category in CAREER_RELATION_TYPES else "CAREER_ORGANIZATION"
        start, end, precision = _biography_bounds(q)
        return Affiliation(
            via=ViaEntity(f"career_text:{kind}:{normalize_institution_text(organization_text)}",
                          kind, organization_text, Binding.SOURCE_TEXT_UNBOUND),
            layer=Layer.CAMPAIGN if kind in {"CAMPAIGN", "TRANSITION_COMMITTEE"}
            else Layer.GOVERNMENT if kind == "GOVERNMENT_COMMITTEE" else Layer.CAREER,
            affiliation_type=f"BIOGRAPHY_{category}", role=q.get("role_text"),
            period=Period(start=start, end=end, precision=precision,
                          as_of=_as_date(claim.valid_from),
                          ongoing=q.get("period_ongoing") == "true" or None),
            **common,
        )
    return None


# --------------------------------------------------------------------------------------------
# Temporal comparison


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

        if self.rule.rule_id == "shared_career_org_candidate":
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
    if overlap == Overlap.VERIFIED and rule.overlap_relation_type:
        relation_type = (
            f"{relation_type}_OVERLAP" if rule.rule_id == "shared_career_org_candidate"
            else rule.overlap_relation_type
        )
    if rule.rule_id == "shared_school_candidate":
        left_dept = dict(left.via.attributes).get("department_text")
        if (
            overlap != Overlap.VERIFIED
            and left_dept
            and left_dept == dict(right.via.attributes).get("department_text")
        ):
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
