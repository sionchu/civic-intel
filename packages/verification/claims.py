from __future__ import annotations

import re
from dataclasses import dataclass

from packages.domain.contracts import (
    Claim,
    ClaimEvidence,
    Hypothesis,
    Person,
    Relationship,
    Source,
    SourcePolicy,
)
from packages.domain.enums import (
    EpistemicStatus,
    EvidenceStance,
    IdentityStatus,
    PublicationStatus,
    RelationshipEvidenceType,
    RelationshipStrength,
)
from packages.verification.policy import PolicyAction, PolicyDenied, require_policy


@dataclass(frozen=True)
class GateResult:
    publishable: bool
    failures: tuple[str, ...] = ()


def is_atomic(proposition: str) -> bool:
    text = proposition.strip()
    if len(re.findall(r"[.!?](?:\s|$)", text)) > 1:
        return False
    return not bool(re.search(r"\b(and|그리고|하며|했으며)\b", text, re.IGNORECASE))


def validate_relationship(relationship: Relationship) -> GateResult:
    if relationship.strength == RelationshipStrength.STRONG:
        typed = {
            item.evidence_type
            for item in relationship.evidence
            if item.evidence_type != RelationshipEvidenceType.CO_MENTION
        }
        if not typed:
            return GateResult(False, ("strong_relationship_requires_typed_evidence",))
    return GateResult(True)


def validate_pattern(episode_origin_ids: list[set[str]]) -> GateResult:
    unique = {origin for episode in episode_origin_ids for origin in episode}
    if len(episode_origin_ids) < 2 or len(unique) < 2:
        return GateResult(False, ("pattern_requires_two_independent_episodes",))
    return GateResult(True)


def validate_hypothesis(hypothesis: Hypothesis) -> GateResult:
    if hypothesis.publication_status == PublicationStatus.PUBLISHED and (
        not hypothesis.ordinary_explanation.strip() or not hypothesis.falsifier.strip()
    ):
        return GateResult(False, ("hypothesis_requires_h0_and_falsifier",))
    return GateResult(True)


def validate_claim_publication(
    claim: Claim, person: Person, evidence: list[ClaimEvidence], sources: dict, policies: dict
) -> GateResult:
    failures: list[str] = []
    if claim.publication_status != PublicationStatus.PUBLISHED:
        failures.append("claim_not_marked_for_publication")
    if person.identity_status != IdentityStatus.RESOLVED:
        failures.append("identity_not_resolved")
    if not is_atomic(claim.proposition):
        failures.append("claim_not_atomic")
    if claim.epistemic_status == EpistemicStatus.UNKNOWN:
        if claim.asserted_as_true:
            failures.append("unknown_cannot_be_asserted_as_true")
        if not claim.resolution_note:
            failures.append("unknown_requires_resolution_note")
    claim_evidence = [item for item in evidence if item.claim_id == claim.id]
    supports = [item for item in claim_evidence if item.stance == EvidenceStance.SUPPORT]
    if claim.epistemic_status == EpistemicStatus.FACT and not supports:
        failures.append("fact_requires_support")
    if claim.epistemic_status == EpistemicStatus.FACT and not claim.asserted_as_true:
        failures.append("fact_requires_explicit_assertion")
    for item in claim_evidence:
        source: Source | None = sources.get(item.source_id)
        if source is None:
            failures.append("evidence_source_missing")
            continue
        policy: SourcePolicy | None = policies.get(source.policy_id)
        try:
            require_policy(policy, PolicyAction.STORE_METADATA)
            if item.excerpt:
                require_policy(policy, PolicyAction.SHOW_EXCERPT)
        except PolicyDenied:
            failures.append("source_policy_prohibits_publication")
    return GateResult(not failures, tuple(dict.fromkeys(failures)))
