"""Committee Claims from the official Assembly committee-member list.

The list states, per committee (``DEPT_CD``) and ``MONA_CD``, the role text 위원장/간사/위원.
Two Claim lanes read the same observations:

- ``ASSEMBLY_COMMITTEE_ROLE``: only the two roles that carry a committee office (위원장, 간사);
- ``ASSEMBLY_COMMITTEE_MEMBERSHIP``: every row, keyed by the official committee code. It is the
  code-keyed membership fact that relation derivation binds on; the roster's comma-separated
  ``ASSEMBLY_COMMITTEES`` text stays a display Claim and is never joined across People by name.

The role text is copied verbatim and no authority is derived from it. The list has no start/end
date, so the Claim is valid from collection time.
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
from packages.verification.assembly_member_claims import AssemblyMemberClaimLane
from packages.verification.claims import validate_claim_publication
from packages.verification.person_record_links import _as
from packages.verification.policy import PolicyAction, require_policy

if TYPE_CHECKING:
    from packages.persistence.repository import SqlAlchemyRepository

ASSEMBLY_COMMITTEE_MEMBERSHIP_FEEDER = "assembly_committee_memberships"
ASSEMBLY_COMMITTEE_MEMBERSHIP_SCOPE = "assembly_committee_member_list:current"
ASSEMBLY_COMMITTEE_MEMBERSHIP_SEMANTIC_SCOPE = "legislative_committee_membership_role"
ASSEMBLY_COMMITTEE_MEMBERSHIP_SOURCE_CONTRACT = "assembly_committee_member_list_full"
ASSEMBLY_COMMITTEE_MEMBERSHIP_SEMANTICS = "official_committee_member_list_row_as_of_collection"
ASSEMBLY_COMMITTEE_ROLE_PREDICATE = "ASSEMBLY_COMMITTEE_ROLE"
ASSEMBLY_COMMITTEE_ROLE_SOURCE_CONTRACT = "assembly_committee_member_list_role"
ASSEMBLY_COMMITTEE_MEMBERSHIP_PREDICATE = "ASSEMBLY_COMMITTEE_MEMBERSHIP"
ASSEMBLY_COMMITTEE_MEMBERSHIP_CLAIM_CONTRACT = "assembly_committee_member_list_membership"
PUBLISHED_COMMITTEE_ROLES = frozenset({"위원장", "간사"})
LISTED_COMMITTEE_ROLES = frozenset({"위원장", "간사", "위원"})
_COMMITTEE_ROLE_CLAIM_NAMESPACE = UUID("6d0f3b8e-4c5a-4f1e-9b7d-2a8c1e5f9d31")
_COMMITTEE_MEMBERSHIP_CLAIM_NAMESPACE = UUID("8a51c0d2-6b3e-4f7a-9c18-3d2e7f4b5a60")


class AssemblyCommitteeRoleError(ValueError):
    pass


def _role_claim_matches_observation(claim: Claim, observation: FeederObservation) -> bool:
    normalized = observation.normalized
    return (
        f"{claim.qualifiers.get('committee_code')}:{claim.qualifiers.get('provider_person_key')}"
        == observation.provider_record_key
        and claim.qualifiers.get("committee_code") == normalized.get("committee_code")
        and claim.qualifiers.get("committee_name") == normalized.get("committee_name")
        and claim.qualifiers.get("committee_role") == normalized.get("role_published")
        and claim.qualifiers.get("committee_role") in PUBLISHED_COMMITTEE_ROLES
        and claim.object_text
        == f"{normalized.get('committee_name')} {normalized.get('role_published')}"
    )


def _membership_claim_matches_observation(claim: Claim, observation: FeederObservation) -> bool:
    normalized = observation.normalized
    return (
        f"{claim.qualifiers.get('committee_code')}:{claim.qualifiers.get('provider_person_key')}"
        == observation.provider_record_key
        and claim.qualifiers.get("committee_code") == normalized.get("committee_code")
        and claim.qualifiers.get("committee_name") == normalized.get("committee_name")
        and claim.qualifiers.get("committee_role") == normalized.get("role_published")
        and claim.qualifiers.get("committee_role") in LISTED_COMMITTEE_ROLES
        and claim.object_text == normalized.get("committee_name")
    )


ASSEMBLY_COMMITTEE_MEMBERSHIP_LANE = AssemblyMemberClaimLane(
    feeder=ASSEMBLY_COMMITTEE_MEMBERSHIP_FEEDER,
    semantic_scope=ASSEMBLY_COMMITTEE_MEMBERSHIP_SEMANTIC_SCOPE,
    predicate=ASSEMBLY_COMMITTEE_MEMBERSHIP_PREDICATE,
    source_contract=ASSEMBLY_COMMITTEE_MEMBERSHIP_CLAIM_CONTRACT,
    logical_key_qualifiers=("committee_code",),
    claim_matches_observation=_membership_claim_matches_observation,
    error=AssemblyCommitteeRoleError,
    label="Assembly committee membership",
)


ASSEMBLY_COMMITTEE_ROLE_LANE = AssemblyMemberClaimLane(
    feeder=ASSEMBLY_COMMITTEE_MEMBERSHIP_FEEDER,
    semantic_scope=ASSEMBLY_COMMITTEE_MEMBERSHIP_SEMANTIC_SCOPE,
    predicate=ASSEMBLY_COMMITTEE_ROLE_PREDICATE,
    source_contract=ASSEMBLY_COMMITTEE_ROLE_SOURCE_CONTRACT,
    logical_key_qualifiers=("committee_code",),
    claim_matches_observation=_role_claim_matches_observation,
    error=AssemblyCommitteeRoleError,
    label="Assembly committee role",
)


def _text(normalized: dict[str, object], key: str) -> str:
    value = normalized.get(key)
    if not isinstance(value, str) or not value.strip():
        raise AssemblyCommitteeRoleError(f"committee-member observation field {key} is missing")
    return value.strip()


@dataclass(frozen=True)
class AssemblyCommitteeRoleBundle:
    claims: tuple[Claim, ...]
    evidence: tuple[ClaimEvidence, ...]


def build_assembly_committee_role_bundle(
    person: Person,
    observation: FeederObservation,
    *,
    source: Source,
    policy: SourcePolicy,
    membership: bool = False,
) -> AssemblyCommitteeRoleBundle:
    """Build one committee-office (default) or code-keyed membership Claim for an exact MONA_CD."""

    if person.identity_status != IdentityStatus.RESOLVED:
        raise AssemblyCommitteeRoleError("Assembly committee role requires a resolved Person")
    if (
        observation.feeder != ASSEMBLY_COMMITTEE_MEMBERSHIP_FEEDER
        or observation.scope_key != ASSEMBLY_COMMITTEE_MEMBERSHIP_SCOPE
        or observation.semantic_scope != ASSEMBLY_COMMITTEE_MEMBERSHIP_SEMANTIC_SCOPE
    ):
        raise AssemblyCommitteeRoleError("observation is outside the committee-role scope")
    if source.policy_id != policy.id:
        raise AssemblyCommitteeRoleError("committee-role SourcePolicy does not match Source")
    require_policy(policy, PolicyAction.STORE_METADATA)
    normalized = observation.normalized
    if normalized.get("membership_semantics") != ASSEMBLY_COMMITTEE_MEMBERSHIP_SEMANTICS:
        raise AssemblyCommitteeRoleError("committee-member observation semantics are invalid")
    committee_code = _text(normalized, "committee_code")
    committee_name = _text(normalized, "committee_name")
    member_code = _text(normalized, "member_code")
    role = _text(normalized, "role_published")
    if observation.provider_record_key != f"{committee_code}:{member_code}":
        raise AssemblyCommitteeRoleError("committee-member key does not match its codes")
    if membership:
        if role not in LISTED_COMMITTEE_ROLES:
            raise AssemblyCommitteeRoleError("committee role is not a listed committee role")
        namespace = _COMMITTEE_MEMBERSHIP_CLAIM_NAMESPACE
        predicate = ASSEMBLY_COMMITTEE_MEMBERSHIP_PREDICATE
        contract, object_text = ASSEMBLY_COMMITTEE_MEMBERSHIP_CLAIM_CONTRACT, committee_name
    else:
        if role not in PUBLISHED_COMMITTEE_ROLES:
            raise AssemblyCommitteeRoleError("committee role is not a published committee office")
        namespace, predicate = _COMMITTEE_ROLE_CLAIM_NAMESPACE, ASSEMBLY_COMMITTEE_ROLE_PREDICATE
        contract, object_text = ASSEMBLY_COMMITTEE_ROLE_SOURCE_CONTRACT, f"{committee_name} {role}"

    claim = Claim(
        id=uuid5(
            namespace,
            "|".join((str(person.id), observation.provider_record_key, observation.content_hash)),
        ),
        person_id=person.id,
        proposition=(
            f"{person.canonical_name}는 국회 위원회 위원 명단에 「{committee_name}」 "
            f"{_as(role)} 기재되어 있다."
        ),
        subject=person.canonical_name,
        predicate=predicate,
        object_text=object_text,
        qualifiers={
            "source_contract": contract,
            "source_scope": observation.scope_key,
            "semantic_scope": observation.semantic_scope,
            "provider_record_key": observation.provider_record_key,
            "immutable_observation_hash": observation.content_hash,
            "provider_identity_namespace": "assembly_mona_cd",
            "provider_person_key": member_code,
            "committee_code": committee_code,
            "committee_name": committee_name,
            "committee_role": role,
            "membership_semantics": ASSEMBLY_COMMITTEE_MEMBERSHIP_SEMANTICS,
        },
        epistemic_status=EpistemicStatus.FACT,
        publication_status=PublicationStatus.PUBLISHED,
        asserted_as_true=True,
        valid_from=observation.recorded_at,
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
        raise AssemblyCommitteeRoleError(
            f"committee-role Claim failed publication gate: {gate.failures}"
        )
    return AssemblyCommitteeRoleBundle((claim,), (evidence,))


@dataclass(frozen=True)
class AssemblyCommitteeRolePublicationResult:
    run_id: UUID
    observations_considered: int
    office_rows: int
    published_claims: int
    unchanged_claims: int
    unresolved_member_codes: tuple[str, ...]
    # Current office Claims whose committee no longer lists the Person as 위원장/간사. They are
    # reported, not withdrawn: a role change needs a reviewed supersession.
    stale_claim_ids: tuple[UUID, ...]


class AssemblyCommitteeRolePublisher:
    """Publish committee offices only from the manifest of the latest successful full list."""

    def __init__(self, repository: SqlAlchemyRepository) -> None:
        self.repository = repository

    def _latest_successful_observations(self) -> tuple[UUID, tuple[FeederObservation, ...]]:
        checkpoint = self.repository.source_checkpoint(
            ASSEMBLY_COMMITTEE_MEMBERSHIP_FEEDER, ASSEMBLY_COMMITTEE_MEMBERSHIP_SCOPE
        )
        if checkpoint is None or checkpoint.last_run_id is None:
            raise AssemblyCommitteeRoleError("committee-member success checkpoint is unavailable")
        run = self.repository.source_run(checkpoint.last_run_id)
        if (
            run is None
            or run.status != SourceRunStatus.SUCCESS
            or run.feeder != ASSEMBLY_COMMITTEE_MEMBERSHIP_FEEDER
            or run.scope_key != checkpoint.scope_key
        ):
            raise AssemblyCommitteeRoleError(
                "committee roles require the latest successful full member-list enumeration"
            )
        metadata = checkpoint.metadata
        if metadata.get("source_contract") != ASSEMBLY_COMMITTEE_MEMBERSHIP_SOURCE_CONTRACT:
            raise AssemblyCommitteeRoleError("committee-member checkpoint source contract is invalid")
        raw_hashes = metadata.get("seen_provider_hashes")
        if not isinstance(raw_hashes, dict):
            raise AssemblyCommitteeRoleError("committee-member checkpoint lacks provider manifest")
        try:
            expected_total = int(metadata["list_total_count"])
            expected_pages = int(metadata["expected_pages"])
        except (KeyError, TypeError, ValueError):
            raise AssemblyCommitteeRoleError(
                "committee-member checkpoint coverage metadata is invalid"
            ) from None
        if checkpoint.cursor != str(expected_pages) or len(raw_hashes) != expected_total:
            raise AssemblyCommitteeRoleError("committee-member checkpoint coverage is incomplete")
        by_key: dict[str, FeederObservation] = {}
        for observation in self.repository.feeder_observations(
            ASSEMBLY_COMMITTEE_MEMBERSHIP_FEEDER, checkpoint.scope_key
        ):
            if raw_hashes.get(observation.provider_record_key) != observation.content_hash:
                continue
            if observation.provider_record_key in by_key:
                raise AssemblyCommitteeRoleError(
                    "committee-member manifest maps one key to multiple observations"
                )
            by_key[observation.provider_record_key] = observation
        if set(by_key) != set(raw_hashes):
            raise AssemblyCommitteeRoleError("committee-member manifest lacks committed observations")
        return run.id, tuple(by_key[key] for key in sorted(by_key))

    def publish_latest_successful(
        self, *, dry_run: bool = False, memberships: bool = False
    ) -> AssemblyCommitteeRolePublicationResult:
        """Publish office Claims, or with ``memberships`` every row's code-keyed membership."""

        lane = ASSEMBLY_COMMITTEE_MEMBERSHIP_LANE if memberships else ASSEMBLY_COMMITTEE_ROLE_LANE
        listed = LISTED_COMMITTEE_ROLES if memberships else PUBLISHED_COMMITTEE_ROLES
        run_id, observations = self._latest_successful_observations()
        offices = [
            item for item in observations if item.normalized.get("role_published") in listed
        ]
        contexts = self.repository.assembly_legislative_source_contexts(
            [item.id for item in offices]
        )
        member_codes = sorted({_text(item.normalized, "member_code") for item in offices})
        people_by_code = self.repository.assembly_current_person_contexts(member_codes)
        unresolved = tuple(sorted(set(member_codes) - set(people_by_code)))
        pending = []
        for observation in offices:
            context = contexts.get(observation.id)
            if context is None:
                raise AssemblyCommitteeRoleError("committee-member observation provenance is incomplete")
            person = people_by_code.get(_text(observation.normalized, "member_code"))
            if person is None:
                continue
            source, policy = context
            bundle = build_assembly_committee_role_bundle(
                person, observation, source=source, policy=policy, membership=memberships
            )
            pending.append((person, observation, bundle.claims, bundle.evidence))

        requested_ids = {claim.id for _, _, claims, _ in pending for claim in claims}
        # Every current office Claim of this lane, including Persons no longer listed as an office.
        current_claims = [
            claim
            for claim in self.repository.claims(published_only=True, current_only=True)
            if claim.predicate == lane.predicate
        ]
        existing_before = {claim.id for claim in current_claims}
        unchanged = len(existing_before & requested_ids)
        current_keys = {
            lane.logical_key(str(person.id), claims[0].qualifiers)
            for person, _, claims, _ in pending
        }
        stale = tuple(
            sorted(
                claim.id
                for claim in current_claims
                if lane.logical_key(str(claim.person_id), claim.qualifiers) not in current_keys
            )
        )
        if not dry_run:
            self.repository.import_assembly_member_claims_batch(pending, lane)
        return AssemblyCommitteeRolePublicationResult(
            run_id=run_id,
            observations_considered=len(observations),
            office_rows=len(offices),
            published_claims=len(requested_ids) - unchanged,
            unchanged_claims=unchanged,
            unresolved_member_codes=unresolved,
            stale_claim_ids=stale,
        )
