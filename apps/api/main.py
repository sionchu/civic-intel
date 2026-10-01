from __future__ import annotations

import logging
import re
import secrets
from contextlib import asynccontextmanager
from urllib.parse import urlsplit
from uuid import UUID, uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from packages.application.context import Application
from packages.application.queries import DirectoryView, PublicApiError
from packages.bootstrap import bootstrap_database
from packages.persistence.database import Database


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "unavailable")


def _error_response(request: Request, *, status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        headers={"X-Request-ID": _request_id(request)},
        content={"error": {"code": code, "message": message, "request_id": _request_id(request)}},
    )


def create_app(
    target_repository: Database | None = None,
    *,
    enable_review_surface: bool = False,
    operator_token: str | None = None,
    operator_label: str = "LOCAL",
    operator_writes: bool = False,
    operator_actor: str = "local-operator",
) -> FastAPI:
    target = target_repository or Database()
    if operator_writes and (
        not operator_token or not re.fullmatch("[A-Za-z0-9_.@-]{1,100}", operator_actor)
    ):
        raise ValueError("Admin writes require an explicit private actor and token")
    if operator_token is not None and (
        not enable_review_surface or not re.fullmatch("[A-Za-z0-9_-]{32,128}", operator_token)
    ):
        raise ValueError("Operator token requires private opt-in and at least 32 safe characters")

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        bootstrap_database(target)
        yield

    app = FastAPI(
        title="Civic Intel API",
        version="0.5.0",
        lifespan=lifespan,
        docs_url=None if operator_token else "/docs",
        redoc_url=None if operator_token else "/redoc",
        openapi_url=None if operator_token else "/openapi.json",
    )

    @app.middleware("http")
    async def request_identity(request: Request, call_next):
        request.state.request_id = str(uuid4())
        if operator_token and request.url.path.startswith("/admin"):
            try:
                hostname = urlsplit("http://" + request.headers.get("host", "")).hostname
            except ValueError:
                hostname = None
            supplied = request.headers.get("x-civic-operator-token", "")
            if (
                hostname not in {"127.0.0.1", "localhost", "::1"}
                or request.headers.get("origin")
                or (not secrets.compare_digest(supplied.encode(), operator_token.encode()))
            ):
                return _error_response(
                    request,
                    status_code=403,
                    code="ACCESS_DENIED",
                    message="Operator access denied.",
                )
        response = await call_next(request)
        if request.url.path.startswith("/admin"):
            response.headers["Cache-Control"] = "private, no-store"
            response.headers["X-Robots-Tag"] = "noindex, nofollow"
        response.headers["X-Request-ID"] = request.state.request_id
        return response

    @app.exception_handler(PublicApiError)
    async def public_api_error(request: Request, exc: PublicApiError) -> JSONResponse:
        return _error_response(
            request, status_code=exc.status_code, code=exc.code, message=exc.message
        )

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request: Request, _: RequestValidationError) -> JSONResponse:
        return _error_response(
            request, status_code=422, code="INVALID_INPUT", message="The request input is invalid."
        )

    @app.exception_handler(HTTPException)
    async def framework_http_error(request: Request, exc: HTTPException) -> JSONResponse:
        if (
            operator_token
            and request.url.path.startswith("/admin/operations")
            and isinstance(exc.detail, dict)
            and isinstance(exc.detail.get("code"), str)
            and isinstance(exc.detail.get("message"), str)
        ):
            return _error_response(
                request,
                status_code=exc.status_code,
                code=exc.detail["code"],
                message=exc.detail["message"],
            )
        code = {403: "ACCESS_DENIED", 404: "PUBLIC_RECORD_NOT_FOUND", 422: "INVALID_INPUT"}.get(
            exc.status_code, "SERVICE_UNAVAILABLE"
        )
        message = {
            "ACCESS_DENIED": "This operation is not available.",
            "PUBLIC_RECORD_NOT_FOUND": "The public record was not found.",
            "INVALID_INPUT": "The request input is invalid.",
            "SERVICE_UNAVAILABLE": "The public data service is temporarily unavailable.",
        }[code]
        return _error_response(request, status_code=exc.status_code, code=code, message=message)

    @app.exception_handler(Exception)
    async def unexpected_error(request: Request, _: Exception) -> JSONResponse:
        return _error_response(
            request,
            status_code=503,
            code="SERVICE_UNAVAILABLE",
            message="The public data service is temporarily unavailable.",
        )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/ready")
    def ready() -> dict[str, str]:
        target.assert_ready()
        target.ping()
        return {"status": "ready"}

    @app.get("/people")
    def people() -> list[dict]:
        with target(read_only=True) as uow:
            return DirectoryView(uow).people()

    @app.get("/people/{person_id}")
    def person(person_id: UUID) -> dict:
        with target(read_only=True) as uow:
            return DirectoryView(uow).person(person_id)

    @app.get("/ontology/people/{person_id}")
    def person_ontology(person_id: UUID) -> dict:
        with target(read_only=True) as uow:
            return DirectoryView(uow).person_ontology(person_id)

    @app.get("/ontology/organizations/{organization_id}")
    def organization_ontology(organization_id: UUID) -> dict:
        with target(read_only=True) as uow:
            return DirectoryView(uow).organization_ontology(organization_id)

    @app.get("/organizations")
    def organizations() -> list[dict]:
        with target(read_only=True) as uow:
            return DirectoryView(uow).organizations()

    @app.get("/gukgam/2026/targets")
    def gukgam_2026_targets() -> dict:
        with target(read_only=True) as uow:
            return DirectoryView(uow).gukgam_2026_targets()

    @app.get("/people/{person_id}/claims")
    def claims(person_id: UUID) -> list[dict]:
        with target(read_only=True) as uow:
            return DirectoryView(uow).claims(person_id)

    @app.get("/organizations/{organization_id}")
    def organization(organization_id: UUID) -> dict:
        with target(read_only=True) as uow:
            return DirectoryView(uow).organization(organization_id)

    @app.get("/organizations/{organization_id}/claims")
    def organization_claims(organization_id: UUID) -> list[dict]:
        with target(read_only=True) as uow:
            return DirectoryView(uow).organization_claims(organization_id)

    @app.get("/organizations/{organization_id}/money")
    def organization_money(
        organization_id: UUID, earlier_fiscal_year: int = 2024, later_fiscal_year: int = 2025
    ) -> dict:
        with target(read_only=True) as uow:
            return DirectoryView(uow).organization_money(
                organization_id, earlier_fiscal_year, later_fiscal_year
            )

    @app.get("/people/{person_id}/relationships")
    def relationships(person_id: UUID) -> list[dict]:
        with target(read_only=True) as uow:
            return DirectoryView(uow).relationships(person_id)

    @app.get("/people/{person_id}/assets")
    def assets(person_id: UUID) -> list:
        with target(read_only=True) as uow:
            return DirectoryView(uow).assets(person_id)

    @app.get("/sources/{source_id}")
    def get_source(source_id: UUID) -> dict:
        with target(read_only=True) as uow:
            return DirectoryView(uow).get_source(source_id)

    if enable_review_surface:

        @app.get("/admin/gukgam/2026/schedule")
        def gukgam_2026_schedule_review() -> dict:
            with target(read_only=True) as uow:
                return DirectoryView(uow).gukgam_2026_schedule_review()

        @app.get("/admin/gukgam/2026/organization-binding-candidates")
        def gukgam_2026_organization_binding_candidates() -> dict:
            with target(read_only=True) as uow:
                return DirectoryView(uow).gukgam_2026_organization_binding_candidates()

        @app.get("/admin/gukgam/2026/organization-binding-preflight")
        def gukgam_2026_organization_binding_preflight(
            review_key: str, organization_id: UUID
        ) -> dict:
            with target(read_only=True) as uow:
                return DirectoryView(uow).gukgam_2026_organization_binding_preflight(
                    review_key, organization_id
                )

        @app.get("/admin/review")
        def review_report() -> dict:
            with target(read_only=True) as uow:
                return DirectoryView(uow).review_report()

    if operator_token:

        @app.exception_handler(SQLAlchemyError)
        async def operator_database_error(request: Request, error: SQLAlchemyError) -> JSONResponse:
            original = getattr(error, "orig", None)
            sqlstate = getattr(original, "sqlstate", None)
            state = (
                sqlstate
                if isinstance(sqlstate, str) and re.fullmatch("[A-Z0-9]{5}", sqlstate)
                else "unknown"
            )
            logging.getLogger(__name__).warning(
                "private_db_unavailable class=%s sqlstate=%s invalidated=%s",
                type(original).__name__,
                state,
                bool(getattr(error, "connection_invalidated", False)),
            )
            return _error_response(
                request,
                status_code=503,
                code="SERVICE_UNAVAILABLE",
                message="Private database connection unavailable. Refresh after reconnection.",
            )

        from apps.api.operator import build_operator_router

        app.include_router(build_operator_router(Application(target), operator_label))
        from apps.api.playbook import build_playbook_router

        app.include_router(
            build_playbook_router(
                Application(target).administration, actor=operator_actor, label=operator_label
            )
        )
        from apps.api.admin import build_admin_router

        app.include_router(
            build_admin_router(
                Application(target).administration,
                operator_token,
                writes=operator_writes,
                actor=operator_actor,
            )
        )

    @app.get("/{public_path:path}", include_in_schema=False)
    def public_route_not_found(public_path: str) -> dict:
        raise PublicApiError(404, "PUBLIC_RECORD_NOT_FOUND", "The public record was not found.")

    return app


app = create_app()
