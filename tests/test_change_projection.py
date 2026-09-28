from __future__ import annotations

from uuid import UUID

import pytest

from packages.domain.contracts import Claim, ClaimEvidence
from packages.domain.enums import (
    EpistemicStatus,
    EvidenceStance,
    PublicationStatus,
)
from packages.rendering.change_projection import (
    CHANGE_TRACE_SEMANTICS,
    build_source_neutral_change_trace,
)

PERSON_ID = UUID("10000000-0000-0000-0000-000000000001")
OTHER_PERSON_ID = UUID("10000000-0000-0000-0000-000000000002")
SOURCE_ID = UUID("20000000-0000-0000-0000-000000000001")


def _claim(claim_id: str, *, person_id: UUID = PERSON_ID) -> Claim:
    return Claim(
        id=UUID(claim_id),
        person_id=person_id,
        proposition="공식 기록은 값을 기재한다.",
        subject="테스트 인물",
        predicate="TEST_VALUE",
        object_text="표시값",
        epistemic_status=EpistemicStatus.FACT,
        publication_status=PublicationStatus.PUBLISHED,
        asserted_as_true=True,
    )


def _evidence(evidence_id: str, claim: Claim, stance: EvidenceStance) -> ClaimEvidence:
    return ClaimEvidence(
        id=UUID(evidence_id),
        claim_id=claim.id,
        source_id=SOURCE_ID,
        stance=stance,
    )


def test_source_neutral_change_trace_is_deterministic_and_evidence_linked() -> None:
    earlier = _claim("30000000-0000-0000-0000-000000000001")
    later = _claim("30000000-0000-0000-0000-000000000002")
    earlier_evidence = _evidence(
        "40000000-0000-0000-0000-000000000001",
        earlier,
        EvidenceStance.SUPPORT,
    )
    later_evidence = _evidence(
        "40000000-0000-0000-0000-000000000002",
        later,
        EvidenceStance.SUPPORT,
    )

    kwargs = {
        "method_version": "change.test.v1",
        "comparison_dimension": "TEST_DIMENSION",
        "earlier_claim": earlier,
        "later_claim": later,
        "earlier_order_key": "2024",
        "later_order_key": "2025",
        "earlier_value": "A",
        "later_value": "B",
        "earlier_evidence": (earlier_evidence,),
        "later_evidence": (later_evidence,),
    }
    first = build_source_neutral_change_trace(**kwargs)
    second = build_source_neutral_change_trace(**kwargs)

    assert first == second
    assert first["semantics"] == CHANGE_TRACE_SEMANTICS
    assert first["subject"] == {"type": "PERSON", "id": str(PERSON_ID)}
    assert first["comparison_dimension"] == "TEST_DIMENSION"
    assert first["claim_ids"] == [str(earlier.id), str(later.id)]
    assert first["evidence_ids"] == [
        str(earlier_evidence.id),
        str(later_evidence.id),
    ]
    assert first["source_ids"] == [str(SOURCE_ID)]
    assert first["earlier"] == {
        "claim_id": str(earlier.id),
        "order_key": "2024",
        "value": "A",
    }
    assert len(str(first["trace_key"])) == 64


def test_source_neutral_change_trace_rejects_cross_subject_comparison() -> None:
    earlier = _claim("30000000-0000-0000-0000-000000000003")
    later = _claim(
        "30000000-0000-0000-0000-000000000004",
        person_id=OTHER_PERSON_ID,
    )
    with pytest.raises(ValueError, match="same canonical subject"):
        build_source_neutral_change_trace(
            method_version="change.test.v1",
            comparison_dimension="TEST_DIMENSION",
            earlier_claim=earlier,
            later_claim=later,
            earlier_order_key="2024",
            later_order_key="2025",
            earlier_value="A",
            later_value="B",
            earlier_evidence=(
                _evidence(
                    "40000000-0000-0000-0000-000000000003",
                    earlier,
                    EvidenceStance.SUPPORT,
                ),
            ),
            later_evidence=(
                _evidence(
                    "40000000-0000-0000-0000-000000000004",
                    later,
                    EvidenceStance.SUPPORT,
                ),
            ),
        )


def test_source_neutral_change_trace_requires_published_fact_and_no_refute() -> None:
    earlier = _claim("30000000-0000-0000-0000-000000000005")
    later = _claim("30000000-0000-0000-0000-000000000006").model_copy(
        update={"publication_status": PublicationStatus.DRAFT}
    )
    with pytest.raises(ValueError, match="published FACT"):
        build_source_neutral_change_trace(
            method_version="change.test.v1",
            comparison_dimension="TEST_DIMENSION",
            earlier_claim=earlier,
            later_claim=later,
            earlier_order_key="2024",
            later_order_key="2025",
            earlier_value="A",
            later_value="B",
            earlier_evidence=(
                _evidence(
                    "40000000-0000-0000-0000-000000000005",
                    earlier,
                    EvidenceStance.SUPPORT,
                ),
            ),
            later_evidence=(
                _evidence(
                    "40000000-0000-0000-0000-000000000006",
                    later,
                    EvidenceStance.SUPPORT,
                ),
            ),
        )

    later = _claim("30000000-0000-0000-0000-000000000007")
    with pytest.raises(ValueError, match="REFUTE"):
        build_source_neutral_change_trace(
            method_version="change.test.v1",
            comparison_dimension="TEST_DIMENSION",
            earlier_claim=earlier,
            later_claim=later,
            earlier_order_key="2024",
            later_order_key="2025",
            earlier_value="A",
            later_value="B",
            earlier_evidence=(
                _evidence(
                    "40000000-0000-0000-0000-000000000007",
                    earlier,
                    EvidenceStance.SUPPORT,
                ),
            ),
            later_evidence=(
                _evidence(
                    "40000000-0000-0000-0000-000000000008",
                    later,
                    EvidenceStance.REFUTE,
                ),
                _evidence(
                    "40000000-0000-0000-0000-000000000009",
                    later,
                    EvidenceStance.SUPPORT,
                ),
            ),
        )

def test_source_neutral_change_trace_requires_support_evidence() -> None:
    earlier = _claim("30000000-0000-0000-0000-000000000008")
    later = _claim("30000000-0000-0000-0000-000000000009")

    with pytest.raises(ValueError, match="SUPPORT"):
        build_source_neutral_change_trace(
            method_version="change.test.v1",
            comparison_dimension="TEST_DIMENSION",
            earlier_claim=earlier,
            later_claim=later,
            earlier_order_key="2024",
            later_order_key="2025",
            earlier_value="A",
            later_value="B",
            earlier_evidence=(
                _evidence(
                    "40000000-0000-0000-0000-000000000010",
                    earlier,
                    EvidenceStance.NEUTRAL,
                ),
            ),
            later_evidence=(
                _evidence(
                    "40000000-0000-0000-0000-000000000011",
                    later,
                    EvidenceStance.SUPPORT,
                ),
            ),
        )
