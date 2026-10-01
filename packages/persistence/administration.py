from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sqlalchemy.orm import Session


class AdministrationRepository:
    def __init__(self, session: Session):
        self._session = session

    def operator_summary(self) -> dict[str, Any]:
        from packages.persistence.operator_queries import summary

        session = self._session
        return summary(session)

    def operator_records(self, kind: str, **filters: Any) -> dict[str, Any]:
        from packages.persistence.operator_queries import records

        session = self._session
        return records(session, kind, **filters)

    def operator_record_detail(self, kind: str, record_id: str) -> dict[str, Any] | None:
        from packages.persistence.operator_queries import detail

        session = self._session
        return detail(session, kind, record_id)

    def prepare_work_order_references(self, request) -> dict[str, Any]:
        from packages.persistence.work_orders import prepare_references

        session = self._session
        with session.no_autoflush:
            return prepare_references(session, request)

    def prepare_alio_person_materialization(self):
        from packages.persistence.alio_person_materialization import (
            prepare_alio_person_materialization,
        )

        session = self._session
        with session.no_autoflush:
            return prepare_alio_person_materialization(session)

    def commit_alio_person_materialization(self, *, expected_receipt_sha256: str) -> dict[str, Any]:
        from packages.persistence.alio_person_materialization import (
            commit_alio_person_materialization,
        )

        session = self._session
        result = commit_alio_person_materialization(
            session, expected_receipt_sha256=expected_receipt_sha256
        )
        session.flush()
        return result

    def prepare_nec_person_materialization(
        self, *, election_id: str = "20260603", election_types: Sequence[int] = (3, 4, 5, 6, 11)
    ):
        from packages.persistence.nec_person_materialization import (
            prepare_nec_person_materialization,
        )

        session = self._session
        with session.no_autoflush:
            return prepare_nec_person_materialization(
                session, election_id=election_id, election_types=election_types
            )

    def commit_nec_person_materialization(
        self,
        *,
        expected_receipt_sha256: str,
        election_id: str = "20260603",
        election_types: Sequence[int] = (3, 4, 5, 6, 11),
    ) -> dict[str, Any]:
        from packages.persistence.nec_person_materialization import (
            commit_nec_person_materialization,
        )

        session = self._session
        result = commit_nec_person_materialization(
            session,
            expected_receipt_sha256=expected_receipt_sha256,
            election_id=election_id,
            election_types=election_types,
        )
        session.flush()
        return result

    def admin_preview(self, command):
        from packages.persistence.admin_workflow import build_plan

        session = self._session
        with session.no_autoflush:
            return build_plan(session, command).report()

    def admin_commit(self, command, actor: str, state_hash: str) -> dict[str, Any]:
        from packages.persistence.admin_workflow import commit_command

        session = self._session
        result = commit_command(session, command, actor, state_hash)
        session.flush()
        return result

    def admin_evidence_options(self, q: str = "", limit: int = 10) -> list[dict[str, Any]]:
        from packages.persistence.admin_queries import evidence_options

        session = self._session
        return evidence_options(session, q, limit)

    def admin_queue(self, **filters: Any) -> dict[str, Any]:
        from packages.persistence.admin_queries import person_review_queue

        session = self._session
        return person_review_queue(session, **filters)

    def admin_history(self, offset: int = 0, limit: int = 25) -> dict[str, Any]:
        from packages.persistence.admin_workflow import history

        session = self._session
        return history(session, offset, limit)

    def admin_schema_ready(self) -> bool:
        from packages.persistence.admin_workflow import admin_schema_ready

        return admin_schema_ready(self._session)
