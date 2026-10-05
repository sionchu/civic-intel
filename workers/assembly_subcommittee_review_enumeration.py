from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date
from math import ceil

from packages.connectors.base import ConnectorDocument
from packages.connectors.open_assembly import AssemblyApiError
from packages.connectors.open_assembly_subcommittee import (
    AssemblySubcommitteeReviewRecord,
    OpenAssemblySubcommitteeReviewConnector,
    national_assembly_subcommittee_policy,
)
from packages.domain.contracts import FeederObservation, SourcePolicy, SourceRun
from packages.domain.enums import SourceRunStatus
from packages.persistence import SqlAlchemyRepository
from packages.verification.policy import PolicyAction, PolicyDenied, require_policy
from workers.ingest import IngestionPipeline


class AssemblySubcommitteeReviewCoverageError(AssemblyApiError):
    pass


@dataclass(frozen=True)
class ReviewPage:
    page_index: int
    connector: OpenAssemblySubcommitteeReviewConnector
    document: ConnectorDocument
    records: tuple[AssemblySubcommitteeReviewRecord, ...]


@dataclass(frozen=True)
class ReviewPacket:
    bill_id: str
    bill_no: str
    anchor_page: int
    duplicate_provider_rows: int
    normalized: dict[str, object]
    content_hash: str


@dataclass(frozen=True)
class AssemblySubcommitteeReviewEnumerationResult:
    run: SourceRun
    provider_row_count: int
    packet_count: int
    pages_committed_this_run: int
    pages_committed_total: int
    exact_duplicate_surplus_rows: int
    complete: bool


def _iso(value: date | None) -> str | None:
    return value.isoformat() if value is not None else None


def normalized_review_row(record: AssemblySubcommitteeReviewRecord) -> dict[str, object]:
    return {
        "committee_id": record.committee_id,
        "committee_name": record.committee_name,
        "subcommittee_name": record.subcommittee_name,
        "present_session": record.present_session,
        "present_degree": record.present_degree,
        "process_session": record.process_session,
        "process_degree": record.process_degree,
        "referral_date": _iso(record.referral_date),
        "present_date": _iso(record.present_date),
        "process_date": _iso(record.process_date),
        "process_result": record.process_result,
        "direct_referral": record.direct_referral,
        "review_note": record.review_note,
    }


