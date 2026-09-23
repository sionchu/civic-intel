"""Private operator reads; canonical persistence and publication remain unchanged."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import event
from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError

from packages.persistence import DatabaseNotReady, SqlAlchemyRepository
from packages.persistence.operator_queries import MODELS, safe_url
from packages.persistence.repository import EXPECTED_SCHEMA_REVISION
from workers.orggo_reviewed_organization_manifest import (
    organization_id_for_orggo_code,
    parse_reviewed_orggo_organization_manifest,
    prepare_reviewed_orggo_organization_manifest,
)

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "docs/research/orggo_reviewed_organization_manifest_2026-09-22.json"
PROPOSAL = ROOT / "docs/research/gukgam_2026_orggo_organization_proposal_2026-09-22.json"


def configure_read_only(repository: SqlAlchemyRepository) -> None:
    """Apply database-enforced read-only defaults to this dedicated engine only."""
    dialect = repository.engine.dialect.name
    if dialect not in {"sqlite", "postgresql"}:
        raise RuntimeError("Operator console supports SQLite or PostgreSQL only")

    @event.listens_for(repository.engine, "connect")
    def readonly_connection(connection: Any, _: Any) -> None:
        cursor = connection.cursor()
        try:
            if dialect == "sqlite":
                cursor.execute("PRAGMA query_only = ON")
                cursor.execute("PRAGMA busy_timeout = 5000")
            else:
                connection.autocommit = True
                cursor.execute("SET default_transaction_read_only = on")
                cursor.execute("SET statement_timeout = 15000")
                cursor.execute("SET idle_in_transaction_session_timeout = 20000")
                cursor.execute("SET default_transaction_isolation = 'repeatable read'")
                connection.autocommit = False
        finally:
            cursor.close()

    repository.engine.dispose()


def documented_catalog() -> list[dict[str, str]]:
    """Read the existing strategy table, clearly separate from runtime measurements."""
    document = ROOT / "docs/architecture/FEEDER_SOURCE_COVERAGE.md"
    if not document.exists():
        return []
    section = document.read_text(encoding="utf-8").split("## Coverage matrix", 1)
    if len(section) != 2:
        return []
    table = section[1].split("\n## ", 1)[0]
    result = []
    for line in table.splitlines():
        cells = [part.strip().replace("`", "") for part in line.strip().strip("|").split("|")]
        if not line.startswith("|") or len(cells) != 7 or cells[0] in {"Feeder", "---"}:
            continue
        result.append(
            {
                "name": cells[0],
                "scope": cells[1],
                "source": cells[2],
                "mode": cells[3],
                "maturity": cells[6],
                "basis": "DOCUMENTED_CAPABILITY_NOT_LIVE_COVERAGE",
            }
        )
    return result


def manifest_inspection(repository: SqlAlchemyRepository) -> dict[str, Any]:
    try:
        manifest = parse_reviewed_orggo_organization_manifest(
            json.loads(MANIFEST.read_text(encoding="utf-8"))
        )
        proposal = json.loads(PROPOSAL.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return {
            "status": "ARTIFACT_UNAVAILABLE",
            "write_performed": False,
            "message": "검토 artifact를 읽을 수 없습니다. 저장 상태와 다릅니다.",
        }
    # Canonical preflight is the only authority for CREATE/REUSE. Nothing here commits.
    try:
        preflight = prepare_reviewed_orggo_organization_manifest(repository, manifest, proposal)
        created = sum(item.action == "CREATE" for item in preflight.prepared_items)
        reused = sum(item.action == "REUSE" for item in preflight.prepared_items)
        state = "ALL_PRESENT" if not created else "PARTIAL_BLOCKED" if reused else "READY_NO_WRITE"
        items: list[dict[str, Any]] = [item.to_dict() for item in preflight.prepared_items]
        message = "현재 DB에 대한 읽기 전용 재검증입니다. 과거 receipt 또는 commit 증명이 아닙니다."
    except (ValueError, TypeError):
        state = "BASELINE_OR_IDENTITY_CONFLICT"
        items = [
            {
                **item.to_dict(),
                "organization_id": str(organization_id_for_orggo_code(item.org_code)),
                "action": "BLOCKED",
            }
            for item in manifest.items
        ]
        created, reused = None, None
        message = (
            "검토 당시 기준과 현재 DB가 다르거나 ID/기관명 충돌이 있습니다. 자동 수정하지 않습니다."
        )
    occurrences = {
        item["provider"]["org_code"]: item.get("occurrence_count", 0)
        for item in proposal.get("items", [])
    }
    for item in items:
        item["source_locator"] = safe_url(item["source_locator"])
        item["review_occurrences"] = occurrences.get(item["org_code"], 0)
    return {
        "status": state,
        "message": message,
        "manifest_sha256": manifest.sha256(),
        "proposal_core_sha256": manifest.proposal_core_sha256,
        "item_count": len(items),
        "organizations_to_create": created,
        "organizations_to_reuse": reused,
        "items": items,
        "checked_at": datetime.now(UTC).isoformat(),
        "write_performed": False,
        "gukgam_claim_publication": False,
    }


def build_operator_router(repository: SqlAlchemyRepository, label: str) -> APIRouter:
    router = APIRouter(prefix="/admin/operations", include_in_schema=False)

    @router.get("")
    def overview() -> dict[str, Any]:
        return {
            **repository.operator_summary(),
            "checked_at": datetime.now(UTC).isoformat(),
            "environment_label": label,
            "label_basis": "OPERATOR_SUPPLIED",
            "schema_expected": EXPECTED_SCHEMA_REVISION,
            "documented_catalog": documented_catalog(),
        }

    @router.get("/records")
    def record_list(
        kind: str = "organizations",
        q: str = Query("", max_length=200),
        feeder: str = Query("", max_length=100),
        scope: str = Query("", max_length=300),
        status: str = Query("", max_length=32),
        offset: int = Query(0, ge=0, le=100000),
        limit: int = Query(25, ge=1, le=100),
    ) -> dict[str, Any]:
        try:
            return repository.operator_records(
                kind, q=q, feeder=feeder, scope=scope, status=status, offset=offset, limit=limit
            )
        except ValueError as exc:
            raise HTTPException(422, "Unsupported record kind or filters") from exc

    @router.get("/records/{kind}/{record_id}")
    def record_detail(kind: str, record_id: UUID) -> dict[str, Any]:
        if kind not in MODELS:
            raise HTTPException(422, "Unsupported record kind")
        result = repository.operator_record_detail(kind, str(record_id))
        if result is None:
            raise HTTPException(404, "Record not found")
        return result

    @router.get("/manifest")
    def manifest() -> dict[str, Any]:
        return manifest_inspection(repository)

    return router


def create_operator_app() -> Any:
    from apps.api.main import create_app

    url = os.environ.get("DATABASE_URL", "")
    token = os.environ.get("CIVIC_OPERATOR_TOKEN", "")
    label = os.environ.get("CIVIC_OPERATOR_LABEL", "LOCAL")
    if not url or not token or os.environ.get("CIVIC_OPERATOR_ENABLED") != "1":
        raise RuntimeError("Explicit DATABASE_URL and operator opt-in are required")
    if label not in {"LOCAL", "STAGING", "RESTORED", "TEST"}:
        raise RuntimeError("Invalid operator environment label")
    try:
        parsed = make_url(url)
    except (SQLAlchemyError, ValueError):
        raise RuntimeError("Invalid private operator database configuration") from None
    if parsed.get_backend_name() == "sqlite" and (
        not parsed.database or not Path(parsed.database).is_file()
    ):
        raise RuntimeError("An existing migrated database is required; no automatic creation")
    try:
        repository = SqlAlchemyRepository(url, pool_pre_ping=True)
        configure_read_only(repository)
        repository.assert_ready()
    except (SQLAlchemyError, DatabaseNotReady, OSError, ValueError):
        raise RuntimeError(
            "Private operator database is not ready; no migration or write performed"
        ) from None
    return create_app(
        repository, enable_review_surface=True, operator_token=token, operator_label=label
    )
