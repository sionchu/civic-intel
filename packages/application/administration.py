from __future__ import annotations

from collections.abc import Sequence
from typing import Any
from uuid import UUID

from packages.application.ports import UnitOfWorkFactory


class AdministrationService:
    def __init__(self, uows: UnitOfWorkFactory):
        self.uows = uows

    def operator_summary(self, *, monitoring: bool = False) -> dict[str, Any]:
        with self.uows(read_only=True) as uow:
            result = (
                uow.administration.operator_summary(monitoring=True)
                if monitoring else uow.administration.operator_summary()
            )
            return result

    def operator_records(self, kind: str, **filters: Any) -> dict[str, Any]:
        with self.uows(read_only=True) as uow:
            result = uow.administration.operator_records(kind, **filters)
            return result

    def operator_record_detail(self, kind: str, record_id: str) -> dict[str, Any] | None:
        with self.uows(read_only=True) as uow:
            result = uow.administration.operator_record_detail(kind, record_id)
            return result

    def prepare_work_order_references(self, request) -> dict[str, Any]:
        with self.uows(read_only=True) as uow:
            result = uow.administration.prepare_work_order_references(request)
            return result

    def prepare_alio_person_materialization(self):
        with self.uows(read_only=True) as uow:
            result = uow.administration.prepare_alio_person_materialization()
            return result

    def commit_alio_person_materialization(self, *, expected_receipt_sha256: str) -> dict[str, Any]:
        self.uows.assert_ready()
        with self.uows(read_only=False) as uow:
            result = uow.administration.commit_alio_person_materialization(
                expected_receipt_sha256=expected_receipt_sha256
            )
            uow.commit()
            return result

    def prepare_nec_person_materialization(
        self, *, election_id: str = "20260603", election_types: Sequence[int] = (3, 4, 5, 6, 11)
    ):
        with self.uows(read_only=True) as uow:
            result = uow.administration.prepare_nec_person_materialization(
                election_id=election_id, election_types=election_types
            )
            return result

    def commit_nec_person_materialization(
        self,
        *,
        expected_receipt_sha256: str,
        election_id: str = "20260603",
        election_types: Sequence[int] = (3, 4, 5, 6, 11),
    ) -> dict[str, Any]:
        self.uows.assert_ready()
        with self.uows(read_only=False) as uow:
            result = uow.administration.commit_nec_person_materialization(
                expected_receipt_sha256=expected_receipt_sha256,
                election_id=election_id,
                election_types=election_types,
            )
            uow.commit()
            return result

    def admin_preview(self, command):
        with self.uows(read_only=True) as uow:
            result = uow.administration.admin_preview(command)
            return result

    def inspect_gukgam_witness_release(self, claim_id: UUID) -> dict[str, Any]:
        self.uows.assert_ready()
        with self.uows(read_only=True) as uow:
            return uow.administration.inspect_gukgam_witness_release(claim_id)

    def admin_commit(self, command, actor: str, state_hash: str) -> dict[str, Any]:
        self.uows.assert_ready()
        with self.uows(read_only=False) as uow:
            result = uow.administration.admin_commit(command, actor, state_hash)
            uow.commit()
            return result

    def admin_evidence_options(self, q: str = "", limit: int = 10) -> list[dict[str, Any]]:
        with self.uows(read_only=True) as uow:
            result = uow.administration.admin_evidence_options(q, limit)
            return result

    def admin_queue(self, **filters: Any) -> dict[str, Any]:
        with self.uows(read_only=True) as uow:
            result = uow.administration.admin_queue(**filters)
            return result

    def admin_history(self, offset: int = 0, limit: int = 25) -> dict[str, Any]:
        with self.uows(read_only=True) as uow:
            result = uow.administration.admin_history(offset, limit)
            return result

    def admin_schema_ready(self) -> bool:
        with self.uows(read_only=True) as uow:
            result = uow.administration.admin_schema_ready()
            return result
