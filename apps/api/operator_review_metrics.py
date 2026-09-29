"""Private append-only review-throughput receipts; never canonical approval state."""

from __future__ import annotations

import hashlib
import json
import math
import os
from collections import Counter
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from statistics import median
from threading import Lock
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

GUKGAM_REVIEW_THROUGHPUT_SEMANTICS = (
    "GUKGAM_EXISTING_ORGANIZATION_REVIEW_THROUGHPUT_V1"
)
IDLE_THRESHOLD_MS = 300_000
MAX_REVIEW_WALL_MS = 12 * 60 * 60 * 1000
MAX_RECEIPT_FILE_BYTES = 5_000_000
_RECEIPT_LOCK = Lock()


class ReviewDecision(StrEnum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    HOLD = "HOLD"


class HoldReason(StrEnum):
    INSTITUTION_IDENTITY_UNCLEAR = "INSTITUTION_IDENTITY_UNCLEAR"
    LIFECYCLE_OR_SUCCESSOR_UNCLEAR = "LIFECYCLE_OR_SUCCESSOR_UNCLEAR"
    SOURCE_CONTEXT_INSUFFICIENT = "SOURCE_CONTEXT_INSUFFICIENT"
    OTHER_EVIDENCE_REQUIRED = "OTHER_EVIDENCE_REQUIRED"


class EvidenceOpens(BaseModel):
    organization: int = Field(default=0, ge=0, le=100)
    gukgam_observation: int = Field(default=0, ge=0, le=100)


class GukgamReviewMetricInput(BaseModel):
    request_id: UUID
    manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    review_key: str = Field(min_length=1, max_length=500)
    opened_at: datetime
    decided_at: datetime
    active_ms: int = Field(ge=0, le=MAX_REVIEW_WALL_MS)
    decision: ReviewDecision
    hold_reason: HoldReason | None = None
    evidence_opens: EvidenceOpens = Field(default_factory=EvidenceOpens)
    batch_decided: bool = False

    @model_validator(mode="after")
    def validate_review_metric(self) -> GukgamReviewMetricInput:
        if self.opened_at.tzinfo is None or self.decided_at.tzinfo is None:
            raise ValueError("review timestamps must include a timezone")
        wall_ms = int(
            (self.decided_at.astimezone(UTC) - self.opened_at.astimezone(UTC)).total_seconds()
            * 1000
        )
        if wall_ms < 0 or wall_ms > MAX_REVIEW_WALL_MS:
            raise ValueError("review wall time is outside the accepted bound")
        if self.active_ms > wall_ms:
            raise ValueError("active time cannot exceed wall time")
        if self.decision == ReviewDecision.HOLD and self.hold_reason is None:
            raise ValueError("HOLD requires a hold reason")
        if self.decision != ReviewDecision.HOLD and self.hold_reason is not None:
            raise ValueError("hold reason is valid only for HOLD")
        if self.batch_decided:
            raise ValueError("v0 accepts single-item decisions only")
        return self


def default_review_receipt_path() -> Path:
    configured = os.environ.get("CIVIC_OPERATOR_REVIEW_RECEIPT_PATH", "").strip()
    if configured:
        return Path(configured).expanduser().resolve()
    return (
        Path.home()
        / ".civic-intel"
        / "operator"
        / "gukgam-review-throughput-v1.jsonl"
    ).resolve()


def _canonical_json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _receipt_hash(receipt_without_hash: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(receipt_without_hash).encode("utf-8")).hexdigest()


def _safe_receipt_path(path: Path, *, repo_root: Path | None = None) -> Path:
    target = path.expanduser().resolve()
    if repo_root is not None and target.is_relative_to(repo_root.resolve()):
        raise ValueError("review receipt path must be outside the repository")
    if target.suffix != ".jsonl":
        raise ValueError("review receipt path must use a .jsonl file")
    if target.exists() and target.is_symlink():
        raise ValueError("review receipt path must not be a symlink")
    return target


def _read_receipts(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    if path.stat().st_size > MAX_RECEIPT_FILE_BYTES:
        raise ValueError("review receipt file exceeds the bounded size")
    receipts: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            raw = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"review receipt file contains invalid JSON at line {line_number}"
            ) from exc
        if not isinstance(raw, dict):
            raise TypeError("review receipt entry must be an object")
        receipt_hash = raw.get("receipt_sha256")
        unsigned = {key: value for key, value in raw.items() if key != "receipt_sha256"}
        if (
            not isinstance(receipt_hash, str)
            or receipt_hash != _receipt_hash(unsigned)
            or raw.get("semantics") != GUKGAM_REVIEW_THROUGHPUT_SEMANTICS
        ):
            raise ValueError("review receipt integrity check failed")
        receipts.append(raw)
    return receipts


def _append_receipt(path: Path, receipt: dict[str, Any]) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    payload = (_canonical_json(receipt) + "\n").encode("utf-8")
    descriptor = os.open(path, os.O_APPEND | os.O_CREAT | os.O_WRONLY, 0o600)
    try:
        os.write(descriptor, payload)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    os.chmod(path, 0o600)


def _current_gukgam_lane(
    inspection: dict[str, Any],
    *,
    manifest_sha256: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if inspection.get("status") != "CURRENT_HUMAN_REVIEW_READY":
        raise ValueError("current Gukgam review state is unavailable")
    lane = inspection.get("gukgam_claim_review")
    if not isinstance(lane, dict):
        raise TypeError("current Gukgam review lane is unavailable")
    if (
        lane.get("status") != "HUMAN_REVIEW_REQUIRED_NO_WRITE"
        or lane.get("manifest_sha256") != manifest_sha256
        or lane.get("claim_commit_authorized") is not False
    ):
        raise ValueError("Gukgam review manifest changed; refresh before reviewing")
    items = lane.get("items")
    if not isinstance(items, list) or not all(isinstance(item, dict) for item in items):
        raise TypeError("current Gukgam review items are invalid")
    return lane, items


def _occurrence_position(
    items: list[dict[str, Any]],
    target: dict[str, Any],
) -> tuple[int, int]:
    organization_id = target.get("organization_id")
    siblings = sorted(
        [item for item in items if item.get("organization_id") == organization_id],
        key=lambda item: (
            str(item.get("audit_date", "")),
            str(item.get("review_key", "")),
        ),
    )
    for index, item in enumerate(siblings, 1):
        if item.get("review_key") == target.get("review_key"):
            return index, len(siblings)
    raise ValueError("review occurrence is not present in the current manifest")


def record_gukgam_review_metric(
    *,
    inspection: dict[str, Any],
    actor: str,
    request: GukgamReviewMetricInput,
    receipt_path: Path,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    _, items = _current_gukgam_lane(
        inspection, manifest_sha256=request.manifest_sha256
    )
    target = next(
        (item for item in items if item.get("review_key") == request.review_key),
        None,
    )
    if target is None or target.get("current_claim_present") is not False:
        raise ValueError("review item is stale or no longer pending")

    path = _safe_receipt_path(receipt_path, repo_root=repo_root)
    request_id = str(request.request_id)
    request_payload = request.model_dump(mode="json")
    with _RECEIPT_LOCK:
        prior = _read_receipts(path)
        for existing in prior:
            if existing.get("request_id") != request_id:
                continue
            comparable = existing.get("request")
            if comparable != request_payload or existing.get("actor") != actor:
                raise ValueError("request ID was already used with different review data")
            return {**existing, "replayed": True}

    occurrence_index, occurrence_count = _occurrence_position(items, target)
    opened = request.opened_at.astimezone(UTC)
    decided = request.decided_at.astimezone(UTC)
    wall_ms = int((decided - opened).total_seconds() * 1000)
    unsigned: dict[str, Any] = {
        "semantics": GUKGAM_REVIEW_THROUGHPUT_SEMANTICS,
        "request_id": request_id,
        "actor": actor,
        "created_at": datetime.now(UTC).isoformat(),
        "manifest_sha256": request.manifest_sha256,
        "review_key": request.review_key,
        "organization_id": str(target["organization_id"]),
        "opened_at": opened.isoformat(),
        "decided_at": decided.isoformat(),
        "wall_ms": wall_ms,
        "active_ms": request.active_ms,
        "idle_ms": max(0, wall_ms - request.active_ms),
        "idle_threshold_ms": IDLE_THRESHOLD_MS,
        "decision": request.decision.value,
        "hold_reason": request.hold_reason.value if request.hold_reason else None,
        "evidence_opens": request.evidence_opens.model_dump(),
        "org_occurrence_index": occurrence_index,
        "org_occurrence_count": occurrence_count,
        "batch_decided": request.batch_decided,
        "canonical_write_performed": False,
        "claim_commit_authorized": False,
        "request": request_payload,
    }
    receipt = {**unsigned, "receipt_sha256": _receipt_hash(unsigned)}
    with _RECEIPT_LOCK:
        prior = _read_receipts(path)
        for existing in prior:
            if existing.get("request_id") == request_id:
                if existing.get("request") != request_payload or existing.get("actor") != actor:
                    raise ValueError("request ID was already used with different review data")
                return {**existing, "replayed": True}
        _append_receipt(path, receipt)
    return {**receipt, "replayed": False}


def _p90(values: list[int]) -> int | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[max(0, math.ceil(len(ordered) * 0.90) - 1)]


def _metric_group(receipts: list[dict[str, Any]]) -> dict[str, Any]:
    active = [int(item["active_ms"]) for item in receipts]
    decisions = Counter(str(item["decision"]) for item in receipts)
    hold_reasons = Counter(
        str(item["hold_reason"])
        for item in receipts
        if item.get("hold_reason") is not None
    )
    with_evidence = sum(
        1
        for item in receipts
        if sum(int(value) for value in item["evidence_opens"].values()) > 0
    )
    return {
        "count": len(receipts),
        "decision_counts": dict(sorted(decisions.items())),
        "hold_reason_counts": dict(sorted(hold_reasons.items())),
        "median_active_ms": int(median(active)) if active else None,
        "p90_active_ms": _p90(active),
        "with_evidence_opens": with_evidence,
        "evidence_open_rate": round(with_evidence / len(receipts), 4)
        if receipts
        else None,
        "batch_decided_count": sum(bool(item["batch_decided"]) for item in receipts),
    }


def gukgam_review_metric_summary(
    *,
    inspection: dict[str, Any],
    manifest_sha256: str,
    receipt_path: Path,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    lane, items = _current_gukgam_lane(
        inspection, manifest_sha256=manifest_sha256
    )
    path = _safe_receipt_path(receipt_path, repo_root=repo_root)
    receipts = [
        item
        for item in _read_receipts(path)
        if item.get("manifest_sha256") == manifest_sha256
    ]
    current_keys = {str(item["review_key"]) for item in items}
    latest: dict[str, dict[str, Any]] = {}
    for receipt in receipts:
        review_key = str(receipt.get("review_key", ""))
        if review_key in current_keys:
            latest[review_key] = receipt
    latest_items = list(latest.values())
    first = [
        item for item in latest_items if int(item["org_occurrence_index"]) == 1
    ]
    repeat = [
        item for item in latest_items if int(item["org_occurrence_index"]) > 1
    ]
    public_items = [
        {
            key: item[key]
            for key in (
                "review_key",
                "decision",
                "hold_reason",
                "decided_at",
                "active_ms",
                "evidence_opens",
                "org_occurrence_index",
                "org_occurrence_count",
                "batch_decided",
                "receipt_sha256",
            )
        }
        for item in latest_items
    ]
    public_items.sort(key=lambda item: str(item["review_key"]))
    return {
        "semantics": GUKGAM_REVIEW_THROUGHPUT_SEMANTICS,
        "manifest_sha256": manifest_sha256,
        "review_item_count": int(lane.get("item_count", len(items))),
        "organization_count": int(lane.get("organization_count", 0)),
        "decided_count": len(latest_items),
        "remaining_count": max(0, len(items) - len(latest_items)),
        "all_reviewed": len(items) > 0 and len(latest_items) == len(items),
        "overall": _metric_group(latest_items),
        "first_occurrence": _metric_group(first),
        "repeat_occurrence": _metric_group(repeat),
        "items": public_items,
        "canonical_write_performed": False,
        "claim_commit_authorized": False,
    }
