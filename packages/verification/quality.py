from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from pydantic import ValidationError

from packages.domain.contracts import Person
from packages.domain.enums import (
    EpistemicStatus,
    EvidenceStance,
    IdentityStatus,
    PublicationStatus,
    SourceCollectionMode,
)
from packages.verification.claims import (
    validate_claim_publication,
    validate_pattern,
    validate_relationship,
)
from packages.verification.golden import load_golden_set
from packages.verification.identity import IdentityCandidate, resolve_identity
from packages.verification.origin import source_counts
from packages.verification.policy import PolicyAction, PolicyDenied, require_policy

EXPECTED_ROSTER = {
    "이형일",
    "홍지선",
    "이소영",
    "강신철",
    "김승원",
    "용혜인",
    "이해민",
    "이원주",
    "하정우",
    "김경수",
}


@dataclass(frozen=True)
class QualityReport:
    golden_set_id: str
    checks: dict[str, bool]
    metrics: dict[str, int]
    failures: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return all(self.checks.values()) and not self.failures


def _record(checks: dict[str, bool], failures: list[str], name: str, passed: bool) -> None:
    checks[name] = passed
    if not passed:
        failures.append(name)


def evaluate_golden(root: Path | None = None) -> QualityReport:
    golden = load_golden_set(root)
    checks: dict[str, bool] = {}
    failures: list[str] = []
    people = {item.person.id: item.person for item in golden.people}
    policies = {item.id: item for item in golden.policies}
    sources = {item.id: item for item in golden.sources}
    evidence_by_claim = {
        claim.id: [item for item in golden.evidence if item.claim_id == claim.id]
        for claim in golden.claims
    }

    _record(
        checks,
        failures,
        "real_ten_person_roster",
        {item.person.canonical_name for item in golden.people} == EXPECTED_ROSTER,
    )
    all_names = [
        name.casefold()
        for item in golden.people
        for name in (item.person.canonical_name, *item.aliases)
    ]
    cross_matches_clean = len(all_names) == len(set(all_names))
    candidates = {
        item.person.id: IdentityCandidate(
            item.person.canonical_name,
            item.aliases,
            office=(
                item.identity_anchors.get("current_office")
                or item.identity_anchors.get("nominated_office")
                or item.identity_anchors.get("designated_office")
                or item.identity_anchors.get("appointed_office")
            ),
            organization=item.identity_anchors.get("organization"),
            career_anchors=tuple(item.identity_anchors.values()),
        )
        for item in golden.people
    }
    self_matches_resolve = all(
        resolve_identity(candidate, candidate).status == IdentityStatus.RESOLVED
        for candidate in candidates.values()
    )
    for left_index, left in enumerate(golden.people):
        for right in golden.people[left_index + 1 :]:
            decision = resolve_identity(candidates[left.person.id], candidates[right.person.id])
            cross_matches_clean = (
                cross_matches_clean and decision.status == IdentityStatus.UNRESOLVED
            )
    _record(
        checks,
        failures,
        "no_identity_contamination",
        cross_matches_clean and self_matches_resolve,
    )

    fact_results = [
        validate_claim_publication(
            claim,
            people[claim.person_id],
            evidence_by_claim[claim.id],
            sources,
            policies,
        )
        for claim in golden.claims
        if claim.epistemic_status == EpistemicStatus.FACT
    ]
    _record(
        checks,
        failures,
        "published_facts_traceable",
        bool(fact_results) and all(item.publishable for item in fact_results),
    )

    official_claims = [
        claim for claim in golden.claims if claim.qualifiers.get("speaker") == "대통령비서실"
    ]
    _record(
        checks,
        failures,
        "official_assertion_remains_claim",
        bool(official_claims)
        and all(item.epistemic_status == EpistemicStatus.CLAIM for item in official_claims),
    )

    reprint_sources = [
        item
        for item in golden.sources
        if str(item.origin_cluster_id) == "90000000-0000-0000-0000-000000000002"
    ]
    counts = source_counts(reprint_sources)
    _record(
        checks,
        failures,
        "source_reprints_collapsed",
        counts == {"raw_url_count": 2, "independent_origin_count": 1},
    )

    conflicting = [
        claim_id
        for claim_id, items in evidence_by_claim.items()
        if {item.stance for item in items} >= {EvidenceStance.SUPPORT, EvidenceStance.REFUTE}
    ]
    _record(checks, failures, "support_and_refute_coexist", bool(conflicting))

    unknowns = [
        claim for claim in golden.claims if claim.epistemic_status == EpistemicStatus.UNKNOWN
    ]
    unknown_valid = bool(unknowns) and all(
        claim.publication_status == PublicationStatus.PUBLISHED
        and not claim.asserted_as_true
        and bool(claim.resolution_note)
        and validate_claim_publication(
            claim, people[claim.person_id], evidence_by_claim[claim.id], sources, policies
        ).publishable
        for claim in unknowns
    )
    _record(checks, failures, "unknown_renderable_not_fact", unknown_valid)

    episodes_by_person: dict = {}
    for episode in golden.episodes:
        episodes_by_person.setdefault(episode.person_id, []).append(
            {str(item) for item in episode.independent_origin_ids}
        )
    one_episode = [items for items in episodes_by_person.values() if len(items) == 1]
    two_episodes = [items for items in episodes_by_person.values() if len(items) >= 2]
    _record(
        checks,
        failures,
        "one_episode_not_pattern",
        bool(one_episode) and all(not validate_pattern(items).publishable for items in one_episode),
    )
    _record(
        checks,
        failures,
        "independent_episodes_pattern_candidate",
        bool(two_episodes) and any(validate_pattern(items).publishable for items in two_episodes),
    )
    _record(
        checks,
        failures,
        "strong_relationships_typed",
        all(validate_relationship(item).publishable for item in golden.relationships),
    )

    restricted = [
        policy
        for policy in golden.policies
        if policy.collection_mode
        in {SourceCollectionMode.BLOCKED, SourceCollectionMode.DISCOVERY_ONLY}
    ]
    denied = 0
    for policy in restricted:
        try:
            require_policy(policy, PolicyAction.FETCH)
        except PolicyDenied:
            denied += 1
    _record(checks, failures, "restricted_policies_cannot_fetch", denied == len(restricted))

    forbidden_keys = {"private_family", "precise_residence", "precise_residential_address"}
    raw_text = json.dumps(golden.raw, ensure_ascii=False).casefold()
    forbidden_absent = not any(f'"{key}"' in raw_text for key in forbidden_keys)
    try:
        Person.model_validate({"canonical_name": "금지 필드", "precise_residence": "비공개"})
    except ValidationError:
        model_rejects = True
    else:
        model_rejects = False
    _record(
        checks,
        failures,
        "prohibited_fields_rejected",
        forbidden_absent and model_rejects,
    )

    manual_only = all(
        snapshot.metadata.get("capture") == "manual_review" and snapshot.fulltext is None
        for snapshot in golden.snapshots
    )
    no_search_sources = all(
        source.publisher and policies[source.policy_id].source_class != "search_result"
        for source in golden.sources
    )
    _record(
        checks,
        failures,
        "no_raw_search_to_profile_path",
        manual_only and no_search_sources,
    )

    metrics = {
        "people": len(golden.people),
        "published_facts": len(fact_results),
        "published_unknowns": len(unknowns),
        "claims": len(golden.claims),
        "evidence_items": len(golden.evidence),
        "conflicting_claims": len(conflicting),
        "raw_reprint_urls": counts["raw_url_count"],
        "independent_reprint_origins": counts["independent_origin_count"],
        "decision_episodes": len(golden.episodes),
        "relationships": len(golden.relationships),
    }
    return QualityReport(golden.id, checks, metrics, tuple(failures))


def main() -> int:
    report = evaluate_golden()
    print(json.dumps(asdict(report) | {"passed": report.passed}, indent=2, ensure_ascii=False))
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
