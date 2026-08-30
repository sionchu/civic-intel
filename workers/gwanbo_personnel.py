from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, date, datetime
from math import ceil

from packages.connectors.gwanbo_personnel import (
    GwanboPersonnelConnector,
    GwanboPersonnelError,
    GwanboPersonnelNotice,
    gwanbo_personnel_policy,
)
from packages.domain.contracts import FeederObservation, SourcePolicy, SourceRun
from packages.domain.enums import SourceRunStatus
from packages.persistence import SqlAlchemyRepository
from packages.verification.policy import PolicyAction, PolicyDenied, require_policy
from workers.ingest import IngestionPipeline


class GwanboCoverageError(GwanboPersonnelError):
    pass


@dataclass(frozen=True)
class GwanboEnumerationResult:
    run: SourceRun
    pages_committed: int
    unique_records: int


def normalized_gwanbo_notice(notice: GwanboPersonnelNotice) -> dict[str, object]:
    return {
        "notice_id": notice.notice_id,
        "title": notice.title,
        "publication_date": notice.publication_date.isoformat(),
        "gazette_name": notice.gazette_name,
        "compilation_type": notice.compilation_type,
        "publication_institution": notice.publication_institution,
        "basis_law": notice.basis_law,
        "revision_reason": notice.revision_reason,
        "detail_path": notice.detail_path,
    }


