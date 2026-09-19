from __future__ import annotations

import argparse
import json
from datetime import date

from packages.connectors.open_assembly import AssemblyApiError, MissingAssemblyApiKey
from packages.connectors.open_assembly_schedule import (
    AssemblyScheduleRecord,
    OpenAssemblyScheduleConnector,
)


def _safe_record(record: AssemblyScheduleRecord) -> dict[str, object]:
    return {
        "schedule_date": record.schedule_date.isoformat(),
        "schedule_kind": record.schedule_kind,
        "schedule_time": record.schedule_time,
        "committee_name": record.committee_name,
        "content": record.content,
        "place": record.place,
        "session": record.session,
        "degree": record.degree,
    }


def build_probe_report(
    *,
    connector: OpenAssemblyScheduleConnector,
) -> dict[str, object]:
    document = connector.fetch(connector.discover()[0])
    records = connector.parse_schedules(document)
    candidates = connector.gukgam_candidates(records)
    return {
        "status": "READ_ONLY_PROBE",
        "api_code": connector.API_CODE,
        "source_contract": document.metadata.get("source_contract"),
        "query": {
            "schedule_date": (
                connector.schedule_date.isoformat()
                if connector.schedule_date is not None
                else None
            ),
            "committee": connector.committee,
            "page_size": connector.page_size,
        },
        "provider": {
            "result_code": document.metadata.get("result_code"),
            "list_total_count": document.metadata.get("list_total_count"),
            "row_count": document.metadata.get("row_count"),
        },
        "gukgam_candidate_count": len(candidates),
        "gukgam_candidates": [_safe_record(record) for record in candidates],
        "semantics": (
            "DISCOVERY_ONLY; schedule candidates do not publish audited organizations, "
            "witnesses, reference persons, or identity links"
        ),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Read one bounded National Assembly schedule slice and print safe Gukgam "
            "discovery candidates without persistence."
        )
    )
    parser.add_argument("--date", type=date.fromisoformat, required=True)
    parser.add_argument("--committee", required=True)
    parser.add_argument("--page-size", type=int, default=10)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.committee.strip():
        parser.error("--committee must not be empty")
    if not 1 <= args.page_size <= 100:
        parser.error("--page-size must be between 1 and 100")

    connector = OpenAssemblyScheduleConnector(
        schedule_date=args.date,
        committee=args.committee.strip(),
        page_size=args.page_size,
    )
    try:
        report = build_probe_report(connector=connector)
    except (AssemblyApiError, MissingAssemblyApiKey, ValueError) as exc:
        parser.error(str(exc))

    print(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
