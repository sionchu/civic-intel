"""Read published press and self-housing Claims through their canonical source gates."""

from collections.abc import Mapping, Sequence
from uuid import UUID

from packages.connectors.open_assembly import POLICY_ID, OpenAssemblyMemberConnector
from packages.domain.contracts import Claim, ClaimEvidence, Person
from packages.domain.enums import EpistemicStatus, EvidenceStance, IdentityReviewStatus
from packages.persistence.repository import SqlAlchemyRepository
from packages.rendering.money_projection import AssetSourceVersionConflict
from packages.verification.assembly_asset_import import (
    PETI_HOUSING_PREDICATE,
    assembly_asset_observation_hash,
    build_peti_housing_claim,
)
from packages.verification.assembly_press_import import PRESS_PREDICATE, build_press_claim
from packages.verification.claims import validate_claim_publication

DISCLOSURE_RECORD_PREDICATES = (PRESS_PREDICATE, PETI_HOUSING_PREDICATE)


def _current_roster_bridge(
    repository: SqlAlchemyRepository, person: Person, claim: Claim, proofs: Sequence[ClaimEvidence]
) -> bool:
    """Read the same current full-roster authority required by the reviewed admin path."""
    for proof in proofs:
        if proof.stance != EvidenceStance.SUPPORT or proof.feeder_observation_id is None:
            continue
        context = repository.feeder_observation_contexts([proof.feeder_observation_id]).get(
            proof.feeder_observation_id
        )
        if context is None:
            continue
        observation, snapshot, source, policy = context
        if (
            observation.feeder != "national_assembly_members"
            or observation.scope_key != "current_member_roster"
            or observation.semantic_scope != "legislative_member_roster"
            or observation.normalized.get("canonical_name") != person.canonical_name
            or observation.normalized.get("member_code") != observation.provider_record_key
            or assembly_asset_observation_hash(observation.normalized) != observation.content_hash
            or claim.qualifiers.get("provider_record_key") != observation.provider_record_key
            or claim.qualifiers.get("immutable_observation_hash") != observation.content_hash
            or proof.claim_id != claim.id
            or proof.snapshot_id != snapshot.id
            or proof.source_id != source.id
            or policy.id != POLICY_ID
        ):
            continue
        try:
            OpenAssemblyMemberConnector._validated_query(str(source.url))
        except ValueError:
            continue
        if repository.active_person_ids_by_observation([observation.id]).get(
            observation.id
        ) != frozenset({person.id}):
            continue
        checkpoint = repository.source_checkpoint(observation.feeder, observation.scope_key)
        if checkpoint is None or checkpoint.last_run_id is None:
            continue
        run = repository.source_run(checkpoint.last_run_id)
        metadata = checkpoint.metadata
        hashes = metadata.get("seen_provider_hashes", {})
        total, pages = metadata.get("list_total_count"), metadata.get("expected_pages")
        if (
            metadata.get("source_contract") == "assembly_member_roster"
            and isinstance(hashes, dict)
            and isinstance(total, int)
            and total > 0
            and isinstance(pages, int)
            and pages > 0
            and checkpoint.cursor == str(pages)
            and len(hashes) == total
            and hashes.get(observation.provider_record_key) == observation.content_hash
            and run is not None
            and run.status == "SUCCESS"
            and run.feeder == observation.feeder
            and run.scope_key == observation.scope_key
            and run.records_seen == total
        ):
            return True
    return False


