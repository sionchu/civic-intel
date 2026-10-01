from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid5

from packages.domain.contracts import (
    Claim,
    ClaimEvidence,
    FeederObservation,
    Person,
    Source,
    SourcePolicy,
)
from packages.domain.enums import EpistemicStatus, EvidenceStance, IdentityStatus, PublicationStatus
from packages.verification.claims import validate_claim_publication
from packages.verification.policy import PolicyAction, require_policy

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
    person: Person, observation: FeederObservation, *, source: Source, policy: SourcePolicy
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
        if raw_value is None or (isinstance(raw_value, str) and (not raw_value.strip())):
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
            claim, person, [item], {source.id: source}, {policy.id: policy}
        )
        if not gate.publishable:
            raise AssemblyBaseProfileError(
                f"Assembly base profile Claim failed publication gate: {gate.failures}"
            )
        claims.append(claim)
        evidence.append(item)
    return AssemblyBaseProfileBundle(tuple(claims), tuple(evidence), tuple(missing_fields))


def is_assembly_base_profile_field(name: str) -> bool:
    return name in _ASSEMBLY_BASE_PROFILE_FIELD_NAMES
