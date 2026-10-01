"""Private operator reads; canonical persistence and publication remain unchanged."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError

from apps.api.operator_review import current_review_inspection
from packages.application.context import Application
from packages.persistence import DatabaseNotReady
from packages.persistence.database import EXPECTED_SCHEMA_REVISION, Database
from packages.persistence.operator_database import configure_read_only
from packages.persistence.operator_queries import MODELS

ROOT = Path(__file__).resolve().parents[2]


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


def manifest_inspection(repository: Application) -> dict[str, Any]:
    return current_review_inspection(repository)


def build_operator_router(repository: Application, label: str) -> APIRouter:
    router = APIRouter(prefix="/admin/operations", include_in_schema=False)

    @router.get("")
    def overview() -> dict[str, Any]:
        return {
            **repository.administration.operator_summary(),
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
            return repository.administration.operator_records(
                kind, q=q, feeder=feeder, scope=scope, status=status, offset=offset, limit=limit
            )
        except ValueError as exc:
            raise HTTPException(422, "Unsupported record kind or filters") from exc

    @router.get("/records/{kind}/{record_id}")
    def record_detail(kind: str, record_id: UUID) -> dict[str, Any]:
        if kind not in MODELS:
            raise HTTPException(422, "Unsupported record kind")
        result = repository.administration.operator_record_detail(kind, str(record_id))
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
    writes = os.environ.get("CIVIC_OPERATOR_WRITES") == "1"
    actor = os.environ.get("CIVIC_OPERATOR_ACTOR", "local-operator")
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
        repository = Database(url, pool_pre_ping=True)
        configure_read_only(repository, allow_writes=writes)
        repository.assert_ready()
        if writes and (not Application(repository).administration.admin_schema_ready()):
            raise RuntimeError(
                "Admin writes require a reviewed admin-receipt schema (0007 or 0008)"
            )
    except (SQLAlchemyError, DatabaseNotReady, OSError, ValueError):
        raise RuntimeError(
            "Private operator database is not ready; no migration or write performed"
        ) from None
    return create_app(
        repository,
        enable_review_surface=True,
        operator_token=token,
        operator_label=label,
        operator_writes=writes,
        operator_actor=actor,
    )
