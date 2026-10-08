"""Bind a human-reviewed Assembly asset-disclosure packet to its exact Gazette PDF bytes.

Writes nothing itself: the worker commits the capture through the shared
`commit_source_page` seam (Source / SourceSnapshot / FeederObservation only). No Person,
AssetDisclosure, Claim or identity link is created; observations deliberately carry no
`canonical_name`, so the generic materializer refuses them.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta, timezone
from uuid import UUID, uuid5

from packages.connectors.assembly_asset_packet import (
    AMOUNT_UNIT,
    ASSET_PACKET_SCHEMA,
    GAZETTE_HOST,
    VALUE_SEMANTICS,
    AssetItemRow,
    MemberDisclosure,
    ReviewedAssemblyAssetPacket,
)
from packages.domain.contracts import (
    Claim,
    ClaimEvidence,
    FeederObservation,
    IdentityReviewItem,
    Person,
    PersonObservationLink,
    Source,
    SourcePolicy,
    SourceSnapshot,
)
from packages.domain.enums import (
    EpistemicStatus,
    EvidenceStance,
    IdentityReviewStatus,
    IdentityStatus,
    MaterializationAction,
    PublicationStatus,
    SourceCollectionMode,
)
from packages.verification.claims import validate_claim_publication
from packages.verification.policy import PolicyAction, PolicyDenied, require_policy

ASSEMBLY_ASSET_FEEDER = "assembly_asset_gazette_reviewed"
ASSEMBLY_ASSET_SEMANTIC_SCOPE = "national_assembly_member_asset_disclosure_declared_values"
ASSEMBLY_ASSET_SOURCE_CONTRACT = "assembly_asset_gazette_reviewed_packet_v1"
GAZETTE_SOURCE_CLASS = "official_gazette_human_reviewed_artifact"
HUMAN_ASSISTED_CAPTURE = "HUMAN_ASSISTED_LOCAL_ARTIFACT"
GAZETTE_RIGHTS_SCOPE = "GAZETTE_ISSUE_RIGHTS_REVIEWED"
RECORD_KIND_MEMBER_TOTAL = "MEMBER_DECLARED_TOTAL"
RECORD_KIND_ITEM = "SELF_HELD_ASSET_ITEM"
RELATIVE_ITEMS_POLICY = "RELATIVE_HELD_ITEMS_EXCLUDED_FROM_OBSERVATIONS"
TOTALS_SCOPE = "PRINTED_MEMBER_TOTAL_INCLUDES_REPORTED_RELATIVES"
LINK_MODE = "REVIEW_ONLY_NO_AUTO_LINK"
AUTHORITY = "OFFICIAL_NATIONAL_ASSEMBLY_GAZETTE"
ASSEMBLY_ASSET_TOTAL_PREDICATE = "ASSEMBLY_DECLARED_ASSET_TOTAL"
_POLICY_NAMESPACE = UUID("3f6c1d0e-8a51-4c43-9e0f-2b7f5a9d6c14")
_KST = timezone(timedelta(hours=9))


class AssemblyAssetImportError(ValueError):
    """A packet lacks exact review, provenance or policy permission for persistence."""


def gazette_asset_policy() -> SourcePolicy:
    """Metadata-only policy for human-captured Gazette artifacts; never fetches."""

    return SourcePolicy(
        id=uuid5(_POLICY_NAMESPACE, GAZETTE_HOST),
        domain=GAZETTE_HOST,
        source_class=GAZETTE_SOURCE_CLASS,
        collection_mode=SourceCollectionMode.BROWSER,
        can_fetch=False,
        can_store_metadata=True,
        can_store_fulltext=False,
        can_send_to_ai=False,
        can_show_excerpt=False,
        can_commercialize=False,
        robots_checked_at=datetime(2026, 10, 5, tzinfo=UTC),
        terms_checked_at=None,
        license=None,
        policy_note=(
            "www.assembly.go.kr robots.txt is `Disallow: /` (re-observed 2026-10-05): no "
            "automated fetch. An operator saves one exact 국회공보 재산공개 PDF; a human-reviewed "
            "packet of member-level declared values is imported as metadata only. No fulltext, "
            "AI use, excerpt display or commercialization. Copyright Act Art. 7 status of the "
            "specific issue and redistribution terms remain owner decisions."
        ),
    )


def effective_gazette_policy(stored: Iterable[SourcePolicy]) -> SourcePolicy:
    """The policy that governs the commit: a stored domain decision wins, and must permit."""

    expected = gazette_asset_policy()
    matches = [policy for policy in stored if policy.domain == expected.domain]
    if len(matches) > 1:
        raise PolicyDenied(f"{expected.domain} has multiple SourcePolicy decisions")
    policy = matches[0] if matches else expected
    if policy.id != expected.id:
        raise PolicyDenied(f"{expected.domain} is bound to another SourcePolicy")
    require_policy(policy, PolicyAction.STORE_METADATA)
    if policy.can_fetch:
        raise PolicyDenied("Gazette asset lane never fetches; stored policy allows fetch")
    return policy


def assembly_asset_observation_hash(normalized: dict[str, object]) -> str:
    return hashlib.sha256(
        json.dumps(normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()


@dataclass(frozen=True)
class AssemblyAssetCapture:
    packet: ReviewedAssemblyAssetPacket
    policy: SourcePolicy
    source: Source
    snapshot: SourceSnapshot

    @property
    def scope_key(self) -> str:
        return self.packet.scope_key

    @property
    def packet_hash(self) -> str:
        return self.packet.content_hash

    @property
    def cursor(self) -> str:
        return f"{self.packet.source.artifact_sha256}:{self.packet_hash}"

    @property
    def self_item_count(self) -> int:
        return sum(1 for m in self.packet.members for item in m.items if item.is_self_held)

    @property
    def excluded_relative_item_count(self) -> int:
        return sum(1 for m in self.packet.members for item in m.items if not item.is_self_held)

    @property
    def run_metadata(self) -> dict[str, object]:
        return {
            "source_contract": ASSEMBLY_ASSET_SOURCE_CONTRACT,
            "packet_schema": ASSET_PACKET_SCHEMA,
            "review_status": self.packet.review_status,
            "coverage": self.packet.coverage,
            "reviewed_packet_hash": self.packet_hash,
            "artifact_sha256": self.packet.source.artifact_sha256,
            "gazette_issue": self.packet.source.gazette_issue,
            "member_count": len(self.packet.members),
            "self_item_count": self.self_item_count,
            "excluded_relative_item_count": self.excluded_relative_item_count,
            "value_semantics": VALUE_SEMANTICS,
        }

    @property
    def checkpoint_metadata(self) -> dict[str, object]:
        return self.run_metadata

    def _common(self) -> dict[str, object]:
        source = self.packet.source
        return {
            "authority": AUTHORITY,
            "packet_schema": ASSET_PACKET_SCHEMA,
            "gazette_issue": source.gazette_issue,
            "publication_date": source.publication_date.isoformat(),
            "disclosure_kind": source.disclosure_kind,
            "reporting_period_text": source.reporting_period_text,
            "reporting_period_start": (
                source.reporting_period_start.isoformat() if source.reporting_period_start else None
            ),
            "reporting_period_end": (
                source.reporting_period_end.isoformat() if source.reporting_period_end else None
            ),
            "amount_unit": AMOUNT_UNIT,
            "value_semantics": VALUE_SEMANTICS,
        }

    def _identity_hints(self, member: MemberDisclosure) -> dict[str, object]:
        if member.reviewer_stated_mona_cd is None:
            # Name + issue + locator stay review-only handles; never an identity hint.
            return {}
        return {
            "assembly_mona_cd_stated": member.reviewer_stated_mona_cd,
            "identity_basis": "PACKET_REVIEWER_STATED",
            "link_mode": LINK_MODE,
        }

    def _member_observation(self, member: MemberDisclosure, run_id: UUID) -> FeederObservation:
        normalized: dict[str, object] = self._common() | {
            "record_kind": RECORD_KIND_MEMBER_TOTAL,
            "printed_member_name": member.printed_member_name,
            "printed_affiliation": member.printed_affiliation,
            "printed_position": member.printed_position,
            "reviewer_stated_mona_cd": member.reviewer_stated_mona_cd,
            "mona_cd_basis": member.mona_cd_basis,
            "report_type": member.report_type,
            "locator": member.total_locator.normalized(),
            "declared_totals": {
                name: (amount.normalized() if amount else None)
                for name, amount in member.declared_totals.items()
            },
            "declared_totals_scope": TOTALS_SCOPE,
            "totals_cross_check": "ITEM_SUM_MATCHED",
            "relative_items_policy": RELATIVE_ITEMS_POLICY,
        }
        return FeederObservation(
            feeder=ASSEMBLY_ASSET_FEEDER,
            scope_key=self.scope_key,
            provider_record_key=self.packet.record_key(member.total_locator),
            snapshot_id=self.snapshot.id,
            run_id=run_id,
            semantic_scope=ASSEMBLY_ASSET_SEMANTIC_SCOPE,
            identity_hints=self._identity_hints(member),
            normalized=normalized,
            content_hash=assembly_asset_observation_hash(normalized),
        )

    def _item_observation(
        self, member: MemberDisclosure, item: AssetItemRow, run_id: UUID
    ) -> FeederObservation:
        normalized: dict[str, object] = self._common() | {
            "record_kind": RECORD_KIND_ITEM,
            "member_record_key": self.packet.record_key(member.total_locator),
            "reviewer_stated_mona_cd": member.reviewer_stated_mona_cd,
            "report_type": member.report_type,
            "holder_relation": item.holder_relation,
            "item_category": item.item_category,
            "item_category_text": item.item_category_text,
            "item_kind": item.item_kind,
            "region_sido": item.region_sido,
            "locator": item.locator.normalized(),
            "amounts": {
                name: (amount.normalized() if amount else None)
                for name, amount in item.amounts.items()
            },
        }
        return FeederObservation(
            feeder=ASSEMBLY_ASSET_FEEDER,
            scope_key=self.scope_key,
            provider_record_key=self.packet.record_key(item.locator),
            snapshot_id=self.snapshot.id,
            run_id=run_id,
            semantic_scope=ASSEMBLY_ASSET_SEMANTIC_SCOPE,
            identity_hints=self._identity_hints(member),
            normalized=normalized,
            content_hash=assembly_asset_observation_hash(normalized),
        )

    def observations(self, run_id: UUID) -> tuple[FeederObservation, ...]:
        items: list[FeederObservation] = []
        for member in self.packet.members:
            items.append(self._member_observation(member, run_id))
            items.extend(
                self._item_observation(member, item, run_id)
                for item in member.items
                if item.is_self_held  # relative-held items are validated, never persisted
            )
        return tuple(items)


def build_assembly_asset_capture(
    packet: ReviewedAssemblyAssetPacket,
    *,
    artifact_bytes: bytes,
    policy: SourcePolicy | None = None,
) -> AssemblyAssetCapture:
    """Verify review + sha256 of the operator-saved PDF; build Source and SourceSnapshot."""

    if not packet.is_human_reviewed:
        raise AssemblyAssetImportError("asset packet must be HUMAN_REVIEWED before persistence")
    if not artifact_bytes:
        raise AssemblyAssetImportError("Gazette artifact is empty")
    if not artifact_bytes.startswith(b"%PDF-"):
        raise AssemblyAssetImportError("Gazette artifact is not a PDF")
    actual = hashlib.sha256(artifact_bytes).hexdigest()
    if actual != packet.source.artifact_sha256:
        raise AssemblyAssetImportError("Gazette artifact sha256 does not match the reviewed packet")
    try:
        governing = effective_gazette_policy([policy] if policy is not None else [])
    except PolicyDenied as exc:
        raise AssemblyAssetImportError(f"SourcePolicy denies this import: {exc}") from None
    source_info = packet.source
    metadata: dict[str, object] = {
        "source_contract": ASSEMBLY_ASSET_SOURCE_CONTRACT,
        "authority": AUTHORITY,
        "gazette_issue": source_info.gazette_issue,
        "gazette_title": source_info.gazette_title,
        "publication_date": source_info.publication_date.isoformat(),
        "disclosure_kind": source_info.disclosure_kind,
        "pdf_id": source_info.pdf_id,
        "parent_page_url": source_info.page_url,
        "artifact_format": "PDF",
        "artifact_filename": source_info.artifact_filename,
        "rights_mark": source_info.rights_mark or "NOT_STATED",
        "rights_scope": GAZETTE_RIGHTS_SCOPE,
        "capture_mode": HUMAN_ASSISTED_CAPTURE,
        "content_hash_semantics": "RAW_ARTIFACT_SHA256",
        "automation_gate": source_info.automation_gate,
        "amount_unit": AMOUNT_UNIT,
        "value_semantics": VALUE_SEMANTICS,
        "packet_coverage": packet.coverage,
        "review_status": packet.review_status,
        "reviewed_packet_hash": packet.content_hash,
    }
    source = Source(
        url=source_info.canonical_url,  # type: ignore[arg-type]
        title=source_info.gazette_title,
        publisher="대한민국 국회 국회공직자윤리위원회 (국회공보)",
        published_at=datetime.combine(source_info.publication_date, time(), tzinfo=_KST),
        policy_id=governing.id,
    )
    snapshot = SourceSnapshot(
        source_id=source.id, content_hash=actual, metadata=metadata, fulltext=None
    )
    return AssemblyAssetCapture(packet=packet, policy=governing, source=source, snapshot=snapshot)


def build_assembly_asset_total_claim(
    capture: AssemblyAssetCapture,
    observation: FeederObservation,
    *,
    person: Person,
    link: PersonObservationLink,
    review: IdentityReviewItem,
    official_member_code: str,
    publication_approved: bool = False,
) -> tuple[Claim, ClaimEvidence]:
    """Stage one exact reviewed linkage; never create/link a Person or write rows.

    The caller obtains official_member_code from the canonical Assembly roster context.
    Reviewer-stated codes and names alone cannot authorize the supplied reviewed link.
    Publication is a separate explicit decision, and needs reviewed source terms.
    """
    candidates = capture.observations(observation.run_id)
    expected = next((item for item in candidates if
                     item.provider_record_key == observation.provider_record_key), None)
    if (expected is None or expected.content_hash != observation.content_hash
            or expected.normalized != observation.normalized
            or observation.snapshot_id != capture.snapshot.id
            or observation.normalized.get("record_kind") != RECORD_KIND_MEMBER_TOTAL):
        raise AssemblyAssetImportError("asset total observation does not match reviewed capture")
    if (person.identity_status != IdentityStatus.RESOLVED or person.superseded_at is not None
            or link.person_id != person.id or link.observation_id != observation.id
            or link.superseded_at is not None or link.action != MaterializationAction.REVIEWED_LINK
            or link.review_item_id != review.id or review.status != IdentityReviewStatus.RESOLVED
            or review.observation_id != observation.id or review.candidate_person_id != person.id
            or not review.resolution_note):
        raise AssemblyAssetImportError("asset total requires an exact resolved reviewed Person link")
    code = observation.normalized.get("reviewer_stated_mona_cd")
    if not code or code != official_member_code:
        raise AssemblyAssetImportError("asset total requires the exact canonical Assembly code")
    amount = observation.normalized["declared_totals"]["current_value"]
    if amount is None:
        raise AssemblyAssetImportError("asset total current value is unavailable, never zero")
    if publication_approved and (
        not capture.policy.license or capture.policy.terms_checked_at is None
        or not capture.packet.source.rights_mark
    ):
        raise AssemblyAssetImportError("asset publication requires reviewed issue rights and SourcePolicy terms")
    claim_id = uuid5(_POLICY_NAMESPACE, "|".join((str(person.id),
        ASSEMBLY_ASSET_TOTAL_PREDICATE, observation.provider_record_key, observation.content_hash)))
    claim = Claim(
        id=claim_id, person_id=person.id, subject=person.canonical_name,
        proposition=f"{person.canonical_name}의 국회공보 신고 재산 총액은 {amount['value']:,}천원이다.",
        predicate=ASSEMBLY_ASSET_TOTAL_PREDICATE, object_text=f"{amount['value']:,}천원",
        qualifiers={
            "source_contract": ASSEMBLY_ASSET_SOURCE_CONTRACT,
            "provider_record_key": observation.provider_record_key,
            "immutable_observation_hash": observation.content_hash,
            "reviewed_packet_hash": capture.packet_hash,
            "assembly_mona_cd": official_member_code,
            "review_item_id": str(review.id),
            "amount_thousand_krw": str(amount["value"]), "amount_unit": AMOUNT_UNIT,
            "value_semantics": VALUE_SEMANTICS, "declared_totals_scope": TOTALS_SCOPE,
            "publication_date": observation.normalized["publication_date"],
            "gazette_issue": capture.packet.source.gazette_issue,
            "report_type": observation.normalized["report_type"],
            "reporting_period_text": observation.normalized["reporting_period_text"],
        },
        epistemic_status=EpistemicStatus.CLAIM, asserted_as_true=False,
        publication_status=PublicationStatus.PUBLISHED if publication_approved else PublicationStatus.DRAFT,
        valid_from=capture.source.published_at or observation.recorded_at,
        recorded_at=observation.recorded_at,
    )
    evidence = ClaimEvidence(id=uuid5(claim.id, str(observation.id)), claim_id=claim.id,
        source_id=capture.source.id, snapshot_id=capture.snapshot.id,
        feeder_observation_id=observation.id, stance=EvidenceStance.SUPPORT, excerpt=None)
    if publication_approved:
        gate = validate_claim_publication(claim, person, [evidence],
            {capture.source.id: capture.source}, {capture.policy.id: capture.policy})
        if not gate.publishable:
            raise AssemblyAssetImportError("asset total publication gate rejected the reviewed claim")
    return claim, evidence