def validate_public_disclosure_records(
    repository: SqlAlchemyRepository,
    person: Person,
    claims: Sequence[Claim],
    evidence: Mapping[UUID, Sequence[ClaimEvidence]],
) -> list[Claim]:
    selected = [claim for claim in claims if claim.predicate in DISCLOSURE_RECORD_PREDICATES]
    if not selected:
        return []
    observation_ids = {
        proof.feeder_observation_id
        for claim in selected
        for proof in evidence.get(claim.id, ())
        if proof.feeder_observation_id is not None and proof.stance == EvidenceStance.SUPPORT
    }
    contexts = repository.feeder_observation_contexts(observation_ids)
    active = repository.active_person_ids_by_observation(list(observation_ids))
    links = {
        link.observation_id: link
        for link in repository.person_observation_links(person.id)
        if link.superseded_at is None
    }
    reviews = {
        review.id: review
        for review in repository.identity_review_items(IdentityReviewStatus.RESOLVED)
    }
    for claim in selected:
        all_proofs = list(evidence.get(claim.id, ()))
        proofs = [proof for proof in all_proofs if proof.stance == EvidenceStance.SUPPORT]
        bridges = [proof for proof in all_proofs if proof.stance == EvidenceStance.NEUTRAL]
        if (
            claim.person_id != person.id
            or len(proofs) != 1
            or len(bridges) != 1
            or len(all_proofs) != len(proofs) + len(bridges)
        ):
            raise ValueError(
                "public disclosure requires exact subject, one source proof and one roster bridge"
            )
        proof = proofs[0]
        if proof.feeder_observation_id is None:
            raise ValueError("public disclosure has no immutable observation")
        context = contexts.get(proof.feeder_observation_id)
        if context is None or active.get(proof.feeder_observation_id) != frozenset({person.id}):
            raise ValueError("public disclosure has no exclusive active Person link")
        observation, snapshot, source, policy = context
        versions = repository.feeder_observations(
            observation.feeder, observation.scope_key, observation.provider_record_key
        )
        if any(version.content_hash != observation.content_hash for version in versions):
            raise AssetSourceVersionConflict("public disclosure has conflicting immutable versions")
        link = links.get(observation.id)
        review = (
            reviews.get(link.review_item_id) if link is not None and link.review_item_id else None
        )
        if link is None or review is None:
            raise ValueError("public disclosure has no resolved owner-reviewed identity")
        factory = (
            build_press_claim if claim.predicate == PRESS_PREDICATE else build_peti_housing_claim
        )
        expected, expected_proof = factory(
            source,
            snapshot,
            observation,
            policy=policy,
            person=person,
            link=link,
            review=review,
            publication_approved=True,
        )
        actual_fields = claim.model_dump()
        expected_fields = expected.model_dump()
        # SQLite preserves wall-clock values but drops timezone information. Match its stored
        # calendar value without attaching an invented timezone; PostgreSQL compares instants.
        for field in ("valid_from", "recorded_at"):
            actual_time, expected_time = actual_fields[field], expected_fields[field]
            if (actual_time.tzinfo is None) != (expected_time.tzinfo is None):
                actual_fields[field] = actual_time.replace(tzinfo=None)
                expected_fields[field] = expected_time.replace(tzinfo=None)
        if actual_fields != expected_fields or proof.model_dump(
            exclude={"id"}
        ) != expected_proof.model_dump(exclude={"id"}):
            raise ValueError(
                "published disclosure differs from canonical immutable materialization"
            )
        bridge = bridges[0]
        if bridge.claim_id != claim.id or bridge.excerpt is not None:
            raise ValueError("public disclosure identity bridge differs")
        roster, roster_evidence = repository.published_person_claim_contexts(
            [person.id],
            predicates=(
                "ASSEMBLY_PARTY",
                "ASSEMBLY_DISTRICT",
                "ASSEMBLY_COMMITTEES",
                "ASSEMBLY_REELECTION",
            ),
        ).get(person.id, ((), {}))
        matches = [
            (anchor, list(roster_evidence.get(anchor.id, ())))
            for anchor in roster
            if anchor.person_id == person.id
            and anchor.qualifiers.get("source_contract") == "assembly_member_roster"
            and anchor.epistemic_status == EpistemicStatus.FACT
            and anchor.asserted_as_true
            and any(
                item.stance == EvidenceStance.SUPPORT
                and item.claim_id == anchor.id
                and item.model_dump(exclude={"id", "claim_id", "stance", "excerpt"})
                == bridge.model_dump(exclude={"id", "claim_id", "stance", "excerpt"})
                for item in roster_evidence.get(anchor.id, ())
            )
        ]
        source_map = repository.sources(item.source_id for _, items in matches for item in items)
        policy_map = repository.policies(item.policy_id for item in source_map.values())
        if not any(
            validate_claim_publication(anchor, person, items, source_map, policy_map).publishable
            and _current_roster_bridge(repository, person, anchor, items)
            for anchor, items in matches
        ):
            raise ValueError(
                "public disclosure identity bridge has no current published roster proof"
            )
    return selected
