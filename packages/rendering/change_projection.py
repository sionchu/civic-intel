from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence

from packages.domain.contracts import Claim, ClaimEvidence
from packages.domain.enums import (
    EpistemicStatus,
    EvidenceStance,
    PublicationStatus,
)

CHANGE_TRACE_SEMANTICS = "SOURCE_NEUTRAL_DERIVED_CHANGE_TRACE_V1"


def _subject_ref(claim: Claim) -> tuple[str, str]:
    if claim.person_id is not None:
        return "PERSON", str(claim.person_id)
    if claim.organization_id is not None:
        return "ORGANIZATION", str(claim.organization_id)
    raise ValueError("change trace Claim has no canonical subject")


def _validate_claim(claim: Claim) -> None:
    if (
        claim.superseded_at is not None
        or claim.publication_status != PublicationStatus.PUBLISHED
        or claim.epistemic_status != EpistemicStatus.FACT
        or not claim.asserted_as_true
    ):
        raise ValueError("change trace requires current published FACT Claims")


def _validate_evidence(
    claim: Claim,
    evidence: Sequence[ClaimEvidence],
) -> tuple[ClaimEvidence, ...]:
    items = tuple(evidence)
    if not items:
        raise ValueError("change trace requires ClaimEvidence for each input Claim")
    if any(item.claim_id != claim.id for item in items):
        raise ValueError("change trace evidence does not belong to the input Claim")
    stances = {item.stance for item in items}
    if EvidenceStance.REFUTE in stances:
        raise ValueError("change trace refuses input Claims with REFUTE evidence")
    if EvidenceStance.SUPPORT not in stances:
        raise ValueError("change trace requires SUPPORT evidence")
    return items


def _ordered_unique(values: Sequence[str]) -> list[str]:
    return list(dict.fromkeys(values))


def build_source_neutral_change_trace(
    *,
    method_version: str,
    comparison_dimension: str,
    earlier_claim: Claim,
    later_claim: Claim,
    earlier_order_key: str,
    later_order_key: str,
    earlier_value: str,
    later_value: str,
    earlier_evidence: Sequence[ClaimEvidence],
    later_evidence: Sequence[ClaimEvidence],
) -> dict[str, object]:
    """Build evidence-linked metadata for an already validated two-point comparison.

    This helper does not decide whether two domain values are comparable. Callers retain
    source-specific ordering, correction/version, identity and value semantics.
    """
    method_version = method_version.strip()
    comparison_dimension = comparison_dimension.strip()
    earlier_order_key = earlier_order_key.strip()
    later_order_key = later_order_key.strip()
    earlier_value = earlier_value.strip()
    later_value = later_value.strip()
    if not all(
        (
            method_version,
            comparison_dimension,
            earlier_order_key,
            later_order_key,
            earlier_value,
            later_value,
        )
    ):
        raise ValueError("change trace fields must be non-empty")
    if earlier_claim.id == later_claim.id:
        raise ValueError("change trace requires two distinct Claims")

    _validate_claim(earlier_claim)
    _validate_claim(later_claim)
    earlier_subject = _subject_ref(earlier_claim)
    later_subject = _subject_ref(later_claim)
    if earlier_subject != later_subject:
        raise ValueError("change trace Claims must target the same canonical subject")

    earlier_items = _validate_evidence(earlier_claim, earlier_evidence)
    later_items = _validate_evidence(later_claim, later_evidence)
    evidence = (*earlier_items, *later_items)
    claim_ids = [str(earlier_claim.id), str(later_claim.id)]
    evidence_ids = _ordered_unique([str(item.id) for item in evidence])
    source_ids = _ordered_unique([str(item.source_id) for item in evidence])
    payload = {
        "semantics": CHANGE_TRACE_SEMANTICS,
        "method_version": method_version,
        "subject": {
            "type": earlier_subject[0],
            "id": earlier_subject[1],
        },
        "comparison_dimension": comparison_dimension,
        "earlier": {
            "claim_id": claim_ids[0],
            "order_key": earlier_order_key,
            "value": earlier_value,
        },
        "later": {
            "claim_id": claim_ids[1],
            "order_key": later_order_key,
            "value": later_value,
        },
        "claim_ids": claim_ids,
        "evidence_ids": evidence_ids,
        "source_ids": source_ids,
    }
    trace_key = hashlib.sha256(
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    return {
        **payload,
        "trace_key": trace_key,
    }
