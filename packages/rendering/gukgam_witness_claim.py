"""Private in-memory source-listing Claims; no identity or publication authority."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, time
from uuid import UUID, uuid5

from packages.domain.contracts import (
    Claim,
    ClaimEvidence,
    IdentityReviewItem,
    Person,
    PersonObservationLink,
)
from packages.domain.enums import (
    EpistemicStatus,
    EvidenceStance,
    IdentityReviewStatus,
    IdentityStatus,
    MaterializationAction,
    MaterializationDecisionClass,
    PublicationStatus,
)
from packages.rendering.gukgam_witness_review import CurrentGukgamWitnessDocument
from packages.verification.claims import validate_claim_publication
from packages.verification.gukgam_witness_import import GUKGAM_WITNESS_SOURCE_CONTRACT

GUKGAM_WITNESS_LISTING_PREDICATE = "LISTED_IN_GUKGAM_WITNESS_ATTACHMENT"
_NAMESPACE = UUID("1f1a53c2-c20f-4e20-888f-00c97418175b")


class GukgamWitnessClaimError(ValueError):
    pass


@dataclass(frozen=True)
class GukgamWitnessClaimPreparation:
    claim: Claim
    evidence: ClaimEvidence
    packet_hash: str
    observation_hash: str
    attachment_sha256: str
    identity_link_id: UUID
    identity_review_id: UUID

    def to_dict(self) -> dict[str, object]:
        """Operational stdout excludes names, source-row fields and review notes."""
        return {
            "status": "DRAFT_PREPARED_IN_MEMORY",
            "person_id": str(self.claim.person_id),
            "claim_id": str(self.claim.id),
            "evidence_id": str(self.evidence.id),
            "source_id": str(self.evidence.source_id),
            "snapshot_id": str(self.evidence.snapshot_id),
            "observation_id": str(self.evidence.feeder_observation_id),
            "packet_hash": self.packet_hash,
            "observation_hash": self.observation_hash,
            "attachment_sha256": self.attachment_sha256,
            "identity_link_id": str(self.identity_link_id),
            "identity_review_id": str(self.identity_review_id),
            "predicate": self.claim.predicate,
            "category": self.claim.qualifiers["category"],
            "publication_status": self.claim.publication_status.value,
            "epistemic_status": self.claim.epistemic_status.value,
            "asserted_as_true": self.claim.asserted_as_true,
            "attendance_state": "NOT_VERIFIED",
            "publication_approval": False,
            "claim_persisted": False,
            "identity_changed": False,
            "network_fetch": False,
        }


def build_gukgam_witness_claim(
    document: CurrentGukgamWitnessDocument,
    index: int,
    *,
    person: Person,
    link: PersonObservationLink,
    review: IdentityReviewItem,
) -> GukgamWitnessClaimPreparation:
    """Consume a validated current document and an exact already reviewed identity bridge."""
    observation, snapshot, source, policy = document.contexts[index]
    packet, row = document.packet, document.packet.rows[index]
    if (
        person.identity_status != IdentityStatus.RESOLVED
        or person.superseded_at is not None
        or link.person_id != person.id
        or link.observation_id != observation.id
        or link.superseded_at is not None
        or link.action != MaterializationAction.REVIEWED_LINK
        or link.decision_class != MaterializationDecisionClass.REVIEWED_BRIDGE
        or link.review_item_id != review.id
        or review.observation_id != observation.id
        or review.candidate_person_id != person.id
        or review.status != IdentityReviewStatus.RESOLVED
        or review.resolved_at is None
        or not review.resolution_note
        or not review.resolution_note.strip()
    ):
        raise GukgamWitnessClaimError(
            "witness Claim requires an exact current reviewed identity bridge"
        )
    qualifiers = {
        "source_contract": GUKGAM_WITNESS_SOURCE_CONTRACT,
        "source_scope": observation.scope_key,
        "semantic_scope": observation.semantic_scope,
        "provider_record_key": row.record_key,
        "immutable_observation_hash": observation.content_hash,
        "reviewed_packet_hash": packet.content_hash,
        "attachment_sha256": snapshot.content_hash,
        "committee_name": packet.source.committee_name,
        "source_published_date": packet.source.published_date.isoformat(),
        "category": row.category,
        "printed_name": row.printed_name,
        "source_section": row.source_section,
        "source_name_cell_key": row.source_name_cell_key,
        "page_number": str(row.page_number),
        "table_number": str(row.table_number),
        "table_row_number": str(row.table_row_number),
        "relation": row.relation,
        "name_from_merged_cell": str(row.name_from_merged_cell).lower(),
        "identity_link_id": str(link.id),
        "identity_review_id": str(review.id),
        "identity_scope": "EXACT_REVIEWED_OBSERVATION_BRIDGE",
        "event_semantics": "OFFICIAL_SOURCE_LISTING_NOT_ACTUAL_ATTENDANCE",
    }
    for field in (
        "printed_institution_group",
        "printed_role",
        "printed_affiliation_role",
        "printed_audited_target",
        "requested_datetime_text",
        "decision_date_text",
        "printed_ordinal",
    ):
        value = getattr(row, field)
        if value is not None:
            qualifiers[field] = value
    category_label = {
        "INSTITUTION_WITNESS": "기관증인",
        "GENERAL_WITNESS": "일반증인",
        "REFERENCE_PERSON": "참고인",
    }[row.category]
    claim_id = uuid5(
        _NAMESPACE,
        "|".join(
            (
                str(person.id),
                str(observation.id),
                observation.content_hash,
                packet.content_hash,
                row.category,
                str(link.id),
                str(review.id),
            )
        ),
    )
    claim = Claim(
        id=claim_id,
        person_id=person.id,
        subject=person.canonical_name,
        predicate=GUKGAM_WITNESS_LISTING_PREDICATE,
        proposition=(
            f"{packet.source.committee_name}의 국정감사 증인 첨부명단은 "
            f"{row.printed_name}을 {category_label}으로 기재한다."
        ),
        object_text=f"{packet.source.committee_name} · {category_label} 명단 기재",
        qualifiers=qualifiers,
        epistemic_status=EpistemicStatus.CLAIM,
        publication_status=PublicationStatus.DRAFT,
        asserted_as_true=False,
        valid_from=datetime.combine(packet.source.published_date, time.min, tzinfo=UTC),
        recorded_at=observation.recorded_at,
    )
    evidence = ClaimEvidence(
        id=uuid5(claim_id, "|".join((str(source.id), str(snapshot.id), str(observation.id)))),
        claim_id=claim_id,
        source_id=source.id,
        snapshot_id=snapshot.id,
        feeder_observation_id=observation.id,
        stance=EvidenceStance.SUPPORT,
        excerpt=None,
    )
    gate = validate_claim_publication(
        claim, person, [evidence], {source.id: source}, {policy.id: policy}
    )
    if gate.failures != ("claim_not_marked_for_publication",):
        raise GukgamWitnessClaimError("witness DRAFT Claim failed canonical evidence checks")
    return GukgamWitnessClaimPreparation(
        claim,
        evidence,
        packet.content_hash,
        observation.content_hash,
        snapshot.content_hash,
        link.id,
        review.id,
    )
