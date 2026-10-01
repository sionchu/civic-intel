"""Current operator review projections derived from canonical DB state."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from packages.application.context import Application
from packages.domain.enums import SourceRunStatus
from packages.rendering.gukgam_organization_binding_review import (
    EXACT_ONE,
    NO_EXACT,
    build_gukgam_organization_binding_review,
)
from packages.rendering.gukgam_organization_claim import GUKGAM_AUDIT_TARGET_PREDICATE
from packages.rendering.gukgam_schedule_review import load_current_gukgam_schedule_review
from packages.rendering.mois_organization_proposal import (
    MOIS_FEEDER,
    MOIS_ORGANIZATION_PROPOSAL_SEMANTICS,
    MOIS_SCOPE_KEY,
    mois_organization_proposal_provider_row,
)
from workers.gukgam_reviewed_claim_batch_manifest import (
    ReviewedGukgamClaimBatchManifest,
    ReviewedGukgamClaimManifestItem,
)

ROOT = Path(__file__).resolve().parents[2]
MOIS_PROPOSAL = ROOT / "docs/research/gukgam_2026_mois_organization_proposal_2026-09-28.json"


def _canonical_sha256(payload: object) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(raw).hexdigest()


def _provider_manifest_sha256(items: list[tuple[str, str]]) -> str:
    raw = json.dumps(sorted(items), ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _current_gukgam_context(repository: Application):
    schedule = load_current_gukgam_schedule_review(repository.acquisition)
    if not schedule.committees:
        raise RuntimeError("current Gukgam reviewed schedule is unavailable")
    organizations = repository.public.organizations(current_only=True)
    review = build_gukgam_organization_binding_review(schedule, organizations)
    if not review.items:
        raise RuntimeError("current Gukgam reviewed schedule has no audited targets")
    return (organizations, review)


def _gukgam_claim_review_inspection(
    repository: Application, organizations, review
) -> dict[str, Any]:
    existing_claims = [
        claim
        for claim in repository.public.claims(current_only=True)
        if claim.predicate == GUKGAM_AUDIT_TARGET_PREDICATE
    ]
    existing_keys = {
        key
        for claim in existing_claims
        if isinstance((key := claim.qualifiers.get("provider_record_key")), str) and key
    }
    pending = []
    manifest_items = []
    for item in review.items:
        if (
            item.match_class != EXACT_ONE
            or len(item.candidates) != 1
            or item.review_key in existing_keys
        ):
            continue
        candidate = item.candidates[0]
        manifest_items.append(
            ReviewedGukgamClaimManifestItem(
                review_key=item.review_key, organization_id=candidate.organization_id
            )
        )
        pending.append(
            {
                "review_key": item.review_key,
                "organization_id": str(candidate.organization_id),
                "organization_name": candidate.name,
                "committee_name": item.committee_name,
                "audit_date": item.audit_date,
                "audited_target": item.audited_target,
                "observation_id": str(item.observation_id),
                "match_class": item.match_class,
                "current_claim_present": False,
            }
        )
    manifest = ReviewedGukgamClaimBatchManifest(
        items=tuple(
            sorted(manifest_items, key=lambda item: (item.review_key, str(item.organization_id)))
        )
    )
    pending.sort(
        key=lambda item: (item["organization_name"], item["audit_date"], item["review_key"])
    )
    return {
        "status": "HUMAN_REVIEW_REQUIRED_NO_WRITE",
        "message": "현재 Gukgam schedule/checkpoint, current Organization, current Claim을 다시 읽어 exact-one 미공개 후보만 계산했습니다. 이름 일치는 승인 권한이 아닙니다.",
        "manifest_sha256": manifest.sha256() if manifest.items else None,
        "item_count": len(pending),
        "organization_count": len({item["organization_id"] for item in pending}),
        "current_organization_count": len(organizations),
        "existing_gukgam_claim_count": len(existing_claims),
        "claim_commit_authorized": False,
        "items": pending,
    }


def _mois_review_inspection(repository: Application, organizations, review) -> dict[str, Any]:
    try:
        artifact = json.loads(MOIS_PROPOSAL.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {
            "status": "ARTIFACT_UNAVAILABLE",
            "message": "MOIS review artifact를 읽을 수 없습니다.",
            "write_performed": False,
            "items": [],
        }
    if (
        not isinstance(artifact, dict)
        or artifact.get("semantics") != MOIS_ORGANIZATION_PROPOSAL_SEMANTICS
        or artifact.get("status") != "REVIEW_ONLY"
        or (artifact.get("canonical_name_conflict_count") != 0)
        or (not isinstance(artifact.get("items"), list))
    ):
        return {
            "status": "ARTIFACT_INVALID",
            "message": "MOIS review artifact contract가 현재 코드와 다릅니다.",
            "write_performed": False,
            "items": [],
        }
    checkpoint = repository.acquisition.source_checkpoint(MOIS_FEEDER, MOIS_SCOPE_KEY)
    if checkpoint is None:
        return {
            "status": "CURRENT_SOURCE_UNAVAILABLE",
            "message": "현재 MOIS checkpoint가 없어 proposal을 재검증할 수 없습니다.",
            "artifact_sha256": _canonical_sha256(artifact),
            "write_performed": False,
            "items": [],
        }
    if checkpoint.last_run_id is None:
        return {
            "status": "CURRENT_SOURCE_CONFLICT",
            "message": "현재 MOIS checkpoint에 완료 run 참조가 없습니다.",
            "artifact_sha256": _canonical_sha256(artifact),
            "write_performed": False,
            "items": [],
        }
    run = repository.acquisition.source_run(checkpoint.last_run_id)
    if (
        run is None
        or run.status != SourceRunStatus.SUCCESS
        or run.feeder != MOIS_FEEDER
        or (run.scope_key != MOIS_SCOPE_KEY)
        or (run.checkpoint_after != checkpoint.cursor)
    ):
        return {
            "status": "CURRENT_SOURCE_CONFLICT",
            "message": "현재 MOIS checkpoint가 완결된 SUCCESS run과 일치하지 않습니다.",
            "artifact_sha256": _canonical_sha256(artifact),
            "write_performed": False,
            "items": [],
        }
    try:
        total_count = int(checkpoint.metadata["total_count"])
        seen_count = int(checkpoint.metadata["seen_provider_count"])
        manifest_sha = str(checkpoint.metadata["seen_provider_manifest_sha256"])
        expected_pages = int(checkpoint.metadata["expected_pages"])
        source_contract = str(checkpoint.metadata["source_contract"])
        stop_selector = str(checkpoint.metadata["stop_selt"])
    except (KeyError, TypeError, ValueError):
        return {
            "status": "CURRENT_SOURCE_CONFLICT",
            "message": "현재 MOIS checkpoint coverage metadata가 불완전합니다.",
            "artifact_sha256": _canonical_sha256(artifact),
            "write_performed": False,
            "items": [],
        }
    hash_manifest = repository.acquisition.feeder_observation_hash_manifest(
        MOIS_FEEDER, MOIS_SCOPE_KEY
    )
    unique_hashes = dict(hash_manifest)
    source_stable = (
        total_count
        == artifact.get("provider_universe_count")
        == artifact.get("candidate_provider_row_count")
        and seen_count == total_count
        and (len(hash_manifest) == total_count)
        and (len(unique_hashes) == total_count)
        and (checkpoint.cursor == str(expected_pages))
        and (source_contract == "mois_standard_organization_code_v1")
        and (stop_selector == "0")
        and (run.metadata.get("source_contract") == source_contract)
        and (run.metadata.get("stop_selt") == stop_selector)
        and (_provider_manifest_sha256(hash_manifest) == manifest_sha)
    )
    if not source_stable:
        return {
            "status": "CURRENT_SOURCE_DRIFT",
            "message": "현재 MOIS observation/checkpoint universe가 review artifact 기준과 달라졌습니다. proposal 재생성이 필요합니다.",
            "artifact_sha256": _canonical_sha256(artifact),
            "write_performed": False,
            "items": [],
        }
    if artifact.get("current_organization_count") != len(organizations):
        return {
            "status": "CURRENT_ORGANIZATION_DRIFT",
            "message": "현재 canonical Organization 수가 proposal 기준과 달라졌습니다. proposal 재생성이 필요합니다.",
            "artifact_sha256": _canonical_sha256(artifact),
            "write_performed": False,
            "items": [],
        }
    current_names = {organization.name.strip() for organization in organizations}
    current_review = {item.review_key: item for item in review.items}
    current_no_exact_names = {
        item.audited_target.strip() for item in review.items if item.match_class == NO_EXACT
    }
    artifact_items = artifact["items"]
    ambiguous_items = artifact.get("ambiguous_items")
    if not isinstance(ambiguous_items, list):
        return {
            "status": "ARTIFACT_INVALID",
            "message": "MOIS review artifact ambiguous-items contract가 현재 코드와 다릅니다.",
            "artifact_sha256": _canonical_sha256(artifact),
            "write_performed": False,
            "items": [],
        }
    proposal_names = {
        str(item.get("organization_name", "")).strip()
        for item in artifact_items
        if isinstance(item, dict)
    }
    ambiguous_names = {
        str(item.get("audited_target", "")).strip()
        for item in ambiguous_items
        if isinstance(item, dict)
    }
    current_unmatched_count = len(current_no_exact_names - proposal_names - ambiguous_names)
    if (
        artifact.get("gukgam_no_exact_distinct_target_count") != len(current_no_exact_names)
        or artifact.get("ambiguous_distinct_target_count") != len(ambiguous_names)
        or artifact.get("unmatched_distinct_target_count") != current_unmatched_count
    ):
        return {
            "status": "CURRENT_REVIEW_DRIFT",
            "message": "현재 Gukgam NO_EXACT target 집합이 MOIS proposal 기준과 달라졌습니다. proposal 재생성이 필요합니다.",
            "artifact_sha256": _canonical_sha256(artifact),
            "write_performed": False,
            "items": [],
        }
    validated_items: list[dict[str, Any]] = []
    try:
        for raw_item in artifact_items:
            if not isinstance(raw_item, dict):
                raise TypeError("MOIS proposal item is invalid")
            name = raw_item.get("organization_name")
            provider = raw_item.get("provider")
            occurrences = raw_item.get("gukgam_occurrences")
            if (
                not isinstance(name, str)
                or not name.strip()
                or (not isinstance(provider, dict))
                or (not isinstance(occurrences, list))
                or (name.strip() in current_names)
            ):
                raise ValueError("MOIS proposal item conflicts with current Organizations")
            observation_id = UUID(str(provider.get("observation_id")))
            observation = repository.acquisition.feeder_observation(observation_id)
            if observation is None:
                raise ValueError("MOIS proposal observation is missing")
            current_provider = mois_organization_proposal_provider_row(observation).to_dict()
            if current_provider != provider:
                raise ValueError("MOIS proposal provider observation changed")
            occurrence_refs: list[dict[str, str]] = []
            for occurrence in occurrences:
                if not isinstance(occurrence, dict):
                    raise TypeError("MOIS proposal occurrence is invalid")
                review_key = occurrence.get("review_key")
                current = current_review.get(str(review_key))
                if (
                    current is None
                    or current.match_class != NO_EXACT
                    or current.candidates
                    or (current.audited_target.strip() != name.strip())
                    or (current.committee_name != occurrence.get("committee_name"))
                    or (current.audit_date != occurrence.get("audit_date"))
                    or (current.provider_record_key != occurrence.get("provider_record_key"))
                    or (str(current.observation_id) != occurrence.get("observation_id"))
                ):
                    raise ValueError("MOIS proposal Gukgam occurrence changed")
                occurrence_refs.append(
                    {
                        "review_key": current.review_key,
                        "committee_name": current.committee_name,
                        "audit_date": current.audit_date,
                        "audited_target": current.audited_target,
                        "observation_id": str(current.observation_id),
                    }
                )
            validated_items.append(
                {
                    "organization_name": name.strip(),
                    "org_code": str(provider.get("org_code")),
                    "lowest_name": provider.get("lowest_name"),
                    "type_big": provider.get("type_big"),
                    "type_mid": provider.get("type_mid"),
                    "parent_org_code": provider.get("parent_org_code"),
                    "top_org_code": provider.get("top_org_code"),
                    "representative_org_code": provider.get("representative_org_code"),
                    "base_date": provider.get("base_date"),
                    "changed_date": provider.get("changed_date"),
                    "observation_id": str(observation_id),
                    "occurrence_count": len(occurrence_refs),
                    "occurrences": occurrence_refs,
                    "materialization_authorized": False,
                }
            )
    except (TypeError, ValueError):
        return {
            "status": "CURRENT_REVIEW_DRIFT",
            "message": "MOIS proposal의 provider observation 또는 Gukgam occurrence가 현재 DB와 일치하지 않습니다. 자동 수정하지 않습니다.",
            "artifact_sha256": _canonical_sha256(artifact),
            "write_performed": False,
            "items": [],
        }
    validated_items.sort(key=lambda item: (item["organization_name"], item["org_code"]))
    return {
        "status": "HUMAN_REVIEW_REQUIRED_NO_WRITE",
        "message": "체크인된 MOIS proposal을 현재 checkpoint, exact provider observations, current Organizations와 Gukgam NO_EXACT occurrences에 대해 재검증했습니다.",
        "artifact_sha256": _canonical_sha256(artifact),
        "proposal_count": len(validated_items),
        "occurrence_count": sum(item["occurrence_count"] for item in validated_items),
        "unmatched_distinct_target_count": artifact.get("unmatched_distinct_target_count"),
        "ambiguous_distinct_target_count": artifact.get("ambiguous_distinct_target_count"),
        "materialization_authorized": False,
        "items": validated_items,
    }


def current_review_inspection(repository: Application) -> dict[str, Any]:
    before = datetime.now(UTC).isoformat()
    try:
        organizations, review = _current_gukgam_context(repository)
    except (RuntimeError, TypeError, ValueError):
        return {
            "status": "CURRENT_REVIEW_UNAVAILABLE",
            "message": "현재 Gukgam reviewed schedule/checkpoint를 canonical DB에서 복구하지 못했습니다. 과거 artifact로 대체하지 않습니다.",
            "checked_at": before,
            "write_performed": False,
            "gukgam_claim_review": {
                "status": "CURRENT_REVIEW_UNAVAILABLE",
                "items": [],
                "claim_commit_authorized": False,
            },
            "mois_organization_review": {
                "status": "CURRENT_REVIEW_UNAVAILABLE",
                "items": [],
                "materialization_authorized": False,
            },
        }
    gukgam = _gukgam_claim_review_inspection(repository, organizations, review)
    mois = _mois_review_inspection(repository, organizations, review)
    ready = (
        gukgam["status"] == "HUMAN_REVIEW_REQUIRED_NO_WRITE"
        and mois["status"] == "HUMAN_REVIEW_REQUIRED_NO_WRITE"
    )
    return {
        "status": "CURRENT_HUMAN_REVIEW_READY" if ready else "CURRENT_REVIEW_BLOCKED",
        "message": "현재 DB 기준 human-review lanes입니다. 어떤 항목도 자동 승인·반영하지 않습니다."
        if ready
        else "하나 이상의 review lane이 현재 DB와 일치하지 않아 fail-closed 상태입니다.",
        "checked_at": datetime.now(UTC).isoformat(),
        "write_performed": False,
        "gukgam_claim_review": gukgam,
        "mois_organization_review": mois,
    }
