from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

import pytest

from apps.api.operator_review_metrics import (
    GukgamReviewMetricInput,
    HoldReason,
    ReviewDecision,
    gukgam_review_metric_summary,
    record_gukgam_review_metric,
)

MANIFEST_SHA = "a" * 64
ORG_A = "10000000-0000-0000-0000-000000000001"
ORG_B = "10000000-0000-0000-0000-000000000002"


def _inspection() -> dict:
    return {
        "status": "CURRENT_HUMAN_REVIEW_READY",
        "gukgam_claim_review": {
            "status": "HUMAN_REVIEW_REQUIRED_NO_WRITE",
            "manifest_sha256": MANIFEST_SHA,
            "item_count": 3,
            "organization_count": 2,
            "claim_commit_authorized": False,
            "items": [
                {
                    "review_key": "schedule:a:audited-target:1",
                    "organization_id": ORG_A,
                    "organization_name": "기관A",
                    "audit_date": "2026-10-01",
                    "current_claim_present": False,
                },
                {
                    "review_key": "schedule:b:audited-target:1",
                    "organization_id": ORG_A,
                    "organization_name": "기관A",
                    "audit_date": "2026-10-02",
                    "current_claim_present": False,
                },
                {
                    "review_key": "schedule:c:audited-target:1",
                    "organization_id": ORG_B,
                    "organization_name": "기관B",
                    "audit_date": "2026-10-03",
                    "current_claim_present": False,
                },
            ],
        },
    }


def _metric(
    *,
    request_id: str,
    review_key: str,
    active_ms: int,
    decision: ReviewDecision,
    hold_reason: HoldReason | None = None,
    organization_opens: int = 0,
    gukgam_opens: int = 0,
) -> GukgamReviewMetricInput:
    opened = datetime(2026, 9, 28, 12, 0, tzinfo=UTC)
    return GukgamReviewMetricInput(
        request_id=UUID(request_id),
        manifest_sha256=MANIFEST_SHA,
        review_key=review_key,
        opened_at=opened,
        decided_at=opened + timedelta(minutes=10),
        active_ms=active_ms,
        decision=decision,
        hold_reason=hold_reason,
        evidence_opens={
            "organization": organization_opens,
            "gukgam_observation": gukgam_opens,
        },
        batch_decided=False,
    )


def test_review_receipts_are_append_only_idempotent_and_manifest_bound(
    tmp_path: Path,
) -> None:
    path = tmp_path / "review.jsonl"
    request = _metric(
        request_id="20000000-0000-0000-0000-000000000001",
        review_key="schedule:a:audited-target:1",
        active_ms=60_000,
        decision=ReviewDecision.APPROVE,
        organization_opens=1,
    )

    first = record_gukgam_review_metric(
        inspection=_inspection(),
        actor="tester",
        request=request,
        receipt_path=path,
    )
    replay = record_gukgam_review_metric(
        inspection=_inspection(),
        actor="tester",
        request=request,
        receipt_path=path,
    )

    assert first["replayed"] is False
    assert replay["replayed"] is True
    assert first["receipt_sha256"] == replay["receipt_sha256"]
    assert first["manifest_sha256"] == MANIFEST_SHA
    assert first["org_occurrence_index"] == 1
    assert first["org_occurrence_count"] == 2
    assert first["canonical_write_performed"] is False
    assert first["claim_commit_authorized"] is False
    assert len(path.read_text(encoding="utf-8").splitlines()) == 1

    stale = request.model_copy(update={"manifest_sha256": "b" * 64})
    with pytest.raises(ValueError, match="manifest changed"):
        record_gukgam_review_metric(
            inspection=_inspection(),
            actor="tester",
            request=stale,
            receipt_path=path,
        )


def test_review_summary_reports_first_repeat_median_p90_and_hold_reasons(
    tmp_path: Path,
) -> None:
    path = tmp_path / "review.jsonl"
    requests = [
        _metric(
            request_id="20000000-0000-0000-0000-000000000011",
            review_key="schedule:a:audited-target:1",
            active_ms=60_000,
            decision=ReviewDecision.APPROVE,
            organization_opens=1,
        ),
        _metric(
            request_id="20000000-0000-0000-0000-000000000012",
            review_key="schedule:b:audited-target:1",
            active_ms=120_000,
            decision=ReviewDecision.HOLD,
            hold_reason=HoldReason.SOURCE_CONTEXT_INSUFFICIENT,
            gukgam_opens=2,
        ),
        _metric(
            request_id="20000000-0000-0000-0000-000000000013",
            review_key="schedule:c:audited-target:1",
            active_ms=30_000,
            decision=ReviewDecision.REJECT,
        ),
    ]
    for request in requests:
        record_gukgam_review_metric(
            inspection=_inspection(),
            actor="tester",
            request=request,
            receipt_path=path,
        )

    summary = gukgam_review_metric_summary(
        inspection=_inspection(),
        manifest_sha256=MANIFEST_SHA,
        receipt_path=path,
    )

    assert summary["decided_count"] == 3
    assert summary["remaining_count"] == 0
    assert summary["all_reviewed"] is True
    assert summary["overall"]["decision_counts"] == {
        "APPROVE": 1,
        "HOLD": 1,
        "REJECT": 1,
    }
    assert summary["overall"]["median_active_ms"] == 60_000
    assert summary["overall"]["p90_active_ms"] == 120_000
    assert summary["overall"]["with_evidence_opens"] == 2
    assert summary["overall"]["evidence_open_rate"] == pytest.approx(0.6667)
    assert summary["first_occurrence"]["count"] == 2
    assert summary["first_occurrence"]["median_active_ms"] == 45_000
    assert summary["repeat_occurrence"]["count"] == 1
    assert summary["repeat_occurrence"]["median_active_ms"] == 120_000
    assert summary["overall"]["hold_reason_counts"] == {
        "SOURCE_CONTEXT_INSUFFICIENT": 1
    }


