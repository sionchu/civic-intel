from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid5

from packages.domain.contracts import (
    Claim,
    ClaimEvidence,
    FeederObservation,
    Organization,
    Person,
    PersonObservationLink,
    Source,
    SourceCheckpoint,
    SourcePolicy,
    SourceRun,
    SourceSnapshot,
)
from packages.domain.enums import (
    EpistemicStatus,
    EvidenceStance,
    IdentityStatus,
    MaterializationAction,
    MaterializationDecisionClass,
    PublicationStatus,
    SourceRunStatus,
)
from packages.rendering.alio_organization_content import (
    ALIO_EXECUTIVE_FEEDER,
    ALIO_EXECUTIVE_PREDICATE,
    ALIO_EXECUTIVE_SCOPE,
    ALIO_EXECUTIVE_SOURCE_CONTRACT,
    validate_alio_item4_observation,
)
from packages.verification.policy import PolicyAction, PolicyDenied, require_policy

PERSON_ROLE_PREDICATE = "ALIO_REVIEWED_PERSON_ROLE"
ALIO_SOURCE_PERSON_NAMESPACE = UUID("0c58801e-a5c9-5bb1-8b26-e1f65e7d71aa")
ALIO_SOURCE_ROLE_CLAIM_NAMESPACE = UUID("3f5cbeb6-ea96-559e-a423-2093d15c37ee")
ALIO_SOURCE_LINK_NAMESPACE = UUID("f729a1a9-f6f0-5c22-ad18-837e6c357639")
ALIO_SOURCE_EVIDENCE_NAMESPACE = UUID("a4283ad7-0127-5442-998c-728a6f161c54")


class AlioPersonMaterializationError(ValueError):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


@dataclass(frozen=True)
class AlioPersonSourceContext:
    observation: FeederObservation
    fields: dict[str, str]
    organization: Organization
    source: Source


@dataclass(frozen=True)
class AlioPersonMaterializationPacket:
    person: Person
    link: PersonObservationLink
    claim: Claim
    evidence: ClaimEvidence

    def ids(self) -> dict[str, str]:
        return {
            "person_id": str(self.person.id),
            "link_id": str(self.link.id),
            "claim_id": str(self.claim.id),
            "evidence_id": str(self.evidence.id),
        }


def validate_alio_person_source_context(
    observation: FeederObservation,
    *,
    snapshot: SourceSnapshot,
    source: Source,
    policy: SourcePolicy,
    checkpoint: SourceCheckpoint,
    run: SourceRun,
    versions: tuple[FeederObservation, ...],
    organization_claims: tuple[Claim, ...],
    organization: Organization | None,
) -> AlioPersonSourceContext:
    try:
        fields = validate_alio_item4_observation(
            observation,
            snapshot=snapshot,
            source=source,
            policy=policy,
        )
        require_policy(policy, PolicyAction.STORE_METADATA)
    except (PolicyDenied, ValueError) as exc:
        raise AlioPersonMaterializationError("PROVENANCE_CONFLICT", str(exc)) from exc
    if fields["name_status"] != "PUBLIC":
        raise AlioPersonMaterializationError(
            "NO_PUBLIC_PERSON",
            "ALIO row does not expose a public person name",
        )

    metadata = checkpoint.metadata
    provider_hashes = metadata.get("seen_provider_hashes")
    current_disclosures = metadata.get("seen_current_disclosures")
    if (
        checkpoint.feeder != ALIO_EXECUTIVE_FEEDER
        or checkpoint.scope_key != ALIO_EXECUTIVE_SCOPE
        or checkpoint.last_run_id != run.id
        or run.status != SourceRunStatus.SUCCESS
        or run.feeder != observation.feeder
        or run.scope_key != observation.scope_key
        or run.checkpoint_after != checkpoint.cursor
        or metadata.get("source_contract") != ALIO_EXECUTIVE_SOURCE_CONTRACT
        or not isinstance(provider_hashes, dict)
        or provider_hashes.get(observation.provider_record_key) != observation.content_hash
        or not isinstance(current_disclosures, dict)
        or current_disclosures.get(fields["disclosure_no"]) != fields["alio_apba_id"]
    ):
        raise AlioPersonMaterializationError(
            "SOURCE_VERSION_CONFLICT",
            "ALIO observation is not the exact current successful checkpoint version",
        )

    if {item.content_hash for item in versions} != {observation.content_hash}:
        raise AlioPersonMaterializationError(
            "HISTORICAL_VERSION_DRIFT",
            "ALIO provider row has more than one historical content version",
        )

    exact = [
        claim
        for claim in organization_claims
        if claim.predicate == ALIO_EXECUTIVE_PREDICATE
        and claim.organization_id is not None
        and claim.publication_status == PublicationStatus.PUBLISHED
        and claim.superseded_at is None
        and claim.qualifiers.get("source_contract") == ALIO_EXECUTIVE_SOURCE_CONTRACT
    ]
    organization_ids = {claim.organization_id for claim in exact}
    if len(exact) != 1 or len(organization_ids) != 1:
        raise AlioPersonMaterializationError(
            "ORGANIZATION_BINDING_REQUIRED",
            "ALIO row does not resolve to exactly one current published Organization binding",
        )
    expected_id = next(iter(organization_ids))
    if organization is None or organization.id != expected_id:
        raise AlioPersonMaterializationError(
            "ORGANIZATION_BINDING_REQUIRED",
            "ALIO Organization binding target is missing",
        )
    if organization.superseded_at is not None or organization.name != fields["institution_name"]:
        raise AlioPersonMaterializationError(
            "ORGANIZATION_CONFLICT",
            "ALIO institution differs from the current canonical Organization",
        )
    return AlioPersonSourceContext(
        observation=observation,
        fields=fields,
        organization=organization,
        source=source,
    )


