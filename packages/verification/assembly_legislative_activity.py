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
from packages.domain.enums import (
    EpistemicStatus,
    EvidenceStance,
    IdentityStatus,
    PublicationStatus,
)
from packages.verification.claims import validate_claim_publication
from packages.verification.policy import PolicyAction, require_policy

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
    observation: FeederObservation, *, participation_role: str, mona_cd: str
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
    person: Person, observation: FeederObservation, *, participation_role: str, mona_cd: str
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
        or (not observation.scope_key.startswith("assembly_age:"))
    ):
        raise AssemblyLegislativeActivityError(
            "observation is outside the Assembly legislative-activity scope"
        )
    if source.policy_id != policy.id:
        raise AssemblyLegislativeActivityError(
            "Assembly activity SourcePolicy does not match Source"
        )
    require_policy(policy, PolicyAction.STORE_METADATA)
    normalized = observation.normalized
    bill_id = _required_text(normalized, "bill_id")
    if bill_id != observation.provider_record_key:
        raise AssemblyLegislativeActivityError(
            "bill provider identity does not match observation key"
        )
    if normalized.get("participation_semantics") != "official_code_linked_bill_participation":
        raise AssemblyLegislativeActivityError(
            "bill observation participation semantics are invalid"
        )
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
        person, observation, participation_role=participation_role, mona_cd=mona_cd
    )
    bill_name = _required_text(normalized, "bill_name")
    role_label = "대표 발의자" if participation_role == "REPRESENTATIVE_PROPOSER" else "공동 발의자"
    claim = Claim(
        id=claim_id,
        person_id=person.id,
        proposition=f"{person.canonical_name}는 국회 의안정보에서 「{bill_name}」의 {role_label}로 기록되어 있다.",
        subject=person.canonical_name,
        predicate=ASSEMBLY_LEGISLATIVE_PARTICIPATION_PREDICATE,
        object_text=bill_name,
        qualifiers=_qualifier_values(
            observation, participation_role=participation_role, mona_cd=mona_cd
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
    gate = validate_claim_publication(
        claim, person, [evidence], {source.id: source}, {policy.id: policy}
    )
    if not gate.publishable:
        raise AssemblyLegislativeActivityError(
            f"Assembly legislative activity Claim failed publication gate: {gate.failures}"
        )
    return AssemblyLegislativeActivityBundle((claim,), (evidence,))
