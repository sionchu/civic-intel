from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime, time
from math import ceil

from sqlalchemy import text

from packages.connectors.mois_organization_codes import (
    MissingMoisOrganizationCodeApiKey,
    MoisOrganizationCodeApiError,
    MoisOrganizationCodeConnector,
    MoisOrganizationCodeRecord,
    mois_organization_code_policy,
)
from packages.domain.contracts import FeederObservation, SourcePolicy, SourceRun
from packages.domain.enums import SourceRunStatus
from packages.persistence import SqlAlchemyRepository
from packages.verification.policy import PolicyAction, PolicyDenied, require_policy
from workers.ingest import IngestionPipeline


class MoisOrganizationCoverageError(MoisOrganizationCodeApiError):
    pass


@dataclass(frozen=True)
class MoisOrganizationEnumerationResult:
    run: SourceRun
    pages_committed: int
    unique_records: int


def normalized_mois_organization(record: MoisOrganizationCodeRecord) -> dict[str, object]:
    return {
        "org_code": record.org_code,
        "full_name": record.full_name,
        "lowest_name": record.lowest_name,
        "abbreviation": record.abbreviation,
        "gap_no": record.gap_no,
        "rank_no": record.rank_no,
        "sub_chasu": record.sub_chasu,
        "parent_org_code": record.parent_org_code,
        "top_org_code": record.top_org_code,
        "representative_org_code": record.representative_org_code,
        "type_big": record.type_big,
        "type_mid": record.type_mid,
        "type_small": record.type_small,
        "location_standard_code": record.location_standard_code,
        "use_code": record.use_code,
        "created_date": record.created_date.isoformat() if record.created_date else None,
        "created_date_text": record.created_date_text,
        "closed_date": record.closed_date.isoformat() if record.closed_date else None,
        "stop_selector": record.stop_selector,
        "changed_date": record.changed_date.isoformat() if record.changed_date else None,
        "base_date": record.base_date.isoformat() if record.base_date else None,
        "applied_date": record.applied_date.isoformat() if record.applied_date else None,
        "previous_org_code": record.previous_org_code,
        "identity_semantics": "PROVIDER_ORGANIZATION_KEY_NOT_CANONICAL_ORGANIZATION",
    }


