from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass

from packages.connectors.open_assembly_bills import national_assembly_bill_policy
from packages.connectors.open_assembly_meetings import (
    AssemblyMeetingAgendaRecord,
    AssemblyMeetingBillRecord,
    AssemblyMeetingDetailRecord,
    OpenAssemblyMeetingAgendaConnector,
    OpenAssemblyMeetingBillConnector,
    OpenAssemblyMeetingDetailConnector,
)
from packages.domain.contracts import SourcePolicy
from packages.verification.policy import PolicyAction, PolicyDenied, require_policy


class AssemblyMeetingGraphError(RuntimeError):
    pass


@dataclass(frozen=True)
class StagedAssemblyMeetingGraph:
    meeting: AssemblyMeetingDetailRecord
    agendas: tuple[AssemblyMeetingAgendaRecord, ...]
    bills: tuple[AssemblyMeetingBillRecord, ...]
    detail_total: int | None
    agenda_total: int | None
    bill_total: int | None
    sample_mode: bool

    def to_dict(self) -> dict[str, object]:
        meeting = asdict(self.meeting)
        meeting["meeting_date"] = self.meeting.meeting_date.isoformat()
        return {
            "meeting": meeting,
            "agendas": [asdict(item) for item in self.agendas],
            "bills": [asdict(item) for item in self.bills],
            "totals": {
                "detail": self.detail_total,
                "agendas": self.agenda_total,
                "bills": self.bill_total,
            },
            "sample_mode": self.sample_mode,
            "exact_edges": {
                "meeting_to_agendas": len(self.agendas),
                "meeting_to_bills": len(self.bills),
                "agenda_to_bill": 0,
            },
        }


class AssemblyMeetingGraphStager:
    def __init__(
        self,
        detail_connector: OpenAssemblyMeetingDetailConnector,
        agenda_connector: OpenAssemblyMeetingAgendaConnector,
        bill_connector: OpenAssemblyMeetingBillConnector,
        policy: SourcePolicy | None = None,
    ) -> None:
        self.detail_connector = detail_connector
        self.agenda_connector = agenda_connector
        self.bill_connector = bill_connector
        self.policy = policy or national_assembly_bill_policy()

    def _authorize(self) -> None:
        connectors = (
            self.detail_connector,
            self.agenda_connector,
            self.bill_connector,
        )
        if any(item.HOST != self.policy.domain for item in connectors):
            raise PolicyDenied(
                "SourcePolicy domain does not match National Assembly meeting connectors"
            )
        meeting_ids = {item.meeting_id for item in connectors}
        if len(meeting_ids) != 1:
            raise AssemblyMeetingGraphError("meeting graph connectors must share one CONF_ID")
        if self.bill_connector.has_bill_filter:
            raise AssemblyMeetingGraphError(
                "meeting graph bill source must not filter BILL_ID"
            )
        sample_modes = {item.sample_mode for item in connectors}
        if len(sample_modes) != 1:
            raise AssemblyMeetingGraphError(
                "meeting graph connectors must share one sample-mode boundary"
            )
        require_policy(self.policy, PolicyAction.FETCH)

    @staticmethod
    def _total(document) -> int | None:
        value = document.metadata.get("list_total_count", "")
        return int(value) if value else None

    @staticmethod
    def _context(record) -> tuple[str, str, str, str]:
        return (
            record.meeting_id,
            record.assembly_term,
            record.session,
            record.degree,
        )

    def stage(self) -> StagedAssemblyMeetingGraph:
        self._authorize()
        detail_document = self.detail_connector.fetch(
            self.detail_connector.discover()[0]
        )
        agenda_document = self.agenda_connector.fetch(
            self.agenda_connector.discover()[0]
        )
        bill_document = self.bill_connector.fetch(
            self.bill_connector.discover()[0]
        )

        meeting = self.detail_connector.parse_detail(detail_document)
        agendas = self.agenda_connector.parse_agendas(agenda_document)
        bills = self.bill_connector.parse_bills(bill_document)

        expected_context = self._context(meeting)
        for agenda in agendas:
            if self._context(agenda) != expected_context:
                raise AssemblyMeetingGraphError(
                    "agenda row does not match meeting context"
                )
        for bill in bills:
            if self._context(bill) != expected_context:
                raise AssemblyMeetingGraphError(
                    "bill row does not match meeting context"
                )

        detail_total = self._total(detail_document)
        if detail_total != 1:
            raise AssemblyMeetingGraphError(
                "meeting-detail total must be exactly one"
            )
        return StagedAssemblyMeetingGraph(
            meeting=meeting,
            agendas=agendas,
            bills=bills,
            detail_total=detail_total,
            agenda_total=self._total(agenda_document),
            bill_total=self._total(bill_document),
            sample_mode=self.detail_connector.sample_mode,
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Stage one official National Assembly meeting/agenda/bill graph."
    )
    parser.add_argument("--meeting-id", required=True)
    parser.add_argument("--sample", action="store_true")
    parser.add_argument("--page-index", type=int, default=1)
    parser.add_argument("--page-size", type=int, default=100)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    page_index = 1 if args.sample else args.page_index
    page_size = 5 if args.sample else args.page_size
    try:
        kwargs = {
            "meeting_id": args.meeting_id,
            "page_index": page_index,
            "page_size": page_size,
            "sample_mode": args.sample,
        }
        graph = AssemblyMeetingGraphStager(
            OpenAssemblyMeetingDetailConnector(**kwargs),
            OpenAssemblyMeetingAgendaConnector(**kwargs),
            OpenAssemblyMeetingBillConnector(**kwargs),
        ).stage()
    except (PolicyDenied, ValueError, RuntimeError) as exc:
        parser.error(str(exc))
    print(
        json.dumps(
            graph.to_dict(),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
