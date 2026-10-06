"""Acquire and publish Assembly member-profile biography entries (``MEM_TITLE``).

``--enumerate`` persists one metadata-only observation per current member: ``MONA_CD`` plus the
verbatim biography lines (contact-like lines dropped). ``--publish`` builds source-attributed
education/career CLAIMs from the latest successful complete enumeration for exact current-roster
members only. No Person is created or matched by name.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from math import ceil

from packages.connectors.open_assembly import (
    AssemblyApiError,
    AssemblyMemberBiographyRecord,
    OpenAssemblyMemberConnector,
    national_assembly_member_policy,
)
from packages.domain.contracts import FeederObservation, SourcePolicy, SourceRun
from packages.domain.enums import SourceRunStatus
from packages.persistence import SqlAlchemyRepository
from packages.verification.assembly_member_biography import (
    ASSEMBLY_BIOGRAPHY_FEEDER,
    ASSEMBLY_BIOGRAPHY_SCOPE,
    ASSEMBLY_BIOGRAPHY_SEMANTIC_SCOPE,
    ASSEMBLY_BIOGRAPHY_SEMANTICS,
    ASSEMBLY_BIOGRAPHY_SOURCE_CONTRACT,
    AssemblyBiographyError,
    AssemblyBiographyPublisher,
    biography_lines,
)
from packages.verification.policy import PolicyAction, PolicyDenied, require_policy
from workers.ingest import IngestionPipeline


class AssemblyBiographyCoverageError(AssemblyApiError):
    pass


def normalized_biography(record: AssemblyMemberBiographyRecord) -> dict[str, object]:
    lines = biography_lines(record.biography)
    return {
        "member_code": record.member_code,
        "biography_lines": list(lines),
        "line_count": len(lines),
        "biography_semantics": ASSEMBLY_BIOGRAPHY_SEMANTICS,
    }


def biography_content_hash(normalized: dict[str, object]) -> str:
    canonical = json.dumps(normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class AssemblyBiographyEnumerationResult:
    run: SourceRun
    list_total_count: int
    pages_committed: int


class AssemblyBiographyEnumerator:
    """Full unfiltered member-list enumeration; every page must be complete and consistent."""

    def __init__(
        self,
        repository: SqlAlchemyRepository,
        *,
        api_key: str | None = None,
        page_size: int = 1000,
        policy: SourcePolicy | None = None,
        transport=None,
        max_pages: int = 5,
    ) -> None:
        self.repository = repository
        self.api_key = api_key
        self.page_size = page_size
        self.policy = policy or national_assembly_member_policy()
        self.transport = transport
        self.max_pages = max_pages

    def _connector(self, page_index: int) -> OpenAssemblyMemberConnector:
        return OpenAssemblyMemberConnector(
            api_key=self.api_key,
            page_index=page_index,
            page_size=self.page_size,
            transport=self.transport,
        )

    def enumerate(self) -> AssemblyBiographyEnumerationResult:
        if self.policy.domain != OpenAssemblyMemberConnector.HOST:
            raise PolicyDenied("SourcePolicy domain does not match the member connector")
        require_policy(self.policy, PolicyAction.FETCH)
        require_policy(self.policy, PolicyAction.STORE_METADATA)
        self.repository.assert_ready()
        run = self.repository.start_source_run(
            ASSEMBLY_BIOGRAPHY_FEEDER,
            ASSEMBLY_BIOGRAPHY_SCOPE,
            {"source_contract": ASSEMBLY_BIOGRAPHY_SOURCE_CONTRACT},
        )
        commits = 0
        try:
            pages = []
            expected_total: int | None = None
            page_index = 1
            while True:
                connector = self._connector(page_index)
                document = connector.fetch(connector.discover()[0])
                try:
                    total = int(document.metadata["list_total_count"])
                except (KeyError, TypeError, ValueError):
                    raise AssemblyBiographyCoverageError("member total count is unavailable") from None
                if total < 1 or (expected_total is not None and total != expected_total):
                    raise AssemblyBiographyCoverageError("member total count is inconsistent")
                expected_total = total
                expected_pages = ceil(total / self.page_size)
                if expected_pages > self.max_pages:
                    raise AssemblyBiographyCoverageError("member pages exceed the configured maximum")
                records = connector.parse_biographies(document)
                if len(records) != min(self.page_size, total - (page_index - 1) * self.page_size):
                    raise AssemblyBiographyCoverageError("member page row count is incomplete")
                pages.append((connector, document, records))
                if page_index == expected_pages:
                    break
                page_index += 1
            keys = [record.member_code for _, _, records in pages for record in records]
            if len(set(keys)) != len(keys):
                raise AssemblyBiographyCoverageError("duplicate MONA_CD in the member list")
            assert expected_total is not None

            seen: dict[str, str] = {}
            for connector, document, records in pages:
                ingestion = IngestionPipeline(connector).ingest_document(document, self.policy)
                observations = []
                for record in records:
                    normalized = normalized_biography(record)
                    content_hash = biography_content_hash(normalized)
                    seen[record.member_code] = content_hash
                    observations.append(
                        FeederObservation(
                            feeder=ASSEMBLY_BIOGRAPHY_FEEDER,
                            scope_key=ASSEMBLY_BIOGRAPHY_SCOPE,
                            provider_record_key=record.member_code,
                            snapshot_id=ingestion.snapshot.id,
                            run_id=run.id,
                            semantic_scope=ASSEMBLY_BIOGRAPHY_SEMANTIC_SCOPE,
                            identity_hints={
                                "record_kind": "single_person_profile_biography",
                                "external_ids": {"assembly_mona_cd": record.member_code},
                            },
                            normalized=normalized,
                            content_hash=content_hash,
                        )
                    )
                commits += 1
                self.repository.commit_source_page(
                    run_id=run.id,
                    policy=self.policy,
                    source=ingestion.source,
                    snapshot=ingestion.snapshot,
                    observations=observations,
                    cursor=str(commits),
                    checkpoint_metadata={
                        "source_contract": ASSEMBLY_BIOGRAPHY_SOURCE_CONTRACT,
                        "page_size": self.page_size,
                        "list_total_count": expected_total,
                        "expected_pages": len(pages),
                        "seen_provider_hashes": dict(sorted(seen.items())),
                    },
                )
            completed = self.repository.finish_source_run(run.id, SourceRunStatus.SUCCESS)
            return AssemblyBiographyEnumerationResult(completed, expected_total, commits)
        except Exception as exc:
            self.repository.finish_source_run(
                run.id,
                SourceRunStatus.PARTIAL if commits else SourceRunStatus.FAILED,
                error_code=type(exc).__name__[:120],
                error_summary="Assembly member biography enumeration did not complete",
            )
            raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--enumerate", action="store_true")
    mode.add_argument("--publish", action="store_true")
    parser.add_argument("--dry-run", action="store_true", help="With --publish: validate only.")
    parser.add_argument("--database-url")
    args = parser.parse_args(argv)
    repository = SqlAlchemyRepository(args.database_url)
    try:
        if args.enumerate:
            result = AssemblyBiographyEnumerator(repository).enumerate()
            payload: dict[str, object] = {
                "run_id": str(result.run.id),
                "status": result.run.status.value,
                "list_total_count": result.list_total_count,
                "pages_committed": result.pages_committed,
                "observations_created": result.run.observations_created,
                "observations_unchanged": result.run.observations_unchanged,
            }
        else:
            published = AssemblyBiographyPublisher(repository).publish_latest_successful(
                dry_run=args.dry_run
            )
            payload = {
                "dry_run": args.dry_run,
                "run_id": str(published.run_id),
                "observations_considered": published.observations_considered,
                "members_with_entries": published.members_with_entries,
                "education_claims": published.education_claims,
                "career_claims": published.career_claims,
                "unchanged_claims": published.unchanged_claims,
                "unresolved_member_codes": list(published.unresolved_member_codes),
                "career_category_counts": published.category_counts,
            }
    except (AssemblyApiError, AssemblyBiographyError, PolicyDenied, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
