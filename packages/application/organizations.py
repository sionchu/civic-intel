from __future__ import annotations

from collections.abc import Sequence

from packages.application.errors import ConcurrentWrite
from packages.application.ports import UnitOfWorkFactory
from packages.application.results import (
    OrganizationBatchResult,
    OrganizationClaimBatchResult,
)
from packages.domain.contracts import (
    Claim,
    ClaimEvidence,
    Organization,
)
from packages.verification.import_semantics import OrganizationClaimImportError


class OrganizationsService:
    def __init__(self, uows: UnitOfWorkFactory):
        self.uows = uows

    def import_organization_claim(
        self, organization: Organization, claim: Claim, evidence: Sequence[ClaimEvidence]
    ) -> Claim:
        self.uows.assert_ready()
        with self.uows(read_only=False) as uow:
            result = uow.organizations.import_organization_claim(organization, claim, evidence)
            uow.commit()
            return result

    def import_organization_claim_pair(
        self,
        organization: Organization,
        claim_pairs: Sequence[tuple[Claim, Sequence[ClaimEvidence]]],
    ) -> tuple[Claim, Claim]:
        self.uows.assert_ready()
        for attempt in range(2):
            try:
                with self.uows() as uow:
                    result = uow.organizations.import_organization_claim_pair(
                        organization, claim_pairs
                    )
                    uow.commit()
                    return result
            except ConcurrentWrite:
                if attempt:
                    raise OrganizationClaimImportError(
                        "organization claim import collided with another transaction"
                    ) from None
        raise AssertionError("unreachable retry state")

    def import_organization_claim_batch(
        self,
        organizations: Sequence[Organization],
        items: Sequence[tuple[Organization, Claim, Sequence[ClaimEvidence]]],
    ) -> OrganizationClaimBatchResult:
        self.uows.assert_ready()
        with self.uows(read_only=False) as uow:
            result = uow.organizations.import_organization_claim_batch(organizations, items)
            uow.commit()
            return result

    def import_organization_batch(
        self, organizations: Sequence[Organization]
    ) -> OrganizationBatchResult:
        self.uows.assert_ready()
        with self.uows(read_only=False) as uow:
            result = uow.organizations.import_organization_batch(organizations)
            uow.commit()
            return result
