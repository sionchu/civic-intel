"""Exact selected references for a DRAFT; no writes, model calls or side-effect runners."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from packages.domain import db
from packages.domain.work_orders import WorkOrderRequest
from packages.persistence.admin_workflow import AdminError, digest, receipt
from packages.persistence.operator_queries import MODELS, _columns, _record


def prepare_references(session: Session, request: WorkOrderRequest) -> dict[str, Any]:
    requested: dict[tuple[str, str], Any] = {(item.kind, str(item.id)): item for item in request.references}
    resolved: dict[tuple[str, str], dict[str, Any]] = {}
    for kind in sorted({item.kind for item in request.references}):
        ids = [str(item.id) for item in request.references if item.kind == kind]
        if kind == "operations":
            for operation_row in session.scalars(
                select(db.AdminOperationRow).where(db.AdminOperationRow.id.in_(ids))
            ):
                value = receipt(operation_row)
                resolved[(kind, operation_row.id)] = {
                    "id": operation_row.id,
                    "kind": kind,
                    "version": value["version"],
                    "fields": {"status": "COMMITTED", "created_at": value["created_at"]},
                }
        else:
            for row in session.execute(
                select(*_columns(kind)).where(MODELS[kind].id.in_(ids))
            ).mappings():
                resolved[(kind, str(row["id"]))] = _record(kind, row)
    if set(resolved) != set(requested):
        raise AdminError(
            "WORK_INPUT_MISSING", "선택한 기록 일부가 없습니다. 목록을 새로 확인하세요."
        )
    for key, record in resolved.items():
        if record["version"] != requested[key].version:
            raise AdminError(
                "WORK_INPUT_CHANGED",
                "선택한 자료가 화면을 연 뒤 바뀌었습니다. 새로 조회한 뒤 요청서를 준비하세요.",
            )
        if request.recipe_id == "collection_failure" and record["fields"].get("status") not in {
            "FAILED",
            "PARTIAL",
        }:
            raise AdminError("WORK_NOT_FAILED_RUN", "실패 또는 부분 완료된 수집 실행을 선택하세요.")

    # Reference IDs only. Do not export displayed names, raw errors, excerpts, provider keys or URLs.
    result = []
    for reference in request.references:
        record = resolved[(reference.kind, str(reference.id))]
        fields = record["fields"]
        anchors = {
            field: fields[field]
            for field in (
                "snapshot_id",
                "run_id",
                "source_id",
                "claim_id",
                "feeder_observation_id",
                "person_id",
                "organization_id",
                "policy_id",
                "content_hash",
            )
            if fields.get(field)
        }
        result.append(
            {
                **reference.model_dump(mode="json"),
                "anchors": anchors,
                "view_href": f"/admin/review?tab=records&kind={reference.kind}&focus_kind={reference.kind}&focus_id={reference.id}"
                if reference.kind != "operations"
                else "/admin/review?tab=history",
            }
        )

    scope_rows = [
        record["fields"]
        for record in resolved.values()
        if record["kind"] in {"observations", "runs"}
    ]
    scopes = sorted({(str(row["feeder"]), str(row["scope_key"])) for row in scope_rows})
    source_ids: set[str] = set()
    snapshot_ids = {
        item["anchors"]["snapshot_id"] for item in result if item["anchors"].get("snapshot_id")
    }
    source_ids.update(
        item["anchors"]["source_id"] for item in result if item["anchors"].get("source_id")
    )
    if snapshot_ids:
        source_ids.update(
            session.scalars(
                select(db.SourceSnapshotRow.source_id).where(
                    db.SourceSnapshotRow.id.in_(snapshot_ids)
                )
            )
        )
    policies = []
    if source_ids:
        rows = session.execute(
            select(
                db.SourceRow.id,
                db.SourcePolicyRow.id.label("policy_id"),
                db.SourcePolicyRow.can_send_to_ai,
            )
            .join(db.SourcePolicyRow, db.SourceRow.policy_id == db.SourcePolicyRow.id)
            .where(db.SourceRow.id.in_(source_ids))
        ).mappings()
        policies = [
            {
                "source_id": row["id"],
                "policy_id": row["policy_id"],
                "can_send_source_content_to_ai": row["can_send_to_ai"],
            }
            for row in rows
        ]
    return {
        "references": result,
        "scope_pairs": [{"feeder": f, "scope": s} for f, s in scopes],
        "selected_view_sha256": digest(result),
        "source_policies": sorted(policies, key=lambda p: p["source_id"]),
        "source_content_included": False,
        "source_content_ai_permission": "RECHECK_BEFORE_FETCH_OR_SEND",
        "scope_basis": "SELECTED_REFERENCE_VIEWS_ONLY_NOT_FULL_GRAPH_OR_DATABASE_SNAPSHOT",
    }