def test_latest_review_receipt_replaces_only_summary_state(tmp_path: Path) -> None:
    path = tmp_path / "review.jsonl"
    first = _metric(
        request_id="20000000-0000-0000-0000-000000000021",
        review_key="schedule:a:audited-target:1",
        active_ms=60_000,
        decision=ReviewDecision.HOLD,
        hold_reason=HoldReason.OTHER_EVIDENCE_REQUIRED,
    )
    second = _metric(
        request_id="20000000-0000-0000-0000-000000000022",
        review_key="schedule:a:audited-target:1",
        active_ms=40_000,
        decision=ReviewDecision.APPROVE,
    )
    for request in (first, second):
        record_gukgam_review_metric(
            inspection=_inspection(),
            actor="tester",
            request=request,
            receipt_path=path,
        )

    summary = gukgam_review_metric_summary(
        inspection=_inspection(),
        manifest_sha256=MANIFEST_SHA,
        receipt_path=path,
    )

    assert len(path.read_text(encoding="utf-8").splitlines()) == 2
    assert summary["decided_count"] == 1
    assert summary["overall"]["decision_counts"] == {"APPROVE": 1}
    assert summary["items"][0]["decision"] == "APPROVE"
    assert summary["items"][0]["active_ms"] == 40_000


def test_review_metric_rejects_bad_hold_shape_and_repo_local_receipt(
    tmp_path: Path,
) -> None:
    with pytest.raises(ValueError, match="HOLD requires"):
        _metric(
            request_id="20000000-0000-0000-0000-000000000031",
            review_key="schedule:a:audited-target:1",
            active_ms=10_000,
            decision=ReviewDecision.HOLD,
        )

    request = _metric(
        request_id="20000000-0000-0000-0000-000000000032",
        review_key="schedule:a:audited-target:1",
        active_ms=10_000,
        decision=ReviewDecision.REJECT,
    )
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    with pytest.raises(ValueError, match="outside the repository"):
        record_gukgam_review_metric(
            inspection=_inspection(),
            actor="tester",
            request=request,
            receipt_path=repo_root / "receipt.jsonl",
            repo_root=repo_root,
        )


def test_operator_review_metric_http_boundary(tmp_path: Path, monkeypatch) -> None:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from apps.api import operator as operator_api

    monkeypatch.setattr(
        operator_api,
        "current_review_inspection",
        lambda _repository: _inspection(),
    )
    receipt_path = tmp_path / "operator-review.jsonl"
    app = FastAPI()
    app.include_router(
        operator_api.build_operator_router(
            object(),  # type: ignore[arg-type]
            "TEST",
            actor="tester",
            review_receipt_path=receipt_path,
        )
    )

    payload = _metric(
        request_id="20000000-0000-0000-0000-000000000041",
        review_key="schedule:a:audited-target:1",
        active_ms=15_000,
        decision=ReviewDecision.APPROVE,
        organization_opens=1,
    ).model_dump(mode="json")

    with TestClient(app) as client:
        saved = client.post("/admin/operations/review-throughput", json=payload)
        assert saved.status_code == 200
        assert saved.json()["canonical_write_performed"] is False
        assert saved.json()["claim_commit_authorized"] is False

        summary = client.get(
            "/admin/operations/review-throughput",
            params={"manifest_sha256": MANIFEST_SHA},
        )
        assert summary.status_code == 200
        assert summary.json()["decided_count"] == 1
        assert summary.json()["remaining_count"] == 2

        stale = {
            **payload,
            "request_id": "20000000-0000-0000-0000-000000000042",
            "manifest_sha256": "b" * 64,
        }
        conflict = client.post("/admin/operations/review-throughput", json=stale)
        assert conflict.status_code == 409
        assert conflict.json()["detail"]["code"] == "REVIEW_STATE_CONFLICT"

        invalid = client.post(
            "/admin/operations/review-throughput",
            json={**payload, "request_id": "not-a-uuid"},
        )
        assert invalid.status_code == 422

    assert len(receipt_path.read_text(encoding="utf-8").splitlines()) == 1


def test_review_metric_rejects_batch_decision_and_receipt_omits_display_content(
    tmp_path: Path,
) -> None:
    base = _metric(
        request_id="20000000-0000-0000-0000-000000000051",
        review_key="schedule:a:audited-target:1",
        active_ms=10_000,
        decision=ReviewDecision.APPROVE,
        organization_opens=1,
    )
    with pytest.raises(ValueError, match="single-item"):
        GukgamReviewMetricInput.model_validate(
            {**base.model_dump(mode="json"), "batch_decided": True}
        )

    path = tmp_path / "review.jsonl"
    record_gukgam_review_metric(
        inspection=_inspection(),
        actor="tester",
        request=base,
        receipt_path=path,
    )
    stored = path.read_text(encoding="utf-8")
    assert "기관A" not in stored
    assert "http://" not in stored
    assert "https://" not in stored
    assert "canonical_write_performed" in stored
    assert '"claim_commit_authorized":false' in stored