def _canonical(value: dict[str, object]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def build_review_packet(
    bill_id: str,
    records: tuple[AssemblySubcommitteeReviewRecord, ...],
    source_pages: tuple[int, ...],
) -> ReviewPacket:
    if not records:
        raise AssemblySubcommitteeReviewCoverageError("review packet is empty")
    bill_nos = {record.bill_no for record in records}
    ages = {record.assembly_age for record in records}
    if len(bill_nos) != 1:
        raise AssemblySubcommitteeReviewCoverageError(
            f"BILL_ID {bill_id} maps to multiple BILL_NO values"
        )
    if len(ages) != 1:
        raise AssemblySubcommitteeReviewCoverageError(
            f"BILL_ID {bill_id} maps to multiple Assembly ages"
        )

    variants: Counter[str] = Counter(_canonical(normalized_review_row(item)) for item in records)
    reviews: list[dict[str, object]] = []
    for canonical, count in sorted(variants.items()):
        row = json.loads(canonical)
        row["provider_row_count"] = count
        reviews.append(row)

    duplicate_provider_rows = len(records) - len(reviews)
    normalized: dict[str, object] = {
        "assembly_age": next(iter(ages)),
        "bill_id": bill_id,
        "bill_no": next(iter(bill_nos)),
        "reviews": reviews,
        "provider_row_total": len(records),
        "distinct_review_rows": len(reviews),
        "duplicate_provider_rows": duplicate_provider_rows,
        "source_pages": sorted(source_pages),
        "source_page_count": len(set(source_pages)),
        "packet_semantics": "official_subcommittee_review_rows_by_bill_id",
    }
    digest = hashlib.sha256(_canonical(normalized).encode("utf-8")).hexdigest()
    return ReviewPacket(
        bill_id=bill_id,
        bill_no=next(iter(bill_nos)),
        anchor_page=max(source_pages),
        duplicate_provider_rows=duplicate_provider_rows,
        normalized=normalized,
        content_hash=digest,
    )


class AssemblySubcommitteeReviewEnumerator:
    FEEDER = "assembly_subcommittee_bill_reviews"
    SEMANTIC_SCOPE = "legislative_subcommittee_review_packet"
    SOURCE_CONTRACT = "assembly_age_subcommittee_review_packets_by_bill_id"

    def __init__(
        self,
        connector: OpenAssemblySubcommitteeReviewConnector,
        repository: SqlAlchemyRepository,
        policy: SourcePolicy | None = None,
        *,
        max_pages: int | None = None,
        max_source_pages: int = 50,
    ) -> None:
        if connector.sample_mode:
            raise ValueError("sample mode cannot be used for L3 enumeration")
        if connector.has_filters:
            raise ValueError("L3 enumeration requires an unfiltered AGE scope")
        if max_pages is not None and max_pages < 1:
            raise ValueError("max_pages must be >= 1")
        if max_source_pages < 1:
            raise ValueError("max_source_pages must be >= 1")
        self.connector = connector
        self.repository = repository
        self.policy = policy or national_assembly_subcommittee_policy()
        self.max_pages = max_pages
        self.max_source_pages = max_source_pages

    @property
    def scope_key(self) -> str:
        return f"assembly_age:{self.connector.assembly_age}"

    def _fetch_universe(
        self,
    ) -> tuple[
        list[ReviewPage],
        dict[int, tuple[ReviewPacket, ...]],
        int,
        int,
        str,
    ]:
        pages: list[ReviewPage] = []
        expected_total: int | None = None
        expected_pages: int | None = None
        records_by_bill: dict[str, list[AssemblySubcommitteeReviewRecord]] = defaultdict(list)
        pages_by_bill: dict[str, set[int]] = defaultdict(set)

        page_index = 1
        while expected_pages is None or page_index <= expected_pages:
            connector = self.connector.for_page(page_index)
            document = connector.fetch(connector.discover()[0])
            raw_total = document.metadata.get("list_total_count", "")
            try:
                total = int(raw_total)
            except ValueError:
                raise AssemblySubcommitteeReviewCoverageError(
                    "subcommittee-review total count is invalid"
                ) from None
            if expected_total is None:
                expected_total = total
                expected_pages = max(1, ceil(total / self.connector.page_size))
                if expected_pages > self.max_source_pages:
                    raise AssemblySubcommitteeReviewCoverageError(
                        "subcommittee-review pages exceed configured maximum"
                    )
            elif total != expected_total:
                raise AssemblySubcommitteeReviewCoverageError(
                    "subcommittee-review total changed during enumeration"
                )

            records = connector.parse_reviews(document)
            expected_rows = min(
                self.connector.page_size,
                max(0, total - (page_index - 1) * self.connector.page_size),
            )
            if len(records) != expected_rows:
                raise AssemblySubcommitteeReviewCoverageError(
                    "subcommittee-review page row count is incomplete"
                )
            for record in records:
                if record.assembly_age != self.connector.assembly_age:
                    raise AssemblySubcommitteeReviewCoverageError(
                        "subcommittee-review row AGE is inconsistent"
                    )
                records_by_bill[record.bill_id].append(record)
                pages_by_bill[record.bill_id].add(page_index)
            pages.append(ReviewPage(page_index, connector, document, records))
            page_index += 1

        if expected_total is None or expected_pages is None:
            raise AssemblySubcommitteeReviewCoverageError(
                "subcommittee-review universe was not initialized"
            )
        if sum(len(page.records) for page in pages) != expected_total:
            raise AssemblySubcommitteeReviewCoverageError(
                "subcommittee-review universe row coverage is incomplete"
            )

        packets: list[ReviewPacket] = []
        exact_duplicate_surplus = 0
        for bill_id in sorted(records_by_bill):
            packet = build_review_packet(
                bill_id,
                tuple(records_by_bill[bill_id]),
                tuple(sorted(pages_by_bill[bill_id])),
            )
            exact_duplicate_surplus += packet.duplicate_provider_rows
            packets.append(packet)

        by_anchor: dict[int, list[ReviewPacket]] = defaultdict(list)
        for packet in packets:
            by_anchor[packet.anchor_page].append(packet)
        packets_by_anchor = {
            page: tuple(sorted(items, key=lambda item: item.bill_id))
            for page, items in by_anchor.items()
        }

        fingerprint_payload = {
            "assembly_age": self.connector.assembly_age,
            "page_size": self.connector.page_size,
            "provider_row_count": expected_total,
            "page_count": expected_pages,
            "packets": [
                {
                    "bill_id": packet.bill_id,
                    "content_hash": packet.content_hash,
                    "anchor_page": packet.anchor_page,
                }
                for packet in packets
            ],
        }
        fingerprint = hashlib.sha256(
            json.dumps(
                fingerprint_payload,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        return (
            pages,
            packets_by_anchor,
            expected_total,
            exact_duplicate_surplus,
            fingerprint,
        )

    def _checkpoint_metadata(
        self,
        *,
        fingerprint: str,
        provider_row_count: int,
        packet_count: int,
        page_count: int,
        pages_committed: int,
        packets_committed: int,
        exact_duplicate_surplus_rows: int,
    ) -> dict[str, object]:
        return {
            "source_contract": self.SOURCE_CONTRACT,
            "assembly_age": self.connector.assembly_age,
            "page_size": self.connector.page_size,
            "universe_fingerprint": fingerprint,
            "provider_row_count": provider_row_count,
            "packet_count": packet_count,
            "page_count": page_count,
            "pages_committed": pages_committed,
            "packets_committed": packets_committed,
            "exact_duplicate_surplus_rows": exact_duplicate_surplus_rows,
        }

    def _resume_page(
        self,
        checkpoint,
        *,
        fingerprint: str,
        provider_row_count: int,
        packet_count: int,
        page_count: int,
    ) -> tuple[int, int]:
        metadata = checkpoint.metadata
        try:
            page = int(checkpoint.cursor)
            contract = str(metadata["source_contract"])
            age = int(metadata["assembly_age"])
            page_size = int(metadata["page_size"])
            checkpoint_fingerprint = str(metadata["universe_fingerprint"])
            row_count = int(metadata["provider_row_count"])
            packets = int(metadata["packet_count"])
            pages = int(metadata["page_count"])
            packets_committed = int(metadata["packets_committed"])
        except (KeyError, TypeError, ValueError):
            raise AssemblySubcommitteeReviewCoverageError(
                "subcommittee-review resume checkpoint is invalid"
            ) from None
        if (
            contract != self.SOURCE_CONTRACT
            or age != self.connector.assembly_age
            or page_size != self.connector.page_size
        ):
            raise AssemblySubcommitteeReviewCoverageError(
                "subcommittee-review resume scope is inconsistent"
            )
        if (
            checkpoint_fingerprint != fingerprint
            or row_count != provider_row_count
            or packets != packet_count
            or pages != page_count
        ):
            raise AssemblySubcommitteeReviewCoverageError(
                "subcommittee-review universe changed since checkpoint; start fresh"
            )
        if not 0 <= page < page_count:
            raise AssemblySubcommitteeReviewCoverageError(
                "subcommittee-review checkpoint is already complete or out of range"
            )
        return page + 1, packets_committed

    def enumerate(
        self, *, resume: bool = False
    ) -> AssemblySubcommitteeReviewEnumerationResult:
        if self.policy.domain != self.connector.HOST:
            raise PolicyDenied(
                "SourcePolicy domain does not match subcommittee-review connector"
            )
        require_policy(self.policy, PolicyAction.FETCH)
        require_policy(self.policy, PolicyAction.STORE_METADATA)
        self.repository.assert_ready()

        prior = self.repository.source_checkpoint(self.FEEDER, self.scope_key)
        run = self.repository.start_source_run(
            self.FEEDER,
            self.scope_key,
            {
                "source_contract": self.SOURCE_CONTRACT,
                "assembly_age": self.connector.assembly_age,
                "resume": resume,
                "max_pages": self.max_pages,
            },
        )
        committed_page_transactions = 0
        pages_this_run = 0
        try:
            (
                pages,
                packets_by_anchor,
                provider_row_count,
                exact_duplicate_surplus,
                fingerprint,
            ) = self._fetch_universe()
            packet_count = sum(len(items) for items in packets_by_anchor.values())
            page_count = len(pages)
            start_page = 1
            packets_committed = 0
            if resume:
                if prior is None:
                    raise AssemblySubcommitteeReviewCoverageError(
                        "no subcommittee-review checkpoint to resume from"
                    )
                start_page, packets_committed = self._resume_page(
                    prior,
                    fingerprint=fingerprint,
                    provider_row_count=provider_row_count,
                    packet_count=packet_count,
                    page_count=page_count,
                )

            last_page_committed = start_page - 1
            for page in pages:
                if page.page_index < start_page:
                    continue
                if self.max_pages is not None and pages_this_run >= self.max_pages:
                    break
                ingestion = IngestionPipeline(page.connector).ingest_document(
                    page.document, self.policy
                )
                packets = packets_by_anchor.get(page.page_index, ())
                observations = [
                    FeederObservation(
                        feeder=self.FEEDER,
                        scope_key=self.scope_key,
                        provider_record_key=packet.bill_id,
                        snapshot_id=ingestion.snapshot.id,
                        run_id=run.id,
                        provider_observed_at=None,
                        semantic_scope=self.SEMANTIC_SCOPE,
                        identity_hints={},
                        normalized=packet.normalized,
                        content_hash=packet.content_hash,
                    )
                    for packet in packets
                ]
                packets_committed += len(observations)
                self.repository.commit_source_page(
                    run_id=run.id,
                    policy=self.policy,
                    source=ingestion.source,
                    snapshot=ingestion.snapshot,
                    observations=observations,
                    cursor=str(page.page_index),
                    checkpoint_metadata=self._checkpoint_metadata(
                        fingerprint=fingerprint,
                        provider_row_count=provider_row_count,
                        packet_count=packet_count,
                        page_count=page_count,
                        pages_committed=page.page_index,
                        packets_committed=packets_committed,
                        exact_duplicate_surplus_rows=exact_duplicate_surplus,
                    ),
                )
                committed_page_transactions += 1
                pages_this_run += 1
                last_page_committed = page.page_index

            complete = last_page_committed == page_count
            if complete:
                finished = self.repository.finish_source_run(
                    run.id, SourceRunStatus.SUCCESS
                )
            else:
                finished = self.repository.finish_source_run(
                    run.id,
                    SourceRunStatus.PARTIAL,
                    error_code="MaxPagesReached",
                    error_summary=(
                        "Subcommittee-review enumeration stopped at the configured page budget"
                    ),
                )

            return AssemblySubcommitteeReviewEnumerationResult(
                run=finished,
                provider_row_count=provider_row_count,
                packet_count=packet_count,
                pages_committed_this_run=pages_this_run,
                pages_committed_total=last_page_committed,
                exact_duplicate_surplus_rows=exact_duplicate_surplus,
                complete=complete,
            )
        except Exception as exc:
            status = (
                SourceRunStatus.PARTIAL
                if committed_page_transactions
                else SourceRunStatus.FAILED
            )
            self.repository.finish_source_run(
                run.id,
                status,
                error_code=type(exc).__name__[:120],
                error_summary=(
                    "Assembly subcommittee-review enumeration did not complete"
                ),
            )
            raise


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Acquire all subcommittee bill-review rows for one National Assembly age "
            "as one packet observation per BILL_ID."
        )
    )
    parser.add_argument("--age", type=int, required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--enumerate", action="store_true")
    mode.add_argument("--resume", action="store_true")
    parser.add_argument("--page-size", type=int, default=1000)
    parser.add_argument("--max-pages", type=int)
    parser.add_argument("--max-source-pages", type=int, default=50)
    parser.add_argument("--database-url")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result = AssemblySubcommitteeReviewEnumerator(
            OpenAssemblySubcommitteeReviewConnector(
                assembly_age=args.age,
                page_size=args.page_size,
            ),
            SqlAlchemyRepository(args.database_url),
            max_pages=args.max_pages,
            max_source_pages=args.max_source_pages,
        ).enumerate(resume=args.resume)
    except (AssemblyApiError, PolicyDenied, ValueError) as exc:
        parser.error(str(exc))
    print(
        json.dumps(
            {
                "run_id": str(result.run.id),
                "status": result.run.status.value,
                "scope_key": result.run.scope_key,
                "provider_row_count": result.provider_row_count,
                "packet_count": result.packet_count,
                "pages_committed_this_run": result.pages_committed_this_run,
                "pages_committed_total": result.pages_committed_total,
                "exact_duplicate_surplus_rows": result.exact_duplicate_surplus_rows,
                "complete": result.complete,
                "observations_created": result.run.observations_created,
                "observations_unchanged": result.run.observations_unchanged,
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
