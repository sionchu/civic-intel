from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from math import ceil
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from packages.connectors.open_assembly import AssemblyApiError
from packages.connectors.open_assembly_bills import (
    AssemblyBillRecord,
    OpenAssemblyBillConnector,
    national_assembly_bill_policy,
)
from packages.domain.contracts import FeederObservation, SourcePolicy, SourceRun
from packages.domain.enums import SourceRunStatus
from packages.persistence import SqlAlchemyRepository
from packages.verification.identity import IdentityCandidate
from packages.verification.policy import PolicyAction, PolicyDenied, require_policy
from workers.ingest import IngestionPipeline


class AssemblyBillCoverageError(AssemblyApiError):
    pass


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
class AssemblyBillEnumerationResult:
    run: SourceRun
    pages_committed: int
    unique_records: int


def _safe_detail_url(value: str | None) -> str | None:
    if not value:
        return None
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    query = urlencode(
        [
            (key, item)
            for key, item in parse_qsl(parsed.query, keep_blank_values=True)
            if key.casefold() not in {"key", "authkey", "servicekey"}
        ],
        doseq=True,
    )
    return urlunparse(parsed._replace(query=query, fragment=""))


def normalized_assembly_bill(record: AssemblyBillRecord) -> dict[str, object]:
    if not record.role_code_fields_complete:
        raise AssemblyBillCoverageError(
            "National Assembly bill row lacks complete proposer code fields"
        )
    return {
        "bill_id": record.bill_id,
        "bill_no": record.bill_no,
        "bill_name": record.bill_name,
        "assembly_age": record.assembly_age,
        "proposed_date": record.proposed_date.isoformat() if record.proposed_date else None,
        "committee": record.committee,
        "committee_id": record.committee_id,
        "process_result": record.process_result,
        "representative_proposer_codes": sorted(record.representative_proposer_codes or ()),
        "co_proposer_codes": sorted(record.co_proposer_codes or ()),
        "detail_url": _safe_detail_url(record.detail_url),
        "participation_semantics": "official_code_linked_bill_participation",
    }


