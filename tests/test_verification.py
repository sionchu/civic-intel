from datetime import UTC, date, datetime
from uuid import uuid4

import pytest

from packages.domain.contracts import (
    Claim,
    ClaimEvidence,
    Person,
    Relationship,
    RelationshipEvidenceRef,
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
    assert (
        resolve_identity(
            observed, IdentityCandidate("Kim Min", birth_date=date(1980, 1, 1), office="Minister")
        ).status
        == IdentityStatus.REVIEW
    )


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
    assert source_counts(
        [
            a.model_copy(update={"origin_cluster_id": cluster}),
            b.model_copy(update={"origin_cluster_id": cluster}),
        ]
    ) == {"raw_url_count": 2, "independent_origin_count": 1}


def test_claim_atomicity_examples() -> None:
    assert is_atomic("The official took office on 1 January 2026.")
    assert not is_atomic("The official took office and changed the policy.")


def test_fact_traceability_and_unknown_display_semantics() -> None:
    p = policy()
    person = Person(canonical_name="Kim Min", identity_status=IdentityStatus.RESOLVED)
    source = Source(
        url="https://example.gov/bio", title="Biography", publisher="Government", policy_id=p.id
    )
    claim = Claim(
        person_id=person.id,
        proposition="Kim Min took office in 2026.",
        subject="Kim Min",
        predicate="TOOK_OFFICE",
        object_text="Office in 2026",
        epistemic_status=EpistemicStatus.FACT,
        publication_status=PublicationStatus.PUBLISHED,
        asserted_as_true=True,
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
    unknown = Claim(
        person_id=person.id,
        proposition="Kim Min's birth date is not confirmed.",
        subject="Kim Min",
        predicate="BIRTH_DATE",
        object_text="unconfirmed",
        epistemic_status=EpistemicStatus.UNKNOWN,
        publication_status=PublicationStatus.PUBLISHED,
        asserted_as_true=False,
        resolution_note="Reviewed sources do not establish it.",
    )
    assert validate_claim_publication(unknown, person, [], {}, {}).publishable


def test_analysis_gates() -> None:
    relationship = Relationship(
        person_id=uuid4(),
        related_person_id=uuid4(),
        relationship_type="co-mention",
        strength=RelationshipStrength.STRONG,
    )
    assert not validate_relationship(relationship).publishable
    typed = relationship.model_copy(
        update={
            "evidence": [
                RelationshipEvidenceRef(
                    claim_evidence_id=uuid4(), evidence_type=RelationshipEvidenceType.APPOINTMENT
                )
            ]
        }
    )
    assert validate_relationship(typed).publishable
    assert not validate_pattern([{"origin-a"}]).publishable
    assert validate_pattern([{"origin-a"}, {"origin-b"}]).publishable
