"""Private operator reads; canonical persistence and publication remain unchanged."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import event
from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError

from apps.api.operator_review import current_review_inspection
from apps.api.operator_review_metrics import (
    GukgamReviewMetricInput,
    default_review_receipt_path,
    gukgam_review_metric_summary,
    record_gukgam_review_metric,
)
from packages.persistence import DatabaseNotReady, SqlAlchemyRepository
from packages.persistence.operator_queries import MODELS
from packages.persistence.repository import EXPECTED_SCHEMA_REVISION

ROOT = Path(__file__).resolve().parents[2]


def configure_read_only(repository: SqlAlchemyRepository, *, allow_writes: bool = False) -> None:
    """Apply database-enforced read-only defaults to this dedicated engine only."""
    dialect = repository.engine.dialect.name
    if dialect not in {"sqlite", "postgresql"}:
        raise RuntimeError("Operator console supports SQLite or PostgreSQL only")

    @event.listens_for(repository.engine, "connect")
    def readonly_connection(connection: Any, _: Any) -> None:
        cursor = connection.cursor()
        try:
            if dialect == "sqlite":
                cursor.execute("PRAGMA query_only = OFF" if allow_writes else "PRAGMA query_only = ON")
                cursor.execute("PRAGMA busy_timeout = 5000")
            else:
                connection.autocommit = True
                cursor.execute("SET default_transaction_read_only = off" if allow_writes else "SET default_transaction_read_only = on")
                cursor.execute("SET statement_timeout = 15000")
                cursor.execute("SET idle_in_transaction_session_timeout = 20000")
                cursor.execute("SET default_transaction_isolation = 'read committed'" if allow_writes
                               else "SET default_transaction_isolation = 'repeatable read'")
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
    return current_review_inspection(repository)


def build_operator_router(
    repository: SqlAlchemyRepository,
    label: str,
    *,
    actor: str = "local-operator",
    review_receipt_path: Path | None = None,
) -> APIRouter:
    router = APIRouter(prefix="/admin/operations", include_in_schema=False)
    receipt_path = review_receipt_path or default_review_receipt_path()

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

    @router.get("/review-throughput")
    def review_throughput(
        manifest_sha256: str = Query(..., pattern=r"^[0-9a-f]{64}$"),
    ) -> dict[str, Any]:
        try:
            return gukgam_review_metric_summary(
                inspection=current_review_inspection(repository),
                manifest_sha256=manifest_sha256,
                receipt_path=receipt_path,
                repo_root=ROOT,
            )
        except (TypeError, ValueError) as exc:
            raise HTTPException(
                409,
                {"code": "REVIEW_STATE_CONFLICT", "message": str(exc)},
            ) from exc
        except OSError as exc:
            raise HTTPException(
                503,
                {
                    "code": "REVIEW_RECEIPT_UNAVAILABLE",
                    "message": "Private review receipt storage is unavailable.",
                },
            ) from exc

    @router.post("/review-throughput")
    def record_review_throughput(
        request: GukgamReviewMetricInput,
    ) -> dict[str, Any]:
        try:
            return record_gukgam_review_metric(
                inspection=current_review_inspection(repository),
                actor=actor,
                request=request,
                receipt_path=receipt_path,
                repo_root=ROOT,
            )
        except (TypeError, ValueError) as exc:
            raise HTTPException(
                409,
                {"code": "REVIEW_STATE_CONFLICT", "message": str(exc)},
            ) from exc
        except OSError as exc:
            raise HTTPException(
                503,
                {
                    "code": "REVIEW_RECEIPT_UNAVAILABLE",
                    "message": "Private review receipt storage is unavailable.",
                },
            ) from exc

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
        repository = SqlAlchemyRepository(url, pool_pre_ping=True)
        configure_read_only(repository, allow_writes=writes)
        repository.assert_ready()
        if writes and not repository.admin_schema_ready():
            raise RuntimeError("Admin writes require a reviewed admin-receipt schema (0007 or 0008)")
    except (SQLAlchemyError, DatabaseNotReady, OSError, ValueError):
        raise RuntimeError(
            "Private operator database is not ready; no migration or write performed"
        ) from None
    return create_app(
        repository, enable_review_surface=True, operator_token=token, operator_label=label,
        operator_writes=writes, operator_actor=actor
    )