def mois_organization_content_hash(normalized: dict[str, object]) -> str:
    canonical = json.dumps(
        normalized,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _manifest_sha256(hashes: dict[str, str]) -> str:
    canonical = json.dumps(
        sorted(hashes.items()),
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _provider_observed_at(record: MoisOrganizationCodeRecord) -> datetime | None:
    source_date = record.changed_date or record.applied_date or record.base_date
    if source_date is None:
        return None
    return datetime.combine(source_date, time.min, tzinfo=UTC)


def _identity_hints(record: MoisOrganizationCodeRecord) -> dict[str, object]:
    return {
        "record_kind": "organization_registry_record",
        "external_ids": {"mois_org_cd": record.org_code},
        "organization_name": record.full_name or record.lowest_name,
        "materialization": "REVIEW_ONLY",
    }


def _require_policy_reconciled_schema(repository: SqlAlchemyRepository) -> None:
    with repository.engine.connect() as connection:
        revision = connection.scalar(text("SELECT version_num FROM alembic_version"))
    if revision != "0008":
        raise MoisOrganizationCoverageError(
            "MOIS L3 writes require schema revision 0008 policy reconciliation"
        )


class MoisOrganizationEnumerator:
    FEEDER = "mois_standard_organization_codes"
    SEMANTIC_SCOPE = "current_organization_code_registry"
    SOURCE_CONTRACT = "mois_standard_organization_code_v1"
    SCOPE_KEY = "current:stop_selt=0"

    def __init__(
        self,
        connector: MoisOrganizationCodeConnector,
        repository: SqlAlchemyRepository,
        *,
        policy: SourcePolicy | None = None,
        max_pages: int = 500,
    ) -> None:
        if connector.page_no != 1:
            raise MoisOrganizationCoverageError("L3 MOIS enumeration must start at page 1")
        if connector.full_name or connector.org_code:
            raise MoisOrganizationCoverageError("L3 MOIS enumeration must be unfiltered")
        if max_pages < 1:
            raise ValueError("max_pages must be >= 1")
        self.connector = connector
        self.repository = repository
        self.policy = policy or mois_organization_code_policy()
        self.max_pages = max_pages

    def enumerate(self, *, resume: bool = False) -> MoisOrganizationEnumerationResult:
        if self.policy.domain != self.connector.HOST:
            raise PolicyDenied("SourcePolicy domain does not match the MOIS connector")
        require_policy(self.policy, PolicyAction.FETCH)
        require_policy(self.policy, PolicyAction.STORE_METADATA)

        self.repository.assert_ready()
        _require_policy_reconciled_schema(self.repository)
        prior_checkpoint = self.repository.source_checkpoint(self.FEEDER, self.SCOPE_KEY)
        prior_runs = self.repository.source_runs(self.FEEDER, self.SCOPE_KEY)
        if resume and prior_checkpoint is None:
            raise MoisOrganizationCoverageError("MOIS resume requires a committed checkpoint")
        if resume and any(run.status == SourceRunStatus.SUCCESS for run in prior_runs):
            raise MoisOrganizationCoverageError(
                "MOIS resume is only allowed before the first successful full enumeration"
            )

        run = self.repository.start_source_run(
            self.FEEDER,
            self.SCOPE_KEY,
            {
                "source_contract": self.SOURCE_CONTRACT,
                "stop_selt": "0",
                "page_size": self.connector.page_size,
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

            if resume:
                assert prior_checkpoint is not None
                if prior_checkpoint.cursor is None:
                    raise MoisOrganizationCoverageError("MOIS resume checkpoint lacks page cursor")
                try:
                    start_page = int(prior_checkpoint.cursor) + 1
                    expected_total = int(prior_checkpoint.metadata["total_count"])
                    expected_pages = int(prior_checkpoint.metadata["expected_pages"])
                    checkpoint_page_size = int(prior_checkpoint.metadata["page_size"])
                    checkpoint_contract = str(prior_checkpoint.metadata["source_contract"])
                    checkpoint_selector = str(prior_checkpoint.metadata["stop_selt"])
                    expected_seen_count = int(prior_checkpoint.metadata["seen_provider_count"])
                    expected_manifest = str(
                        prior_checkpoint.metadata["seen_provider_manifest_sha256"]
                    )
                    page_fingerprints = list(
                        prior_checkpoint.metadata["page_fingerprints"]
                    )
                except (KeyError, TypeError, ValueError):
                    raise MoisOrganizationCoverageError(
                        "MOIS resume checkpoint metadata is invalid"
                    ) from None
                committed_pages = start_page - 1
                if (
                    checkpoint_page_size != self.connector.page_size
                    or checkpoint_contract != self.SOURCE_CONTRACT
                    or checkpoint_selector != "0"
                    or len(page_fingerprints) != committed_pages
                    or any(
                        not isinstance(item, str) or len(item) != 64
                        for item in page_fingerprints
                    )
                ):
                    raise MoisOrganizationCoverageError(
                        "MOIS resume checkpoint scope metadata is inconsistent"
                    )
                if start_page > expected_pages:
                    raise MoisOrganizationCoverageError(
                        "MOIS resume checkpoint already covers the full scope"
                    )
                prior_observations = self.repository.feeder_observations(
                    self.FEEDER,
                    self.SCOPE_KEY,
                )
                for observation in prior_observations:
                    existing = seen_hashes.get(observation.provider_record_key)
                    if existing is not None and existing != observation.content_hash:
                        raise MoisOrganizationCoverageError(
                            "MOIS resume scope contains multiple versions before first success"
                        )
                    if existing is not None:
                        raise MoisOrganizationCoverageError(
                            "MOIS resume scope contains duplicate provider keys"
                        )
                    seen_hashes[observation.provider_record_key] = observation.content_hash
                if (
                    len(seen_hashes) != expected_seen_count
                    or _manifest_sha256(seen_hashes) != expected_manifest
                ):
                    raise MoisOrganizationCoverageError(
                        "MOIS resume manifest does not match committed observations"
                    )

            page_no = start_page
            while True:
                page_connector = self.connector.for_page(page_no)
                document = page_connector.fetch(page_connector.discover()[0])
                metadata = document.metadata
                if metadata.get("source_contract") != self.SOURCE_CONTRACT:
                    raise MoisOrganizationCoverageError("MOIS source contract is inconsistent")
                if metadata.get("stop_selt") != "0":
                    raise MoisOrganizationCoverageError("MOIS current-only scope is inconsistent")
                if metadata.get("page_no") != str(page_no):
                    raise MoisOrganizationCoverageError("MOIS requested page is inconsistent")
                if metadata.get("page_size") != str(self.connector.page_size):
                    raise MoisOrganizationCoverageError("MOIS requested page size is inconsistent")
                if metadata.get("provider_page_no") != str(page_no):
                    raise MoisOrganizationCoverageError("MOIS provider page is inconsistent")
                if metadata.get("provider_page_size") != str(self.connector.page_size):
                    raise MoisOrganizationCoverageError(
                        "MOIS provider page size is inconsistent"
                    )
                try:
                    total_count = int(metadata["total_count"])
                except (KeyError, TypeError, ValueError):
                    raise MoisOrganizationCoverageError(
                        "MOIS total count is unavailable"
                    ) from None
                if total_count <= 0:
                    raise MoisOrganizationCoverageError(
                        "MOIS current organization universe must not be empty"
                    )
                current_expected_pages = max(1, ceil(total_count / self.connector.page_size))
                if current_expected_pages > self.max_pages:
                    raise MoisOrganizationCoverageError(
                        "MOIS expected pages exceed the configured maximum"
                    )
                if expected_total is None:
                    expected_total = total_count
                    expected_pages = current_expected_pages
                elif total_count != expected_total or current_expected_pages != expected_pages:
                    raise MoisOrganizationCoverageError(
                        "MOIS total count changed during enumeration"
                    )
                assert expected_pages is not None
                if page_no > expected_pages:
                    raise MoisOrganizationCoverageError(
                        "MOIS API returned an unexpected extra page"
                    )

                records = page_connector.parse_organizations(document)
                expected_row_count = min(
                    self.connector.page_size,
                    max(0, expected_total - ((page_no - 1) * self.connector.page_size)),
                )
                if len(records) != expected_row_count:
                    raise MoisOrganizationCoverageError(
                        "MOIS page row count is incomplete"
                    )

                page_hashes: dict[str, str] = {}
                normalized_by_key: dict[str, dict[str, object]] = {}
                for record in records:
                    normalized = normalized_mois_organization(record)
                    content_hash = mois_organization_content_hash(normalized)
                    if record.org_code in page_hashes:
                        if page_hashes[record.org_code] != content_hash:
                            raise MoisOrganizationCoverageError(
                                "conflicting MOIS org_cd appears within one page"
                            )
                        raise MoisOrganizationCoverageError(
                            "duplicate MOIS org_cd appears within one page"
                        )
                    if record.org_code in seen_hashes:
                        if seen_hashes[record.org_code] != content_hash:
                            raise MoisOrganizationCoverageError(
                                "conflicting MOIS org_cd appears across pages"
                            )
                        raise MoisOrganizationCoverageError(
                            "duplicate MOIS org_cd appears across pages"
                        )
                    page_hashes[record.org_code] = content_hash
                    normalized_by_key[record.org_code] = normalized

                page_fingerprint = _manifest_sha256(page_hashes)
                if page_fingerprint in page_fingerprints:
                    raise MoisOrganizationCoverageError(
                        "MOIS API returned duplicate page content"
                    )

                ingestion = IngestionPipeline(page_connector).ingest_document(
                    document,
                    self.policy,
                )
                observations = [
                    FeederObservation(
                        feeder=self.FEEDER,
                        scope_key=self.SCOPE_KEY,
                        provider_record_key=record.org_code,
                        snapshot_id=ingestion.snapshot.id,
                        run_id=run.id,
                        provider_observed_at=_provider_observed_at(record),
                        semantic_scope=self.SEMANTIC_SCOPE,
                        identity_hints=_identity_hints(record),
                        normalized=normalized_by_key[record.org_code],
                        content_hash=page_hashes[record.org_code],
                    )
                    for record in records
                ]

                next_seen_hashes = seen_hashes | page_hashes
                next_page_fingerprints = [*page_fingerprints, page_fingerprint]
                checkpoint_metadata = {
                    "page_size": self.connector.page_size,
                    "expected_pages": expected_pages,
                    "total_count": expected_total,
                    "source_contract": self.SOURCE_CONTRACT,
                    "stop_selt": "0",
                    "seen_provider_count": len(next_seen_hashes),
                    "seen_provider_manifest_sha256": _manifest_sha256(next_seen_hashes),
                    "page_fingerprints": next_page_fingerprints,
                }
                self.repository.commit_source_page(
                    run_id=run.id,
                    policy=self.policy,
                    source=ingestion.source,
                    snapshot=ingestion.snapshot,
                    observations=observations,
                    cursor=str(page_no),
                    checkpoint_metadata=checkpoint_metadata,
                )
                pages_committed += 1
                seen_hashes = next_seen_hashes
                page_fingerprints = next_page_fingerprints

                if page_no == expected_pages:
                    if len(seen_hashes) != expected_total:
                        raise MoisOrganizationCoverageError(
                            "MOIS unique record coverage is incomplete"
                        )
                    break
                page_no += 1

            completed = self.repository.finish_source_run(run.id, SourceRunStatus.SUCCESS)
            return MoisOrganizationEnumerationResult(
                completed,
                pages_committed,
                len(seen_hashes),
            )
        except Exception as exc:
            status = (
                SourceRunStatus.PARTIAL
                if pages_committed or prior_checkpoint is not None
                else SourceRunStatus.FAILED
            )
            self.repository.finish_source_run(
                run.id,
                status,
                error_code=type(exc).__name__[:120],
                error_summary="MOIS organization-code enumeration did not complete",
            )
            raise


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Persist the complete current MOIS standard-organization-code universe."
    )
    parser.add_argument("--page-size", type=int, default=1000)
    parser.add_argument("--max-pages", type=int, default=500)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--database-url")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    connector = MoisOrganizationCodeConnector(
        page_no=1,
        page_size=args.page_size,
    )
    try:
        result = MoisOrganizationEnumerator(
            connector,
            SqlAlchemyRepository(args.database_url),
            max_pages=args.max_pages,
        ).enumerate(resume=args.resume)
    except (
        MissingMoisOrganizationCodeApiKey,
        MoisOrganizationCodeApiError,
        PolicyDenied,
        ValueError,
    ) as exc:
        raise SystemExit(str(exc)) from None
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
