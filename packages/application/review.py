from __future__ import annotations

from uuid import UUID

from packages.application.ports import UnitOfWorkFactory
from packages.domain.contracts import (
    IdentityReviewItem,
)
from packages.domain.enums import (
    IdentityReviewStatus,
)


class ReviewService:
    def __init__(self, uows: UnitOfWorkFactory):
        self.uows = uows

    def identity_review_items(
        self, status: IdentityReviewStatus | None = None
    ) -> list[IdentityReviewItem]:
        with self.uows(read_only=True) as uow:
            result = uow.review.identity_review_items(status)
            return result

    def resolve_assembly_distinct_person_review(
        self, review_item_id: UUID, *, resolution_note: str
    ) -> MaterializationResult:
        self.uows.assert_ready()
        with self.uows(read_only=False) as uow:
            result = uow.review.resolve_assembly_distinct_person_review(
                review_item_id, resolution_note=resolution_note
            )
            uow.commit()
            return result


from packages.verification.materialization import MaterializationResult
