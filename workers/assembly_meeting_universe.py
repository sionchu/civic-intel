"""Acquisition-only National Assembly meeting (CONF_ID) universe for one Assembly age.

Universe for one run: every CONF_ID listed by the official plenary minutes index
(``nzbyfwhwaoanttzje``) and committee minutes index (``ncwgseseafwbuheph``) for ``DAE_NUM=age``
across calendar years ``from_year .. to_year``. The run proves its lower bound by requiring the
year before ``from_year`` to be empty in both indexes.

One FeederObservation per CONF_ID. No Person, Organization or Claim is created; committee
names and DEPT_CD stay provider metadata. Agenda titles (SUB_NAME) stay in the snapshot only;
agenda rows belong to VCONFBLLLIST in the meeting-graph lane.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from math import ceil
from zoneinfo import ZoneInfo

from packages.connectors.base import ConnectorDocument
from packages.connectors.open_assembly import AssemblyApiError
from packages.connectors.open_assembly_bills import national_assembly_bill_policy
from packages.connectors.open_assembly_meetings import (
    AssemblyMinutesIndexRow,
    OpenAssemblyMinutesIndexConnector,
)
from packages.domain.contracts import FeederObservation, SourcePolicy, SourceRun
from packages.domain.enums import SourceRunStatus
from packages.persistence import SqlAlchemyRepository
from packages.verification.policy import PolicyAction, PolicyDenied, require_policy
from workers.ingest import IngestionPipeline

SEOUL = ZoneInfo("Asia/Seoul")
INDEX_KIND = {
    OpenAssemblyMinutesIndexConnector.PLENARY: "plenary",
    OpenAssemblyMinutesIndexConnector.COMMITTEE: "committee",
}


class AssemblyMeetingUniverseError(AssemblyApiError):
    pass


@dataclass(frozen=True)
class AssemblyMeeting:
    meeting_id: str
    first: AssemblyMinutesIndexRow
    agenda_row_count: int

    def normalized(self) -> dict[str, object]:
        row = self.first
        return {
            "meeting_id": self.meeting_id,
            "minutes_number": row.minutes_number,
            "assembly_age": row.assembly_age,
            "meeting_date": row.meeting_date.isoformat(),
            "minutes_index": INDEX_KIND[row.index_code],
            "class_name": row.class_name,
            "committee_name": row.committee_name,
            "committee_dept_code": row.committee_dept_code,
            "title": row.title,
            "minutes_pdf_url": row.minutes_pdf_url,
            "index_agenda_row_count": self.agenda_row_count,
            "meeting_semantics": "official_minutes_index_meeting",
        }


@dataclass(frozen=True)
class AssemblyMeetingUniverseResult:
    run: SourceRun
    from_year: int
    to_year: int
    index_row_count: int
    meeting_count: int
    meetings_by_index: dict[str, int]
    universe_fingerprint: str


def meeting_content_hash(normalized: dict[str, object]) -> str:
    canonical = json.dumps(normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def aggregate_meetings(rows: list[AssemblyMinutesIndexRow]) -> list[AssemblyMeeting]:
    """Group agenda rows by CONF_ID; any disagreement inside one CONF_ID fails closed."""

    first: dict[str, AssemblyMinutesIndexRow] = {}
    counts: Counter[str] = Counter()
    minutes_owner: dict[int, str] = {}
    for row in rows:
        existing = first.get(row.meeting_id)
        if existing is None:
            first[row.meeting_id] = row
        elif existing.meeting_signature() != row.meeting_signature():
            raise AssemblyMeetingUniverseError(
                "rows sharing one CONF_ID disagree on meeting fields"
            )
        owner = minutes_owner.setdefault(row.minutes_number, row.meeting_id)
        if owner != row.meeting_id:
            raise AssemblyMeetingUniverseError("one CONFER_NUM maps to more than one CONF_ID")
        counts[row.meeting_id] += 1
    return [
        AssemblyMeeting(meeting_id=key, first=first[key], agenda_row_count=counts[key])
        for key in sorted(first)
    ]


def universe_fingerprint(meetings: list[AssemblyMeeting]) -> str:
    payload = json.dumps(
        [item.normalized() for item in meetings],
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class AssemblyMeetingUniverseEnumerator:
    FEEDER = "assembly_meeting_universe"
    SEMANTIC_SCOPE = "legislative_meeting_index"
    SOURCE_CONTRACT = "assembly_age_minutes_index_conf_id_universe"
    INDEXES = (
        OpenAssemblyMinutesIndexConnector.PLENARY,
        OpenAssemblyMinutesIndexConnector.COMMITTEE,
    )

    def __init__(
        self,
        connector: OpenAssemblyMinutesIndexConnector,
        repository: SqlAlchemyRepository,
        policy: SourcePolicy | None = None,
        *,
        from_year: int,
        to_year: int | None = None,
        max_pages_per_year: int = 100,
    ) -> None:
        today = datetime.now(UTC).astimezone(SEOUL).date()
        to_year = today.year if to_year is None else to_year
        if from_year > to_year:
            raise ValueError("from_year must be <= to_year")
        if to_year > today.year:
            raise ValueError("to_year must not be in the future")
        if max_pages_per_year < 1:
            raise ValueError("max_pages_per_year must be >= 1")
        self.connector = connector
        self.repository = repository
        self.policy = policy or national_assembly_bill_policy()
        self.from_year = from_year
        self.to_year = to_year
        self.max_pages_per_year = max_pages_per_year

    @property
    def scope_key(self) -> str:
        return f"assembly_age:{self.connector.assembly_age}"

    def _index(self, index_code: str, year: int) -> OpenAssemblyMinutesIndexConnector:
        return OpenAssemblyMinutesIndexConnector(
            index_code=index_code,
            assembly_age=self.connector.assembly_age,
            year=year,
            api_key=self.connector._api_key,
            page_size=self.connector.page_size,
            transport=self.connector._transport,
        )

    def _fetch_year(
        self, base: OpenAssemblyMinutesIndexConnector
    ) -> list[tuple[OpenAssemblyMinutesIndexConnector, ConnectorDocument, tuple]]:
        pages: list[tuple[OpenAssemblyMinutesIndexConnector, ConnectorDocument, tuple]] = []
        expected_total: int | None = None
        page_index = 1
        while True:
            page = base.for_page(page_index)
            document = page.fetch(page.discover()[0])
            total = int(document.metadata["list_total_count"])
            if expected_total is None:
                expected_total = total
            elif total != expected_total:
                raise AssemblyMeetingUniverseError(
                    "minutes index total count changed during enumeration"
                )
            expected_pages = max(1, ceil(total / base.page_size))
            if expected_pages > self.max_pages_per_year:
                raise AssemblyMeetingUniverseError(
                    "minutes index pages exceed the configured maximum"
                )
            rows = page.parse_rows(document)
            expected_rows = min(base.page_size, max(0, total - (page_index - 1) * base.page_size))
            if len(rows) != expected_rows:
                raise AssemblyMeetingUniverseError("minutes index page row count is incomplete")
            pages.append((page, document, rows))
            if page_index >= expected_pages:
                return pages
            page_index += 1

    def _assert_lower_bound(self) -> None:
        for index_code in self.INDEXES:
            probe = self._index(index_code, self.from_year - 1)
            document = probe.fetch(probe.discover()[0])
            if document.metadata["list_total_count"] != "0":
                raise AssemblyMeetingUniverseError(
                    "the year before from_year still lists meetings; lower bound not proven"
                )

    def enumerate(self) -> AssemblyMeetingUniverseResult:
        if self.policy.domain != self.connector.HOST:
            raise PolicyDenied("SourcePolicy domain does not match the minutes index connector")
        require_policy(self.policy, PolicyAction.FETCH)
        require_policy(self.policy, PolicyAction.STORE_METADATA)
        self.repository.assert_ready()
        run = self.repository.start_source_run(
            self.FEEDER,
            self.scope_key,
            {
                "source_contract": self.SOURCE_CONTRACT,
                "assembly_age": self.connector.assembly_age,
                "from_year": self.from_year,
                "to_year": self.to_year,
            },
        )
        commits = 0
        try:
            # Fetch and validate the whole universe before committing anything.
            self._assert_lower_bound()
            pages: list[tuple[OpenAssemblyMinutesIndexConnector, ConnectorDocument, tuple]] = []
            for index_code in self.INDEXES:
                for year in range(self.from_year, self.to_year + 1):
                    pages.extend(self._fetch_year(self._index(index_code, year)))
            rows = [row for _, _, page_rows in pages for row in page_rows]
            meetings = aggregate_meetings(rows)
            fingerprint = universe_fingerprint(meetings)
            by_index = Counter(INDEX_KIND[item.first.index_code] for item in meetings)
            meeting_by_id = {item.meeting_id: item for item in meetings}

            # Each meeting is observed once, on the snapshot of the page carrying its first row.
            emitted: set[str] = set()
            for position, (page, document, page_rows) in enumerate(pages, start=1):
                ingestion = IngestionPipeline(page).ingest_document(document, self.policy)
                observations = []
                for row in page_rows:
                    if row.meeting_id in emitted:
                        continue
                    emitted.add(row.meeting_id)
                    normalized = meeting_by_id[row.meeting_id].normalized()
                    observations.append(
                        FeederObservation(
                            feeder=self.FEEDER,
                            scope_key=self.scope_key,
                            provider_record_key=row.meeting_id,
                            snapshot_id=ingestion.snapshot.id,
                            run_id=run.id,
                            provider_observed_at=datetime.combine(
                                row.meeting_date, datetime.min.time(), tzinfo=SEOUL
                            ),
                            semantic_scope=self.SEMANTIC_SCOPE,
                            identity_hints={},
                            normalized=normalized,
                            content_hash=meeting_content_hash(normalized),
                        )
                    )
                self.repository.commit_source_page(
                    run_id=run.id,
                    policy=self.policy,
                    source=ingestion.source,
                    snapshot=ingestion.snapshot,
                    observations=observations,
                    cursor=str(position),
                    checkpoint_metadata={
                        "source_contract": self.SOURCE_CONTRACT,
                        "assembly_age": self.connector.assembly_age,
                        "from_year": self.from_year,
                        "to_year": self.to_year,
                        "universe_fingerprint": fingerprint,
                        "universe_meeting_count": len(meetings),
                        "pages_committed": position,
                        "pages_total": len(pages),
                    },
                )
                commits += 1
            if emitted != set(meeting_by_id):
                raise AssemblyMeetingUniverseError("not every meeting was observed")
            completed = self.repository.finish_source_run(run.id, SourceRunStatus.SUCCESS)
            return AssemblyMeetingUniverseResult(
                run=completed,
                from_year=self.from_year,
                to_year=self.to_year,
                index_row_count=len(rows),
                meeting_count=len(meetings),
                meetings_by_index=dict(sorted(by_index.items())),
                universe_fingerprint=fingerprint,
            )
        except Exception as exc:
            status = SourceRunStatus.PARTIAL if commits else SourceRunStatus.FAILED
            self.repository.finish_source_run(
                run.id,
                status,
                error_code=type(exc).__name__[:120],
                error_summary="Assembly meeting universe enumeration did not complete",
            )
            raise


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Acquire one National Assembly age's CONF_ID meeting universe from the official "
            "plenary and committee minutes indexes (acquisition only)."
        )
    )
    parser.add_argument("--age", type=int, required=True)
    parser.add_argument(
        "--from-year",
        type=int,
        required=True,
        help="First calendar year; the prior year must be empty in both indexes.",
    )
    parser.add_argument("--to-year", type=int, help="Last calendar year (default: this year).")
    parser.add_argument("--page-size", type=int, default=1000)
    parser.add_argument("--database-url")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        connector = OpenAssemblyMinutesIndexConnector(
            index_code=OpenAssemblyMinutesIndexConnector.COMMITTEE,
            assembly_age=args.age,
            year=args.from_year,
            page_size=args.page_size,
        )
        result = AssemblyMeetingUniverseEnumerator(
            connector,
            SqlAlchemyRepository(args.database_url),
            from_year=args.from_year,
            to_year=args.to_year,
        ).enumerate()
    except (AssemblyApiError, PolicyDenied, ValueError) as exc:
        parser.error(str(exc))
    print(
        json.dumps(
            {
                "run_id": str(result.run.id),
                "status": result.run.status.value,
                "scope_key": result.run.scope_key,
                "from_year": result.from_year,
                "to_year": result.to_year,
                "index_row_count": result.index_row_count,
                "meeting_count": result.meeting_count,
                "meetings_by_index": result.meetings_by_index,
                "universe_fingerprint": result.universe_fingerprint,
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
