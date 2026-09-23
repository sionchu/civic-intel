"""Server-authorized preview/confirmation of bounded administrative transactions."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import ValidationError

from packages.domain.admin import AdminAction, AdminCommand, AdminCommit
from packages.persistence import SqlAlchemyRepository
from packages.persistence.admin_workflow import AdminError, digest
from packages.verification.policy import PolicyDenied


def sign_preview(command: AdminCommand, actor: str, state: str, secret: str) -> str:
    payload = json.dumps(
        {
            "request": str(command.request_id),
            "command": digest(command.model_dump(mode="json")),
            "actor": actor,
            "state": state,
            "expires": int(time.time()) + 300,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    encoded = base64.urlsafe_b64encode(payload).decode().rstrip("=")
    signature = hmac.new(secret.encode(), encoded.encode(), hashlib.sha256).hexdigest()
    return encoded + "." + signature


def verify_preview(token: str, command: AdminCommand, actor: str, secret: str) -> str:
    try:
        encoded, signature = token.split(".", 1)
        expected = hmac.new(secret.encode(), encoded.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected):
            raise ValueError("signature")
        payload = json.loads(base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4)))
        if (
            payload["actor"] != actor
            or payload["request"] != str(command.request_id)
            or payload["command"] != digest(command.model_dump(mode="json"))
            or payload["expires"] < time.time()
        ):
            raise ValueError("scope or expiry")
        return payload["state"]
    except (ValueError, KeyError, TypeError):
        raise AdminError(
            "INVALID_PREVIEW", "미리보기가 만료되었거나 변경되었습니다. 다시 확인하세요."
        ) from None


def build_admin_router(
    repository: SqlAlchemyRepository, secret: str, *, writes: bool, actor: str
) -> APIRouter:
    router = APIRouter(prefix="/admin/operations", include_in_schema=False)

    @router.get("/capabilities")
    def capabilities() -> dict[str, Any]:
        schema = repository.admin_schema_ready()
        return {
            "schema_ready": schema,
            "writes_enabled": writes and schema,
            "actor": actor,
            "write_mode_requested": writes,
            "schema_required": "0007",
            "operations": [action.value for action in AdminAction],
        }

    @router.get("/people-review")
    def people_review(
        q: str = Query("", max_length=200),
        state: str = "UNREVIEWED",
        offset: int = Query(0, ge=0, le=100000),
        limit: int = Query(25, ge=1, le=100),
    ) -> dict:
        try:
            return repository.admin_queue(q=q, state=state, offset=offset, limit=limit)
        except ValueError as exc:
            raise HTTPException(422, "Unsupported review filters") from exc

    @router.get("/evidence-options")
    def evidence_options(q: str = Query("", max_length=200)) -> dict:
        return {"items": repository.admin_evidence_options(q)}

    @router.get("/history")
    def history(
        offset: int = Query(0, ge=0, le=100000), limit: int = Query(25, ge=1, le=100)
    ) -> dict:
        return repository.admin_history(offset, limit)

    @router.post("/preview")
    def preview(command: AdminCommand) -> dict:
        try:
            report = repository.admin_preview(command)
            return {
                **report,
                "preview_token": sign_preview(command, actor, report["state_hash"], secret),
                "expires_in_seconds": 300,
                "writes_enabled": writes and repository.admin_schema_ready(),
                "actor": actor,
            }
        except AdminError as exc:
            raise HTTPException(409, {"code": exc.code, "message": exc.message}) from exc
        except (PolicyDenied, ValidationError, ValueError):
            raise HTTPException(
                422,
                {
                    "code": "VALIDATION_BLOCKED",
                    "message": "출처·신원·내용 검증을 통과하지 못했습니다.",
                },
            ) from None

    @router.post("/commit")
    def commit(request: AdminCommit) -> dict:
        if not writes or not request.confirmed:
            raise HTTPException(
                403,
                {
                    "code": "WRITE_NOT_AUTHORIZED",
                    "message": "쓰기 모드와 명시적 최종 확인이 필요합니다.",
                },
            )
        try:
            state = verify_preview(request.preview_token, request.command, actor, secret)
            return repository.admin_commit(request.command, actor, state)
        except AdminError as exc:
            raise HTTPException(409, {"code": exc.code, "message": exc.message}) from exc
        except (PolicyDenied, ValidationError, ValueError):
            raise HTTPException(
                422,
                {
                    "code": "VALIDATION_BLOCKED",
                    "message": "현재 데이터가 검증 조건을 충족하지 않습니다. 전체 작업을 취소했습니다.",
                },
            ) from None

    return router
