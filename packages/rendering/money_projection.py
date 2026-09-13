from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from decimal import ROUND_HALF_UP, Decimal
from typing import Any
from urllib.parse import parse_qs, urlparse
from uuid import UUID

from packages.connectors.alio_disclosures import (
    ALIO_ITEM12_SOURCE_CONTRACT,
    ITEM12_REPORT_FORM_NO,
    POLICY_ID,
)
from packages.domain.contracts import (
    Claim,
    ClaimEvidence,
    FeederObservation,
    Organization,
    Source,
    SourcePolicy,
    SourceSnapshot,
)
from packages.domain.enums import EpistemicStatus, EvidenceStance, PublicationStatus
from packages.verification.claims import validate_claim_publication

MONEY_METHOD_VERSION = "money.alio-head-expense-yoy.v1"
MONEY_FEEDER = "alio_institution_head_business_expense"
MONEY_SEMANTIC_SCOPE = "institutional_head_business_expense_annual_disclosure"
_PERCENT_QUANTUM = Decimal("0.01")


def _ordered_unique(values: Sequence[str]) -> list[str]:
    return list(dict.fromkeys(values))


def _require_int(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"ALIO MONEY field is not a non-negative integer: {field}")
    return value


def _validated_input(
    observation: FeederObservation,
    *,
    snapshots: Mapping[UUID, SourceSnapshot],
    sources: Mapping[UUID, Source],
) -> dict[str, Any]:
    if observation.feeder != MONEY_FEEDER:
        raise ValueError("MONEY input feeder is outside the ALIO Item 12 lane")
    if observation.semantic_scope != MONEY_SEMANTIC_SCOPE:
        raise ValueError("MONEY input semantic scope is outside the ALIO Item 12 lane")
    if observation.identity_hints:
        raise ValueError("ALIO MONEY observations may not carry Person identity hints")
    normalized = observation.normalized
    required = {
        "institution_code",
        "institution_name",
        "report_form_no",
        "role_scope",
        "disclosure_no",
        "report_period",
        "fiscal_year",
        "amount_thousand_krw",
        "amount_krw",
        "currency",
        "source_unit",
        "as_of_date",
        "submission_date",
        "source_ref",
    }
    if not required.issubset(normalized):
        missing = ", ".join(sorted(required - normalized.keys()))
        raise ValueError(f"ALIO MONEY observation lacks fields: {missing}")
    if normalized["role_scope"] != "INSTITUTION_HEAD":
        raise ValueError("ALIO MONEY role scope is not institution head")
    if normalized["report_form_no"] != ITEM12_REPORT_FORM_NO:
        raise ValueError("ALIO MONEY report form is not item 12")
    if normalized["currency"] != "KRW" or normalized["source_unit"] != "THOUSAND_KRW":
        raise ValueError("ALIO MONEY currency or unit is unsupported")
    fiscal_year = _require_int(normalized["fiscal_year"], "fiscal_year")
    if fiscal_year < 1900:
        raise ValueError("ALIO MONEY fiscal year is invalid")
    amount_thousand_krw = _require_int(normalized["amount_thousand_krw"], "amount_thousand_krw")
    amount_krw = _require_int(normalized["amount_krw"], "amount_krw")
    if amount_krw != amount_thousand_krw * 1000:
        raise ValueError("ALIO MONEY amount normalization is inconsistent")
    disclosure_no = normalized["disclosure_no"]
    if not isinstance(disclosure_no, str) or not disclosure_no.isdigit():
        raise ValueError("ALIO MONEY disclosure identity is invalid")
    if normalized["source_ref"] != disclosure_no:
        raise ValueError("ALIO MONEY source reference is inconsistent")
    expected_key = f"{disclosure_no}:{fiscal_year}"
    if observation.provider_record_key != expected_key:
        raise ValueError("ALIO MONEY provider record key is inconsistent")

    snapshot = snapshots.get(observation.snapshot_id)
    if snapshot is None or snapshot.id != observation.snapshot_id:
        raise ValueError("ALIO MONEY snapshot provenance is unavailable")
    if (
        snapshot.metadata.get("source_contract") != ALIO_ITEM12_SOURCE_CONTRACT
        or snapshot.metadata.get("report_form_no") != ITEM12_REPORT_FORM_NO
        or snapshot.metadata.get("disclosure_no") != disclosure_no
        or snapshot.metadata.get("institution_code") != normalized["institution_code"]
        or snapshot.metadata.get("report_period") != normalized["report_period"]
        or snapshot.fulltext is not None
    ):
        raise ValueError("ALIO MONEY snapshot contract provenance is inconsistent")
    source = sources.get(snapshot.source_id)
    if source is None or source.id != snapshot.source_id:
        raise ValueError("ALIO MONEY source provenance is unavailable")
    if source.policy_id != POLICY_ID:
        raise ValueError("ALIO MONEY source policy provenance is inconsistent")
    parsed = urlparse(str(source.url))
    query = parse_qs(parsed.query, keep_blank_values=True)
    if (
        parsed.scheme != "https"
        or parsed.hostname != "alio.go.kr"
        or parsed.path != "/mobile/item/itemReportTerm.do"
        or set(query) != {"apbaId", "reportFormRootNo", "disclosureNo", "nowYear", "nowQuarter"}
        or any(len(values) != 1 for values in query.values())
        or query["apbaId"][0] != normalized["institution_code"]
        or query["reportFormRootNo"][0] != ITEM12_REPORT_FORM_NO
        or query["disclosureNo"][0] != disclosure_no
        or f"{query['nowYear'][0]}-Q{query['nowQuarter'][0]}" != normalized["report_period"]
    ):
        raise ValueError("ALIO MONEY source provenance is not official ALIO")
    return {
        "observation": observation,
        "normalized": normalized,
        "snapshot": snapshot,
        "source": source,
        "fiscal_year": fiscal_year,
        "amount_thousand_krw": amount_thousand_krw,
        "amount_krw": amount_krw,
    }


