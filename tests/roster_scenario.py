from dataclasses import dataclass

from packages.application.publication import publish_claim
from packages.domain.enums import MaterializationAction
from packages.verification.materialization import MaterializationResult
from workers.assembly_roster import AssemblyEnumerationResult


@dataclass(frozen=True)
class FixtureRosterScenario:
    enumeration: AssemblyEnumerationResult
    materializations: tuple[MaterializationResult, ...]

    def outcome_counts(self) -> dict[str, int]:
        automatic_actions = (
            MaterializationAction.AUTO_CREATE,
            MaterializationAction.AUTO_LINK,
            MaterializationAction.REVIEW_REQUIRED,
            MaterializationAction.HARD_CONFLICT,
        )
        counts = {action.value: 0 for action in automatic_actions}
        for result in self.materializations:
            counts[result.decision.action.value] += 1
        return counts


def enumerate_materialize_publish(enumerator, *, resume=False):
    enumeration = enumerator.enumerate(resume=resume)
    repository = enumerator.repository
    results = tuple(
        repository.identity.materialize_feeder_observation(item)
        for item in enumeration.observation_ids
    )
    for result in results:
        if result.claim_id is not None:
            publish_claim(repository.uows, result.claim_id)
    return FixtureRosterScenario(enumeration, results)
