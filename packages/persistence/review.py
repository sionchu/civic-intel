from __future__ import annotations

from datetime import date
from uuid import UUID, uuid5

from sqlalchemy import select
from sqlalchemy.orm import Session

from packages.domain.contracts import (
    Claim,
    ClaimEvidence,
    FeederObservation,
    IdentityReviewItem,
    MaterializationDecision,
    Person,
    PersonObservationLink,
    Source,
    SourcePolicy,
    now_utc,
)
from packages.domain.enums import (
    EpistemicStatus,
    EvidenceStance,
    IdentityReviewStatus,
    IdentityStatus,
    MaterializationAction,
    MaterializationDecisionClass,
    PublicationStatus,
    SourceRunStatus,
)
from packages.persistence.mapping import (
    _claim,
    _evidence,
    _identity_review_item,
    _observation,
    _person,
    _policy,
    _snapshot,
    _source,
    _temporal,
)
from packages.persistence.models import (
    ClaimEvidenceRow,
    ClaimRow,
    FeederObservationRow,
    IdentityReviewItemRow,
    PersonObservationLinkRow,
    PersonRow,
    SourceCheckpointRow,
    SourcePolicyRow,
    SourceRow,
    SourceRunRow,
    SourceSnapshotRow,
)
from packages.verification.assembly_base_profile import (
    ASSEMBLY_BASE_PROFILE_FEEDER,
    ASSEMBLY_BASE_PROFILE_SCOPE,
    ASSEMBLY_BASE_PROFILE_SEMANTIC_SCOPE,
    ASSEMBLY_BASE_PROFILE_SOURCE_CONTRACT,
)
from packages.verification.assembly_provenance import validate_assembly_member_provenance
from packages.verification.claims import validate_claim_publication
from packages.verification.materialization import MaterializationError, MaterializationResult

_ASSEMBLY_REVIEWED_ROLE_CLAIM_NAMESPACE = UUID("a1e9f24f-4c9b-4f8a-9c7b-2d6c2a8de5f1")


def _assembly_reviewed_role_claim_id(
    review_item_id: UUID, person_id: UUID, observation: FeederObservation
) -> UUID:
    return uuid5(
        _ASSEMBLY_REVIEWED_ROLE_CLAIM_NAMESPACE,
        "|".join(
            (str(review_item_id), str(person_id), str(observation.id), observation.content_hash)
        ),
    )


def _assembly_reviewed_role_qualifiers(observation: FeederObservation) -> dict[str, str]:
    return {
        "source_contract": ASSEMBLY_BASE_PROFILE_SOURCE_CONTRACT,
        "source_scope": observation.scope_key,
        "semantic_scope": observation.semantic_scope,
        "provider_record_key": observation.provider_record_key,
        "immutable_observation_hash": observation.content_hash,
    }


