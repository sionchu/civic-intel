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
from packages.verification.claims import validate_claim_publication
from packages.verification.policy import PolicyAction, require_policy

if TYPE_CHECKING:
    from packages.persistence.repository import SqlAlchemyRepository


ASSEMBLY_LEGISLATIVE_FEEDER = "national_assembly_bill_participation"
ASSEMBLY_LEGISLATIVE_SEMANTIC_SCOPE = "legislative_bill_participation"
ASSEMBLY_LEGISLATIVE_SOURCE_CONTRACT = "assembly_term_bill_participation"
ASSEMBLY_LEGISLATIVE_PARTICIPATION_PREDICATE = "ASSEMBLY_BILL_PARTICIPATION"
_ASSEMBLY_LEGISLATIVE_CLAIM_NAMESPACE = UUID("f269f4db-6504-4a38-a0f5-bb36e7b4c1a6")


class AssemblyLegislativeActivityError(ValueError):
    pass


@dataclass(frozen=True)
class AssemblyLegislativeActivityBundle:
    claims: tuple[Claim, ...]
    evidence: tuple[ClaimEvidence, ...]


@dataclass(frozen=True)
class AssemblyLegislativeActivityPublicationResult:
    run_id: UUID
    observations_considered: int
    observations_published: int
    published_claims: int
    unchanged_claims: int
    unresolved_member_codes: tuple[str, ...] = ()


def _required_text(normalized: dict[str, object], key: str) -> str:
    value = normalized.get(key)
    if not isinstance(value, str) or not value.strip():
        raise AssemblyLegislativeActivityError(f"bill observation field {key} is missing")
    return value.strip()


def _optional_text(normalized: dict[str, object], key: str) -> str | None:
    value = normalized.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise AssemblyLegislativeActivityError(f"bill observation field {key} is invalid")
    value = value.strip()
    return value or None


def _code_list(normalized: dict[str, object], key: str) -> tuple[str, ...]:
    value = normalized.get(key)
    if not isinstance(value, list) or any(
        not isinstance(item, str) or not item.strip() for item in value
    ):
        raise AssemblyLegislativeActivityError(f"bill observation field {key} is invalid")
    codes = tuple(sorted({item.strip() for item in value}))
    if len(codes) != len(value):
        raise AssemblyLegislativeActivityError(f"bill observation field {key} contains duplicates")
    return codes


def _qualifier_values(
    observation: FeederObservation,
    *,
    participation_role: str,
    mona_cd: str,
) -> dict[str, str]:
    normalized = observation.normalized
    values: dict[str, str] = {
        "source_contract": ASSEMBLY_LEGISLATIVE_SOURCE_CONTRACT,
        "source_scope": observation.scope_key,
        "semantic_scope": observation.semantic_scope,
        "provider_record_key": observation.provider_record_key,
        "immutable_observation_hash": observation.content_hash,
        "bill_id": _required_text(normalized, "bill_id"),
        "assembly_age": str(normalized.get("assembly_age", "")),
        "provider_identity_namespace": "assembly_mona_cd",
        "provider_person_key": mona_cd,
        "participation_role": participation_role,
    }
    for key in (
        "bill_no",
        "proposed_date",
        "committee",
        "committee_id",
        "process_result",
        "detail_url",
    ):
        value = _optional_text(normalized, key)
        if value is not None:
            values[key] = value
    return values


def _claim_id(
    person: Person,
    observation: FeederObservation,
    *,
    participation_role: str,
    mona_cd: str,
) -> UUID:
    return uuid5(
        _ASSEMBLY_LEGISLATIVE_CLAIM_NAMESPACE,
        "|".join(
            (
                str(person.id),
                observation.provider_record_key,
                observation.content_hash,
                participation_role,
                mona_cd,
            )
        ),
    )


