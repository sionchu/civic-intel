"""Shared contract for Person Claims keyed to one exact current-roster ``MONA_CD``.

Several Open Assembly lanes publish such Claims: bill participation, committee roles and
memberships, and member-profile biography entries. Each builds one Claim plus one SUPPORT
ClaimEvidence from one immutable observation, requires an exact current-roster identity link and
is idempotent per logical key. Record lanes publish an asserted FACT; the biography lane publishes
a non-asserted, source-attributed CLAIM. Only those shared invariants live here; each lane keeps
its own source-specific checks.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from packages.domain.contracts import Claim, FeederObservation
from packages.domain.enums import EpistemicStatus


@dataclass(frozen=True)
class AssemblyMemberClaimLane:
    feeder: str
    semantic_scope: str
    predicate: str
    source_contract: str
    # Qualifiers that, with the Person, identify one current Claim of this lane.
    logical_key_qualifiers: tuple[str, ...]
    # Lane-specific provenance check beyond the shared contract.
    claim_matches_observation: Callable[[Claim, FeederObservation], bool]
    error: type[ValueError]
    label: str
    # FACT asserts the provider record; CLAIM attributes member-maintained text (never asserted).
    epistemic_status: EpistemicStatus = EpistemicStatus.FACT

    def logical_key(self, person_id: str, qualifiers: dict[str, str]) -> tuple[str, ...] | None:
        values = [qualifiers.get(name) for name in self.logical_key_qualifiers]
        if any(not isinstance(value, str) or not value for value in values):
            return None
        return (person_id, *[str(value) for value in values])
