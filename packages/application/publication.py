from uuid import UUID

from packages.application.ports import UnitOfWorkFactory
from packages.domain.contracts import Claim
from packages.domain.enums import PublicationStatus
from packages.verification.claims import validate_claim_publication
from packages.verification.materialization import MaterializationError


def publish_claim(factory: UnitOfWorkFactory, claim_id: UUID) -> Claim:
    """Explicit publication, validated again in the same transaction as the status write."""
    factory.assert_ready()
    with factory() as uow:
        claim = uow.public.claim(claim_id)
        if claim is None or claim.superseded_at is not None:
            raise MaterializationError("current claim does not exist")
        person = (
            uow.public.person(claim.person_id)
            if claim.person_id is not None
            else uow.public.organization(claim.organization_id)
            if claim.organization_id is not None
            else None
        )
        if person is None:
            raise MaterializationError("claim Person does not exist")
        evidence = uow.public.evidence_for(claim.id)
        sources = uow.public.sources(item.source_id for item in evidence)
        policies = uow.public.policies(source.policy_id for source in sources.values())
        published = claim.model_copy(update={"publication_status": PublicationStatus.PUBLISHED})
        gate = validate_claim_publication(published, person, evidence, sources, policies)
        if not gate.publishable:
            raise MaterializationError(f"claim failed publication gate: {gate.failures}")
        uow.onboarding.set_publication_status(claim.id, PublicationStatus.PUBLISHED)
        uow.commit()
        return published
