from __future__ import annotations

from packages.application.ports import UnitOfWorkFactory
from packages.domain.contracts import (
    Person,
)
from packages.verification.golden import GoldenSet
from packages.verification.person_onboarding import ReviewedPersonBundle


class OnboardingService:
    def __init__(self, uows: UnitOfWorkFactory):
        self.uows = uows

    def seed_golden(self, golden: GoldenSet | None = None) -> None:
        self.uows.assert_ready()
        with self.uows(read_only=False) as uow:
            uow.onboarding.seed_golden(golden)
            uow.commit()
            return

    def import_reviewed_person(self, bundle: ReviewedPersonBundle) -> Person:
        self.uows.assert_ready()
        with self.uows(read_only=False) as uow:
            result = uow.onboarding.import_reviewed_person(bundle)
            uow.commit()
            return result
