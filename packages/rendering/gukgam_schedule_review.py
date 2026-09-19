from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from packages.connectors.gukgam_reviewed_packet import PACKET_SCHEMA
from packages.domain.contracts import FeederObservation, Source, SourcePolicy, SourceSnapshot
from packages.domain.enums import SourceCollectionMode
from packages.verification.gukgam_reviewed_plan_import import (
    GUKGAM_REVIEWED_PLAN_FEEDER,
    GUKGAM_REVIEWED_PLAN_SEMANTIC_SCOPE,
    GUKGAM_REVIEWED_PLAN_SOURCE_CONTRACT,
)

GUKGAM_SCHEDULE_REVIEW_SEMANTICS = (
    "REVIEW_ONLY_PROJECTION_FROM_REVIEWED_GUKGAM_PLAN_OBSERVATIONS"
)


class GukgamScheduleReviewError(ValueError):
    pass


@dataclass(frozen=True)
class GukgamScheduleReviewSource:
    source_id: UUID
    snapshot_id: UUID
    url: str
    title: str
    publisher: str
    attachment_sha256: str
    rights_mark: str | None
    source_class: str

    def to_dict(self) -> dict[str, object]:
        return {
            "source_id": str(self.source_id),
            "snapshot_id": str(self.snapshot_id),
            "url": self.url,
            "title": self.title,
            "publisher": self.publisher,
            "attachment_sha256": self.attachment_sha256,
            "rights_mark": self.rights_mark,
            "source_class": self.source_class,
        }


@dataclass(frozen=True)
class GukgamScheduleReviewRow:
    observation_id: UUID
    provider_record_key: str
    audit_date: str
    time_text: str | None
    venue: str | None
    section: str
    audited_targets: tuple[str, ...]
    page_number: int

    def to_dict(self) -> dict[str, object]:
        return {
            "observation_id": str(self.observation_id),
            "provider_record_key": self.provider_record_key,
            "audit_date": self.audit_date,
            "time_text": self.time_text,
            "venue": self.venue,
            "section": self.section,
            "audited_targets": list(self.audited_targets),
            "page_number": self.page_number,
        }


@dataclass(frozen=True)
class GukgamCommitteeScheduleReview:
    committee_name: str
    source_published_date: str
    source: GukgamScheduleReviewSource
    rows: tuple[GukgamScheduleReviewRow, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "committee_name": self.committee_name,
            "source_published_date": self.source_published_date,
            "source": self.source.to_dict(),
            "schedule_rows": [row.to_dict() for row in self.rows],
        }


@dataclass(frozen=True)
class GukgamScheduleReviewReport:
    committees: tuple[GukgamCommitteeScheduleReview, ...]

    def to_dict(self) -> dict[str, object]:
        rows = [row for committee in self.committees for row in committee.rows]
        return {
            "semantics": GUKGAM_SCHEDULE_REVIEW_SEMANTICS,
            "committee_count": len(self.committees),
            "schedule_row_count": len(rows),
            "audited_target_mentions": sum(len(row.audited_targets) for row in rows),
            "committees": [committee.to_dict() for committee in self.committees],
            "limitations": [
                "Review-only source metadata; this is not public Claim/Evidence publication.",
                "Audited-target strings are source-scoped and are not canonical Organization links.",
                "Witness/reference-person rows are outside this plan projection.",
            ],
        }


Context = tuple[FeederObservation, SourceSnapshot, Source, SourcePolicy]
_NORMALIZED_FIELDS = {
    "committee_name",
    "source_published_date",
    "audit_date",
    "time_text",
    "venue",
    "section",
    "audited_targets",
    "page_number",
    "packet_schema",
}


def _required_text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise GukgamScheduleReviewError(f"{field} must be a non-empty string")
    return value.strip()


def _optional_text(value: object, field: str) -> str | None:
    if value is None:
        return None
    return _required_text(value, field)


