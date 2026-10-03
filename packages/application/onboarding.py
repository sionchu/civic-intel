from __future__ import annotations

from uuid import UUID

from packages.application.ports import UnitOfWorkFactory
from packages.domain.contracts import (
    Person,
)
from packages.domain.enums import IdentityReviewStatus
from packages.rendering.gukgam_witness_claim import (
    GukgamWitnessClaimError,
    GukgamWitnessClaimPreparation,
    build_gukgam_witness_claim,
)
from packages.rendering.gukgam_witness_review import load_current_gukgam_witness_documents
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

    def prepare_gukgam_witness_claim(
        self,
        *,
        person_id: UUID,
        observation_id: UUID,
        expected_observation_hash: str,
        expected_packet_hash: str,
    ) -> GukgamWitnessClaimPreparation:
        """Prepare one private DRAFT pair in a coherent no-write read snapshot."""
        self.uows.assert_ready()
        with self.uows(read_only=True) as uow:
            documents = load_current_gukgam_witness_documents(uow.acquisition)
            selected = [
                (document, index)
                for document in documents
                for index, context in enumerate(document.contexts)
                if context[0].id == observation_id
            ]
            if len(selected) != 1:
                raise GukgamWitnessClaimError(
                    "witness Claim requires one current selected observation"
                )
            document, index = selected[0]
            if (
                document.packet.content_hash != expected_packet_hash
                or document.contexts[index][0].content_hash != expected_observation_hash
            ):
                raise GukgamWitnessClaimError("witness Claim input hashes changed")
            person = uow.public.person(person_id)
            if person is None:
                raise GukgamWitnessClaimError("witness Claim requires an existing Person")
            if uow.identity.active_person_ids_by_observation([observation_id]).get(
                observation_id
            ) != frozenset({person_id}):
                raise GukgamWitnessClaimError(
                    "witness Claim requires a unique active Person binding"
                )
            links = [
                link
                for link in uow.identity.person_observation_links(person_id)
                if link.observation_id == observation_id and link.superseded_at is None
            ]
            if len(links) != 1:
                raise GukgamWitnessClaimError(
                    "witness Claim requires one exact active identity link"
                )
            reviews = [
                review
                for review in uow.review.identity_review_items(IdentityReviewStatus.RESOLVED)
                if review.id == links[0].review_item_id
            ]
            if len(reviews) != 1:
                raise GukgamWitnessClaimError(
                    "witness Claim requires an existing resolved identity review"
                )
            return build_gukgam_witness_claim(
                document, index, person=person, link=links[0], review=reviews[0]
            )
