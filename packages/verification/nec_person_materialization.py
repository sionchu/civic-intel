from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from uuid import UUID, uuid5

from packages.connectors.nec_local_elections import (
    LOCAL_ELECTION_TYPES,
    NecCandidateConnector,
)
from packages.connectors.nec_local_elections import (
    POLICY_ID as NEC_POLICY_ID,
)
from packages.domain.contracts import (
    Claim,
    ClaimEvidence,
    FeederObservation,
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
from packages.verification.policy import PolicyAction, PolicyDenied, require_policy

NEC_CANDIDATE_FEEDER = "nec_local_election_candidates"
NEC_CANDIDATE_SEMANTIC_SCOPE = "local_election_candidacy"
NEC_CANDIDATE_SOURCE_CONTRACT = "nec_local_election_candidate_roster"
NEC_CANDIDACY_PREDICATE = "NEC_LOCAL_ELECTION_CANDIDACY"

NEC_SOURCE_PERSON_NAMESPACE = UUID("ca0b494d-4377-59b7-b155-2a2042cc8835")
NEC_SOURCE_LINK_NAMESPACE = UUID("169d7dfb-a183-58ab-bfb7-9d682e4ca5ca")
NEC_SOURCE_CLAIM_NAMESPACE = UUID("b537d8af-eb70-5653-9f88-fe5473b9ea8c")
NEC_SOURCE_EVIDENCE_NAMESPACE = UUID("52013a32-2d3d-5ce8-bc88-6e0fef329845")


class NecPersonMaterializationError(ValueError):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


@dataclass(frozen=True)
class NecCandidateSourceContext:
    observation: FeederObservation
    source: Source
    election_id: str
    election_type: int
    candidate_id: str
    canonical_name: str
    birth_date: date
    jurisdiction: str


@dataclass(frozen=True)
class NecPersonMaterializationPacket:
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


def _required_text(normalized: dict, key: str) -> str:
    value = normalized.get(key)
    text = value.strip() if isinstance(value, str) else ""
    if not text:
        raise NecPersonMaterializationError(
            "IDENTITY_ANCHOR_MISSING", f"NEC candidate row lacks {key}"
        )
    return text


def validate_nec_candidate_source_context(
    observation: FeederObservation,
    *,
    snapshot: SourceSnapshot,
    source: Source,
    policy: SourcePolicy,
    checkpoint: SourceCheckpoint,
    run: SourceRun,
    versions: tuple[FeederObservation, ...],
) -> NecCandidateSourceContext:
    if (
        observation.feeder != NEC_CANDIDATE_FEEDER
        or observation.semantic_scope != NEC_CANDIDATE_SEMANTIC_SCOPE
    ):
        raise NecPersonMaterializationError(
            "SOURCE_SCOPE_CONFLICT", "observation is outside the NEC candidate contract"
        )
    try:
        require_policy(policy, PolicyAction.STORE_METADATA)
        query = NecCandidateConnector._validated_query(str(source.url))
    except (PolicyDenied, ValueError) as exc:
        raise NecPersonMaterializationError("PROVENANCE_CONFLICT", str(exc)) from exc
    if (
        policy.id != NEC_POLICY_ID
        or policy.domain != NecCandidateConnector.HOST
        or source.policy_id != policy.id
        or snapshot.source_id != source.id
        or snapshot.fulltext is not None
        or snapshot.metadata.get("service_name")
        != "getPofelcddRegistSttusInfoInqire"
    ):
        raise NecPersonMaterializationError(
            "PROVENANCE_CONFLICT", "NEC candidate provenance is outside the reviewed API contract"
        )

    normalized = observation.normalized
    candidate_id = _required_text(normalized, "candidate_id")
    canonical_name = _required_text(normalized, "canonical_name")
    election_id = _required_text(normalized, "election_id")
    if candidate_id != observation.provider_record_key:
        raise NecPersonMaterializationError(
            "PROVIDER_IDENTITY_CONFLICT", "huboid differs from provider_record_key"
        )
    election_type_raw = normalized.get("election_type")
    if isinstance(election_type_raw, int):
        election_type = election_type_raw
    elif isinstance(election_type_raw, str) and election_type_raw.isdigit():
        election_type = int(election_type_raw)
    else:
        raise NecPersonMaterializationError(
            "IDENTITY_ANCHOR_MISSING", "NEC candidate row lacks a valid election_type"
        )
    if election_type not in LOCAL_ELECTION_TYPES:
        raise NecPersonMaterializationError(
            "SOURCE_SCOPE_CONFLICT", "NEC candidate election type is unsupported"
        )
    if observation.scope_key != f"{election_id}:{election_type}":
        raise NecPersonMaterializationError(
            "SOURCE_SCOPE_CONFLICT", "NEC candidate scope key is inconsistent"
        )
    if (
        query.get("sgId") != election_id
        or query.get("sgTypecode") != str(election_type)
        or snapshot.metadata.get("election_id") != election_id
        or snapshot.metadata.get("election_type") != str(election_type)
    ):
        raise NecPersonMaterializationError(
            "SOURCE_SCOPE_CONFLICT", "NEC source URL/snapshot differs from observation scope"
        )

    birth_text = _required_text(normalized, "birth_date")
    try:
        birth_date = date.fromisoformat(birth_text)
    except ValueError:
        raise NecPersonMaterializationError(
            "IDENTITY_ANCHOR_MISSING", "NEC candidate birth_date is invalid"
        ) from None
    province = _required_text(normalized, "province")
    district = _required_text(normalized, "district")
    municipality = normalized.get("municipality")
    jurisdiction = "/".join(
        value
        for value in (
            province,
            municipality.strip() if isinstance(municipality, str) else "",
            district,
        )
        if value
    )

    metadata = checkpoint.metadata
    hashes = metadata.get("seen_provider_hashes")
    try:
        total_count = int(metadata["total_count"])
        expected_pages = int(metadata["expected_pages"])
        page_size = int(metadata["page_size"])
    except (KeyError, TypeError, ValueError):
        raise NecPersonMaterializationError(
            "CHECKPOINT_CONFLICT", "NEC candidate checkpoint coverage metadata is invalid"
        ) from None

    expected_pages_from_total = max(1, (total_count + page_size - 1) // page_size)
    resume_mode = run.metadata.get("resume") is True
    if resume_mode:
        try:
            prior_pages = int(run.checkpoint_before or "0")
        except (TypeError, ValueError):
            raise NecPersonMaterializationError(
                "CHECKPOINT_CONFLICT", "NEC resume checkpoint cursor is invalid"
            ) from None
        prior_seen = min(prior_pages * page_size, total_count)
        run_coverage_complete = (
            0 <= prior_pages < expected_pages
            and prior_seen + run.records_seen == total_count
        )
    else:
        run_coverage_complete = run.records_seen == total_count

    if (
        checkpoint.feeder != NEC_CANDIDATE_FEEDER
        or checkpoint.scope_key != observation.scope_key
        or checkpoint.last_run_id != run.id
        or run.status != SourceRunStatus.SUCCESS
        or run.feeder != NEC_CANDIDATE_FEEDER
        or run.scope_key != observation.scope_key
        or not run_coverage_complete
        or run.checkpoint_after != checkpoint.cursor
        or run.metadata.get("source_contract") != NEC_CANDIDATE_SOURCE_CONTRACT
        or run.metadata.get("election_id") != election_id
        or run.metadata.get("election_type") != election_type
        or metadata.get("source_contract") != NEC_CANDIDATE_SOURCE_CONTRACT
        or metadata.get("election_id") != election_id
        or metadata.get("election_type") != election_type
        or not isinstance(hashes, dict)
        or len(hashes) != total_count
        or hashes.get(candidate_id) != observation.content_hash
        or expected_pages != expected_pages_from_total
        or checkpoint.cursor != str(expected_pages)
        or not 1 <= page_size <= 100
    ):
        raise NecPersonMaterializationError(
            "CHECKPOINT_CONFLICT",
            "NEC candidate observation is not in the exact complete SUCCESS checkpoint",
        )

    if {item.content_hash for item in versions} != {observation.content_hash}:
        raise NecPersonMaterializationError(
            "HISTORICAL_VERSION_DRIFT",
            "NEC candidate provider record has multiple historical content versions",
        )

    return NecCandidateSourceContext(
        observation=observation,
        source=source,
        election_id=election_id,
        election_type=election_type,
        candidate_id=candidate_id,
        canonical_name=canonical_name,
        birth_date=birth_date,
        jurisdiction=jurisdiction,
    )


def person_id_for_nec_source_context(context: NecCandidateSourceContext) -> UUID:
    return uuid5(
        NEC_SOURCE_PERSON_NAMESPACE,
        f"{context.election_id}|{context.candidate_id}",
    )


def build_nec_source_context_packet(
    context: NecCandidateSourceContext,
) -> NecPersonMaterializationPacket:
    observation = context.observation
    person_id = person_id_for_nec_source_context(context)
    effective_at = observation.provider_observed_at or observation.recorded_at
    normalized = observation.normalized
    type_name = LOCAL_ELECTION_TYPES[context.election_type]

    person = Person(
        id=person_id,
        canonical_name=context.canonical_name,
        birth_date=context.birth_date,
        identity_status=IdentityStatus.REVIEW,
        valid_from=effective_at,
        recorded_at=observation.recorded_at,
    )
    link = PersonObservationLink(
        id=uuid5(NEC_SOURCE_LINK_NAMESPACE, f"{person_id}|{observation.id}"),
        person_id=person_id,
        observation_id=observation.id,
        action=MaterializationAction.AUTO_CREATE,
        decision_class=MaterializationDecisionClass.DETERMINISTIC_SOURCE_CONTEXT,
        linked_at=observation.recorded_at,
    )
    claim_id = uuid5(
        NEC_SOURCE_CLAIM_NAMESPACE,
        f"{person_id}|{observation.id}|{observation.content_hash}",
    )
    object_text = f"{type_name} 후보 · {context.jurisdiction}"
    qualifiers = {
        "candidate_id": context.candidate_id,
        "election_id": context.election_id,
        "election_type": str(context.election_type),
        "election_type_name": type_name,
        "jurisdiction": context.jurisdiction,
        "source_contract": NEC_CANDIDATE_SOURCE_CONTRACT,
        "source_observation_id": str(observation.id),
        "immutable_observation_hash": observation.content_hash,
        "identity_scope": "DETERMINISTIC_NEC_CANDIDACY_SOURCE_CONTEXT",
    }
    for key in ("party", "candidate_number", "candidate_sub_number", "registration_status"):
        value = normalized.get(key)
        if isinstance(value, str) and value.strip():
            qualifiers[key] = value.strip()

    claim = Claim(
        id=claim_id,
        person_id=person_id,
        subject=context.canonical_name,
        predicate=NEC_CANDIDACY_PREDICATE,
        proposition=(
            f"중앙선거관리위원회 후보자 정보는 {context.canonical_name}을 "
            f"{context.jurisdiction} {type_name} 후보로 기재한다."
        ),
        object_text=object_text,
        qualifiers=qualifiers,
        epistemic_status=EpistemicStatus.CLAIM,
        publication_status=PublicationStatus.DRAFT,
        asserted_as_true=False,
        valid_from=effective_at,
        recorded_at=observation.recorded_at,
    )
    evidence = ClaimEvidence(
        id=uuid5(
            NEC_SOURCE_EVIDENCE_NAMESPACE,
            f"{claim_id}|{context.source.id}|{observation.snapshot_id}|{observation.id}",
        ),
        claim_id=claim_id,
        source_id=context.source.id,
        snapshot_id=observation.snapshot_id,
        feeder_observation_id=observation.id,
        stance=EvidenceStance.SUPPORT,
    )
    return NecPersonMaterializationPacket(person=person, link=link, claim=claim, evidence=evidence)
