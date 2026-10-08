"""Stage bounded official declared-asset metadata with exact canonical provenance.

Writes nothing itself. The Gazette worker uses the shared `commit_source_page`
seam; PETI accepts supplied scoped public metadata without a collector. Pure Claim
builders require an existing reviewed linkage and default to DRAFT. No Person,
AssetDisclosure or identity link is created. Observations carry no `canonical_name`,
so the generic materializer refuses automatic identity materialization.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta, timezone
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
PETI_ASSET_SOURCE_CONTRACT = "peti_public_declared_total_metadata_v1"
PETI_ASSET_FEEDER = "peti_public_declared_total"
PETI_ASSET_TOTALS_SCOPE = "PRINTED_PUBLIC_DISCLOSURE_TOTAL_NOT_SELF_ONLY"
PETI_ASSET_PAGE = "https://www.peti.go.kr/peOptpListVie.do"
PETI_ASSET_DETAIL = "https://www.peti.go.kr/peoptp/openPeOptpListVieDtlPop.do"
PETI_TOTAL_HEADERS = (
    "종전가액(천원)", "증가액(실거래가격)", "감소액(실거래가격)", "현재가액(천원)",
)
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


def require_peti_asset_metadata_policy(policy: SourcePolicy) -> None:
    """Supplied metadata staging only. FETCH is transport-neutral and stays disabled."""
    require_policy(policy, PolicyAction.STORE_METADATA)
    if (policy.domain != "www.peti.go.kr"
            or policy.collection_mode != SourceCollectionMode.BROWSER
            or policy.can_fetch or policy.can_store_fulltext or policy.can_show_excerpt):
        raise PolicyDenied("PETI total staging requires its bounded metadata-only policy")


def normalize_peti_asset_receipt(
    raw: Mapping[str, object], *, policy: SourcePolicy,
) -> dict[str, object]:
    """Normalize supplied public fields; never fetch, ingest private rows or attest review."""
    require_peti_asset_metadata_policy(policy)
    keys = {"source_page_url", "detail_route", "publication_date", "registration_date",
            "institution", "office", "printed_name", "column_headers", "amount_unit",
            "prior_value", "increase", "decrease", "current_value", "report_type",
            "report_type_label", "declared_totals_scope"}
    if set(raw) != keys:
        raise AssemblyAssetImportError("PETI total receipt has missing or prohibited fields")
    if (raw["source_page_url"] != PETI_ASSET_PAGE or raw["detail_route"] != PETI_ASSET_DETAIL
            or raw["institution"] != "국회" or raw["office"] != "국회의원"
            or raw["column_headers"] != list(PETI_TOTAL_HEADERS)
            or raw["amount_unit"] != AMOUNT_UNIT
            or raw["declared_totals_scope"] != PETI_ASSET_TOTALS_SCOPE):
        raise AssemblyAssetImportError("PETI source, scope, headers or unit is inconsistent")
    name = raw["printed_name"]
    if not isinstance(name, str) or not re.fullmatch(r"[가-힣A-Za-z·. -]{2,80}", name):
        raise AssemblyAssetImportError("PETI public printed name is malformed")
    dates = {}
    for field in ("publication_date", "registration_date"):
        value = raw[field]
        if not isinstance(value, str):
            raise AssemblyAssetImportError("PETI public date is malformed")
        try:
            dates[field] = date.fromisoformat(value)
        except ValueError:
            raise AssemblyAssetImportError("PETI public date is malformed") from None
        if dates[field].isoformat() != value:
            raise AssemblyAssetImportError("PETI public date must be exact ISO date")
    if dates["registration_date"] > dates["publication_date"]:
        raise AssemblyAssetImportError("PETI registration date follows disclosure date")
    amounts: dict[str, int] = {}
    for field in ("prior_value", "increase", "decrease", "current_value"):
        value = raw[field]
        if isinstance(value, bool) or not isinstance(value, int) or abs(value) > 2**53 - 1:
            raise AssemblyAssetImportError("PETI total requires exact transport-safe integers")
        if field in {"increase", "decrease"} and value < 0:
            raise AssemblyAssetImportError("PETI total changes must preserve printed column signs")
        amounts[field] = value
    if amounts["prior_value"] + amounts["increase"] - amounts["decrease"] != amounts["current_value"]:
        raise AssemblyAssetImportError("PETI printed total arithmetic differs")
    report = raw["report_type"]
    if report == "UNKNOWN":
        if raw["report_type_label"] is not None:
            raise AssemblyAssetImportError("PETI unknown report type cannot invent a label")
    elif (not isinstance(report, str) or report not in {"정기", "수시", "등록신고", "변동신고"}
          or raw["report_type_label"] != report):
        raise AssemblyAssetImportError("PETI report type requires its exact visible public label")
    return dict(raw)


def peti_asset_record_key(normalized: Mapping[str, object]) -> str:
    """A deterministic public selector locator, never an authoritative Person identifier."""
    selector = {key: normalized[key] for key in (
        "publication_date", "registration_date", "institution", "office", "printed_name",
    )}
    return "peti:" + assembly_asset_observation_hash(selector)


def build_peti_asset_capture(
    raw: Mapping[str, object], *, policy: SourcePolicy, run_id: UUID,
) -> tuple[Source, SourceSnapshot, FeederObservation]:
    normalized = normalize_peti_asset_receipt(raw, policy=policy)
    record_key = peti_asset_record_key(normalized)
    content_hash = assembly_asset_observation_hash(normalized)
    source = Source(id=uuid5(_POLICY_NAMESPACE, PETI_ASSET_DETAIL), url=PETI_ASSET_DETAIL,
        title="PETI 국회 공개 재산신고 총계 조회", publisher="공직윤리시스템",
        published_at=None, policy_id=policy.id)
    snapshot = SourceSnapshot(source_id=source.id, content_hash=content_hash,
        metadata={"source_contract": PETI_ASSET_SOURCE_CONTRACT,
                  "capture_mode": "SUPPLIED_SCOPED_PUBLIC_METADATA", "receipt": normalized},
        fulltext=None)
    observation = FeederObservation(feeder=PETI_ASSET_FEEDER,
        scope_key=f"peti:{normalized['publication_date']}:selected-public-records",
        provider_record_key=record_key, snapshot_id=snapshot.id, run_id=run_id,
        semantic_scope=ASSEMBLY_ASSET_SEMANTIC_SCOPE, identity_hints={},
        normalized=normalized, content_hash=content_hash)
    return source, snapshot, observation


def _require_reviewed_asset_subject(
    person: Person, observation: FeederObservation, link: PersonObservationLink,
    review: IdentityReviewItem,
) -> None:
    if (person.identity_status != IdentityStatus.RESOLVED or person.superseded_at is not None
            or link.person_id != person.id or link.observation_id != observation.id
            or link.superseded_at is not None or link.action != MaterializationAction.REVIEWED_LINK
            or link.review_item_id != review.id or review.status != IdentityReviewStatus.RESOLVED
            or review.observation_id != observation.id or review.candidate_person_id != person.id
            or not review.resolution_note):
        raise AssemblyAssetImportError("asset total requires an exact resolved reviewed Person link")


def build_peti_asset_total_claim(
    source: Source, snapshot: SourceSnapshot, observation: FeederObservation, *,
    policy: SourcePolicy, person: Person, link: PersonObservationLink,
    review: IdentityReviewItem, publication_approved: bool = False,
) -> tuple[Claim, ClaimEvidence]:
    normalized = normalize_peti_asset_receipt(observation.normalized, policy=policy)
    if (source.policy_id != policy.id or str(source.url) != PETI_ASSET_DETAIL
            or snapshot.source_id != source.id or snapshot.fulltext is not None
            or snapshot.metadata != {"source_contract": PETI_ASSET_SOURCE_CONTRACT,
                                    "capture_mode": "SUPPLIED_SCOPED_PUBLIC_METADATA",
                                    "receipt": normalized}
            or snapshot.content_hash != assembly_asset_observation_hash(normalized)
            or observation.snapshot_id != snapshot.id
            or observation.content_hash != snapshot.content_hash
            or observation.feeder != PETI_ASSET_FEEDER
            or observation.semantic_scope != ASSEMBLY_ASSET_SEMANTIC_SCOPE
            or observation.scope_key != f"peti:{normalized['publication_date']}:selected-public-records"
            or observation.identity_hints
            or observation.provider_record_key != peti_asset_record_key(normalized)):
        raise AssemblyAssetImportError("PETI total immutable metadata provenance differs")
    _require_reviewed_asset_subject(person, observation, link, review)
    amount = normalized["current_value"]
    claim_id = uuid5(_POLICY_NAMESPACE, "|".join((str(person.id),
        ASSEMBLY_ASSET_TOTAL_PREDICATE, observation.provider_record_key, observation.content_hash)))
    claim = Claim(id=claim_id, person_id=person.id, subject=person.canonical_name,
        proposition=f"{person.canonical_name}의 공개 재산신고 총계는 {amount:,}천원이다.",
        predicate=ASSEMBLY_ASSET_TOTAL_PREDICATE, object_text=f"{amount:,}천원",
        qualifiers={"source_contract": PETI_ASSET_SOURCE_CONTRACT,
            "provider_record_key": observation.provider_record_key,
            "immutable_observation_hash": observation.content_hash,
            "review_item_id": str(review.id), "identity_basis": "REVIEWED_SOURCE_CONTEXT",
            "amount_thousand_krw": str(amount), "amount_unit": AMOUNT_UNIT,
            "value_semantics": VALUE_SEMANTICS, "declared_totals_scope": PETI_ASSET_TOTALS_SCOPE,
            "publication_date": str(normalized["publication_date"]),
            "registration_date": str(normalized["registration_date"]),
            "report_type": str(normalized["report_type"])},
        epistemic_status=EpistemicStatus.CLAIM, asserted_as_true=False,
        publication_status=PublicationStatus.PUBLISHED if publication_approved else PublicationStatus.DRAFT,
        valid_from=datetime.combine(date.fromisoformat(str(normalized["publication_date"])),
                                    time(), tzinfo=_KST),
        recorded_at=observation.recorded_at)
    evidence = ClaimEvidence(id=uuid5(claim.id, str(observation.id)), claim_id=claim.id,
        source_id=source.id, snapshot_id=snapshot.id, feeder_observation_id=observation.id,
        stance=EvidenceStance.SUPPORT, excerpt=None)
    if publication_approved and not validate_claim_publication(
        claim, person, [evidence], {source.id: source}, {policy.id: policy},
    ).publishable:
        raise AssemblyAssetImportError("PETI total publication gate rejected the claim")
    return claim, evidence


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
    _require_reviewed_asset_subject(person, observation, link, review)
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
