from __future__ import annotations

from packages.application.acquisition import AcquisitionService
from packages.application.administration import AdministrationService
from packages.application.identity import IdentityService
from packages.application.onboarding import OnboardingService
from packages.application.organizations import OrganizationsService
from packages.application.ports import UnitOfWorkFactory
from packages.application.profiles import ProfilesService
from packages.application.public import PublicService
from packages.application.review import ReviewService


class Application:
    """Named transaction-owning use cases, composed without a repository facade."""

    def __init__(self, uows: UnitOfWorkFactory):
        self.uows = uows
        self.acquisition = AcquisitionService(uows)
        self.administration = AdministrationService(uows)
        self.identity = IdentityService(uows)
        self.onboarding = OnboardingService(uows)
        self.organizations = OrganizationsService(uows)
        self.profiles = ProfilesService(uows)
        self.public = PublicService(uows)
        self.review = ReviewService(uows)
