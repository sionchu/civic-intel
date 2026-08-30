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


class GoldenSupplementError(ValueError):
    pass


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


MERGE_COLLECTIONS = (
    "policies",
    "sources",
    "snapshots",
    "claims",
    "evidence",
    "origin_clusters",
    "relationships",
    "episodes",
)


def fixture_path(root: Path | None = None) -> Path:
    return (root or Path("tests/golden/fixtures")) / "golden_set_001.json"


def supplement_path(root: Path | None = None) -> Path:
    return (root or Path("tests/golden/fixtures")) / "golden_set_001_profile_evidence.json"


def _assert_unique_ids(base: dict[str, Any], supplement: dict[str, Any]) -> None:
    seen: dict[str, str] = {}
    for origin, payload, collections in (
        ("base", base, ("people", *MERGE_COLLECTIONS)),
        ("supplement", supplement, MERGE_COLLECTIONS),
    ):
        for collection in collections:
            for item in payload.get(collection, []):
                record_id = str(item.get("id", "")).strip()
                if not record_id:
                    raise GoldenSupplementError(f"{origin} {collection} record requires id")
                previous = seen.get(record_id)
                if previous is not None:
                    raise GoldenSupplementError(
                        f"duplicate Golden record id {record_id}: {previous} and {origin}.{collection}"
                    )
                seen[record_id] = f"{origin}.{collection}"


def _merge_raw(base: dict[str, Any], supplement: dict[str, Any] | None) -> dict[str, Any]:
    if supplement is None:
        return base
    if supplement.get("base_id") != base.get("id"):
        raise GoldenSupplementError("profile evidence supplement base_id does not match Golden set")
    if "people" in supplement:
        raise GoldenSupplementError("profile evidence supplement cannot declare Person records")

    _assert_unique_ids(base, supplement)
    merged = dict(base)
    for collection in MERGE_COLLECTIONS:
        merged[collection] = [*base.get(collection, []), *supplement.get(collection, [])]
    merged["profile_evidence_supplement"] = {
        "id": supplement.get("id"),
        "review_note": supplement.get("review_note"),
    }
    return merged


def _load_raw(root: Path | None = None) -> dict[str, Any]:
    base = json.loads(fixture_path(root).read_text(encoding="utf-8"))
    extra_path = supplement_path(root)
    supplement = json.loads(extra_path.read_text(encoding="utf-8")) if extra_path.exists() else None
    return _merge_raw(base, supplement)


def _validate_references(golden: GoldenSet) -> None:
    people = {item.person.id for item in golden.people}
    policies = {item.id for item in golden.policies}
    sources = {item.id for item in golden.sources}
    snapshots = {item.id for item in golden.snapshots}
    claims = {item.id for item in golden.claims}
    evidence = {item.id for item in golden.evidence}
    origin_clusters = {item.id for item in golden.origin_clusters}

    for source in golden.sources:
        if source.policy_id not in policies:
            raise GoldenSupplementError(f"source {source.id} references missing SourcePolicy")
        if source.origin_cluster_id and source.origin_cluster_id not in origin_clusters:
            raise GoldenSupplementError(f"source {source.id} references missing origin cluster")

    for snapshot in golden.snapshots:
        if snapshot.source_id not in sources:
            raise GoldenSupplementError(f"snapshot {snapshot.id} references missing source")

    for claim in golden.claims:
        if claim.person_id not in people:
            raise GoldenSupplementError(f"claim {claim.id} references non-Golden person")

    for item in golden.evidence:
        if item.claim_id not in claims:
            raise GoldenSupplementError(f"evidence {item.id} references missing claim")
        if item.source_id not in sources:
            raise GoldenSupplementError(f"evidence {item.id} references missing source")
        if item.snapshot_id and item.snapshot_id not in snapshots:
            raise GoldenSupplementError(f"evidence {item.id} references missing snapshot")

    for cluster in golden.origin_clusters:
        if cluster.canonical_source_id not in sources:
            raise GoldenSupplementError(f"origin cluster {cluster.id} has missing canonical source")
        if any(source_id not in sources for source_id in cluster.member_source_ids):
            raise GoldenSupplementError(f"origin cluster {cluster.id} has missing member source")

    for relationship in golden.relationships:
        if relationship.person_id not in people:
            raise GoldenSupplementError(f"relationship {relationship.id} references non-Golden person")
        if relationship.related_person_id and relationship.related_person_id not in people:
            raise GoldenSupplementError(
                f"relationship {relationship.id} references missing related person"
            )
        if any(item.claim_evidence_id not in evidence for item in relationship.evidence):
            raise GoldenSupplementError(f"relationship {relationship.id} has missing evidence")

    for episode in golden.episodes:
        if episode.person_id not in people:
            raise GoldenSupplementError(f"decision episode {episode.id} references non-Golden person")
        if any(source_id not in sources for source_id in episode.source_ids):
            raise GoldenSupplementError(f"decision episode {episode.id} has missing source")
        if any(origin_id not in origin_clusters for origin_id in episode.independent_origin_ids):
            raise GoldenSupplementError(
                f"decision episode {episode.id} has missing independent origin"
            )


def load_golden_set(root: Path | None = None) -> GoldenSet:
    raw = _load_raw(root)
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
    golden = GoldenSet(
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
    _validate_references(golden)
    return golden
