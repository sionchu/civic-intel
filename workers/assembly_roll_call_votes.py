"""Acquisition-only National Assembly plenary roll-call vote enumerator.

Universe for one run: every bill listed by 의안별 표결현황 (``ncocpgfiaoituanbr``) for one
Assembly term x every member row that 국회의원 본회의 표결정보 (``nojepdqqaweusdfbi``)
publishes for that bill. This module never creates Persons and never publishes Claims.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from dataclasses import dataclass
from math import ceil

from packages.connectors.base import ConnectorDocument
from packages.connectors.open_assembly import AssemblyApiError
from packages.connectors.open_assembly_votes import (
    AssemblyBillVoteSummary,
    AssemblyMemberVoteRecord,
    OpenAssemblyBillVoteSummaryConnector,
    OpenAssemblyMemberVoteConnector,
    RollCallVoteValue,
    national_assembly_roll_call_vote_policy,
)
from packages.domain.contracts import FeederObservation, SourcePolicy, SourceRun
from packages.domain.enums import SourceRunStatus
from packages.persistence import SqlAlchemyRepository
from packages.verification.policy import PolicyAction, PolicyDenied, require_policy
from workers.ingest import IngestionPipeline
from workers.legislative_activity import _safe_detail_url


class AssemblyRollCallCoverageError(AssemblyApiError):
    pass


@dataclass(frozen=True)
class AssemblyRollCallEnumerationResult:
    run: SourceRun
    universe_bill_count: int
    bills_committed_this_run: int
    bills_committed_total: int
    complete: bool


def normalized_member_vote(record: AssemblyMemberVoteRecord) -> dict[str, object]:
    return {
        "bill_id": record.bill_id,
        "bill_no": record.bill_no,
        "bill_name": record.bill_name,
        "assembly_age": record.assembly_age,
        "member_code": record.member_code,
        "vote_value_published": record.vote_value_published,
        "vote_value": record.vote_value.value,
        "vote_datetime_published": record.vote_datetime_published,
        "vote_datetime": record.vote_datetime.isoformat(),
        "session_code": record.session_code,
        "sitting_number": record.sitting_number,
        "committee": record.committee,
        "committee_id": record.committee_id,
        "bill_url": _safe_detail_url(record.bill_url),
        "vote_semantics": "official_member_plenary_roll_call_record",
    }


def roll_call_content_hash(normalized: dict[str, object]) -> str:
    canonical = json.dumps(normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def universe_fingerprint(summaries: list[AssemblyBillVoteSummary]) -> str:
    payload = json.dumps(
        [item.fingerprint_fields() for item in summaries],
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _member_vote_identity_hints(record: AssemblyMemberVoteRecord) -> dict[str, object]:
    return {
        "record_kind": "single_person_roll_call_vote",
        "participants": [
            {
                "external_id_namespace": "assembly_mona_cd",
                "external_id": record.member_code,
                "role": "VOTER",
            }
        ],
    }


def validate_bill_tallies(
    summary: AssemblyBillVoteSummary, records: list[AssemblyMemberVoteRecord]
) -> None:
    """Member rows must reproduce the bill's published tallies exactly."""

    counts = Counter(record.vote_value for record in records)
    yes = counts[RollCallVoteValue.YES]
    no = counts[RollCallVoteValue.NO]
    abstain = counts[RollCallVoteValue.ABSTAIN]
    if yes != summary.yes_total or no != summary.no_total or abstain != summary.abstain_total:
        raise AssemblyRollCallCoverageError(
            "member vote rows do not reproduce the published YES/NO/ABSTAIN tallies"
        )
    if yes + no + abstain != summary.vote_total:
        raise AssemblyRollCallCoverageError(
            "member vote rows do not reproduce the published vote total"
        )
    if len(records) != summary.member_total:
        raise AssemblyRollCallCoverageError(
            "member vote row count does not match the published member total"
        )