def assembly_bill_content_hash(normalized: dict[str, object]) -> str:
    canonical = json.dumps(
        normalized,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _bill_observed_at(proposed_date: date | None) -> datetime | None:
    if proposed_date is None:
        return None
    return datetime.combine(proposed_date, time.min, tzinfo=UTC)


def _bill_identity_hints(record: AssemblyBillRecord) -> dict[str, object]:
    participants = [
        {
            "external_id_namespace": "assembly_mona_cd",
            "external_id": member_code,
            "role": role,
        }
        for role, codes in (
            ("REPRESENTATIVE_PROPOSER", record.representative_proposer_codes or ()),
            ("CO_PROPOSER", record.co_proposer_codes or ()),
        )
        for member_code in sorted(codes)
    ]
    return {
        "record_kind": "multi_person_legislative_event",
        "participants": participants,
    }


class AssemblyBillParticipationEnumerator:
    FEEDER = "national_assembly_bill_participation"
    SEMANTIC_SCOPE = "legislative_bill_participation"
    SOURCE_CONTRACT = "assembly_term_bill_participation"

    def __init__(
        self,
        connector: OpenAssemblyBillConnector,
        repository: SqlAlchemyRepository,
        policy: SourcePolicy | None = None,
        *,
        max_pages: int = 100,
    ) -> None:
        if max_pages < 1:
            raise ValueError("max_pages must be >= 1")
        self.connector = connector
        self.repository = repository
        self.policy = policy or national_assembly_bill_policy()
        self.max_pages = max_pages

    @property
    def scope_key(self) -> str:
        return f"assembly_age:{self.connector.assembly_age}"

    def enumerate(self, *, resume: bool = False) -> AssemblyBillEnumerationResult:
        if self.connector.page_index != 1:
            raise AssemblyBillCoverageError(
                "L3 Assembly bill enumeration must start at page 1"
            )
        if self.connector.has_filters:
            raise AssemblyBillCoverageError(
                "L3 Assembly bill enumeration must be unfiltered"
            )
        if self.policy.domain != self.connector.HOST:
            raise PolicyDenied(
                "SourcePolicy domain does not match National Assembly bill connector"
            )
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
            },
        )
        pages_committed = 0
        try:
            start_page = 1
            expected_total: int | None = None
            expected_pages: int | None = None
            seen_hashes: dict[str, str] = {}
            page_fingerprints: list[str] = []
            if resume and prior_checkpoint is not None:
                if prior_checkpoint.cursor is None:
                    raise AssemblyBillCoverageError("resume checkpoint lacks a page cursor")
                try:
                    start_page = int(prior_checkpoint.cursor) + 1
                    expected_total = int(prior_checkpoint.metadata["list_total_count"])
                    expected_pages = int(prior_checkpoint.metadata["expected_pages"])
                    checkpoint_page_size = int(prior_checkpoint.metadata["page_size"])
                    checkpoint_age = int(prior_checkpoint.metadata["assembly_age"])
                    source_contract = str(prior_checkpoint.metadata["source_contract"])
                    seen_hashes = dict(prior_checkpoint.metadata["seen_provider_hashes"])
                    page_fingerprints = list(prior_checkpoint.metadata["page_fingerprints"])
                except (KeyError, TypeError, ValueError):
                    raise AssemblyBillCoverageError(
                        "resume checkpoint metadata is invalid"
                    ) from None
                if checkpoint_page_size != self.connector.page_size:
                    raise AssemblyBillCoverageError("resume checkpoint page size is inconsistent")
                if checkpoint_age != self.connector.assembly_age:
                    raise AssemblyBillCoverageError("resume checkpoint Assembly age is inconsistent")
                if source_contract != self.SOURCE_CONTRACT:
                    raise AssemblyBillCoverageError("resume checkpoint source contract is inconsistent")
                if start_page > expected_pages:
                    raise AssemblyBillCoverageError(
                        "resume checkpoint already covers the full Assembly term"
                    )

            page_index = start_page
            while True:
                page_connector = self.connector.for_page(page_index)
                document = page_connector.fetch(page_connector.discover()[0])
                if document.metadata.get("api_code") != self.connector.API_CODE:
                    raise AssemblyBillCoverageError(
                        "National Assembly bill source contract is inconsistent"
                    )
                if document.metadata.get("assembly_age") != str(self.connector.assembly_age):
                    raise AssemblyBillCoverageError(
                        "National Assembly bill scope is inconsistent"
                    )
                if document.metadata.get("page_index") != str(page_index):
                    raise AssemblyBillCoverageError(
                        "National Assembly bill requested page is inconsistent"
                    )
                if document.metadata.get("page_size") != str(self.connector.page_size):
                    raise AssemblyBillCoverageError(
                        "National Assembly bill requested page size is inconsistent"
                    )
                try:
                    total_count = int(document.metadata["list_total_count"])
                except (KeyError, TypeError, ValueError):
                    raise AssemblyBillCoverageError(
                        "National Assembly bill total count is unavailable"
                    ) from None
                if total_count < 0:
                    raise AssemblyBillCoverageError(
                        "National Assembly bill total count must not be negative"
                    )
                current_expected_pages = max(1, ceil(total_count / self.connector.page_size))
                if current_expected_pages > self.max_pages:
                    raise AssemblyBillCoverageError(
                        "National Assembly bill expected pages exceed the configured maximum"
                    )
                if expected_total is None:
                    expected_total = total_count
                    expected_pages = current_expected_pages
                elif total_count != expected_total or current_expected_pages != expected_pages:
                    raise AssemblyBillCoverageError(
                        "National Assembly bill total count changed during enumeration"
                    )
                assert expected_pages is not None
                if page_index > expected_pages:
                    raise AssemblyBillCoverageError(
                        "National Assembly bill API returned an unexpected extra page"
                    )

                bills = self.connector.parse_bills(document)
                expected_row_count = min(
                    self.connector.page_size,
                    max(0, expected_total - ((page_index - 1) * self.connector.page_size)),
                )
                if len(bills) != expected_row_count:
                    raise AssemblyBillCoverageError(
                        "National Assembly bill page row count is incomplete"
                    )

                page_hashes: dict[str, str] = {}
                normalized_by_key: dict[str, dict[str, object]] = {}
                for bill in bills:
                    if bill.assembly_age != self.connector.assembly_age:
                        raise AssemblyBillCoverageError(
                            "National Assembly bill row Assembly age is inconsistent"
                        )
                    normalized = normalized_assembly_bill(bill)
                    content_hash = assembly_bill_content_hash(normalized)
                    if bill.bill_id in page_hashes:
                        if page_hashes[bill.bill_id] != content_hash:
                            raise AssemblyBillCoverageError(
                                "conflicting BILL_ID appears within one page"
                            )
                        raise AssemblyBillCoverageError(
                            "duplicate BILL_ID appears within one page"
                        )
                    page_hashes[bill.bill_id] = content_hash
                    normalized_by_key[bill.bill_id] = normalized

                fingerprint_payload = json.dumps(
                    sorted(page_hashes.items()),
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
                page_fingerprint = hashlib.sha256(
                    fingerprint_payload.encode("utf-8")
                ).hexdigest()
                if page_fingerprint in page_fingerprints:
                    raise AssemblyBillCoverageError(
                        "National Assembly bill API returned duplicate page content"
                    )
                for bill_id, content_hash in page_hashes.items():
                    if bill_id in seen_hashes:
                        if seen_hashes[bill_id] != content_hash:
                            raise AssemblyBillCoverageError(
                                "conflicting BILL_ID appears across pages"
                            )
                        raise AssemblyBillCoverageError(
                            "duplicate BILL_ID appears across pages"
                        )

                ingestion = IngestionPipeline(page_connector).ingest_document(
                    document, self.policy
                )
                observations = [
                    FeederObservation(
                        feeder=self.FEEDER,
                        scope_key=self.scope_key,
                        provider_record_key=bill.bill_id,
                        snapshot_id=ingestion.snapshot.id,
                        run_id=run.id,
                        provider_observed_at=_bill_observed_at(bill.proposed_date),
                        semantic_scope=self.SEMANTIC_SCOPE,
                        identity_hints=_bill_identity_hints(bill),
                        normalized=normalized_by_key[bill.bill_id],
                        content_hash=page_hashes[bill.bill_id],
                    )
                    for bill in bills
                ]

                next_seen_hashes = seen_hashes | page_hashes
                next_page_fingerprints = [*page_fingerprints, page_fingerprint]
                checkpoint_metadata = {
                    "page_size": self.connector.page_size,
                    "expected_pages": expected_pages,
                    "list_total_count": expected_total,
                    "source_contract": self.SOURCE_CONTRACT,
                    "assembly_age": self.connector.assembly_age,
                    "seen_provider_hashes": next_seen_hashes,
                    "page_fingerprints": next_page_fingerprints,
                }
                self.repository.commit_source_page(
                    run_id=run.id,
                    policy=self.policy,
                    source=ingestion.source,
                    snapshot=ingestion.snapshot,
                    observations=observations,
                    cursor=str(page_index),
                    checkpoint_metadata=checkpoint_metadata,
                )
                pages_committed += 1
                seen_hashes = next_seen_hashes
                page_fingerprints = next_page_fingerprints

                if page_index == expected_pages:
                    if len(seen_hashes) != expected_total:
                        raise AssemblyBillCoverageError(
                            "National Assembly bill unique record coverage is incomplete"
                        )
                    break
                page_index += 1

            completed = self.repository.finish_source_run(run.id, SourceRunStatus.SUCCESS)
            return AssemblyBillEnumerationResult(
                completed,
                pages_committed,
                len(seen_hashes),
            )
        except Exception as exc:
            status = SourceRunStatus.PARTIAL if pages_committed else SourceRunStatus.FAILED
            self.repository.finish_source_run(
                run.id,
                status,
                error_code=type(exc).__name__[:120],
                error_summary="Assembly bill participation enumeration did not complete",
            )
            raise


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
        description=(
            "Stage code-first legislative activity or persist one complete National Assembly "
            "term bill-participation scope."
        )
    )
    parser.add_argument("--name")
    parser.add_argument("--member-code")
    parser.add_argument("--age", required=True, type=int)
    parser.add_argument("--page-size", type=int, default=1000)
    parser.add_argument("--max-pages", type=int, default=100)
    parser.add_argument(
        "--enumerate-bills",
        action="store_true",
        help="Persist and validate the complete unfiltered bill-participation scope.",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume bill enumeration from the last committed page.",
    )
    parser.add_argument("--database-url")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    connector = OpenAssemblyBillConnector(
        assembly_age=args.age,
        page_index=1,
        page_size=args.page_size,
    )
    if args.enumerate_bills or args.resume:
        try:
            result = AssemblyBillParticipationEnumerator(
                connector,
                SqlAlchemyRepository(args.database_url),
                max_pages=args.max_pages,
            ).enumerate(resume=args.resume)
        except (AssemblyApiError, PolicyDenied, ValueError) as exc:
            parser.error(str(exc))
        print(
            json.dumps(
                {
                    "run_id": str(result.run.id),
                    "status": result.run.status.value,
                    "scope_key": result.run.scope_key,
                    "pages_committed": result.pages_committed,
                    "unique_records": result.unique_records,
                },
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    if not args.name or not args.member_code:
        parser.error("--name and --member-code are required for review staging")
    candidate = IdentityCandidate(
        canonical_name=args.name,
        office="국회의원",
        career_anchors=(f"assembly_member_code:{args.member_code}",),
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
