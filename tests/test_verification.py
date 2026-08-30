from datetime import UTC, date, datetime
from uuid import uuid4

import pytest

from packages.domain.contracts import (
    Claim,
    ClaimEvidence,
    Person,
    Relationship,
    Source,
    SourcePolicy,
)
from packages.domain.enums import (
    EpistemicStatus,
    EvidenceStance,
    IdentityStatus,
    RelationshipStrength,
    SourceCollectionMode,
)
from packages.verification.claims import (
    is_atomic,
    validate_claim_publication,
    validate_pattern,
    validate_relationship,
)
from packages.verification.identity import IdentityCandidate, resolve_identity
from packages.verification.origin import compare_sources, source_counts
from packages.verification.policy import PolicyAction, PolicyDenied, require_policy


def policy(**changes):
    values = {
        "domain": "example.gov",
        "source_class": "official",
        "collection_mode": SourceCollectionMode.HTTP,
        "can_fetch": True,
        "can_store_metadata": True,
        "can_store_fulltext": True,
        "can_send_to_ai": False,
        "can_show_excerpt": True,
        "can_commercialize": False,
    }
    return SourcePolicy(**(values | changes))


def test_blocked_and_discovery_only_never_fetch() -> None:
    for mode in (SourceCollectionMode.BLOCKED, SourceCollectionMode.DISCOVERY_ONLY):
        with pytest.raises(PolicyDenied):
            require_policy(policy(collection_mode=mode, can_fetch=True), PolicyAction.FETCH)


def test_entity_resolution_resolves_anchors_but_reviews_hard_conflict() -> None:
    observed = IdentityCandidate("Kim Min", birth_date=date(1970, 1, 1), office="Minister")
    assert resolve_identity(observed, observed).status == IdentityStatus.RESOLVED
    false_match = IdentityCandidate("Kim Min", birth_date=date(1980, 1, 1), office="Minister")
    assert resolve_identity(observed, false_match).status == IdentityStatus.REVIEW


def test_origin_reprint_collapses_and_counts_are_distinct() -> None:
    p = policy()
    when = datetime(2026, 1, 1, tzinfo=UTC)
    a = Source(
        url="https://a.test/report?utm_source=x",
        title="Cabinet report released",
        publisher="A",
        published_at=when,
        policy_id=p.id,
    )
    b = Source(
        url="https://b.test/reprint",
        title="Cabinet report released",
        publisher="B",
        published_at=when,
        policy_id=p.id,
    )
    assert compare_sources(
        a, b, "same body words here now", "same body words here now", True
    ).same_origin
    cluster = uuid4()
    a = a.model_copy(update={"origin_cluster_id": cluster})
    b = b.model_copy(update={"origin_cluster_id": cluster})
    assert source_counts([a, b]) == {"raw_url_count": 2, "independent_origin_count": 1}


def test_claim_atomicity_examples() -> None:
    assert is_atomic("The official took office on 1 January 2026.")
    assert not is_atomic("The official took office and changed the policy.")


def test_fact_traceability_and_unknown_gate() -> None:
    p = policy()
    person = Person(canonical_name="Kim Min", identity_status=IdentityStatus.RESOLVED)
    source = Source(
        url="https://example.gov/bio", title="Biography", publisher="Government", policy_id=p.id
    )
    claim = Claim(
        person_id=person.id,
        proposition="Kim Min took office in 2026.",
        epistemic_status=EpistemicStatus.FACT,
        published=True,
    )
    assert not validate_claim_publication(
        claim, person, [], {source.id: source}, {p.id: p}
    ).publishable
    evidence = ClaimEvidence(
        claim_id=claim.id,
        source_id=source.id,
        stance=EvidenceStance.SUPPORT,
        excerpt="Took office in 2026",
    )
    assert validate_claim_publication(
        claim, person, [evidence], {source.id: source}, {p.id: p}
    ).publishable
    unknown = claim.model_copy(update={"epistemic_status": EpistemicStatus.UNKNOWN})
    assert not validate_claim_publication(
        unknown, person, evidence=[evidence], sources={source.id: source}, policies={p.id: p}
    ).publishable


def test_analysis_gates() -> None:
    relationship = Relationship(
        person_id=uuid4(),
        related_person_id=uuid4(),
        relationship_type="co-mention",
        strength=RelationshipStrength.STRONG,
    )
    assert not validate_relationship(relationship).publishable
    assert not validate_pattern([{"origin-a"}]).publishable
    assert validate_pattern([{"origin-a"}, {"origin-b"}]).publishable
