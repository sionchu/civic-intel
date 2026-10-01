from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from packages.application.ports import UnitOfWorkFactory
from packages.domain.contracts import (
    Claim,
    ClaimEvidence,
    Person,
    PersonObservationLink,
)
from packages.domain.enums import (
    EpistemicStatus,
    EvidenceStance,
    IdentityStatus,
    MaterializationAction,
    PublicationStatus,
)


class IdentityService:
    def __init__(self, uows: UnitOfWorkFactory):
        self.uows = uows

    def person_observation_links(
        self, person_id: UUID | None = None
    ) -> list[PersonObservationLink]:
        with self.uows(read_only=True) as uow:
            result = uow.identity.person_observation_links(person_id)
            return result

    def active_person_ids_by_observation(
        self, observation_ids: Sequence[UUID]
    ) -> dict[UUID, frozenset[UUID]]:
        with self.uows(read_only=True) as uow:
            result = uow.identity.active_person_ids_by_observation(observation_ids)
            return result

    def materialize_feeder_observation(self, observation_id: UUID) -> MaterializationResult:
        return materialize_identity(self.uows, observation_id)


from datetime import date

from packages.verification.assembly_base_profile import ASSEMBLY_BASE_PROFILE_FEEDER
from packages.verification.assembly_provenance import validate_assembly_member_provenance
from packages.verification.claims import validate_claim_publication
from packages.verification.materialization import (
    MaterializationError,
    MaterializationResult,
    decide_materialization,
)
from packages.verification.policy import PolicyAction, PolicyDenied, require_policy


def materialize_identity(factory: UnitOfWorkFactory, observation_id: UUID) -> MaterializationResult:
    """Resolve the exact provider identity and prepare gated DRAFT evidence, without publishing."""
    factory.assert_ready()
    with factory() as uow:
        observation = uow.acquisition.feeder_observation(observation_id)
        if observation is None:
            raise MaterializationError("feeder observation does not exist")
        snapshot = uow.public.source_snapshot(observation.snapshot_id)
        if snapshot is None:
            raise MaterializationError("observation snapshot does not exist")
        source = uow.public.source(snapshot.source_id)
        if source is None:
            raise MaterializationError("observation source does not exist")
        policy = uow.public.policies([source.policy_id]).get(source.policy_id)
        if policy is None:
            raise MaterializationError("observation SourcePolicy does not exist")
        try:
            require_policy(policy, PolicyAction.STORE_METADATA)
        except PolicyDenied:
            raise MaterializationError(
                "observation SourcePolicy does not permit metadata storage"
            ) from None
        if observation.feeder == ASSEMBLY_BASE_PROFILE_FEEDER:
            validate_assembly_member_provenance(observation, snapshot, source, policy)
        canonical_name = observation.normalized.get("canonical_name")
        if not isinstance(canonical_name, str) or not canonical_name.strip():
            raise MaterializationError("feeder observation lacks canonical_name")
        linked_people, same_name_people = uow.identity.matching_people(observation)
        decision = decide_materialization(
            observation, linked_people=linked_people, same_name_people=same_name_people
        )
        if decision.action in {
            MaterializationAction.REVIEW_REQUIRED,
            MaterializationAction.HARD_CONFLICT,
        }:
            review = uow.review.ensure_materialization_review(observation, decision)
            uow.commit()
            return MaterializationResult(decision=decision, review_item_id=review.id, created=False)
        if decision.action == MaterializationAction.AUTO_LINK:
            if decision.candidate_person_id is None:
                raise MaterializationError("AUTO_LINK requires a candidate Person")
            uow.identity.link_observation(
                PersonObservationLink(
                    person_id=decision.candidate_person_id,
                    observation_id=observation.id,
                    action=decision.action,
                    decision_class=decision.decision_class,
                )
            )
            uow.commit()
            return MaterializationResult(
                decision=decision, person_id=decision.candidate_person_id, created=False
            )
        if decision.action != MaterializationAction.AUTO_CREATE:
            raise MaterializationError("unsupported materialization action")
        birth_value = observation.normalized.get("birth_date")
        birth_date = None
        if birth_value is not None:
            if not isinstance(birth_value, str):
                raise MaterializationError("observation birth_date is invalid")
            try:
                birth_date = date.fromisoformat(birth_value)
            except ValueError:
                raise MaterializationError("observation birth_date is invalid") from None
        person = Person(
            canonical_name=canonical_name,
            birth_date=birth_date,
            identity_status=IdentityStatus.RESOLVED,
        )
        draft = Claim(
            person_id=person.id,
            proposition=f"{canonical_name}는 국회의원 명부에 등재되어 있다.",
            subject=canonical_name,
            predicate="HELD_ROLE",
            object_text="국회의원",
            qualifiers={
                "provider_record_key": observation.provider_record_key,
                "source_scope": observation.scope_key,
            },
            epistemic_status=EpistemicStatus.FACT,
            publication_status=PublicationStatus.DRAFT,
            asserted_as_true=True,
        )
        evidence = ClaimEvidence(
            claim_id=draft.id,
            source_id=source.id,
            snapshot_id=observation.snapshot_id,
            feeder_observation_id=observation.id,
            stance=EvidenceStance.SUPPORT,
        )
        candidate = draft.model_copy(update={"publication_status": PublicationStatus.PUBLISHED})
        gate = validate_claim_publication(
            candidate, person, [evidence], {source.id: source}, {policy.id: policy}
        )
        if not gate.publishable:
            raise MaterializationError(f"batch claim failed publication gate: {gate.failures}")
        uow.identity.add_person(person)
        uow.onboarding.add_claim(draft, evidence)
        uow.identity.link_observation(
            PersonObservationLink(
                person_id=person.id,
                observation_id=observation.id,
                action=decision.action,
                decision_class=decision.decision_class,
            )
        )
        uow.commit()
        return MaterializationResult(
            decision=decision, person_id=person.id, claim_id=draft.id, created=True
        )
