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


def _metadata_int(metadata: dict[str, str], key: str) -> int | None:
    value = metadata.get(key)
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        return None


@dataclass(frozen=True)
class StagedLegislativeBill:
    bill_id: str
    bill_no: str | None
    bill_name: str
    proposed_date: date | None
    committee: str | None
    process_result: str | None
    role: str
    representative_proposers: tuple[str, ...]
    co_proposers: tuple[str, ...]
    representative_proposer_codes: tuple[str, ...]
    co_proposer_codes: tuple[str, ...]
    detail_url: str | None

    @classmethod
    def from_record(
        cls, record: AssemblyBillRecord, member_code: str
    ) -> StagedLegislativeBill | None:
        role = record.role_for_code(member_code)
        if role is None:
            return None
        return cls(
            bill_id=record.bill_id,
            bill_no=record.bill_no,
            bill_name=record.bill_name,
            proposed_date=record.proposed_date,
            committee=record.committee,
            process_result=record.process_result,
            role=role,
            representative_proposers=record.representative_proposers,
            co_proposers=record.co_proposers,
            representative_proposer_codes=record.representative_proposer_codes or (),
            co_proposer_codes=record.co_proposer_codes or (),
            detail_url=record.detail_url,
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
            "representative_proposer_codes": list(self.representative_proposer_codes),
            "co_proposer_codes": list(self.co_proposer_codes),
            "detail_url": self.detail_url,
        }


@dataclass(frozen=True)
class LegislativeActivitySummary:
    canonical_name: str
    member_code: str
    assembly_age: int
    source_total_count: int | None
    source_unique_bill_count: int
    coverage_complete: bool
    role_code_coverage_complete: bool
    pages_fetched: int
    expected_pages: int | None
    coverage_errors: tuple[str, ...]
    role_code_errors: tuple[str, ...]
    staged_bill_count: int
    representative_sponsored_count: int | None
    co_sponsored_count: int | None
    process_result_counts: dict[str, int]
    bills: tuple[StagedLegislativeBill, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "canonical_name": self.canonical_name,
            "member_code": self.member_code,
            "assembly_age": self.assembly_age,
            "coverage": {
                "complete": self.coverage_complete,
                "role_codes_complete": self.role_code_coverage_complete,
                "source_total_count": self.source_total_count,
                "source_unique_bill_count": self.source_unique_bill_count,
                "pages_fetched": self.pages_fetched,
                "expected_pages": self.expected_pages,
                "errors": list(self.coverage_errors),
                "role_code_errors": list(self.role_code_errors),
            },
            "counts": {
                "matching_bills": self.staged_bill_count,
                "representative_sponsored": self.representative_sponsored_count,
                "co_sponsored": self.co_sponsored_count,
                "process_results": self.process_result_counts,
                "semantics": "DESCRIPTIVE_COUNTS_NOT_PERFORMANCE_SCORE",
            },
            "bill_purpose_source": {
                "status": "BLOCKED_NO_VERIFIED_STRUCTURED_SOURCE",
                "reason": (
                    "Verified Open Assembly structured APIs do not provide proposal-reason/main-content "
                    "text in this scope; bill-detail HTML scraping is prohibited by Issue #13."
                ),
            },
            "bills": [item.to_dict() for item in self.bills],
        }


