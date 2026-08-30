from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from packages.domain.contracts import (
    Claim,
    ClaimEvidence,
    DecisionEpisode,
    Person,
    Relationship,
    Source,
    SourceOriginCluster,
    SourcePolicy,
    SourceSnapshot,
)


@dataclass(frozen=True)
class GoldenPerson:
    person: Person
    aliases: tuple[str, ...]
    identity_anchors: dict[str, str]


@dataclass(frozen=True)
class GoldenSet:
    id: str
    as_of: str
    people: tuple[GoldenPerson, ...]
    policies: tuple[SourcePolicy, ...]
    sources: tuple[Source, ...]
    snapshots: tuple[SourceSnapshot, ...]
    claims: tuple[Claim, ...]
    evidence: tuple[ClaimEvidence, ...]
    origin_clusters: tuple[SourceOriginCluster, ...]
    relationships: tuple[Relationship, ...]
    episodes: tuple[DecisionEpisode, ...]
    raw: dict[str, Any]


def fixture_path(root: Path | None = None) -> Path:
    return (root or Path("tests/golden/fixtures")) / "golden_set_001.json"


def load_golden_set(root: Path | None = None) -> GoldenSet:
    raw = json.loads(fixture_path(root).read_text(encoding="utf-8"))
    people: list[GoldenPerson] = []
    for item in raw["people"]:
        contract_data = {
            key: value for key, value in item.items() if key not in {"aliases", "identity_anchors"}
        }
        people.append(
            GoldenPerson(
                Person.model_validate(contract_data),
                tuple(item["aliases"]),
                dict(item["identity_anchors"]),
            )
        )
    return GoldenSet(
        id=raw["id"],
        as_of=raw["as_of"],
        people=tuple(people),
        policies=tuple(SourcePolicy.model_validate(item) for item in raw["policies"]),
        sources=tuple(Source.model_validate(item) for item in raw["sources"]),
        snapshots=tuple(SourceSnapshot.model_validate(item) for item in raw["snapshots"]),
        claims=tuple(Claim.model_validate(item) for item in raw["claims"]),
        evidence=tuple(ClaimEvidence.model_validate(item) for item in raw["evidence"]),
        origin_clusters=tuple(
            SourceOriginCluster.model_validate(item) for item in raw["origin_clusters"]
        ),
        relationships=tuple(Relationship.model_validate(item) for item in raw["relationships"]),
        episodes=tuple(DecisionEpisode.model_validate(item) for item in raw["episodes"]),
        raw=raw,
    )