def _input_details(item: dict[str, Any]) -> dict[str, Any]:
    observation: FeederObservation = item["observation"]
    normalized: dict[str, Any] = item["normalized"]
    snapshot: SourceSnapshot = item["snapshot"]
    source: Source = item["source"]
    return {
        "fiscal_year": item["fiscal_year"],
        "amount_thousand_krw": item["amount_thousand_krw"],
        "amount_krw": item["amount_krw"],
        "report_period": normalized["report_period"],
        "as_of_date": normalized["as_of_date"],
        "submission_date": normalized["submission_date"],
        "disclosure_no": normalized["disclosure_no"],
        "observation_id": str(observation.id),
        "snapshot_id": str(snapshot.id),
        "source_id": str(source.id),
    }


def build_alio_head_expense_claim(
    observation: FeederObservation,
    *,
    organization: Organization,
    policy: SourcePolicy,
    snapshots: Mapping[UUID, SourceSnapshot],
    sources: Mapping[UUID, Source],
) -> tuple[Claim, ClaimEvidence]:
    """Build one reviewed annual disclosure Claim for an existing Organization.

    The ALIO institution code remains a source-scoped crosswalk value. This function never
    creates or resolves an Organization; the caller supplies the reviewed canonical target.
    """

    item = _validated_input(observation, snapshots=snapshots, sources=sources)
    normalized: dict[str, Any] = item["normalized"]
    source: Source = item["source"]
    if source.policy_id != policy.id:
        raise ValueError("ALIO MONEY Claim policy does not match Source")
    if organization.superseded_at is not None:
        raise ValueError("ALIO MONEY Claim requires a current Organization")
    if organization.name != normalized["institution_name"]:
        raise ValueError("ALIO MONEY Claim Organization does not match source institution name")

    fiscal_year = item["fiscal_year"]
    amount_thousand_krw = item["amount_thousand_krw"]
    claim = Claim(
        organization_id=organization.id,
        proposition=(
            f"{organization.name}는 {fiscal_year} 회계연도 기관장 업무추진비로 "
            f"{amount_thousand_krw:,}천원을 공시했다."
        ),
        subject=organization.name,
        predicate="DISCLOSED_BUSINESS_EXPENSE",
        object_text=f"{amount_thousand_krw:,}천원",
        qualifiers={
            "source_contract": ALIO_ITEM12_SOURCE_CONTRACT,
            "report_form_no": ITEM12_REPORT_FORM_NO,
            "institution_code": normalized["institution_code"],
            "role_scope": normalized["role_scope"],
            "disclosure_no": normalized["disclosure_no"],
            "report_period": normalized["report_period"],
            "fiscal_year": str(fiscal_year),
            "currency": normalized["currency"],
            "source_unit": normalized["source_unit"],
            "as_of_date": normalized["as_of_date"],
            "submission_date": normalized["submission_date"],
            "provider_record_key": observation.provider_record_key,
        },
        epistemic_status=EpistemicStatus.FACT,
        publication_status=PublicationStatus.PUBLISHED,
        asserted_as_true=True,
    )
    evidence = ClaimEvidence(
        claim_id=claim.id,
        source_id=source.id,
        snapshot_id=observation.snapshot_id,
        feeder_observation_id=observation.id,
        stance=EvidenceStance.SUPPORT,
    )
    gate = validate_claim_publication(
        claim,
        organization,
        [evidence],
        {source.id: source},
        {policy.id: policy},
    )
    if not gate.publishable:
        raise ValueError(f"ALIO MONEY Claim failed publication gate: {gate.failures}")
    return claim, evidence