class LegislativeActivityStager:
    def __init__(
        self,
        candidate: IdentityCandidate,
        connector: OpenAssemblyBillConnector,
        policy: SourcePolicy | None = None,
        *,
        max_pages: int = 100,
    ) -> None:
        member_code = _member_code(candidate)
        if not member_code:
            raise ValueError("legislative staging requires assembly_member_code identity anchor")
        if connector.page_index != 1:
            raise ValueError("exact legislative staging must start at page 1")
        if connector.has_filters:
            raise ValueError("exact legislative staging requires an unfiltered Assembly-term scan")
        if max_pages < 1:
            raise ValueError("max_pages must be >= 1")
        self.candidate = candidate
        self.member_code = member_code
        self.connector = connector
        self.policy = policy or national_assembly_bill_policy()
        self.max_pages = max_pages

    def _fetch_page(self, page_index: int):
        connector = self.connector.for_page(page_index)
        document = connector.fetch(connector.discover()[0])
        return document, connector.parse_bills(document)

    def stage(self) -> LegislativeActivitySummary:
        if self.policy.domain != self.connector.HOST:
            raise PolicyDenied("SourcePolicy domain does not match National Assembly bill connector")
        require_policy(self.policy, PolicyAction.FETCH)

        coverage_errors: list[str] = []
        role_code_errors: list[str] = []
        documents = []
        page_records: list[list[AssemblyBillRecord]] = []

        first_document, first_records = self._fetch_page(1)
        documents.append(first_document)
        page_records.append(first_records)
        total_count = _metadata_int(first_document.metadata, "list_total_count")
        page_size = _metadata_int(first_document.metadata, "page_size") or self.connector.page_size

        if total_count is None:
            expected_pages = None
            coverage_errors.append("TOTAL_COUNT_MISSING_OR_INVALID")
        else:
            expected_pages = max(1, (total_count + page_size - 1) // page_size)
            if expected_pages > self.max_pages:
                coverage_errors.append("EXPECTED_PAGES_EXCEED_MAX")
            else:
                for page_index in range(2, expected_pages + 1):
                    try:
                        document, records = self._fetch_page(page_index)
                    except AssemblyApiError:
                        coverage_errors.append(f"PAGE_{page_index}_FETCH_FAILED")
                        break
                    documents.append(document)
                    page_records.append(records)
                    if _metadata_int(document.metadata, "page_index") != page_index:
                        coverage_errors.append(f"PAGE_{page_index}_INDEX_MISMATCH")
                    if _metadata_int(document.metadata, "list_total_count") != total_count:
                        coverage_errors.append(f"PAGE_{page_index}_TOTAL_COUNT_CHANGED")

        unique_records: dict[str, AssemblyBillRecord] = {}
        page_signatures: set[tuple[str, ...]] = set()
        for records in page_records:
            signature = tuple(record.bill_id for record in records)
            if signature and signature in page_signatures:
                coverage_errors.append("DUPLICATE_PAGE_CONTENT")
            page_signatures.add(signature)
            for record in records:
                existing = unique_records.get(record.bill_id)
                if existing is None:
                    unique_records[record.bill_id] = record
                elif existing != record:
                    raise ValueError(f"conflicting duplicate BILL_ID: {record.bill_id}")
                else:
                    coverage_errors.append(f"DUPLICATE_BILL_ID:{record.bill_id}")

        if total_count is not None and len(unique_records) != total_count:
            coverage_errors.append("UNIQUE_BILL_COUNT_MISMATCH")

        pages_fetched = len(documents)
        coverage_complete = (
            expected_pages is not None
            and pages_fetched == expected_pages
            and not coverage_errors
        )

        records = tuple(unique_records.values())
        incomplete_role_bills = [
            record.bill_id for record in records if not record.role_code_fields_complete
        ]
        if incomplete_role_bills:
            role_code_errors.append("ROLE_CODE_FIELDS_MISSING_OR_MALFORMED")
        role_code_coverage_complete = coverage_complete and not role_code_errors

        matched = tuple(
            staged
            for record in records
            if (staged := StagedLegislativeBill.from_record(record, self.member_code)) is not None
        )

        if role_code_coverage_complete:
            representative_count = sum(item.role == "LEAD" for item in matched)
            co_sponsored_count = sum(item.role == "CO_SPONSOR" for item in matched)
            result_counts = Counter(item.process_result or "UNKNOWN" for item in matched)
            process_result_counts = dict(sorted(result_counts.items()))
        else:
            representative_count = None
            co_sponsored_count = None
            process_result_counts = {}

        return LegislativeActivitySummary(
            canonical_name=self.candidate.canonical_name,
            member_code=self.member_code,
            assembly_age=self.connector.assembly_age,
            source_total_count=total_count,
            source_unique_bill_count=len(unique_records),
            coverage_complete=coverage_complete,
            role_code_coverage_complete=role_code_coverage_complete,
            pages_fetched=pages_fetched,
            expected_pages=expected_pages,
            coverage_errors=tuple(dict.fromkeys(coverage_errors)),
            role_code_errors=tuple(dict.fromkeys(role_code_errors)),
            staged_bill_count=len(matched),
            representative_sponsored_count=representative_count,
            co_sponsored_count=co_sponsored_count,
            process_result_counts=process_result_counts,
            bills=matched,
        )


def render_legislative_json(summary: LegislativeActivitySummary) -> str:
    return json.dumps(summary.to_dict(), ensure_ascii=False, indent=2, sort_keys=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Scan one National Assembly term and stage code-first bill activity for review."
    )
    parser.add_argument("--name", required=True)
    parser.add_argument("--member-code", required=True)
    parser.add_argument("--age", required=True, type=int)
    parser.add_argument("--page-size", type=int, default=1000)
    parser.add_argument("--max-pages", type=int, default=100)
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
        page_index=1,
        page_size=args.page_size,
    )
    try:
        summary = LegislativeActivityStager(
            candidate, connector, max_pages=args.max_pages
        ).stage()
    except (AssemblyApiError, PolicyDenied, ValueError) as exc:
        raise SystemExit(str(exc)) from None
    print(render_legislative_json(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