def build_assembly_legislative_activity_bundle(
    person: Person,
    observation: FeederObservation,
    *,
    source: Source,
    policy: SourcePolicy,
    participation_role: str,
    mona_cd: str,
) -> AssemblyLegislativeActivityBundle:
    """Build one exact person/bill participation Claim without reading names from the provider."""

    if person.identity_status != IdentityStatus.RESOLVED:
        raise AssemblyLegislativeActivityError(
            "Assembly legislative activity requires a resolved Person"
        )
    if (
        observation.feeder != ASSEMBLY_LEGISLATIVE_FEEDER
        or observation.semantic_scope != ASSEMBLY_LEGISLATIVE_SEMANTIC_SCOPE
        or not observation.scope_key.startswith("assembly_age:")
    ):
        raise AssemblyLegislativeActivityError(
            "observation is outside the Assembly legislative-activity scope"
        )
    if source.policy_id != policy.id:
        raise AssemblyLegislativeActivityError("Assembly activity SourcePolicy does not match Source")
    require_policy(policy, PolicyAction.STORE_METADATA)
    normalized = observation.normalized
    bill_id = _required_text(normalized, "bill_id")
    if bill_id != observation.provider_record_key:
        raise AssemblyLegislativeActivityError("bill provider identity does not match observation key")
    if normalized.get("participation_semantics") != "official_code_linked_bill_participation":
        raise AssemblyLegislativeActivityError("bill observation participation semantics are invalid")
    if participation_role not in {"REPRESENTATIVE_PROPOSER", "CO_PROPOSER"}:
        raise AssemblyLegislativeActivityError("unsupported Assembly bill participation role")
    if not mona_cd.strip():
        raise AssemblyLegislativeActivityError("Assembly provider Person identity is missing")
    representative_codes = _code_list(normalized, "representative_proposer_codes")
    co_codes = _code_list(normalized, "co_proposer_codes")
    if set(representative_codes) & set(co_codes):
        raise AssemblyLegislativeActivityError(
            "Assembly bill observation assigns one MONA_CD to both participation roles"
        )
    expected_codes = (
        representative_codes if participation_role == "REPRESENTATIVE_PROPOSER" else co_codes
    )
    if mona_cd not in expected_codes:
        raise AssemblyLegislativeActivityError(
            "Assembly bill participation role does not contain the exact MONA_CD"
        )

    claim_id = _claim_id(
        person,
        observation,
        participation_role=participation_role,
        mona_cd=mona_cd,
    )
    bill_name = _required_text(normalized, "bill_name")
    role_label = "대표 발의자" if participation_role == "REPRESENTATIVE_PROPOSER" else "공동 발의자"
    claim = Claim(
        id=claim_id,
        person_id=person.id,
        proposition=(
            f"{person.canonical_name}는 국회 의안정보에서 「{bill_name}」의 {role_label}로 "
            "기록되어 있다."
        ),
        subject=person.canonical_name,
        predicate=ASSEMBLY_LEGISLATIVE_PARTICIPATION_PREDICATE,
        object_text=bill_name,
        qualifiers=_qualifier_values(
            observation,
            participation_role=participation_role,
            mona_cd=mona_cd,
        ),
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
    gate = validate_claim_publication(claim, person, [evidence], {source.id: source}, {policy.id: policy})
    if not gate.publishable:
        raise AssemblyLegislativeActivityError(
            f"Assembly legislative activity Claim failed publication gate: {gate.failures}"
        )
    return AssemblyLegislativeActivityBundle((claim,), (evidence,))


class AssemblyLegislativeActivityPublisher:
    """Publish only the exact manifest of the latest successful bill enumeration."""

    def __init__(self, repository: SqlAlchemyRepository) -> None:
        self.repository = repository

    def _latest_successful_observations(
        self,
    ) -> tuple[UUID, tuple[FeederObservation, ...]]:
        checkpoint = self.repository.source_checkpoint(
            ASSEMBLY_LEGISLATIVE_FEEDER,
            self._scope_key_from_checkpoint(),
        )
        if checkpoint is None or checkpoint.last_run_id is None:
            raise AssemblyLegislativeActivityError(
                "Assembly legislative success checkpoint is unavailable"
            )
        run = self.repository.source_run(checkpoint.last_run_id)
        if (
            run is None
            or run.status != SourceRunStatus.SUCCESS
            or run.feeder != ASSEMBLY_LEGISLATIVE_FEEDER
            or run.scope_key != checkpoint.scope_key
        ):
            raise AssemblyLegislativeActivityError(
                "Assembly legislative activity requires the latest successful full enumeration"
            )
        metadata = checkpoint.metadata
        if metadata.get("source_contract") != ASSEMBLY_LEGISLATIVE_SOURCE_CONTRACT:
            raise AssemblyLegislativeActivityError(
                "Assembly legislative checkpoint source contract is invalid"
            )
        raw_hashes = metadata.get("seen_provider_hashes")
        if not isinstance(raw_hashes, dict):
            raise AssemblyLegislativeActivityError(
                "Assembly legislative checkpoint lacks provider manifest"
            )
        try:
            expected_total = int(metadata["list_total_count"])
            expected_pages = int(metadata["expected_pages"])
        except (KeyError, TypeError, ValueError):
            raise AssemblyLegislativeActivityError(
                "Assembly legislative checkpoint coverage metadata is invalid"
            ) from None
        if checkpoint.cursor != str(expected_pages) or len(raw_hashes) != expected_total:
            raise AssemblyLegislativeActivityError(
                "Assembly legislative checkpoint coverage is incomplete"
            )
        observations = self.repository.feeder_observations(
            ASSEMBLY_LEGISLATIVE_FEEDER,
            checkpoint.scope_key,
        )
        by_key: dict[str, FeederObservation] = {}
        for observation in observations:
            expected_hash = raw_hashes.get(observation.provider_record_key)
            if expected_hash != observation.content_hash:
                continue
            if observation.provider_record_key in by_key:
                raise AssemblyLegislativeActivityError(
                    "Assembly legislative manifest maps one provider key to multiple observations"
                )
            by_key[observation.provider_record_key] = observation
        if set(by_key) != set(raw_hashes):
            raise AssemblyLegislativeActivityError(
                "Assembly legislative manifest lacks committed observations"
            )
        return run.id, tuple(by_key[key] for key in sorted(by_key))

    def _scope_key_from_checkpoint(self) -> str:
        checkpoints = self.repository.source_checkpoints(ASSEMBLY_LEGISLATIVE_FEEDER)
        if len(checkpoints) != 1:
            raise AssemblyLegislativeActivityError(
                "Assembly legislative activity requires exactly one bounded scope checkpoint"
            )
        return checkpoints[0].scope_key

    def publish_latest_successful(self) -> AssemblyLegislativeActivityPublicationResult:
        run_id, observations = self._latest_successful_observations()
        contexts = self.repository.assembly_legislative_source_contexts(
            [observation.id for observation in observations]
        )
        member_codes = sorted(
            {
                code
                for observation in observations
                for key in ("representative_proposer_codes", "co_proposer_codes")
                for code in _code_list(observation.normalized, key)
            }
        )
        people_by_code = self.repository.assembly_current_person_contexts(member_codes)
        unresolved = sorted(set(member_codes) - set(people_by_code))
        pending: list[
            tuple[Person, FeederObservation, tuple[Claim, ...], tuple[ClaimEvidence, ...]]
        ] = []
        observations_published = 0
        for observation in observations:
            context = contexts.get(observation.id)
            if context is None:
                raise AssemblyLegislativeActivityError(
                    "Assembly legislative observation provenance is incomplete"
                )
            source, policy = context
            normalized = observation.normalized
            for role, field_name in (
                ("REPRESENTATIVE_PROPOSER", "representative_proposer_codes"),
                ("CO_PROPOSER", "co_proposer_codes"),
            ):
                for mona_cd in _code_list(normalized, field_name):
                    person = people_by_code.get(mona_cd)
                    if person is None:
                        continue
                    bundle = build_assembly_legislative_activity_bundle(
                        person,
                        observation,
                        source=source,
                        policy=policy,
                        participation_role=role,
                        mona_cd=mona_cd,
                    )
                    pending.append((person, observation, bundle.claims, bundle.evidence))
                    observations_published += 1

        existing_before = {
            claim.id
            for person in people_by_code.values()
            for claim in self.repository.claims(
                person_id=person.id,
                published_only=True,
                current_only=True,
            )
        }
        stored = self.repository.import_assembly_legislative_claims_batch(pending)
        # The repository returns stored Claims for both new and idempotent operations. The
        # deterministic IDs plus the pre-write set make the receipt counts meaningful.
        requested_ids = {claim.id for _, _, claims, _ in pending for claim in claims}
        unchanged_claims = len(existing_before & requested_ids) if requested_ids else 0
        return AssemblyLegislativeActivityPublicationResult(
            run_id=run_id,
            observations_considered=len(observations),
            observations_published=observations_published,
            published_claims=len(stored) - unchanged_claims,
            unchanged_claims=unchanged_claims,
            unresolved_member_codes=tuple(unresolved),
        )