class AssemblyRollCallVoteEnumerator:
    FEEDER = "assembly_plenary_roll_call_votes"
    SEMANTIC_SCOPE = "legislative_plenary_roll_call_vote"
    SOURCE_CONTRACT = "assembly_term_plenary_roll_call_votes"

    def __init__(
        self,
        connector: OpenAssemblyBillVoteSummaryConnector,
        repository: SqlAlchemyRepository,
        policy: SourcePolicy | None = None,
        *,
        member_page_size: int = 1000,
        max_universe_pages: int = 50,
        max_bills: int | None = None,
    ) -> None:
        if max_universe_pages < 1:
            raise ValueError("max_universe_pages must be >= 1")
        if max_bills is not None and max_bills < 1:
            raise ValueError("max_bills must be >= 1")
        if not 1 <= member_page_size <= 1000:
            raise ValueError("member_page_size must be between 1 and 1000")
        self.connector = connector
        self.repository = repository
        self.policy = policy or national_assembly_roll_call_vote_policy()
        self.member_page_size = member_page_size
        self.max_universe_pages = max_universe_pages
        self.max_bills = max_bills

    @property
    def scope_key(self) -> str:
        return f"assembly_age:{self.connector.assembly_age}"

    # -- universe -----------------------------------------------------------------------

    def _fetch_universe(
        self,
    ) -> tuple[
        list[AssemblyBillVoteSummary],
        list[tuple[OpenAssemblyBillVoteSummaryConnector, ConnectorDocument]],
    ]:
        summaries: list[AssemblyBillVoteSummary] = []
        pages: list[tuple[OpenAssemblyBillVoteSummaryConnector, ConnectorDocument]] = []
        expected_total: int | None = None
        expected_pages: int | None = None
        page_index = 1
        while True:
            page_connector = self.connector.for_page(page_index)
            document = page_connector.fetch(page_connector.discover()[0])
            metadata = document.metadata
            if metadata.get("api_code") != self.connector.API_CODE:
                raise AssemblyRollCallCoverageError("vote summary source contract is inconsistent")
            if metadata.get("assembly_age") != str(self.connector.assembly_age):
                raise AssemblyRollCallCoverageError("vote summary scope is inconsistent")
            if metadata.get("page_index") != str(page_index):
                raise AssemblyRollCallCoverageError("vote summary requested page is inconsistent")
            if metadata.get("page_size") != str(self.connector.page_size):
                raise AssemblyRollCallCoverageError(
                    "vote summary requested page size is inconsistent"
                )
            try:
                total = int(metadata["list_total_count"])
            except (KeyError, TypeError, ValueError):
                raise AssemblyRollCallCoverageError(
                    "vote summary total count is unavailable"
                ) from None
            if total < 0:
                raise AssemblyRollCallCoverageError("vote summary total count must not be negative")
            current_pages = max(1, ceil(total / self.connector.page_size))
            if current_pages > self.max_universe_pages:
                raise AssemblyRollCallCoverageError(
                    "vote summary expected pages exceed the configured maximum"
                )
            if expected_total is None:
                expected_total, expected_pages = total, current_pages
            elif total != expected_total:
                raise AssemblyRollCallCoverageError(
                    "vote summary total count changed during enumeration"
                )
            assert expected_pages is not None
            page_rows = self.connector.parse_summaries(document)
            expected_rows = min(
                self.connector.page_size,
                max(0, expected_total - (page_index - 1) * self.connector.page_size),
            )
            if len(page_rows) != expected_rows:
                raise AssemblyRollCallCoverageError("vote summary page row count is incomplete")
            summaries.extend(page_rows)
            pages.append((page_connector, document))
            if page_index == expected_pages:
                break
            page_index += 1

        seen: dict[str, AssemblyBillVoteSummary] = {}
        for summary in summaries:
            if summary.assembly_age != self.connector.assembly_age:
                raise AssemblyRollCallCoverageError("vote summary row Assembly age is inconsistent")
            existing = seen.get(summary.bill_id)
            if existing is not None:
                if existing != summary:
                    raise AssemblyRollCallCoverageError("conflicting BILL_ID in vote summary")
                raise AssemblyRollCallCoverageError("duplicate BILL_ID in vote summary")
            if summary.yes_total + summary.no_total + summary.abstain_total != summary.vote_total:
                raise AssemblyRollCallCoverageError(
                    "vote summary tallies do not add up to the published vote total"
                )
            if summary.vote_total > summary.member_total:
                raise AssemblyRollCallCoverageError(
                    "vote summary vote total exceeds the published member total"
                )
            if summary.member_total > self.member_page_size:
                raise AssemblyRollCallCoverageError(
                    "bill member total exceeds one member-vote page"
                )
            seen[summary.bill_id] = summary
        # Canonical order: provider order is newest-first and shifts as votes are added.
        summaries.sort(key=lambda item: item.bill_id)
        return summaries, pages

    # -- per-bill -----------------------------------------------------------------------

    def _fetch_bill_votes(
        self, summary: AssemblyBillVoteSummary
    ) -> tuple[OpenAssemblyMemberVoteConnector, ConnectorDocument, list[AssemblyMemberVoteRecord]]:
        connector = self.connector.member_votes(summary.bill_id, page_size=self.member_page_size)
        document = connector.fetch(connector.discover()[0])
        metadata = document.metadata
        if metadata.get("api_code") != OpenAssemblyMemberVoteConnector.API_CODE:
            raise AssemblyRollCallCoverageError("member vote source contract is inconsistent")
        if metadata.get("assembly_age") != str(self.connector.assembly_age):
            raise AssemblyRollCallCoverageError("member vote scope is inconsistent")
        if metadata.get("BILL_ID") != summary.bill_id:
            raise AssemblyRollCallCoverageError("member vote requested bill is inconsistent")
        if metadata.get("page_index") != "1" or metadata.get("page_size") != str(
            self.member_page_size
        ):
            raise AssemblyRollCallCoverageError("member vote requested page is inconsistent")
        try:
            total = int(metadata["list_total_count"])
        except (KeyError, TypeError, ValueError):
            raise AssemblyRollCallCoverageError("member vote total count is unavailable") from None
        if total > self.member_page_size:
            raise AssemblyRollCallCoverageError("member vote rows exceed one page")
        records = connector.parse_votes(document)
        if len(records) != total:
            raise AssemblyRollCallCoverageError("member vote page row count is incomplete")

        by_member: dict[str, AssemblyMemberVoteRecord] = {}
        for record in records:
            if record.bill_id != summary.bill_id:
                raise AssemblyRollCallCoverageError("member vote row BILL_ID is inconsistent")
            if record.assembly_age != self.connector.assembly_age:
                raise AssemblyRollCallCoverageError("member vote row Assembly age is inconsistent")
            existing = by_member.get(record.member_code)
            if existing is not None:
                if normalized_member_vote(existing) != normalized_member_vote(record):
                    raise AssemblyRollCallCoverageError(
                        "conflicting MONA_CD appears within one bill"
                    )
                raise AssemblyRollCallCoverageError("duplicate MONA_CD appears within one bill")
            by_member[record.member_code] = record
        validate_bill_tallies(summary, records)
        return connector, document, records

    # -- run ----------------------------------------------------------------------------

    def _checkpoint_metadata(
        self, fingerprint: str, bill_count: int, bills_committed: int
    ) -> dict[str, object]:
        return {
            "source_contract": self.SOURCE_CONTRACT,
            "assembly_age": self.connector.assembly_age,
            "summary_page_size": self.connector.page_size,
            "member_page_size": self.member_page_size,
            "universe_fingerprint": fingerprint,
            "universe_bill_count": bill_count,
            "bills_committed": bills_committed,
        }

    def _resume_position(self, checkpoint, fingerprint: str, bill_count: int) -> int:
        if checkpoint.cursor is None:
            raise AssemblyRollCallCoverageError("resume checkpoint lacks a bill cursor")
        metadata = checkpoint.metadata
        try:
            position = int(checkpoint.cursor)
            source_contract = str(metadata["source_contract"])
            checkpoint_age = int(metadata["assembly_age"])
            summary_page_size = int(metadata["summary_page_size"])
            member_page_size = int(metadata["member_page_size"])
            checkpoint_fingerprint = str(metadata["universe_fingerprint"])
            checkpoint_count = int(metadata["universe_bill_count"])
        except (KeyError, TypeError, ValueError):
            raise AssemblyRollCallCoverageError("resume checkpoint metadata is invalid") from None
        if source_contract != self.SOURCE_CONTRACT:
            raise AssemblyRollCallCoverageError("resume checkpoint source contract is inconsistent")
        if checkpoint_age != self.connector.assembly_age:
            raise AssemblyRollCallCoverageError("resume checkpoint Assembly age is inconsistent")
        if (
            summary_page_size != self.connector.page_size
            or member_page_size != self.member_page_size
        ):
            raise AssemblyRollCallCoverageError("resume checkpoint page size is inconsistent")
        if checkpoint_fingerprint != fingerprint or checkpoint_count != bill_count:
            raise AssemblyRollCallCoverageError(
                "vote universe changed since the checkpoint; start a fresh enumeration"
            )
        if not 0 <= position <= bill_count:
            raise AssemblyRollCallCoverageError("resume checkpoint cursor is out of range")
        if position == bill_count:
            raise AssemblyRollCallCoverageError(
                "resume checkpoint already covers the full Assembly term"
            )
        return position

    def enumerate(self, *, resume: bool = False) -> AssemblyRollCallEnumerationResult:
        if self.connector.page_index != 1:
            raise AssemblyRollCallCoverageError("roll-call enumeration must start at page 1")
        if self.policy.domain != self.connector.HOST:
            raise PolicyDenied("SourcePolicy domain does not match National Assembly vote connector")
        require_policy(self.policy, PolicyAction.FETCH)
        require_policy(self.policy, PolicyAction.STORE_METADATA)

        self.repository.assert_ready()
        prior_checkpoint = self.repository.source_checkpoint(self.FEEDER, self.scope_key)
        run = self.repository.start_source_run(
            self.FEEDER,
            self.scope_key,
            {
                "source_contract": self.SOURCE_CONTRACT,
                "assembly_age": self.connector.assembly_age,
                "resume": resume,
                "max_bills": self.max_bills,
            },
        )
        commits = 0
        bills_this_run = 0
        try:
            summaries, universe_pages = self._fetch_universe()
            fingerprint = universe_fingerprint(summaries)
            bill_count = len(summaries)
            if resume and prior_checkpoint is not None:
                position = self._resume_position(prior_checkpoint, fingerprint, bill_count)
            else:
                position = 0
                # A fresh run records the summary pages that define the universe and tallies.
                for page_connector, document in universe_pages:
                    ingestion = IngestionPipeline(page_connector).ingest_document(
                        document, self.policy
                    )
                    self.repository.commit_source_page(
                        run_id=run.id,
                        policy=self.policy,
                        source=ingestion.source,
                        snapshot=ingestion.snapshot,
                        observations=[],
                        cursor="0",
                        checkpoint_metadata=self._checkpoint_metadata(fingerprint, bill_count, 0),
                    )
                    commits += 1

            while position < bill_count:
                if self.max_bills is not None and bills_this_run >= self.max_bills:
                    break
                summary = summaries[position]
                connector, document, records = self._fetch_bill_votes(summary)
                ingestion = IngestionPipeline(connector).ingest_document(document, self.policy)
                observations = []
                for record in records:
                    normalized = normalized_member_vote(record)
                    observations.append(
                        FeederObservation(
                            feeder=self.FEEDER,
                            scope_key=self.scope_key,
                            provider_record_key=record.provider_record_key,
                            snapshot_id=ingestion.snapshot.id,
                            run_id=run.id,
                            provider_observed_at=record.vote_datetime,
                            semantic_scope=self.SEMANTIC_SCOPE,
                            identity_hints=_member_vote_identity_hints(record),
                            normalized=normalized,
                            content_hash=roll_call_content_hash(normalized),
                        )
                    )
                position += 1
                self.repository.commit_source_page(
                    run_id=run.id,
                    policy=self.policy,
                    source=ingestion.source,
                    snapshot=ingestion.snapshot,
                    observations=observations,
                    cursor=str(position),
                    checkpoint_metadata=self._checkpoint_metadata(
                        fingerprint, bill_count, position
                    ),
                )
                commits += 1
                bills_this_run += 1

            complete = position == bill_count
            if complete:
                completed = self.repository.finish_source_run(run.id, SourceRunStatus.SUCCESS)
            else:
                completed = self.repository.finish_source_run(
                    run.id,
                    SourceRunStatus.PARTIAL,
                    error_code="MaxBillsReached",
                    error_summary="Roll-call enumeration stopped at the configured bill budget",
                )
            return AssemblyRollCallEnumerationResult(
                run=completed,
                universe_bill_count=bill_count,
                bills_committed_this_run=bills_this_run,
                bills_committed_total=position,
                complete=complete,
            )
        except Exception as exc:
            status = SourceRunStatus.PARTIAL if commits else SourceRunStatus.FAILED
            self.repository.finish_source_run(
                run.id,
                status,
                error_code=type(exc).__name__[:120],
                error_summary="Assembly roll-call vote enumeration did not complete",
            )
            raise


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Acquire one National Assembly term's plenary roll-call votes (acquisition only; "
            "no Person creation, no Claim publication)."
        )
    )
    parser.add_argument("--age", type=int, required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--enumerate", action="store_true", help="Start a fresh term enumeration.")
    mode.add_argument("--resume", action="store_true", help="Resume from the last committed bill.")
    parser.add_argument(
        "--max-bills",
        type=int,
        help="Process at most N bills in this invocation; the run ends PARTIAL if unfinished.",
    )
    parser.add_argument("--page-size", type=int, default=1000, help="Vote-summary page size.")
    parser.add_argument("--max-universe-pages", type=int, default=50)
    parser.add_argument("--database-url")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        connector = OpenAssemblyBillVoteSummaryConnector(
            assembly_age=args.age, page_size=args.page_size
        )
        result = AssemblyRollCallVoteEnumerator(
            connector,
            SqlAlchemyRepository(args.database_url),
            max_universe_pages=args.max_universe_pages,
            max_bills=args.max_bills,
        ).enumerate(resume=args.resume)
    except (AssemblyApiError, PolicyDenied, ValueError) as exc:
        parser.error(str(exc))
    print(
        json.dumps(
            {
                "run_id": str(result.run.id),
                "status": result.run.status.value,
                "scope_key": result.run.scope_key,
                "universe_bill_count": result.universe_bill_count,
                "bills_committed_this_run": result.bills_committed_this_run,
                "bills_committed_total": result.bills_committed_total,
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
