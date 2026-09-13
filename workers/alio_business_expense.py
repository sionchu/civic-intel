from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass, replace
from datetime import UTC, datetime

from packages.connectors.alio_disclosures import (
    ALIO_ITEM12_SOURCE_CONTRACT,
    AlioBusinessExpenseDirectoryRow,
    AlioInstitutionHeadBusinessExpenseConnector,
    AlioInstitutionHeadBusinessExpenseRecord,
    AlioRecordError,
    alio_public_institution_policy,
)
from packages.domain.contracts import FeederObservation, SourcePolicy, SourceRun
from packages.domain.enums import SourceRunStatus
from packages.persistence import SqlAlchemyRepository
from packages.verification.policy import PolicyAction, PolicyDenied, require_policy
from workers.ingest import IngestionPipeline

KNOWN_POSITIVE_INSTITUTION_CODES = ("C0019", "C0129", "C0908")
FEEDER = "alio_institution_head_business_expense"
SEMANTIC_SCOPE = "institutional_head_business_expense_annual_disclosure"


def alio_business_expense_scope_key(institution_codes: Sequence[str]) -> str:
    return "item_12_current_known_positive:" + ",".join(
        sorted(set(institution_codes))
    )


def _directory_fingerprint(rows: Sequence[AlioBusinessExpenseDirectoryRow]) -> str:
    payload = [
        {
            "institution_code": row.institution_code,
            "institution_name": row.institution_name,
            "institution_type_code": row.institution_type_code,
            "classification": row.classification.value,
            "classification_text": row.classification_text,
            "report_period": row.report_period,
            "report_form_no": row.report_form_no,
            "submission_no": row.submission_no,
            "disclosure_no": row.disclosure_no,
            "detail_attachment_names": list(row.detail_attachment_names),
        }
        for row in rows
    ]
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def alio_business_expense_provider_key(record: AlioInstitutionHeadBusinessExpenseRecord) -> str:
    if not record.disclosure_no or record.fiscal_year < 1900:
        raise AlioRecordError("ALIO item 12 provider record identity is unavailable")
    return f"{record.disclosure_no}:{record.fiscal_year}"


def normalized_alio_business_expense(
    record: AlioInstitutionHeadBusinessExpenseRecord,
) -> dict[str, object]:
    return {
        "institution_code": record.institution_code,
        "institution_name": record.institution_name,
        "classification": record.classification.value,
        "classification_text": record.classification_text,
        "role_scope": "INSTITUTION_HEAD",
        "report_form_no": "20701",
        "disclosure_no": record.disclosure_no,
        "report_period": record.report_period,
        "report_period_label": record.report_period_label,
        "fiscal_year": record.fiscal_year,
        "amount_thousand_krw": record.amount_thousand_krw,
        "amount_krw": record.amount_krw,
        "currency": "KRW",
        "source_unit": "THOUSAND_KRW",
        "as_of_date": record.as_of_date.isoformat(),
        "submission_date": record.submission_date.isoformat(),
        "detail_attachment_name": record.detail_attachment_name,
        "detail_attachment_locator": record.detail_attachment_locator,
        "source_ref": record.source_ref,
    }


