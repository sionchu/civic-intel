"""Shared contract for Person Claims keyed to one exact current-roster ``MONA_CD``.

Two Open Assembly lanes publish such Claims: bill participation and committee roles. Both build
one FACT Claim plus one SUPPORT ClaimEvidence from one immutable observation, require an exact
current-roster identity link and are idempotent per logical key. Only those shared invariants live
here; each lane keeps its own source-specific checks.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from packages.domain.contracts import Claim, FeederObservation


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

    def logical_key(self, person_id: str, qualifiers: dict[str, str]) -> tuple[str, ...] | None:
        values = [qualifiers.get(name) for name in self.logical_key_qualifiers]
        if any(not isinstance(value, str) or not value for value in values):
            return None
        return (person_id, *[str(value) for value in values])