def person_id_for_alio_source_context(observation: FeederObservation) -> UUID:
    return uuid5(
        ALIO_SOURCE_PERSON_NAMESPACE,
        f"{observation.provider_record_key}|{observation.content_hash}",
    )


def build_alio_source_context_packet(
    context: AlioPersonSourceContext,
) -> AlioPersonMaterializationPacket:
    observation = context.observation
    fields = context.fields
    organization = context.organization
    source = context.source
    person_id = person_id_for_alio_source_context(observation)
    effective_at = observation.provider_observed_at or observation.recorded_at

    person = Person(
        id=person_id,
        canonical_name=fields["canonical_name"],
        identity_status=IdentityStatus.REVIEW,
        valid_from=effective_at,
        recorded_at=observation.recorded_at,
    )
    link = PersonObservationLink(
        id=uuid5(ALIO_SOURCE_LINK_NAMESPACE, f"{person_id}|{observation.id}"),
        person_id=person_id,
        observation_id=observation.id,
        action=MaterializationAction.AUTO_CREATE,
        decision_class=MaterializationDecisionClass.DETERMINISTIC_SOURCE_CONTEXT,
        linked_at=observation.recorded_at,
    )
    claim_id = uuid5(
        ALIO_SOURCE_ROLE_CLAIM_NAMESPACE,
        f"{person_id}|{observation.id}|{observation.content_hash}",
    )
    claim = Claim(
        id=claim_id,
        person_id=person_id,
        subject=fields["canonical_name"],
        predicate=PERSON_ROLE_PREDICATE,
        proposition=(
            f"{organization.name}의 ALIO 공시는 "
            f"{fields['canonical_name']}을 {fields['position_text']}으로 기재한다."
        ),
        object_text=f"{organization.name} · {fields['position_text']}",
        qualifiers={
            "organization_id": str(organization.id),
            "canonical_name": fields["canonical_name"],
            "position_text": fields["position_text"],
            "as_of": fields["as_of"],
            "source_contract": "alio_reviewed_person_role",
            "source_observation_id": str(observation.id),
            "immutable_observation_hash": observation.content_hash,
            "identity_scope": "DETERMINISTIC_ALIO_SOURCE_CONTEXT",
        },
        epistemic_status=EpistemicStatus.CLAIM,
        publication_status=PublicationStatus.DRAFT,
        asserted_as_true=False,
        valid_from=effective_at,
        recorded_at=observation.recorded_at,
    )
    evidence = ClaimEvidence(
        id=uuid5(
            ALIO_SOURCE_EVIDENCE_NAMESPACE,
            f"{claim_id}|{source.id}|{observation.snapshot_id}|{observation.id}",
        ),
        claim_id=claim_id,
        source_id=source.id,
        snapshot_id=observation.snapshot_id,
        feeder_observation_id=observation.id,
        stance=EvidenceStance.SUPPORT,
    )
    return AlioPersonMaterializationPacket(
        person=person,
        link=link,
        claim=claim,
        evidence=evidence,
    )
