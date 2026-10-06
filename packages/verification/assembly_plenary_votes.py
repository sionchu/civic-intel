"""Plenary roll-call vote Claims for exact current-roster ``MONA_CD`` links.

Each Claim restates one official member vote row (찬성/반대/기권/불참) for one bill. It never
infers a reason for 불참, an ideology, an alignment or a party-line score. Bills whose member rows
do not reconcile with the published tallies are excluded rather than corrected.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import UUID, uuid5

from packages.domain.contracts import (
    Claim,
    ClaimEvidence,
    FeederObservation,
    Person,
    Source,
    SourcePolicy,
)
from packages.domain.enums import (
    EpistemicStatus,
    EvidenceStance,
    IdentityStatus,
    PublicationStatus,
    SourceRunStatus,
)
from packages.verification.assembly_base_profile import (
    ASSEMBLY_BASE_PROFILE_FEEDER,
    ASSEMBLY_BASE_PROFILE_SCOPE,
)
from packages.verification.assembly_member_claims import AssemblyMemberClaimLane
from packages.verification.claims import validate_claim_publication
from packages.verification.person_record_links import _as
from packages.verification.policy import PolicyAction, require_policy

if TYPE_CHECKING:
    from packages.persistence.repository import SqlAlchemyRepository

ASSEMBLY_VOTE_FEEDER = "assembly_plenary_roll_call_votes"
ASSEMBLY_VOTE_SEMANTIC_SCOPE = "legislative_plenary_roll_call_vote"
ASSEMBLY_VOTE_ACQUISITION_CONTRACT = "assembly_term_plenary_roll_call_votes"
ASSEMBLY_VOTE_SEMANTICS = "official_member_plenary_roll_call_record"
ASSEMBLY_PLENARY_VOTE_PREDICATE = "ASSEMBLY_PLENARY_VOTE"
ASSEMBLY_PLENARY_VOTE_SOURCE_CONTRACT = "assembly_plenary_roll_call_vote"
VOTE_VALUE_LABELS = {
    "YES": "찬성",
    "NO": "반대",
    "ABSTAIN": "기권",
    "NOT_PARTICIPATING": "불참",
}
_VOTE_CLAIM_NAMESPACE = UUID("b3a1e0c4-7d2f-4e8a-9c61-5f0d2e7a4b19")


class AssemblyPlenaryVoteError(ValueError):
    pass


def _vote_claim_matches_observation(claim: Claim, observation: FeederObservation) -> bool:
    normalized = observation.normalized
    return (
        claim.qualifiers.get("bill_id") == normalized.get("bill_id")
        and f"{normalized.get('bill_id')}:{claim.qualifiers.get('provider_person_key')}"
        == observation.provider_record_key
        and claim.qualifiers.get("vote_value") == normalized.get("vote_value")
        and claim.qualifiers.get("vote_value_published")
        == VOTE_VALUE_LABELS.get(str(normalized.get("vote_value")))
        and normalized.get("bill_tally_reconciliation") == "MATCHED"
        and claim.object_text == normalized.get("bill_name")
    )


ASSEMBLY_PLENARY_VOTE_LANE = AssemblyMemberClaimLane(
    feeder=ASSEMBLY_VOTE_FEEDER,
    semantic_scope=ASSEMBLY_VOTE_SEMANTIC_SCOPE,
    predicate=ASSEMBLY_PLENARY_VOTE_PREDICATE,
    source_contract=ASSEMBLY_PLENARY_VOTE_SOURCE_CONTRACT,
    logical_key_qualifiers=("bill_id",),
    claim_matches_observation=_vote_claim_matches_observation,
    error=AssemblyPlenaryVoteError,
    label="Assembly plenary vote",
)


def _text(normalized: dict[str, object], key: str) -> str:
    value = normalized.get(key)
    if not isinstance(value, str) or not value.strip():
        raise AssemblyPlenaryVoteError(f"vote observation field {key} is missing")
    return value.strip()


@dataclass(frozen=True)
class AssemblyPlenaryVoteBundle:
    claims: tuple[Claim, ...]
    evidence: tuple[ClaimEvidence, ...]


def build_assembly_plenary_vote_bundle(
    person: Person,
    observation: FeederObservation,
    *,
    source: Source,
    policy: SourcePolicy,
) -> AssemblyPlenaryVoteBundle:
    """Build one vote Claim from one reconciled member vote row."""

    if person.identity_status != IdentityStatus.RESOLVED:
        raise AssemblyPlenaryVoteError("Assembly plenary vote requires a resolved Person")
    if (
        observation.feeder != ASSEMBLY_VOTE_FEEDER
        or observation.semantic_scope != ASSEMBLY_VOTE_SEMANTIC_SCOPE
        or not observation.scope_key.startswith("assembly_age:")
    ):
        raise AssemblyPlenaryVoteError("observation is outside the plenary-vote scope")
    if source.policy_id != policy.id:
        raise AssemblyPlenaryVoteError("plenary-vote SourcePolicy does not match Source")
    require_policy(policy, PolicyAction.STORE_METADATA)
    normalized = observation.normalized
    if normalized.get("vote_semantics") != ASSEMBLY_VOTE_SEMANTICS:
        raise AssemblyPlenaryVoteError("vote observation semantics are invalid")
    if normalized.get("bill_tally_reconciliation") != "MATCHED":
        raise AssemblyPlenaryVoteError("vote rows of an unreconciled bill are not published")
    bill_id = _text(normalized, "bill_id")
    bill_name = _text(normalized, "bill_name")
    member_code = _text(normalized, "member_code")
    vote_value = _text(normalized, "vote_value")
    published = _text(normalized, "vote_value_published")
    vote_datetime = _text(normalized, "vote_datetime")
    if observation.provider_record_key != f"{bill_id}:{member_code}":
        raise AssemblyPlenaryVoteError("vote key does not match its bill and member codes")
    if VOTE_VALUE_LABELS.get(vote_value) != published:
        raise AssemblyPlenaryVoteError("vote value does not match the published vote text")

    qualifiers = {
        "source_contract": ASSEMBLY_PLENARY_VOTE_SOURCE_CONTRACT,
        "source_scope": observation.scope_key,
        "semantic_scope": observation.semantic_scope,
        "provider_record_key": observation.provider_record_key,
        "immutable_observation_hash": observation.content_hash,
        "provider_identity_namespace": "assembly_mona_cd",
        "provider_person_key": member_code,
        "bill_id": bill_id,
        "vote_value": vote_value,
        "vote_value_published": published,
        "vote_datetime": vote_datetime,
        "date": vote_datetime[:10],
        "vote_semantics": ASSEMBLY_VOTE_SEMANTICS,
    }
    for key, target in (
        ("bill_no", "bill_no"),
        ("committee", "committee"),
        ("bill_url", "detail_url"),
        ("assembly_age", "assembly_age"),
        ("sitting_number", "sitting_number"),
    ):
        value = normalized.get(key)
        if value is not None and str(value).strip():
            qualifiers[target] = str(value).strip()

    claim = Claim(
        id=uuid5(
            _VOTE_CLAIM_NAMESPACE,
            "|".join((str(person.id), observation.provider_record_key, observation.content_hash)),
        ),
        person_id=person.id,
        proposition=(
            f"{person.canonical_name}의 본회의 표결은 국회 표결 기록에서 「{bill_name}」에 "
            f"{_as(published)} 기록되어 있다."
        ),
        subject=person.canonical_name,
        predicate=ASSEMBLY_PLENARY_VOTE_PREDICATE,
        object_text=bill_name,
        qualifiers=qualifiers,
        epistemic_status=EpistemicStatus.FACT,
        publication_status=PublicationStatus.PUBLISHED,
        asserted_as_true=True,
        valid_from=observation.provider_observed_at or observation.recorded_at,
        recorded_at=observation.recorded_at,
    )
    evidence = ClaimEvidence(
        id=uuid5(
            claim.id,
            "|".join(
                (
                    str(source.id),
                    str(observation.snapshot_id),
                    str(observation.id),
                    EvidenceStance.SUPPORT.value,
                )
            ),
        ),
        claim_id=claim.id,
        source_id=source.id,
        snapshot_id=observation.snapshot_id,
        feeder_observation_id=observation.id,
        stance=EvidenceStance.SUPPORT,
    )
    gate = validate_claim_publication(
        claim, person, [evidence], {source.id: source}, {policy.id: policy}
    )
    if not gate.publishable:
        raise AssemblyPlenaryVoteError(f"plenary-vote Claim failed publication gate: {gate.failures}")
    return AssemblyPlenaryVoteBundle((claim,), (evidence,))


@dataclass(frozen=True)
class AssemblyPlenaryVotePublicationResult:
    run_id: UUID
    members_published: int
    vote_rows_considered: int
    published_claims: int
    unchanged_claims: int
    excluded_unreconciled_bills: tuple[str, ...]


class AssemblyPlenaryVotePublisher:
    """Publish vote Claims per current-roster member from the latest complete term run."""

    def __init__(self, repository: SqlAlchemyRepository, *, assembly_age: int = 22) -> None:
        self.repository = repository
        self.scope_key = f"assembly_age:{assembly_age}"

    def _complete_run(self) -> tuple[UUID, frozenset[str]]:
        checkpoint = self.repository.source_checkpoint(ASSEMBLY_VOTE_FEEDER, self.scope_key)
        if checkpoint is None or checkpoint.last_run_id is None:
            raise AssemblyPlenaryVoteError("roll-call success checkpoint is unavailable")
        run = self.repository.source_run(checkpoint.last_run_id)
        if run is None or run.status != SourceRunStatus.SUCCESS:
            raise AssemblyPlenaryVoteError("vote Claims require the latest complete term run")
        metadata = checkpoint.metadata
        if metadata.get("source_contract") != ASSEMBLY_VOTE_ACQUISITION_CONTRACT:
            raise AssemblyPlenaryVoteError("roll-call checkpoint source contract is invalid")
        try:
            bill_count = int(metadata["universe_bill_count"])
        except (KeyError, TypeError, ValueError):
            raise AssemblyPlenaryVoteError("roll-call checkpoint coverage is invalid") from None
        if checkpoint.cursor != str(bill_count):
            raise AssemblyPlenaryVoteError("roll-call checkpoint does not cover the whole term")
        exceptions = metadata.get("tally_exceptions") or {}
        if not isinstance(exceptions, dict):
            raise AssemblyPlenaryVoteError("roll-call checkpoint tally exceptions are invalid")
        return run.id, frozenset(str(item) for item in exceptions)

    def publish_latest_successful(
        self, *, dry_run: bool = False
    ) -> AssemblyPlenaryVotePublicationResult:
        run_id, excluded = self._complete_run()
        member_codes = sorted(
            {
                item.provider_record_key
                for item in self.repository.feeder_observations(
                    ASSEMBLY_BASE_PROFILE_FEEDER, ASSEMBLY_BASE_PROFILE_SCOPE
                )
            }
        )
        people_by_code = self.repository.assembly_current_person_contexts(member_codes)
        considered = published = unchanged = members = 0
        for member_code in sorted(people_by_code):
            person = people_by_code[member_code]
            latest: dict[str, FeederObservation] = {}
            for observation in self.repository.feeder_observations(
                ASSEMBLY_VOTE_FEEDER, self.scope_key, key_suffix=f":{member_code}"
            ):
                # Observations are ordered by recorded_at; a later version replaces an earlier one.
                latest[observation.provider_record_key] = observation
            rows = [
                item
                for key, item in sorted(latest.items())
                if key.split(":", 1)[0] not in excluded
                and item.normalized.get("member_code") == member_code
            ]
            considered += len(rows)
            if not rows:
                continue
            contexts = self.repository.assembly_legislative_source_contexts(
                [item.id for item in rows]
            )
            pending = []
            for observation in rows:
                context = contexts.get(observation.id)
                if context is None:
                    raise AssemblyPlenaryVoteError("vote observation provenance is incomplete")
                source, policy = context
                bundle = build_assembly_plenary_vote_bundle(
                    person, observation, source=source, policy=policy
                )
                pending.append((person, observation, bundle.claims, bundle.evidence))
            existing = {
                claim.id
                for claim in self.repository.claims(
                    person_id=person.id, published_only=True, current_only=True
                )
                if claim.predicate == ASSEMBLY_PLENARY_VOTE_PREDICATE
            }
            requested = {claim.id for _, _, claims, _ in pending for claim in claims}
            unchanged += len(existing & requested)
            published += len(requested - existing)
            members += 1
            if not dry_run:
                self.repository.import_assembly_member_claims_batch(
                    pending, ASSEMBLY_PLENARY_VOTE_LANE
                )
        return AssemblyPlenaryVotePublicationResult(
            run_id=run_id,
            members_published=members,
            vote_rows_considered=considered,
            published_claims=published,
            unchanged_claims=unchanged,
            excluded_unreconciled_bills=tuple(sorted(excluded)),
        )
