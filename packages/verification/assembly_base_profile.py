from __future__ import annotations

from dataclasses import dataclass, field
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
)
from packages.verification.claims import validate_claim_publication
from packages.verification.policy import PolicyAction, require_policy

if TYPE_CHECKING:
    from packages.persistence.repository import SqlAlchemyRepository


ASSEMBLY_BASE_PROFILE_FEEDER = "national_assembly_members"
ASSEMBLY_BASE_PROFILE_SCOPE = "current_member_roster"
ASSEMBLY_BASE_PROFILE_SEMANTIC_SCOPE = "legislative_member_roster"
ASSEMBLY_BASE_PROFILE_SOURCE_CONTRACT = "assembly_member_roster"
_ASSEMBLY_BASE_PROFILE_CLAIM_NAMESPACE = UUID("e1ac6e8a-9e19-45ef-a0f8-9b3a8c7ac4a2")


class AssemblyBaseProfileError(ValueError):
    pass


@dataclass(frozen=True)
class AssemblyBaseProfileField:
    name: str
    predicate: str
    proposition_label: str


ASSEMBLY_BASE_PROFILE_FIELDS: tuple[AssemblyBaseProfileField, ...] = (
    AssemblyBaseProfileField("party", "ASSEMBLY_PARTY", "국회 명부상 소속 정당은"),
    AssemblyBaseProfileField("district", "ASSEMBLY_DISTRICT", "국회 명부상 지역구는"),
    AssemblyBaseProfileField("committees", "ASSEMBLY_COMMITTEES", "국회 명부상 위원회 표기는"),
    AssemblyBaseProfileField("reelection", "ASSEMBLY_REELECTION", "국회 명부상 재선 구분은"),
)
_ASSEMBLY_BASE_PROFILE_FIELD_NAMES = frozenset(item.name for item in ASSEMBLY_BASE_PROFILE_FIELDS)


@dataclass(frozen=True)
class AssemblyBaseProfileBundle:
    claims: tuple[Claim, ...]
    evidence: tuple[ClaimEvidence, ...]
    missing_fields: tuple[str, ...]