def gwanbo_notice_content_hash(normalized: dict[str, object]) -> str:
    canonical = json.dumps(
        normalized,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class GwanboPersonnelEnumerator:
    FEEDER = "gwanbo_personnel_notices"
    SEMANTIC_SCOPE = "civil_service_personnel_notice"
    SOURCE_CONTRACT = "gwanbo_personnel_notice_list"

    def __init__(
        self,
        connector: GwanboPersonnelConnector,
        repository: SqlAlchemyRepository,
        policy: SourcePolicy | None = None,
    ) -> None:
        self.connector = connector
        self.repository = repository
        self.policy = policy or gwanbo_personnel_policy()

    @property
    def scope_key(self) -> str:
        return f"{self.connector.date_from.isoformat()}:{self.connector.date_to.isoformat()}"

    def enumerate(self, *, resume: bool = False) -> GwanboEnumerationResult:
        if self.policy.domain != self.connector.HOST:
            raise PolicyDenied("SourcePolicy domain does not match the Gwanbo connector")
        require_policy(self.policy, PolicyAction.FETCH)
        require_policy(self.policy, PolicyAction.STORE_METADATA)

        self.repository.assert_ready()
        prior_checkpoint = self.repository.source_checkpoint(self.FEEDER, self.scope_key)
        run = self.repository.start_source_run(
            self.FEEDER,
            self.scope_key,
            {
                "source_contract": self.SOURCE_CONTRACT,
                "date_from": self.connector.date_from.isoformat(),
                "date_to": self.connector.date_to.isoformat(),
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
                    raise GwanboCoverageError("resume checkpoint lacks a page cursor")
                try:
                    start_page = int(prior_checkpoint.cursor) + 1
                    expected_total = int(prior_checkpoint.metadata["list_total_count"])
                    expected_pages = int(prior_checkpoint.metadata["expected_pages"])
                    seen_hashes = dict(prior_checkpoint.metadata["seen_provider_hashes"])
                    page_fingerprints = list(prior_checkpoint.metadata["page_fingerprints"])
                except (KeyError, TypeError, ValueError):
                    raise GwanboCoverageError("resume checkpoint metadata is invalid") from None
                if start_page > expected_pages:
                    raise GwanboCoverageError(
                        "resume checkpoint already covers the full Gwanbo date window"
                    )

            page_index = start_page
            while True:
                self.connector.page_index = page_index
                document = self.connector.fetch(self.connector.discover()[0])
                if document.metadata.get("source_contract") != self.SOURCE_CONTRACT:
                    raise GwanboCoverageError("Gwanbo source contract is inconsistent")
                if document.metadata.get("page_index") != str(page_index):
                    raise GwanboCoverageError("Gwanbo page index is inconsistent")
                if document.metadata.get("page_size") != str(self.connector.page_size):
                    raise GwanboCoverageError("Gwanbo page size is inconsistent")
                if document.metadata.get("date_from") != self.connector.date_from.strftime(
                    "%Y.%m.%d"
                ) or document.metadata.get("date_to") != self.connector.date_to.strftime(
                    "%Y.%m.%d"
                ):
                    raise GwanboCoverageError("Gwanbo date window is inconsistent")
                try:
                    total_count = int(document.metadata["list_total_count"])
                except (KeyError, TypeError, ValueError):
                    raise GwanboCoverageError("Gwanbo total count is unavailable") from None
                if total_count < 0:
                    raise GwanboCoverageError("Gwanbo total count must not be negative")
                current_expected_pages = max(1, ceil(total_count / self.connector.page_size))
                if expected_total is None:
                    expected_total = total_count
                    expected_pages = current_expected_pages
                elif total_count != expected_total or current_expected_pages != expected_pages:
                    raise GwanboCoverageError("Gwanbo total count changed during enumeration")
                assert expected_pages is not None
                if page_index > expected_pages:
                    raise GwanboCoverageError("Gwanbo returned an unexpected extra page")

                notices = self.connector.parse_notices(document)
                expected_row_count = min(
                    self.connector.page_size,
                    max(0, expected_total - ((page_index - 1) * self.connector.page_size)),
                )
                if len(notices) != expected_row_count:
                    raise GwanboCoverageError("Gwanbo page row count is incomplete")

                page_hashes: dict[str, str] = {}
                normalized_by_key: dict[str, dict[str, object]] = {}
                for notice in notices:
                    normalized = normalized_gwanbo_notice(notice)
                    content_hash = gwanbo_notice_content_hash(normalized)
                    if notice.notice_id in page_hashes:
                        if page_hashes[notice.notice_id] != content_hash:
                            raise GwanboCoverageError(
                                "conflicting Gwanbo notice id appears within one page"
                            )
                        raise GwanboCoverageError(
                            "duplicate Gwanbo notice id appears within one page"
                        )
                    if notice.notice_id in seen_hashes:
                        if seen_hashes[notice.notice_id] != content_hash:
                            raise GwanboCoverageError(
                                "conflicting Gwanbo notice id appears across pages"
                            )
                        raise GwanboCoverageError(
                            "duplicate Gwanbo notice id appears across pages"
                        )
                    page_hashes[notice.notice_id] = content_hash
                    normalized_by_key[notice.notice_id] = normalized

                fingerprint_payload = json.dumps(
                    sorted(page_hashes.items()),
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
                page_fingerprint = hashlib.sha256(
                    fingerprint_payload.encode("utf-8")
                ).hexdigest()
                if page_fingerprint in page_fingerprints:
                    raise GwanboCoverageError("Gwanbo returned duplicate page content")

                ingestion = IngestionPipeline(self.connector).ingest_document(document, self.policy)
                observations = [
                    FeederObservation(
                        feeder=self.FEEDER,
                        scope_key=self.scope_key,
                        provider_record_key=notice.notice_id,
                        snapshot_id=ingestion.snapshot.id,
                        run_id=run.id,
                        provider_observed_at=datetime.combine(
                            notice.publication_date, datetime.min.time(), tzinfo=UTC
                        ),
                        semantic_scope=self.SEMANTIC_SCOPE,
                        identity_hints={},
                        normalized=normalized_by_key[notice.notice_id],
                        content_hash=page_hashes[notice.notice_id],
                    )
                    for notice in notices
                ]

                next_seen_hashes = seen_hashes | page_hashes
                next_page_fingerprints = [*page_fingerprints, page_fingerprint]
                checkpoint_metadata = {
                    "page_size": self.connector.page_size,
                    "expected_pages": expected_pages,
                    "list_total_count": expected_total,
                    "source_contract": self.SOURCE_CONTRACT,
                    "date_from": self.connector.date_from.isoformat(),
                    "date_to": self.connector.date_to.isoformat(),
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
                        raise GwanboCoverageError("Gwanbo unique notice coverage is incomplete")
                    break
                page_index += 1

            completed = self.repository.finish_source_run(run.id, SourceRunStatus.SUCCESS)
            return GwanboEnumerationResult(completed, pages_committed, len(seen_hashes))
        except Exception as exc:
            status = SourceRunStatus.PARTIAL if pages_committed else SourceRunStatus.FAILED
            self.repository.finish_source_run(
                run.id,
                status,
                error_code=type(exc).__name__[:120],
                error_summary="Gwanbo personnel enumeration did not complete",
            )
            raise


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Persist a bounded official Gwanbo personnel-notice date window."
    )
    parser.add_argument("--from-date", type=date.fromisoformat, required=True)
    parser.add_argument("--to-date", type=date.fromisoformat, required=True)
    parser.add_argument("--page-size", type=int, default=10)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--database-url")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    connector = GwanboPersonnelConnector(
        date_from=args.from_date,
        date_to=args.to_date,
        page_size=args.page_size,
    )
    try:
        result = GwanboPersonnelEnumerator(
            connector,
            SqlAlchemyRepository(args.database_url),
        ).enumerate(resume=args.resume)
    except (GwanboPersonnelError, PolicyDenied, ValueError) as exc:
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


if __name__ == "__main__":
    raise SystemExit(main())