def _review_row(context: Context) -> tuple[str, str, GukgamScheduleReviewSource, GukgamScheduleReviewRow]:
    observation, snapshot, source, policy = context
    if observation.feeder != GUKGAM_REVIEWED_PLAN_FEEDER:
        raise GukgamScheduleReviewError("unexpected feeder in Gukgam schedule review")
    if observation.semantic_scope != GUKGAM_REVIEWED_PLAN_SEMANTIC_SCOPE:
        raise GukgamScheduleReviewError("unexpected semantic scope in Gukgam schedule review")
    if observation.identity_hints:
        raise GukgamScheduleReviewError("Gukgam schedule observation must not carry identity hints")
    if snapshot.source_id != source.id or source.policy_id != policy.id:
        raise GukgamScheduleReviewError("Gukgam schedule provenance chain is inconsistent")
    if snapshot.fulltext is not None:
        raise GukgamScheduleReviewError("Gukgam review projection must not expose stored fulltext")
    if snapshot.metadata.get("source_contract") != GUKGAM_REVIEWED_PLAN_SOURCE_CONTRACT:
        raise GukgamScheduleReviewError("Gukgam schedule source contract is invalid")
    if snapshot.metadata.get("content_hash_semantics") != "RAW_ATTACHMENT_SHA256":
        raise GukgamScheduleReviewError("Gukgam schedule snapshot hash semantics are invalid")
    if policy.source_class != "official_reviewed_committee_attachment":
        raise GukgamScheduleReviewError("Gukgam schedule source class is invalid")
    if (
        policy.collection_mode != SourceCollectionMode.BROWSER
        or policy.can_fetch
        or not policy.can_store_metadata
        or policy.can_store_fulltext
        or policy.can_send_to_ai
        or policy.can_show_excerpt
    ):
        raise GukgamScheduleReviewError("Gukgam schedule source policy was weakened")

    normalized = observation.normalized
    if set(normalized) != _NORMALIZED_FIELDS:
        raise GukgamScheduleReviewError("Gukgam schedule normalized fields changed unexpectedly")
    if normalized.get("packet_schema") != PACKET_SCHEMA:
        raise GukgamScheduleReviewError("Gukgam schedule packet schema is invalid")

    committee_name = _required_text(normalized.get("committee_name"), "committee_name")
    source_published_date = _required_text(
        normalized.get("source_published_date"), "source_published_date"
    )
    audit_date = _required_text(normalized.get("audit_date"), "audit_date")
    try:
        date.fromisoformat(source_published_date)
        date.fromisoformat(audit_date)
    except ValueError as exc:
        raise GukgamScheduleReviewError("Gukgam schedule date is invalid") from exc

    targets = normalized.get("audited_targets")
    if not isinstance(targets, list) or not targets:
        raise GukgamScheduleReviewError("Gukgam schedule audited_targets must be non-empty")
    audited_targets = tuple(_required_text(item, "audited_target") for item in targets)
    if len(set(audited_targets)) != len(audited_targets):
        raise GukgamScheduleReviewError("Gukgam schedule audited_targets must be unique")

    page_number = normalized.get("page_number")
    if not isinstance(page_number, int) or isinstance(page_number, bool) or page_number < 1:
        raise GukgamScheduleReviewError("Gukgam schedule page_number is invalid")

    rights_mark = snapshot.metadata.get("rights_mark")
    if rights_mark is not None and not isinstance(rights_mark, str):
        raise GukgamScheduleReviewError("Gukgam schedule rights_mark is invalid")

    review_source = GukgamScheduleReviewSource(
        source_id=source.id,
        snapshot_id=snapshot.id,
        url=str(source.url),
        title=source.title,
        publisher=source.publisher,
        attachment_sha256=snapshot.content_hash,
        rights_mark=rights_mark,
        source_class=policy.source_class,
    )
    row = GukgamScheduleReviewRow(
        observation_id=observation.id,
        provider_record_key=observation.provider_record_key,
        audit_date=audit_date,
        time_text=_optional_text(normalized.get("time_text"), "time_text"),
        venue=_optional_text(normalized.get("venue"), "venue"),
        section=_required_text(normalized.get("section"), "section"),
        audited_targets=audited_targets,
        page_number=page_number,
    )
    return committee_name, source_published_date, review_source, row


def build_gukgam_schedule_review(contexts: list[Context]) -> GukgamScheduleReviewReport:
    grouped: dict[str, list[tuple[str, GukgamScheduleReviewSource, GukgamScheduleReviewRow]]] = {}
    for context in contexts:
        committee_name, published_date, source, row = _review_row(context)
        grouped.setdefault(committee_name, []).append((published_date, source, row))

    committees: list[GukgamCommitteeScheduleReview] = []
    for committee_name, items in grouped.items():
        published_dates = {item[0] for item in items}
        sources = {item[1] for item in items}
        if len(published_dates) != 1 or len(sources) != 1:
            raise GukgamScheduleReviewError(
                f"current Gukgam review rows disagree on source for {committee_name}"
            )
        source = next(iter(sources))
        rows = tuple(
            sorted(
                (item[2] for item in items),
                key=lambda row: (
                    row.audit_date,
                    row.time_text or "",
                    row.provider_record_key,
                ),
            )
        )
        committees.append(
            GukgamCommitteeScheduleReview(
                committee_name=committee_name,
                source_published_date=next(iter(published_dates)),
                source=source,
                rows=rows,
            )
        )

    return GukgamScheduleReviewReport(
        committees=tuple(sorted(committees, key=lambda item: item.committee_name))
    )
