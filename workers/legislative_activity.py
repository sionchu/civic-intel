from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import dataclass
from datetime import date

from packages.connectors.open_assembly import AssemblyApiError
from packages.connectors.open_assembly_bills import (
    AssemblyBillRecord,
    OpenAssemblyBillConnector,
    national_assembly_bill_policy,
)
from packages.domain.contracts import SourcePolicy
from packages.verification.identity import IdentityCandidate
from packages.verification.policy import PolicyAction, PolicyDenied, require_policy


def _member_code(candidate: IdentityCandidate) -> str | None:
    prefix = "assembly_member_code:"
    for anchor in candidate.career_anchors:
        if anchor.startswith(prefix) and anchor[len(prefix) :]:
            return anchor[len(prefix) :]
    return None


@dataclass(frozen=True)
class StagedLegislativeBill:
    bill_id: str
    bill_no: str | None
    bill_name: str
    proposed_date: date | None
    committee: str | None
    process_result: str | None
    role: str | None
    representative_proposers: tuple[str, ...]
    co_proposers: tuple[str, ...]

    @classmethod
    def from_record(cls, record: AssemblyBillRecord, person_name: str) -> StagedLegislativeBill:
        return cls(
            bill_id=record.bill_id,
            bill_no=record.bill_no,
            bill_name=record.bill_name,
            proposed_date=record.proposed_date,
            committee=record.committee,
            process_result=record.process_result,
            role=record.role_for(person_name),
            representative_proposers=record.representative_proposers,
            co_proposers=record.co_proposers,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "bill_id": self.bill_id,
            "bill_no": self.bill_no,
            "bill_name": self.bill_name,
            "proposed_date": self.proposed_date.isoformat() if self.proposed_date else None,
            "committee": self.committee,
            "process_result": self.process_result,
            "role": self.role,
            "representative_proposers": list(self.representative_proposers),
            "co_proposers": list(self.co_proposers),
        }


@dataclass(frozen=True)
class LegislativeActivitySummary:
    canonical_name: str
    member_code: str
    assembly_age: int
    source_total_count: int | None
    coverage_complete: bool
    staged_bill_count: int
    representative_sponsored_count: int | None
    co_sponsored_count: int | None
    co_sponsor_coverage_complete: bool
    page_process_result_counts: dict[str, int]
    bills: tuple[StagedLegislativeBill, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "canonical_name": self.canonical_name,
            "member_code": self.member_code,
            "assembly_age": self.assembly_age,
            "coverage": {
                "complete": self.coverage_complete,
                "source_total_count": self.source_total_count,
                "co_sponsor_complete": self.co_sponsor_coverage_complete,
            },
            "counts": {
                "staged_bills": self.staged_bill_count,
                "representative_sponsored": self.representative_sponsored_count,
                "co_sponsored": self.co_sponsored_count,
                "page_process_results": self.page_process_result_counts,
            },
            "bills": [item.to_dict() for item in self.bills],
        }


class LegislativeActivityStager:
    def __init__(
        self,
        candidate: IdentityCandidate,
        connector: OpenAssemblyBillConnector,
        policy: SourcePolicy | None = None,
    ) -> None:
        member_code = _member_code(candidate)
        if not member_code:
            raise ValueError("legislative staging requires assembly_member_code identity anchor")
        self.candidate = candidate
        self.member_code = member_code
        self.connector = connector
        self.policy = policy or national_assembly_bill_policy()

    def stage(self, url: str | None = None) -> LegislativeActivitySummary:
        if self.policy.domain != self.connector.HOST:
            raise PolicyDenied("SourcePolicy domain does not match National Assembly bill connector")
        require_policy(self.policy, PolicyAction.FETCH)
        target = url or self.connector.discover()[0]
        document = self.connector.fetch(target)
        records = self.connector.parse_bills(document)
        bills = tuple(
            StagedLegislativeBill.from_record(record, self.candidate.canonical_name)
            for record in records
        )

        total_text = document.metadata.get("list_total_count")
        try:
            total_count = int(total_text) if total_text else None
        except ValueError:
            total_count = None
        page_index = int(document.metadata.get("page_index", "1"))
        page_size = int(document.metadata.get("page_size", "100"))
        coverage_complete = page_index == 1 and total_count is not None and total_count <= page_size

        proposer_filter = document.metadata.get("PROPOSER")
        exact_representative_scope = (
            coverage_complete
            and proposer_filter == self.candidate.canonical_name
            and all(item.role == "LEAD" for item in bills)
        )
        representative_count = len(bills) if exact_representative_scope else None

        result_counts = Counter(item.process_result or "UNKNOWN" for item in bills)
        return LegislativeActivitySummary(
            canonical_name=self.candidate.canonical_name,
            member_code=self.member_code,
            assembly_age=self.connector.assembly_age,
            source_total_count=total_count,
            coverage_complete=coverage_complete,
            staged_bill_count=len(bills),
            representative_sponsored_count=representative_count,
            co_sponsored_count=None,
            co_sponsor_coverage_complete=False,
            page_process_result_counts=dict(sorted(result_counts.items())),
            bills=bills,
        )


def render_legislative_json(summary: LegislativeActivitySummary) -> str:
    return json.dumps(summary.to_dict(), ensure_ascii=False, indent=2, sort_keys=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Stage National Assembly bill activity for manual review."
    )
    parser.add_argument("--name", required=True)
    parser.add_argument("--member-code", required=True)
    parser.add_argument("--age", required=True, type=int)
    parser.add_argument("--page-index", type=int, default=1)
    parser.add_argument("--page-size", type=int, default=100)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    candidate = IdentityCandidate(
        canonical_name=args.name,
        office="국회의원",
        career_anchors=(f"assembly_member_code:{args.member_code}",),
    )
    connector = OpenAssemblyBillConnector(
        assembly_age=args.age,
        page_index=args.page_index,
        page_size=args.page_size,
        proposer=args.name,
    )
    try:
        summary = LegislativeActivityStager(candidate, connector).stage()
    except (AssemblyApiError, PolicyDenied, ValueError) as exc:
        raise SystemExit(str(exc)) from None
    print(render_legislative_json(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
