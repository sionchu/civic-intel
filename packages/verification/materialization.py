from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from packages.domain.contracts import FeederObservation, MaterializationDecision, Person
from packages.domain.enums import MaterializationAction, MaterializationDecisionClass


@dataclass(frozen=True)
class MaterializationResult:
    decision: MaterializationDecision
    person_id: UUID | None = None
    claim_id: UUID | None = None
    review_item_id: UUID | None = None
    created: bool = False


class MaterializationError(RuntimeError):
    pass


def _observation_birth_date(observation: FeederObservation) -> date | None:
    value = observation.normalized.get("birth_date")
    if value is None:
        return None
    if not isinstance(value, str):
        raise TypeError("observation birth_date must be an ISO date string or null")
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise ValueError("observation birth_date is invalid") from None


def decide_materialization(
    observation: FeederObservation,
    *,
    linked_people: tuple[Person, ...] = (),
    same_name_people: tuple[Person, ...] = (),
) -> MaterializationDecision:
    if (
        observation.feeder != "national_assembly_members"
        or observation.semantic_scope != "legislative_member_roster"
    ):
        return MaterializationDecision(
            action=MaterializationAction.REVIEW_REQUIRED,
            decision_class=MaterializationDecisionClass.UNSUPPORTED_FEEDER,
            reasons=("feeder_has_no_reviewed_automatic_materialization_rule",),
        )

    unique_linked = {item.id: item for item in linked_people}
    if len(unique_linked) > 1:
        return MaterializationDecision(
            action=MaterializationAction.HARD_CONFLICT,
            decision_class=MaterializationDecisionClass.PROVIDER_IDENTITY_CONFLICT,
            reasons=("provider_identity_is_linked_to_multiple_people",),
        )

    observed_birth_date = _observation_birth_date(observation)
    if unique_linked:
        linked = next(iter(unique_linked.values()))
        if (
            observed_birth_date is not None
            and linked.birth_date is not None
            and observed_birth_date != linked.birth_date
        ):
            return MaterializationDecision(
                action=MaterializationAction.HARD_CONFLICT,
                decision_class=MaterializationDecisionClass.EXACT_BIRTH_DATE_CONFLICT,
                candidate_person_id=linked.id,
                reasons=("provider_link_birth_date_conflict",),
            )
        return MaterializationDecision(
            action=MaterializationAction.AUTO_LINK,
            decision_class=MaterializationDecisionClass.EXACT_PROVIDER_IDENTITY,
            candidate_person_id=linked.id,
            reasons=("exact_accepted_provider_identity",),
        )

    if same_name_people:
        conflicts = [
            item
            for item in same_name_people
            if observed_birth_date is not None
            and item.birth_date is not None
            and observed_birth_date != item.birth_date
        ]
        if conflicts:
            candidate_id = conflicts[0].id if len(same_name_people) == 1 else None
            return MaterializationDecision(
                action=MaterializationAction.HARD_CONFLICT,
                decision_class=MaterializationDecisionClass.EXACT_BIRTH_DATE_CONFLICT,
                candidate_person_id=candidate_id,
                reasons=("same_name_exact_birth_date_conflict",),
            )
        candidate_id = same_name_people[0].id if len(same_name_people) == 1 else None
        return MaterializationDecision(
            action=MaterializationAction.REVIEW_REQUIRED,
            decision_class=MaterializationDecisionClass.SAME_NAME_AMBIGUITY,
            candidate_person_id=candidate_id,
            reasons=("same_name_without_exact_provider_identity",),
        )

    return MaterializationDecision(
        action=MaterializationAction.AUTO_CREATE,
        decision_class=MaterializationDecisionClass.AUTHORITATIVE_NEW_IDENTITY,
        reasons=("authoritative_roster_unique_provider_identity_and_name",),
    )
