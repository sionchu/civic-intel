"""Acquisition-only per-meeting graph for one National Assembly age.

Universe: every CONF_ID of the meeting-universe lane (official plenary + committee minutes
indexes, re-fetched and validated on every run). For each CONF_ID, in canonical order:

    VCONFDETAIL   (exactly one row)
    VCONFBLLLIST  (agenda rows, every page)
    VCONFBILLLIST (bill rows, every page, scoped by CONF_ID)

One FeederObservation per CONF_ID carries the meeting detail, the agenda rows and the bill rows.
Exact edges are Meeting -> Agenda(BLL_NO) and Meeting -> Bill(BILL_ID). A BILL_ID that the
provider lists more than once inside one meeting with different bill names is recorded as a
provider conflict and excluded from the exact meeting -> bill edges. No Agenda -> Bill edge is
ever inferred. No Person, Organization or Claim is created.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass, fields, replace
from math import ceil
from typing import Any

from packages.connectors.base import ConnectorDocument
from packages.connectors.open_assembly import AssemblyApiError
from packages.connectors.open_assembly_bills import national_assembly_bill_policy
from packages.connectors.open_assembly_meetings import (
    AssemblyMeetingAgendaRecord,
    AssemblyMeetingBillRecord,
    AssemblyMeetingDetailRecord,
    OpenAssemblyMeetingAgendaConnector,
    OpenAssemblyMeetingBillConnector,
    OpenAssemblyMeetingDetailConnector,
    OpenAssemblyMinutesIndexConnector,
)
from packages.domain.contracts import FeederObservation, SourcePolicy, SourceRun
from packages.domain.enums import SourceRunStatus
from packages.persistence import SqlAlchemyRepository
from packages.verification.policy import PolicyAction, PolicyDenied, require_policy
from workers.assembly_meeting_universe import (
    AssemblyMeeting,
    AssemblyMeetingUniverseEnumerator,
)
from workers.ingest import IngestionPipeline


class AssemblyMeetingGraphCoverageError(AssemblyApiError):
    pass


@dataclass(frozen=True)
class MeetingGraphPage:
    connector: Any
    document: ConnectorDocument


@dataclass(frozen=True)
class AssemblyMeetingGraphEnumerationResult:
    run: SourceRun
    universe_meeting_count: int
    meetings_committed_this_run: int
    meetings_committed_total: int
    complete: bool
    bill_conflict_meetings: dict[str, list[str]]


DETAIL_FLAG_FIELDS = (
    "personnel_hearing",
    "public_hearing",
    "hearing",
    "joint_meeting",
    "presidential_delegated_speech",
    "presidential_policy_speech",
    "foreign_guest_speech",
)


def merge_detail_rows(
    rows: tuple[AssemblyMeetingDetailRecord, ...],
) -> tuple[AssemblyMeetingDetailRecord, list[dict[str, bool | None]]]:
    """One meeting may be published as several detail rows that differ only in the
    meeting-type Y/N flags (observed live: CONF_ID 053887 is one row with HRG_YN=Y and one with
    PBHRG_YN=Y). Any other difference fails closed. The merged flag is True when any row says Y;
    the per-row flag sets are kept verbatim."""

    if not rows:
        raise AssemblyMeetingGraphCoverageError("meeting detail returned no row")
    other = [f.name for f in fields(AssemblyMeetingDetailRecord) if f.name not in DETAIL_FLAG_FIELDS]
    first = rows[0]
    for row in rows[1:]:
        if any(getattr(row, name) != getattr(first, name) for name in other):
            raise AssemblyMeetingGraphCoverageError(
                "meeting detail rows disagree beyond the meeting-type flags"
            )
    flag_sets = [{name: getattr(row, name) for name in DETAIL_FLAG_FIELDS} for row in rows]
    merged: dict[str, Any] = {}
    for name in DETAIL_FLAG_FIELDS:
        values = [getattr(row, name) for row in rows]
        merged[name] = True if any(v is True for v in values) else (
            False if any(v is False for v in values) else None
        )
    return replace(first, **merged), flag_sets


def reconcile_meeting_bills(
    bills: tuple[AssemblyMeetingBillRecord, ...],
) -> dict[str, object]:
    """Collapse identical repeated rows; flag a BILL_ID listed with different bill rows."""

    variants: dict[str, dict[tuple[str, str | None], int]] = {}
    for bill in bills:
        key = (bill.bill_name, bill.link_url)
        per_id = variants.setdefault(bill.bill_id, {})
        per_id[key] = per_id.get(key, 0) + 1
    entries: list[dict[str, object]] = []
    conflicts: list[str] = []
    for bill_id in sorted(variants):
        if len(variants[bill_id]) > 1:
            conflicts.append(bill_id)
        for (name, url), count in sorted(variants[bill_id].items(), key=lambda kv: kv[0][0]):
            entries.append(
                {
                    "bill_id": bill_id,
                    "bill_name": name,
                    "link_url": url,
                    "provider_row_count": count,
                }
            )
    return {
        "bills": entries,
        "bill_row_total": len(bills),
        "duplicate_bill_rows": len(bills) - len(entries),
        "bill_id_conflicts": conflicts,
        "exact_bill_ids": [bill_id for bill_id in sorted(variants) if bill_id not in conflicts],
    }


def normalized_meeting_graph(
    meeting: AssemblyMeeting,
    detail: AssemblyMeetingDetailRecord,
    agendas: tuple[AssemblyMeetingAgendaRecord, ...],
    bills: tuple[AssemblyMeetingBillRecord, ...],
) -> dict[str, object]:
    detail_fields = asdict(detail)
    detail_fields["meeting_date"] = detail.meeting_date.isoformat()
    normalized: dict[str, object] = {
        **detail_fields,
        "minutes_number": meeting.first.minutes_number,
        "minutes_index": meeting.normalized()["minutes_index"],
        "agendas": [
            {
                "agenda_no": agenda.agenda_no,
                "agenda_name": agenda.agenda_name,
                "agenda_level": agenda.agenda_level,
            }
            for agenda in agendas
        ],
        "agenda_total": len(agendas),
        **reconcile_meeting_bills(bills),
        "agenda_to_bill_edges": 0,
        "graph_semantics": "official_meeting_scoped_agenda_and_bill_lists",
    }
    return normalized


def graph_content_hash(normalized: dict[str, object]) -> str:
    canonical = json.dumps(normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class AssemblyMeetingGraphEnumerator:
    FEEDER = "assembly_meeting_graph"
    SEMANTIC_SCOPE = "legislative_meeting_graph"
    SOURCE_CONTRACT = "assembly_age_meeting_graph_by_conf_id"

    def __init__(
        self,
        universe: AssemblyMeetingUniverseEnumerator,
        repository: SqlAlchemyRepository,
        policy: SourcePolicy | None = None,
        *,
        api_key: str | None = None,
        page_size: int = 1000,
        max_pages_per_list: int = 20,
        max_meetings: int | None = None,
        transport=None,
    ) -> None:
        if not 1 <= page_size <= 1000:
            raise ValueError("page_size must be between 1 and 1000")
        if max_pages_per_list < 1:
            raise ValueError("max_pages_per_list must be >= 1")
        if max_meetings is not None and max_meetings < 1:
            raise ValueError("max_meetings must be >= 1")
        self.universe = universe
        self.repository = repository
        self.policy = policy or national_assembly_bill_policy()
        self._api_key = api_key
        self.page_size = page_size
        self.max_pages_per_list = max_pages_per_list
        self.max_meetings = max_meetings
        self._transport = transport

    @property
    def assembly_age(self) -> int:
        return self.universe.connector.assembly_age

    @property
    def scope_key(self) -> str:
        return f"assembly_age:{self.assembly_age}"

    # -- fetching -----------------------------------------------------------------------

    def _connector(self, cls, meeting_id: str, page_index: int):
        return cls(
            meeting_id=meeting_id,
            api_key=self._api_key,
            page_index=page_index,
            page_size=self.page_size,
            transport=self._transport,
        )

    def _fetch_list(self, cls, meeting_id: str) -> list[MeetingGraphPage]:
        pages: list[MeetingGraphPage] = []
        expected_total: int | None = None
        page_index = 1
        while True:
            connector = self._connector(cls, meeting_id, page_index)
            document = connector.fetch(connector.discover()[0])
            raw_total = document.metadata.get("list_total_count", "")
            try:
                total = int(raw_total) if raw_total != "" else 0
            except ValueError:
                raise AssemblyMeetingGraphCoverageError(
                    f"{cls.LABEL} total count is invalid"
                ) from None
            if expected_total is None:
                expected_total = total
            elif total != expected_total:
                raise AssemblyMeetingGraphCoverageError(
                    f"{cls.LABEL} total count changed during enumeration"
                )
            expected_pages = max(1, ceil(total / self.page_size))
            if expected_pages > self.max_pages_per_list:
                raise AssemblyMeetingGraphCoverageError(
                    f"{cls.LABEL} pages exceed the configured maximum"
                )
            expected_rows = min(self.page_size, max(0, total - (page_index - 1) * self.page_size))
            if int(document.metadata.get("row_count", "0")) != expected_rows:
                raise AssemblyMeetingGraphCoverageError(f"{cls.LABEL} page row count is incomplete")
            pages.append(MeetingGraphPage(connector, document))
            if page_index >= expected_pages:
                return pages
            page_index += 1

    def _fetch_meeting(self, meeting: AssemblyMeeting) -> tuple[list[MeetingGraphPage], dict]:
        meeting_id = meeting.meeting_id
        detail_pages = self._fetch_list(OpenAssemblyMeetingDetailConnector, meeting_id)
        agenda_pages = self._fetch_list(OpenAssemblyMeetingAgendaConnector, meeting_id)
        bill_pages = self._fetch_list(OpenAssemblyMeetingBillConnector, meeting_id)
        detail_rows = tuple(
            item for page in detail_pages for item in page.connector.parse_detail_rows(page.document)
        )
        if not detail_rows:
            raise AssemblyMeetingGraphCoverageError("meeting detail must return at least one row")
        detail, detail_flag_sets = merge_detail_rows(detail_rows)
        detail_page = detail_pages[-1]
        agendas = tuple(
            item
            for page in agenda_pages
            for item in page.connector.parse_agendas(page.document)
        )
        bills = tuple(
            item
            for page in bill_pages
            for item in page.connector.parse_bills(page.document)
        )
        if detail.meeting_id != meeting_id:
            raise AssemblyMeetingGraphCoverageError("meeting detail CONF_ID is inconsistent")
        if detail.meeting_date != meeting.first.meeting_date:
            raise AssemblyMeetingGraphCoverageError(
                "meeting detail date disagrees with the minutes index"
            )
        context = (detail.assembly_term, detail.session, detail.degree)
        for record in (*agendas, *bills):
            if (record.assembly_term, record.session, record.degree) != context:
                raise AssemblyMeetingGraphCoverageError(
                    "agenda or bill row does not match the meeting context"
                )
        normalized = normalized_meeting_graph(meeting, detail, agendas, bills)
        normalized["detail_row_count"] = len(detail_rows)
        if len(detail_rows) > 1:
            normalized["detail_row_flag_sets"] = detail_flag_sets
        # The last detail snapshot carries the observation; other pages are committed first.
        return [*detail_pages[:-1], *agenda_pages, *bill_pages, detail_page], normalized

    # -- run ----------------------------------------------------------------------------

    def _checkpoint_metadata(
        self, fingerprint: str, count: int, committed: int, conflicts: dict[str, list[str]]
    ) -> dict[str, object]:
        return {
            "source_contract": self.SOURCE_CONTRACT,
            "assembly_age": self.assembly_age,
            "from_year": self.universe.from_year,
            "to_year": self.universe.to_year,
            "universe_fingerprint": fingerprint,
            "universe_meeting_count": count,
            "meetings_committed": committed,
            "bill_conflict_meetings": dict(sorted(conflicts.items())),
        }

    def _resume_position(self, checkpoint, fingerprint: str, count: int) -> int:
        metadata = checkpoint.metadata
        try:
            position = int(checkpoint.cursor)
            contract = str(metadata["source_contract"])
            age = int(metadata["assembly_age"])
            checkpoint_fingerprint = str(metadata["universe_fingerprint"])
            checkpoint_count = int(metadata["universe_meeting_count"])
        except (KeyError, TypeError, ValueError):
            raise AssemblyMeetingGraphCoverageError("resume checkpoint is invalid") from None
        if contract != self.SOURCE_CONTRACT or age != self.assembly_age:
            raise AssemblyMeetingGraphCoverageError("resume checkpoint scope is inconsistent")
        if checkpoint_fingerprint != fingerprint or checkpoint_count != count:
            raise AssemblyMeetingGraphCoverageError(
                "meeting universe changed since the checkpoint; start a fresh enumeration"
            )
        if not 0 <= position < count:
            raise AssemblyMeetingGraphCoverageError("resume checkpoint cursor is out of range")
        return position

    def enumerate(self, *, resume: bool = False) -> AssemblyMeetingGraphEnumerationResult:
        if self.policy.domain != OpenAssemblyMinutesIndexConnector.HOST:
            raise PolicyDenied("SourcePolicy domain does not match the meeting connectors")
        require_policy(self.policy, PolicyAction.FETCH)
        require_policy(self.policy, PolicyAction.STORE_METADATA)
        self.repository.assert_ready()
        prior = self.repository.source_checkpoint(self.FEEDER, self.scope_key)
        run = self.repository.start_source_run(
            self.FEEDER,
            self.scope_key,
            {
                "source_contract": self.SOURCE_CONTRACT,
                "assembly_age": self.assembly_age,
                "resume": resume,
                "max_meetings": self.max_meetings,
            },
        )
        commits = 0
        this_run = 0
        conflicts: dict[str, list[str]] = {}
        try:
            meetings, fingerprint = self.universe.fetch_meetings()
            count = len(meetings)
            position = 0
            if resume:
                if prior is None:
                    raise AssemblyMeetingGraphCoverageError("no checkpoint to resume from")
                position = self._resume_position(prior, fingerprint, count)
                stored = prior.metadata.get("bill_conflict_meetings") or {}
                if not isinstance(stored, dict):
                    raise AssemblyMeetingGraphCoverageError("resume checkpoint conflicts invalid")
                conflicts = {str(k): [str(x) for x in v] for k, v in stored.items()}
            while position < count:
                if self.max_meetings is not None and this_run >= self.max_meetings:
                    break
                meeting = meetings[position]
                pages, normalized = self._fetch_meeting(meeting)
                if normalized["bill_id_conflicts"]:
                    conflicts[meeting.meeting_id] = [
                        str(item) for item in normalized["bill_id_conflicts"]  # type: ignore[attr-defined]
                    ]
                for index, page in enumerate(pages):
                    last = index == len(pages) - 1
                    ingestion = IngestionPipeline(page.connector).ingest_document(
                        page.document, self.policy
                    )
                    observations = []
                    if last:
                        observations.append(
                            FeederObservation(
                                feeder=self.FEEDER,
                                scope_key=self.scope_key,
                                provider_record_key=meeting.meeting_id,
                                snapshot_id=ingestion.snapshot.id,
                                run_id=run.id,
                                provider_observed_at=None,
                                semantic_scope=self.SEMANTIC_SCOPE,
                                identity_hints={},
                                normalized=normalized,
                                content_hash=graph_content_hash(normalized),
                            )
                        )
                    committed = position + 1 if last else position
                    self.repository.commit_source_page(
                        run_id=run.id,
                        policy=self.policy,
                        source=ingestion.source,
                        snapshot=ingestion.snapshot,
                        observations=observations,
                        cursor=str(committed),
                        checkpoint_metadata=self._checkpoint_metadata(
                            fingerprint, count, committed, conflicts
                        ),
                    )
                    commits += 1
                position += 1
                this_run += 1
            complete = position == count
            if complete:
                finished = self.repository.finish_source_run(run.id, SourceRunStatus.SUCCESS)
            else:
                finished = self.repository.finish_source_run(
                    run.id,
                    SourceRunStatus.PARTIAL,
                    error_code="MaxMeetingsReached",
                    error_summary="Meeting graph enumeration stopped at the configured budget",
                )
            return AssemblyMeetingGraphEnumerationResult(
                run=finished,
                universe_meeting_count=count,
                meetings_committed_this_run=this_run,
                meetings_committed_total=position,
                complete=complete,
                bill_conflict_meetings=dict(sorted(conflicts.items())),
            )
        except Exception as exc:
            status = SourceRunStatus.PARTIAL if commits else SourceRunStatus.FAILED
            self.repository.finish_source_run(
                run.id,
                status,
                error_code=type(exc).__name__[:120],
                error_summary="Assembly meeting graph enumeration did not complete",
            )
            raise


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Acquire the per-meeting agenda/bill graph for every CONF_ID of one National "
            "Assembly age (acquisition only; no Person creation, no Claim publication)."
        )
    )
    parser.add_argument("--age", type=int, required=True)
    parser.add_argument("--from-year", type=int, required=True)
    parser.add_argument("--to-year", type=int)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--enumerate", action="store_true", help="Start a fresh enumeration.")
    mode.add_argument("--resume", action="store_true", help="Resume from the last meeting.")
    parser.add_argument("--max-meetings", type=int)
    parser.add_argument("--database-url")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        repository = SqlAlchemyRepository(args.database_url)
        universe = AssemblyMeetingUniverseEnumerator(
            OpenAssemblyMinutesIndexConnector(
                index_code=OpenAssemblyMinutesIndexConnector.COMMITTEE,
                assembly_age=args.age,
                year=args.from_year,
            ),
            repository,
            from_year=args.from_year,
            to_year=args.to_year,
        )
        result = AssemblyMeetingGraphEnumerator(
            universe, repository, max_meetings=args.max_meetings
        ).enumerate(resume=args.resume)
    except (AssemblyApiError, PolicyDenied, ValueError) as exc:
        parser.error(str(exc))
    print(
        json.dumps(
            {
                "run_id": str(result.run.id),
                "status": result.run.status.value,
                "scope_key": result.run.scope_key,
                "universe_meeting_count": result.universe_meeting_count,
                "meetings_committed_this_run": result.meetings_committed_this_run,
                "meetings_committed_total": result.meetings_committed_total,
                "complete": result.complete,
                "observations_created": result.run.observations_created,
                "observations_unchanged": result.run.observations_unchanged,
                "bill_conflict_meeting_count": len(result.bill_conflict_meetings),
                "bill_conflict_meetings": result.bill_conflict_meetings,
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