def build_assembly_base_profile_bundle(
    person: Person,
    observation: FeederObservation,
    *,
    source: Source,
    policy: SourcePolicy,
) -> AssemblyBaseProfileBundle:
    """Build source-bounded roster field Claims without creating a new canonical model."""

    if person.identity_status != IdentityStatus.RESOLVED:
        raise AssemblyBaseProfileError("Assembly base profile requires a resolved Person")
    if (
        observation.feeder != ASSEMBLY_BASE_PROFILE_FEEDER
        or observation.scope_key != ASSEMBLY_BASE_PROFILE_SCOPE
        or observation.semantic_scope != ASSEMBLY_BASE_PROFILE_SEMANTIC_SCOPE
    ):
        raise AssemblyBaseProfileError("observation is outside the Assembly current-roster scope")
    if observation.normalized.get("member_code") != observation.provider_record_key:
        raise AssemblyBaseProfileError("Assembly provider identity does not match observation key")
    if source.policy_id != policy.id:
        raise AssemblyBaseProfileError("Assembly base profile SourcePolicy does not match Source")

    require_policy(policy, PolicyAction.STORE_METADATA)
    claims: list[Claim] = []
    evidence: list[ClaimEvidence] = []
    missing_fields: list[str] = []
    for field_definition in ASSEMBLY_BASE_PROFILE_FIELDS:
        raw_value = observation.normalized.get(field_definition.name)
        if raw_value is None or (isinstance(raw_value, str) and not raw_value.strip()):
            missing_fields.append(field_definition.name)
            continue
        if not isinstance(raw_value, str):
            raise AssemblyBaseProfileError(
                f"Assembly roster field {field_definition.name} is not a string"
            )
        value = raw_value.strip()
        claim_id = uuid5(
            _ASSEMBLY_BASE_PROFILE_CLAIM_NAMESPACE,
            "|".join(
                (
                    str(person.id),
                    observation.feeder,
                    observation.scope_key,
                    observation.semantic_scope,
                    observation.provider_record_key,
                    observation.content_hash,
                    field_definition.name,
                )
            ),
        )
        claim = Claim(
            id=claim_id,
            person_id=person.id,
            proposition=f"{person.canonical_name}의 {field_definition.proposition_label} {value}이다.",
            subject=person.canonical_name,
            predicate=field_definition.predicate,
            object_text=value,
            qualifiers={
                "source_contract": ASSEMBLY_BASE_PROFILE_SOURCE_CONTRACT,
                "source_scope": observation.scope_key,
                "semantic_scope": observation.semantic_scope,
                "provider_record_key": observation.provider_record_key,
                "field_name": field_definition.name,
                "immutable_observation_hash": observation.content_hash,
            },
            epistemic_status=EpistemicStatus.FACT,
            publication_status=PublicationStatus.PUBLISHED,
            asserted_as_true=True,
            valid_from=observation.recorded_at,
            recorded_at=observation.recorded_at,
        )
        item = ClaimEvidence(
            id=uuid5(
                claim_id,
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
            claim,
            person,
            [item],
            {source.id: source},
            {policy.id: policy},
        )
        if not gate.publishable:
            raise AssemblyBaseProfileError(
                f"Assembly base profile Claim failed publication gate: {gate.failures}"
            )
        claims.append(claim)
        evidence.append(item)

    return AssemblyBaseProfileBundle(tuple(claims), tuple(evidence), tuple(missing_fields))


@dataclass(frozen=True)
class AssemblyBaseProfileRunResult:
    run_id: UUID
    observations_considered: int
    observations_published: int
    published_claims: int
    unchanged_claims: int
    missing_field_counts: dict[str, int] = field(default_factory=dict)
    skipped_observation_ids: tuple[UUID, ...] = ()


class AssemblyBaseProfilePublisher:
    """Publish only the exact manifest of the latest successful full roster run."""

    def __init__(self, repository: SqlAlchemyRepository) -> None:
        self.repository = repository

    def _latest_successful_observations(self) -> tuple[UUID, tuple[FeederObservation, ...]]:
        checkpoint = self.repository.source_checkpoint(
            ASSEMBLY_BASE_PROFILE_FEEDER,
            ASSEMBLY_BASE_PROFILE_SCOPE,
        )
        if checkpoint is None or checkpoint.last_run_id is None:
            raise AssemblyBaseProfileError("Assembly current-roster success checkpoint is unavailable")
        run = self.repository.source_run(checkpoint.last_run_id)
        if (
            run is None
            or run.status.value != "SUCCESS"
            or run.feeder != ASSEMBLY_BASE_PROFILE_FEEDER
            or run.scope_key != ASSEMBLY_BASE_PROFILE_SCOPE
        ):
            raise AssemblyBaseProfileError(
                "Assembly base profile requires the latest successful full enumeration"
            )
        metadata = checkpoint.metadata
        if metadata.get("source_contract") != ASSEMBLY_BASE_PROFILE_SOURCE_CONTRACT:
            raise AssemblyBaseProfileError("Assembly success checkpoint source contract is invalid")
        raw_hashes = metadata.get("seen_provider_hashes")
        if not isinstance(raw_hashes, dict) or not raw_hashes:
            raise AssemblyBaseProfileError("Assembly success checkpoint lacks provider manifest")
        try:
            expected_total = int(metadata["list_total_count"])
            expected_pages = int(metadata["expected_pages"])
        except (KeyError, TypeError, ValueError):
            raise AssemblyBaseProfileError("Assembly success checkpoint coverage metadata is invalid") from None
        if checkpoint.cursor != str(expected_pages) or len(raw_hashes) != expected_total:
            raise AssemblyBaseProfileError("Assembly success checkpoint coverage is incomplete")

        observations = self.repository.feeder_observations(
            ASSEMBLY_BASE_PROFILE_FEEDER,
            ASSEMBLY_BASE_PROFILE_SCOPE,
        )
        by_key: dict[str, FeederObservation] = {}
        for observation in observations:
            expected_hash = raw_hashes.get(observation.provider_record_key)
            if expected_hash != observation.content_hash:
                continue
            if observation.provider_record_key in by_key:
                raise AssemblyBaseProfileError(
                    "Assembly success manifest maps one provider key to multiple observations"
                )
            by_key[observation.provider_record_key] = observation
        if set(by_key) != set(raw_hashes):
            raise AssemblyBaseProfileError("Assembly success manifest lacks committed observations")
        return run.id, tuple(by_key[key] for key in sorted(by_key))

    def publish_latest_successful(self) -> AssemblyBaseProfileRunResult:
        run_id, observations = self._latest_successful_observations()
        contexts = self.repository.assembly_base_profile_contexts(
            [observation.id for observation in observations]
        )
        missing_field_counts = {item.name: 0 for item in ASSEMBLY_BASE_PROFILE_FIELDS}
        skipped: list[UUID] = []
        pending: list[
            tuple[Person, FeederObservation, tuple[Claim, ...], tuple[ClaimEvidence, ...]]
        ] = []
        observations_published = 0
        published_claims = 0
        unchanged_claims = 0
        existing_ids = {
            claim.id
            for claim in self.repository.claims(
                published_only=True,
                current_only=True,
            )
        }

        for observation in observations:
            context = contexts.get(observation.id)
            if context is None:
                skipped.append(observation.id)
                continue
            person, source, policy = context
            if person.identity_status != IdentityStatus.RESOLVED:
                raise AssemblyBaseProfileError(
                    "Assembly base profile link does not resolve to a canonical Person"
                )

            bundle = build_assembly_base_profile_bundle(
                person,
                observation,
                source=source,
                policy=policy,
            )
            for field_name in bundle.missing_fields:
                missing_field_counts[field_name] += 1
            observations_published += 1
            if not bundle.claims:
                continue
            if all(claim.id in existing_ids for claim in bundle.claims):
                published_claims += len(bundle.claims)
                unchanged_claims += len(bundle.claims)
                continue
            pending.append((person, observation, bundle.claims, bundle.evidence))

        stored = self.repository.import_assembly_base_profile_claims_batch(pending)
        published_claims += len(stored)
        unchanged_claims += sum(item.id in existing_ids for item in stored)

        return AssemblyBaseProfileRunResult(
            run_id=run_id,
            observations_considered=len(observations),
            observations_published=observations_published,
            published_claims=published_claims,
            unchanged_claims=unchanged_claims,
            missing_field_counts={
                key: value for key, value in missing_field_counts.items() if value
            },
            skipped_observation_ids=tuple(skipped),
        )


def is_assembly_base_profile_field(name: str) -> bool:
    return name in _ASSEMBLY_BASE_PROFILE_FIELD_NAMES