def _build_assembly_reviewed_role_claim(
    person: Person, observation: FeederObservation, source: Source, review_item_id: UUID
) -> tuple[Claim, ClaimEvidence]:
    claim_id = _assembly_reviewed_role_claim_id(review_item_id, person.id, observation)
    claim = Claim(
        id=claim_id,
        person_id=person.id,
        proposition=f"{person.canonical_name}는 국회의원 명부에 등재되어 있다.",
        subject=person.canonical_name,
        predicate="HELD_ROLE",
        object_text="국회의원",
        qualifiers=_assembly_reviewed_role_qualifiers(observation),
        epistemic_status=EpistemicStatus.FACT,
        publication_status=PublicationStatus.PUBLISHED,
        asserted_as_true=True,
        valid_from=observation.recorded_at,
        recorded_at=observation.recorded_at,
    )
    evidence = ClaimEvidence(
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
    return (claim, evidence)


class ReviewRepository:
    def __init__(self, session: Session):
        self._session = session

    def identity_review_items(
        self, status: IdentityReviewStatus | None = None
    ) -> list[IdentityReviewItem]:
        statement = select(IdentityReviewItemRow)
        if status is not None:
            statement = statement.where(IdentityReviewItemRow.status == status.value)
        session = self._session
        rows = session.scalars(statement.order_by(IdentityReviewItemRow.created_at))
        return [_identity_review_item(row) for row in rows]

    def _assembly_review_source_context(
        self, session: Session, observation: FeederObservation
    ) -> tuple[Source, SourcePolicy]:
        snapshot_row = session.get(SourceSnapshotRow, str(observation.snapshot_id))
        if snapshot_row is None:
            raise MaterializationError("Assembly review observation snapshot does not exist")
        source_row = session.get(SourceRow, snapshot_row.source_id)
        if source_row is None:
            raise MaterializationError("Assembly review observation Source does not exist")
        policy_row = session.get(SourcePolicyRow, source_row.policy_id)
        if policy_row is None:
            raise MaterializationError("Assembly review observation SourcePolicy does not exist")
        source = _source(source_row)
        policy = _policy(policy_row)
        validate_assembly_member_provenance(observation, _snapshot(snapshot_row), source, policy)
        return (source, policy)

    @staticmethod
    def _assert_current_assembly_review_observation(
        session: Session, observation: FeederObservation
    ) -> None:
        checkpoint_row = session.scalar(
            select(SourceCheckpointRow).where(
                SourceCheckpointRow.feeder == ASSEMBLY_BASE_PROFILE_FEEDER,
                SourceCheckpointRow.scope_key == ASSEMBLY_BASE_PROFILE_SCOPE,
            )
        )
        if checkpoint_row is None or checkpoint_row.last_run_id is None:
            raise MaterializationError("Assembly review requires a committed roster checkpoint")
        metadata = checkpoint_row.metadata_json
        if (
            not isinstance(metadata, dict)
            or metadata.get("source_contract") != ASSEMBLY_BASE_PROFILE_SOURCE_CONTRACT
        ):
            raise MaterializationError("Assembly review checkpoint source contract is invalid")
        raw_hashes = metadata.get("seen_provider_hashes")
        if not isinstance(raw_hashes, dict):
            raise MaterializationError("Assembly review checkpoint lacks provider manifest")
        try:
            expected_total = int(metadata["list_total_count"])
            expected_pages = int(metadata["expected_pages"])
        except (KeyError, TypeError, ValueError):
            raise MaterializationError(
                "Assembly review checkpoint coverage metadata is invalid"
            ) from None
        if (
            expected_total <= 0
            or expected_pages <= 0
            or checkpoint_row.cursor != str(expected_pages)
            or (len(raw_hashes) != expected_total)
            or (raw_hashes.get(observation.provider_record_key) != observation.content_hash)
        ):
            raise MaterializationError(
                "Assembly review observation is not the current successful roster version"
            )
        run_row = session.get(SourceRunRow, checkpoint_row.last_run_id)
        if (
            run_row is None
            or run_row.status != SourceRunStatus.SUCCESS.value
            or run_row.feeder != ASSEMBLY_BASE_PROFILE_FEEDER
            or (run_row.scope_key != ASSEMBLY_BASE_PROFILE_SCOPE)
            or (run_row.records_seen != expected_total)
        ):
            raise MaterializationError(
                "Assembly review requires the latest successful full roster enumeration"
            )

    @staticmethod
    def _reviewed_assembly_distinct_decision(candidate_person_id: UUID) -> MaterializationDecision:
        return MaterializationDecision(
            action=MaterializationAction.REVIEWED_CREATE,
            decision_class=MaterializationDecisionClass.REVIEWED_DISTINCT_IDENTITY,
            candidate_person_id=candidate_person_id,
            reasons=("operator_reviewed_exact_provider_record_as_distinct_identity",),
        )

    def _existing_assembly_reviewed_result(
        self,
        session: Session,
        review_row: IdentityReviewItemRow,
        observation: FeederObservation,
        source: Source,
        policy: SourcePolicy,
    ) -> MaterializationResult:
        if review_row.candidate_person_id is None:
            raise MaterializationError("resolved Assembly review lacks its candidate Person")
        candidate_person_id = UUID(review_row.candidate_person_id)
        links = list(
            session.scalars(
                select(PersonObservationLinkRow).where(
                    PersonObservationLinkRow.observation_id == str(observation.id),
                    PersonObservationLinkRow.superseded_at.is_(None),
                )
            )
        )
        if len(links) != 1:
            raise MaterializationError(
                "resolved Assembly review does not have exactly one active observation link"
            )
        link = links[0]
        if (
            link.action != MaterializationAction.REVIEWED_CREATE.value
            or link.decision_class != MaterializationDecisionClass.REVIEWED_DISTINCT_IDENTITY.value
            or link.review_item_id != review_row.id
            or (link.person_id == str(candidate_person_id))
        ):
            raise MaterializationError("resolved Assembly review link semantics are invalid")
        person_row = session.get(PersonRow, link.person_id)
        if person_row is None:
            raise MaterializationError("resolved Assembly review Person does not exist")
        person = _person(person_row)
        if person.identity_status != IdentityStatus.RESOLVED or person.superseded_at is not None:
            raise MaterializationError("resolved Assembly review Person is not public")
        expected_claim, expected_evidence = _build_assembly_reviewed_role_claim(
            person, observation, source, UUID(review_row.id)
        )
        claim_id = expected_claim.id
        claim_row = session.get(ClaimRow, str(claim_id))
        if claim_row is None:
            raise MaterializationError("resolved Assembly review role Claim does not exist")
        claim = _claim(claim_row)
        if (
            _person_claim_import_semantics(claim) != _person_claim_import_semantics(expected_claim)
            or claim.valid_from != expected_claim.valid_from
            or claim.recorded_at != expected_claim.recorded_at
            or (claim.superseded_at is not None)
        ):
            raise MaterializationError("resolved Assembly review role Claim semantics are invalid")
        evidence_rows = list(
            session.scalars(
                select(ClaimEvidenceRow).where(ClaimEvidenceRow.claim_id == str(claim.id))
            )
        )
        if len(evidence_rows) != 1:
            raise MaterializationError("resolved Assembly review role Claim evidence is incomplete")
        evidence = _evidence(evidence_rows[0])
        if _evidence_import_semantics([evidence]) != _evidence_import_semantics(
            [expected_evidence]
        ):
            raise MaterializationError("resolved Assembly review evidence provenance is invalid")
        gate = validate_claim_publication(
            claim, person, [evidence], {source.id: source}, {policy.id: policy}
        )
        if not gate.publishable:
            raise MaterializationError(
                f"resolved Assembly review Claim failed publication gate: {gate.failures}"
            )
        return MaterializationResult(
            decision=self._reviewed_assembly_distinct_decision(candidate_person_id),
            person_id=person.id,
            claim_id=claim.id,
            review_item_id=UUID(review_row.id),
            created=False,
        )

    def resolve_assembly_distinct_person_review(
        self, review_item_id: UUID, *, resolution_note: str
    ) -> MaterializationResult:
        """Resolve one exact Assembly DOB conflict as a reviewed distinct Person.

        This is deliberately narrower than the automatic materialization gate. It accepts only
        an existing open Assembly current-roster hard-conflict review, never merges into the
        candidate Person, and commits the new Person, role Claim/Evidence, link and review
        resolution together.
        """
        if not isinstance(resolution_note, str) or not resolution_note.strip():
            raise MaterializationError("Assembly review resolution requires a non-empty note")
        note = resolution_note.strip()
        if len(note) > 1000:
            raise MaterializationError("Assembly review resolution note is too long")
        lowered_note = note.casefold()
        if any(token in lowered_note for token in ("api_key", "authkey", "token=", "password")):
            raise MaterializationError(
                "Assembly review resolution note may not contain credentials"
            )
        session = self._session
        review_row = session.get(IdentityReviewItemRow, str(review_item_id))
        if review_row is None:
            raise MaterializationError("Assembly review item does not exist")
        observation_row = session.get(FeederObservationRow, review_row.observation_id)
        if observation_row is None:
            raise MaterializationError("Assembly review observation does not exist")
        observation = _observation(observation_row)
        if (
            observation.feeder != ASSEMBLY_BASE_PROFILE_FEEDER
            or observation.scope_key != ASSEMBLY_BASE_PROFILE_SCOPE
            or observation.semantic_scope != ASSEMBLY_BASE_PROFILE_SEMANTIC_SCOPE
        ):
            raise MaterializationError("review item is outside the Assembly current-roster scope")
        source, policy = self._assembly_review_source_context(session, observation)
        if review_row.status == IdentityReviewStatus.RESOLVED.value:
            return self._existing_assembly_reviewed_result(
                session, review_row, observation, source, policy
            )
        if review_row.status != IdentityReviewStatus.OPEN.value:
            raise MaterializationError("Assembly review item is not open")
        if review_row.reason_code != MaterializationDecisionClass.EXACT_BIRTH_DATE_CONFLICT.value:
            raise MaterializationError(
                "Assembly distinct resolution accepts only an exact birth-date conflict"
            )
        details = review_row.details_json
        if not isinstance(details, dict) or (
            details.get("action") != MaterializationAction.HARD_CONFLICT.value
            or details.get("feeder") != ASSEMBLY_BASE_PROFILE_FEEDER
            or details.get("provider_record_key") != observation.provider_record_key
        ):
            raise MaterializationError("Assembly review item details do not match its observation")
        if review_row.candidate_person_id is None:
            raise MaterializationError("Assembly exact conflict lacks its candidate Person")
        candidate_person_id = UUID(review_row.candidate_person_id)
        canonical_name = observation.normalized.get("canonical_name")
        provider_member_code = observation.normalized.get("member_code")
        external_ids = observation.identity_hints.get("external_ids")
        if (
            not isinstance(canonical_name, str)
            or not canonical_name.strip()
            or provider_member_code != observation.provider_record_key
            or (not isinstance(external_ids, dict))
            or (external_ids.get("assembly_mona_cd") != observation.provider_record_key)
        ):
            raise MaterializationError(
                "Assembly review observation lacks an exact provider identity contract"
            )
        canonical_name = canonical_name.strip()
        birth_date_value = observation.normalized.get("birth_date")
        if not isinstance(birth_date_value, str) or not birth_date_value.strip():
            raise MaterializationError(
                "Assembly distinct resolution requires an exact observed birth date"
            )
        try:
            birth_date = date.fromisoformat(birth_date_value)
        except ValueError:
            raise MaterializationError("Assembly observation birth date is invalid") from None
        candidate_row = session.get(PersonRow, str(candidate_person_id))
        if candidate_row is None:
            raise MaterializationError("Assembly exact conflict candidate Person does not exist")
        candidate = _person(candidate_row)
        if (
            candidate.identity_status != IdentityStatus.RESOLVED
            or candidate.superseded_at is not None
            or candidate.canonical_name != canonical_name
            or (candidate.birth_date is None)
            or (candidate.birth_date == birth_date)
        ):
            raise MaterializationError(
                "Assembly review no longer represents a current exact birth-date conflict"
            )
        self._assert_current_assembly_review_observation(session, observation)
        provider_links = list(
            session.scalars(
                select(PersonObservationLinkRow)
                .join(
                    FeederObservationRow,
                    FeederObservationRow.id == PersonObservationLinkRow.observation_id,
                )
                .where(
                    FeederObservationRow.feeder == observation.feeder,
                    FeederObservationRow.scope_key == observation.scope_key,
                    FeederObservationRow.provider_record_key == observation.provider_record_key,
                )
            )
        )
        if provider_links:
            raise MaterializationError(
                "Assembly provider record already has a Person observation link"
            )
        person = Person(
            canonical_name=canonical_name,
            birth_date=birth_date,
            identity_status=IdentityStatus.RESOLVED,
            valid_from=observation.recorded_at,
            recorded_at=observation.recorded_at,
        )
        published_claim, evidence = _build_assembly_reviewed_role_claim(
            person, observation, source, review_item_id
        )
        gate = validate_claim_publication(
            published_claim, person, [evidence], {source.id: source}, {policy.id: policy}
        )
        if not gate.publishable:
            raise MaterializationError(
                f"Assembly reviewed Claim failed publication gate: {gate.failures}"
            )
        if session.get(ClaimRow, str(published_claim.id)) is not None:
            raise MaterializationError("Assembly reviewed role Claim ID is already in use")
        link = PersonObservationLink(
            person_id=person.id,
            observation_id=observation.id,
            action=MaterializationAction.REVIEWED_CREATE,
            decision_class=MaterializationDecisionClass.REVIEWED_DISTINCT_IDENTITY,
            review_item_id=review_item_id,
        )
        session.add(
            PersonRow(
                id=str(person.id),
                canonical_name=person.canonical_name,
                birth_date=person.birth_date,
                identity_status=person.identity_status.value,
                **_temporal(person),
            )
        )
        session.flush()
        session.add(
            ClaimRow(
                id=str(published_claim.id),
                person_id=str(published_claim.person_id),
                organization_id=None,
                proposition=published_claim.proposition,
                subject=published_claim.subject,
                predicate=published_claim.predicate,
                object_text=published_claim.object_text,
                qualifiers=published_claim.qualifiers,
                epistemic_status=published_claim.epistemic_status.value,
                publication_status=published_claim.publication_status.value,
                asserted_as_true=published_claim.asserted_as_true,
                resolution_note=published_claim.resolution_note,
                **_temporal(published_claim),
            )
        )
        session.flush()
        session.add(
            ClaimEvidenceRow(
                id=str(evidence.id),
                claim_id=str(evidence.claim_id),
                source_id=str(evidence.source_id),
                snapshot_id=str(evidence.snapshot_id),
                feeder_observation_id=str(evidence.feeder_observation_id),
                stance=evidence.stance.value,
                excerpt=evidence.excerpt,
            )
        )
        session.add(
            PersonObservationLinkRow(
                id=str(link.id),
                person_id=str(link.person_id),
                observation_id=str(link.observation_id),
                action=link.action.value,
                decision_class=link.decision_class.value,
                linked_at=link.linked_at,
                superseded_at=None,
                review_item_id=str(review_item_id),
            )
        )
        resolved_details = dict(details)
        resolved_details.update(
            {
                "resolution_action": MaterializationAction.REVIEWED_CREATE.value,
                "resolution_decision_class": MaterializationDecisionClass.REVIEWED_DISTINCT_IDENTITY.value,
                "resolved_person_id": str(person.id),
                "resolved_observation_hash": observation.content_hash,
            }
        )
        review_row.status = IdentityReviewStatus.RESOLVED.value
        review_row.resolved_at = now_utc()
        review_row.resolution_note = note
        review_row.details_json = resolved_details
        session.flush()
        return MaterializationResult(
            decision=self._reviewed_assembly_distinct_decision(candidate_person_id),
            person_id=person.id,
            claim_id=published_claim.id,
            review_item_id=review_item_id,
            created=True,
        )

    def ensure_materialization_review(
        self, observation: FeederObservation, decision: MaterializationDecision
    ) -> IdentityReviewItem:
        existing = self._session.scalar(
            select(IdentityReviewItemRow).where(
                IdentityReviewItemRow.observation_id == str(observation.id),
                IdentityReviewItemRow.reason_code == decision.decision_class.value,
                IdentityReviewItemRow.status == IdentityReviewStatus.OPEN.value,
            )
        )
        if existing is None:
            review = IdentityReviewItem(
                observation_id=observation.id,
                candidate_person_id=decision.candidate_person_id,
                reason_code=decision.decision_class.value,
                details={
                    "action": decision.action.value,
                    "feeder": observation.feeder,
                    "provider_record_key": observation.provider_record_key,
                    "reasons": list(decision.reasons),
                },
            )
            existing = IdentityReviewItemRow(
                id=str(review.id),
                observation_id=str(review.observation_id),
                candidate_person_id=str(review.candidate_person_id)
                if review.candidate_person_id
                else None,
                reason_code=review.reason_code,
                details_json=review.details,
                status=review.status.value,
                created_at=review.created_at,
                resolved_at=None,
                resolution_note=None,
            )
            self._session.add(existing)
        return _identity_review_item(existing)


from packages.verification.import_semantics import (
    _evidence_import_semantics,
    _person_claim_import_semantics,
)