def alio_business_expense_content_hash(normalized: dict[str, object]) -> str:
    canonical = json.dumps(
        normalized,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class AlioBusinessExpenseEnumerationResult:
    run: SourceRun
    institutions_committed: int
    unique_records: int


class AlioBusinessExpenseEnumerator:
    """Enumerate only the explicitly reviewed known-positive Item 12 institutions."""

    FEEDER = FEEDER
    SEMANTIC_SCOPE = SEMANTIC_SCOPE
    SOURCE_CONTRACT = ALIO_ITEM12_SOURCE_CONTRACT

    def __init__(
        self,
        connector: AlioInstitutionHeadBusinessExpenseConnector,
        repository: SqlAlchemyRepository,
        policy: SourcePolicy | None = None,
        institution_codes: Sequence[str] = KNOWN_POSITIVE_INSTITUTION_CODES,
    ) -> None:
        normalized_codes = tuple(sorted(set(institution_codes)))
        if not normalized_codes or any(not code.strip() for code in normalized_codes):
            raise ValueError("ALIO item 12 requires a non-empty institution allowlist")
        self.connector = connector
        self.repository = repository
        self.policy = policy or alio_public_institution_policy()
        self.institution_codes = normalized_codes
        self.scope_key = alio_business_expense_scope_key(normalized_codes)

    def _checkpoint_metadata(
        self,
        *,
        directory: tuple[AlioBusinessExpenseDirectoryRow, ...],
        directory_fingerprint: str,
        last_institution_code: str | None,
        seen_provider_hashes: dict[str, str],
        seen_disclosures: dict[str, str],
        processed_institutions: set[str],
    ) -> dict[str, object]:
        return {
            "source_contract": self.SOURCE_CONTRACT,
            "directory_fingerprint": directory_fingerprint,
            "directory_total": len(directory),
            "selected_institution_codes": list(self.institution_codes),
            "selected_report_periods": {
                row.institution_code: row.report_period for row in directory
            },
            "selected_disclosures": {
                row.institution_code: row.disclosure_no
                for row in directory
                if row.institution_code in self.institution_codes
            },
            "last_institution_code": last_institution_code,
            "seen_provider_hashes": seen_provider_hashes,
            "seen_disclosures": seen_disclosures,
            "processed_institutions": sorted(processed_institutions),
        }

    def enumerate(self, *, resume: bool = False) -> AlioBusinessExpenseEnumerationResult:
        if self.policy.domain != self.connector.HOST:
            raise PolicyDenied("SourcePolicy domain does not match the ALIO connector")
        require_policy(self.policy, PolicyAction.FETCH)
        require_policy(self.policy, PolicyAction.STORE_METADATA)

        self.repository.assert_ready()
        prior_checkpoint = self.repository.source_checkpoint(self.FEEDER, self.scope_key)
        if resume and prior_checkpoint is None:
            raise AlioRecordError("ALIO item 12 resume requires a committed checkpoint")
        run = self.repository.start_source_run(
            self.FEEDER,
            self.scope_key,
            {
                "source_contract": self.SOURCE_CONTRACT,
                "selected_institution_codes": list(self.institution_codes),
                "resume": resume,
            },
        )
        institutions_committed = 0
        chunks_committed = 0
        try:
            directory_document = self.connector.fetch(self.connector.discover()[0])
            directory = self.connector.parse_directory_body(directory_document.body)
            if directory.total_count <= 0:
                raise AlioRecordError("ALIO item 12 institution universe must not be empty")
            directory_fingerprint = _directory_fingerprint(directory.rows)
            by_code = {row.institution_code: row for row in directory.rows}
            selected_rows: list[AlioBusinessExpenseDirectoryRow] = []
            for code in self.institution_codes:
                row = by_code.get(code)
                if row is None:
                    raise AlioRecordError(
                        f"ALIO item 12 institution is not in the directory: {code}"
                    )
                selected_rows.append(row)
            selected = tuple(selected_rows)
            if any(row.disclosure_no is None for row in selected):
                raise AlioRecordError("ALIO item 12 selected institution has no current disclosure")

            start_index = 0
            seen_provider_hashes: dict[str, str] = {}
            seen_disclosures: dict[str, str] = {}
            processed_institutions: set[str] = set()
            if resume:
                assert prior_checkpoint is not None
                if prior_checkpoint.cursor is None:
                    raise AlioRecordError("ALIO item 12 resume checkpoint lacks a cursor")
                try:
                    start_index = int(prior_checkpoint.cursor)
                    metadata = prior_checkpoint.metadata
                    checkpoint_fingerprint = str(metadata["directory_fingerprint"])
                    checkpoint_total = int(metadata["directory_total"])
                    checkpoint_codes = tuple(metadata["selected_institution_codes"])
                    seen_provider_hashes = dict(metadata["seen_provider_hashes"])
                    seen_disclosures = dict(metadata["seen_disclosures"])
                    processed_institutions = set(metadata["processed_institutions"])
                except (KeyError, TypeError, ValueError):
                    raise AlioRecordError(
                        "ALIO item 12 resume checkpoint metadata is invalid"
                    ) from None
                if (
                    checkpoint_fingerprint != directory_fingerprint
                    or checkpoint_total != directory.total_count
                    or checkpoint_codes != self.institution_codes
                ):
                    raise AlioRecordError("ALIO item 12 institution universe changed before resume")
                if start_index < 0 or start_index >= len(selected):
                    raise AlioRecordError("ALIO item 12 resume checkpoint already covers the scope")
            else:
                ingestion = IngestionPipeline(self.connector).ingest_document(
                    directory_document, self.policy
                )
                self.repository.commit_source_page(
                    run_id=run.id,
                    policy=self.policy,
                    source=ingestion.source,
                    snapshot=ingestion.snapshot,
                    observations=[],
                    cursor="0",
                    checkpoint_metadata=self._checkpoint_metadata(
                        directory=directory.rows,
                        directory_fingerprint=directory_fingerprint,
                        last_institution_code=None,
                        seen_provider_hashes={},
                        seen_disclosures={},
                        processed_institutions=set(),
                    ),
                )
                chunks_committed += 1

            for index, directory_row in enumerate(selected, start=1):
                if index <= start_index:
                    continue
                assert directory_row.disclosure_no is not None
                prior_institution = seen_disclosures.get(directory_row.disclosure_no)
                if (
                    prior_institution is not None
                    and prior_institution != directory_row.institution_code
                ):
                    raise AlioRecordError("ALIO item 12 disclosure is reused across institutions")
                if prior_institution is not None:
                    raise AlioRecordError("ALIO item 12 disclosure is duplicated")

                report_document = self.connector.fetch(self.connector.report_url(directory_row))
                report_document = replace(
                    report_document,
                    metadata={
                        **report_document.metadata,
                        "institution_name": directory_row.institution_name,
                        "institution_type_code": directory_row.institution_type_code,
                        "classification": directory_row.classification.value,
                        "classification_text": directory_row.classification_text,
                        "report_period_label": directory_row.report_period_label,
                    },
                )
                records = self.connector.parse_business_expense_rows(
                    report_document,
                    directory_row=directory_row,
                )
                page_hashes: dict[str, str] = {}
                normalized_by_key: dict[str, dict[str, object]] = {}
                for record in records:
                    provider_key = alio_business_expense_provider_key(record)
                    normalized = normalized_alio_business_expense(record)
                    content_hash = alio_business_expense_content_hash(normalized)
                    if provider_key in page_hashes or provider_key in seen_provider_hashes:
                        raise AlioRecordError("ALIO item 12 provider record key is duplicated")
                    page_hashes[provider_key] = content_hash
                    normalized_by_key[provider_key] = normalized

                ingestion = IngestionPipeline(self.connector).ingest_document(
                    report_document, self.policy
                )
                observations = [
                    FeederObservation(
                        feeder=self.FEEDER,
                        scope_key=self.scope_key,
                        provider_record_key=provider_key,
                        snapshot_id=ingestion.snapshot.id,
                        run_id=run.id,
                        provider_observed_at=datetime.combine(
                            record.as_of_date, datetime.min.time(), tzinfo=UTC
                        ),
                        semantic_scope=self.SEMANTIC_SCOPE,
                        identity_hints={},
                        normalized=normalized_by_key[provider_key],
                        content_hash=page_hashes[provider_key],
                    )
                    for record in records
                    for provider_key in (alio_business_expense_provider_key(record),)
                ]
                next_seen_hashes = seen_provider_hashes | page_hashes
                next_seen_disclosures = {
                    **seen_disclosures,
                    directory_row.disclosure_no: directory_row.institution_code,
                }
                next_processed = processed_institutions | {directory_row.institution_code}
                self.repository.commit_source_page(
                    run_id=run.id,
                    policy=self.policy,
                    source=ingestion.source,
                    snapshot=ingestion.snapshot,
                    observations=observations,
                    cursor=str(index),
                    checkpoint_metadata=self._checkpoint_metadata(
                        directory=directory.rows,
                        directory_fingerprint=directory_fingerprint,
                        last_institution_code=directory_row.institution_code,
                        seen_provider_hashes=next_seen_hashes,
                        seen_disclosures=next_seen_disclosures,
                        processed_institutions=next_processed,
                    ),
                )
                institutions_committed += 1
                chunks_committed += 1
                seen_provider_hashes = next_seen_hashes
                seen_disclosures = next_seen_disclosures
                processed_institutions = next_processed

            checkpoint = self.repository.source_checkpoint(self.FEEDER, self.scope_key)
            if (
                checkpoint is None
                or checkpoint.cursor != str(len(selected))
                or processed_institutions != set(self.institution_codes)
            ):
                raise AlioRecordError("ALIO item 12 bounded coverage is incomplete")
            completed = self.repository.finish_source_run(run.id, SourceRunStatus.SUCCESS)
            return AlioBusinessExpenseEnumerationResult(
                completed,
                institutions_committed,
                len(seen_provider_hashes),
            )
        except Exception as exc:
            status = SourceRunStatus.PARTIAL if chunks_committed else SourceRunStatus.FAILED
            self.repository.finish_source_run(
                run.id,
                status,
                error_code=type(exc).__name__[:120],
                error_summary="ALIO item 12 bounded business-expense enumeration did not complete",
            )
            raise


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Enumerate the reviewed known-positive ALIO item 12 institutions."
    )
    parser.add_argument("--institution-code", action="append", dest="institution_codes")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--database-url")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    institution_codes = tuple(args.institution_codes or KNOWN_POSITIVE_INSTITUTION_CODES)
    try:
        result = AlioBusinessExpenseEnumerator(
            AlioInstitutionHeadBusinessExpenseConnector(),
            SqlAlchemyRepository(args.database_url),
            institution_codes=institution_codes,
        ).enumerate(resume=args.resume)
    except (AlioRecordError, PolicyDenied, ValueError) as exc:
        parser.error(str(exc))
    print(
        json.dumps(
            {
                "run_id": str(result.run.id),
                "status": result.run.status.value,
                "scope_key": result.run.scope_key,
                "institutions_committed": result.institutions_committed,
                "unique_records": result.unique_records,
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