def build_alio_head_expense_money(
    observations: Sequence[FeederObservation],
    *,
    snapshots: Mapping[UUID, SourceSnapshot],
    sources: Mapping[UUID, Source],
    earlier_fiscal_year: int,
    later_fiscal_year: int,
) -> dict[str, Any]:
    """Build one descriptive Item 12 fiscal-year comparison from exact observations."""

    if earlier_fiscal_year >= later_fiscal_year:
        raise ValueError("MONEY comparison requires an earlier and a later fiscal year")
    if not observations:
        raise ValueError("MONEY comparison requires at least two observations")

    inputs = [
        _validated_input(observation, snapshots=snapshots, sources=sources)
        for observation in observations
    ]
    institutions = {
        (
            item["normalized"]["institution_code"],
            item["normalized"]["institution_name"],
            item["normalized"]["role_scope"],
        )
        for item in inputs
    }
    if len(institutions) != 1:
        raise ValueError("MONEY comparison cannot combine institution or role scopes")
    disclosure_ids = {item["normalized"]["disclosure_no"] for item in inputs}
    snapshot_id_set = {item["observation"].snapshot_id for item in inputs}
    if len(disclosure_ids) != 1 or len(snapshot_id_set) != 1:
        raise ValueError("MONEY comparison cannot combine disclosure versions")

    by_year: dict[int, dict[str, Any]] = {}
    for item in inputs:
        fiscal_year = item["fiscal_year"]
        if fiscal_year in by_year:
            raise ValueError("MONEY comparison has multiple immutable versions for a fiscal year")
        by_year[fiscal_year] = item
    if earlier_fiscal_year not in by_year or later_fiscal_year not in by_year:
        raise ValueError("MONEY comparison lacks one of the requested fiscal-year observations")

    earlier = by_year[earlier_fiscal_year]
    later = by_year[later_fiscal_year]
    earlier_normalized = earlier["normalized"]
    later_normalized = later["normalized"]
    if earlier_normalized["currency"] != later_normalized["currency"]:
        raise ValueError("MONEY comparison currency semantics differ")
    if earlier_normalized["source_unit"] != later_normalized["source_unit"]:
        raise ValueError("MONEY comparison unit semantics differ")
    if earlier_normalized["report_period"] != later_normalized["report_period"]:
        raise ValueError("MONEY comparison report-period scope differs")

    absolute_delta = later["amount_krw"] - earlier["amount_krw"]
    if earlier["amount_krw"] == 0:
        percent_change: str | None = None
    else:
        percent_change = str(
            (Decimal(absolute_delta) / Decimal(earlier["amount_krw"]) * Decimal(100)).quantize(
                _PERCENT_QUANTUM, rounding=ROUND_HALF_UP
            )
        )

    earlier_observation: FeederObservation = earlier["observation"]
    later_observation: FeederObservation = later["observation"]
    presentation_key = hashlib.sha256(
        (
            f"{MONEY_METHOD_VERSION}|{earlier_observation.id}|{later_observation.id}|"
            f"{earlier_fiscal_year}|{later_fiscal_year}"
        ).encode()
    ).hexdigest()
    earlier_input = _input_details(earlier)
    later_input = _input_details(later)
    source_ids = _ordered_unique([earlier_input["source_id"], later_input["source_id"]])
    snapshot_ids = _ordered_unique([earlier_input["snapshot_id"], later_input["snapshot_id"]])
    observation_ids = [earlier_input["observation_id"], later_input["observation_id"]]
    institution_code, institution_name, role_scope = next(iter(institutions))
    return {
        "id": f"money:{presentation_key}",
        "kind": "MONEY",
        "title": "기관장 업무추진비 공시액의 회계연도 간 변화",
        "method_version": MONEY_METHOD_VERSION,
        "claim_id": None,
        "evidence_ids": [],
        "source_ids": source_ids,
        "snapshot_ids": snapshot_ids,
        "observation_ids": observation_ids,
        "publication_status": "BLOCKED",
        "details": {
            "institution": {
                "code": institution_code,
                "name": institution_name,
                "role_scope": role_scope,
            },
            "earlier": earlier_input,
            "later": later_input,
            "absolute_delta_krw": absolute_delta,
            "percent_change": percent_change,
            "coverage": {
                "input_observation_count": len(observations),
                "compared_fiscal_years": [earlier_fiscal_year, later_fiscal_year],
                "semantic_scope": MONEY_SEMANTIC_SCOPE,
            },
            "limitations": [
                "공식 기관·직위 범주의 공시액 변화이며 특정 개인의 지출액이 아니다.",
                "변화 자체는 낭비, 부당집행, 비리, 정책 성과 또는 기관 간 우열을 뜻하지 않는다.",
                "organization-level Claim/Evidence 공개 계약이 없어 현재 public surface는 차단된다.",
            ],
            "provenance": {
                "earlier": {
                    "observation_id": earlier_input["observation_id"],
                    "snapshot_id": earlier_input["snapshot_id"],
                    "source_id": earlier_input["source_id"],
                },
                "later": {
                    "observation_id": later_input["observation_id"],
                    "snapshot_id": later_input["snapshot_id"],
                    "source_id": later_input["source_id"],
                },
            },
        },
    }
