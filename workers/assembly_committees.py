from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass
from math import ceil

from packages.connectors.base import ConnectorDocument
from packages.connectors.open_assembly import AssemblyApiError
from packages.connectors.open_assembly_committees import (
    AssemblyCommitteeMemberRecord,
    AssemblyCommitteeStatusRecord,
    OpenAssemblyCommitteeMemberConnector,
    OpenAssemblyCommitteeStatusConnector,
    national_assembly_committee_policy,
)
from packages.domain.contracts import FeederObservation, SourcePolicy, SourceRun
from packages.domain.enums import SourceRunStatus
from packages.persistence import SqlAlchemyRepository
from packages.verification.assembly_committee_roles import (
    ASSEMBLY_COMMITTEE_MEMBERSHIP_FEEDER,
    ASSEMBLY_COMMITTEE_MEMBERSHIP_SCOPE,
    ASSEMBLY_COMMITTEE_MEMBERSHIP_SEMANTIC_SCOPE,
    ASSEMBLY_COMMITTEE_MEMBERSHIP_SEMANTICS,
    ASSEMBLY_COMMITTEE_MEMBERSHIP_SOURCE_CONTRACT,
    AssemblyCommitteeRoleError,
    AssemblyCommitteeRolePublisher,
)
from packages.verification.policy import PolicyAction, PolicyDenied, require_policy
from workers.ingest import IngestionPipeline


class AssemblyCommitteeCoverageError(AssemblyApiError):
    pass


def committee_status_provider_key(record: AssemblyCommitteeStatusRecord) -> str:
    return record.committee_code


def committee_membership_provider_key(record: AssemblyCommitteeMemberRecord) -> str:
    return f"{record.committee_code}:{record.member_code}"


@dataclass(frozen=True)
class StagedAssemblyCommitteeRoster:
    statuses: tuple[AssemblyCommitteeStatusRecord, ...]
    memberships: tuple[AssemblyCommitteeMemberRecord, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "statuses": [
                {
                    "provider_record_key": committee_status_provider_key(item),
                    **asdict(item),
                }
                for item in self.statuses
            ],
            "memberships": [
                {
                    "provider_record_key": committee_membership_provider_key(item),
                    **asdict(item),
                }
                for item in self.memberships
            ],
        }


class AssemblyCommitteeRosterStager:
    def __init__(
        self,
        status_connector: OpenAssemblyCommitteeStatusConnector,
        member_connector: OpenAssemblyCommitteeMemberConnector,
        policy: SourcePolicy | None = None,
    ) -> None:
        self.status_connector = status_connector
        self.member_connector = member_connector
        self.policy = policy or national_assembly_committee_policy()

    def _authorize(self) -> None:
        if (
            self.policy.domain != self.status_connector.HOST
            or self.policy.domain != self.member_connector.HOST
        ):
            raise PolicyDenied(
                "SourcePolicy domain does not match the National Assembly committee connectors"
            )
        require_policy(self.policy, PolicyAction.FETCH)

    def stage(self) -> StagedAssemblyCommitteeRoster:
        self._authorize()
        status_document = self.status_connector.fetch(
            self.status_connector.discover()[0]
        )
        member_document = self.member_connector.fetch(
            self.member_connector.discover()[0]
        )
        return StagedAssemblyCommitteeRoster(
            statuses=self.status_connector.parse_statuses(status_document),
            memberships=self.member_connector.parse_memberships(member_document),
        )


def normalized_committee_membership(record: AssemblyCommitteeMemberRecord) -> dict[str, object]:
    """Keep the committee/member codes and the published role text only.

    Name, Hanja, party and district are not needed for the exact MONA_CD join and are dropped,
    as in the roll-call lane.
    """

    return {
        "committee_code": record.committee_code,
        "committee_name": record.committee_name,
        "member_code": record.member_code,
        "role_published": record.role,
        "membership_semantics": ASSEMBLY_COMMITTEE_MEMBERSHIP_SEMANTICS,
    }


def committee_membership_content_hash(normalized: dict[str, object]) -> str:
    canonical = json.dumps(normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class AssemblyCommitteeMembershipEnumerationResult:
    run: SourceRun
    list_total_count: int
    pages_committed: int


_MemberPage = tuple[
    OpenAssemblyCommitteeMemberConnector,
    ConnectorDocument,
    list[AssemblyCommitteeMemberRecord],
]


class AssemblyCommitteeMembershipEnumerator:
    """Persist the full official committee-member list as immutable observations.

    Acquisition only: no Person, Organization or Claim is created here. The list publishes no
    term, start or end date, so collection time is the only time recorded.
    """

    def __init__(
        self,
        connector: OpenAssemblyCommitteeMemberConnector,
        repository: SqlAlchemyRepository,
        policy: SourcePolicy | None = None,
        *,
        max_pages: int = 20,
    ) -> None:
        if connector.sample_mode:
            raise ValueError("full enumeration requires an issued key, not sample mode")
        if connector.filters:
            raise ValueError("full enumeration must not apply provider search filters")
        if max_pages < 1:
            raise ValueError("max_pages must be >= 1")
        self.connector = connector
        self.repository = repository
        self.policy = policy or national_assembly_committee_policy()
        self.max_pages = max_pages

    def _fetch_pages(self) -> tuple[int, list[_MemberPage]]:
        pages: list[_MemberPage] = []
        expected_total: int | None = None
        expected_pages = 0
        page_index = 1
        while True:
            page_connector = self.connector.for_page(page_index)
            document = page_connector.fetch(page_connector.discover()[0])
            metadata = document.metadata
            if metadata.get("api_code") != page_connector.API_CODE:
                raise AssemblyCommitteeCoverageError(
                    "committee-member source contract is inconsistent"
                )
            if metadata.get("page_index") != str(page_index) or metadata.get(
                "page_size"
            ) != str(self.connector.page_size):
                raise AssemblyCommitteeCoverageError(
                    "committee-member requested page is inconsistent"
                )
            try:
                total = int(metadata["list_total_count"])
            except (KeyError, TypeError, ValueError):
                raise AssemblyCommitteeCoverageError(
                    "committee-member total count is unavailable"
                ) from None
            if total < 1:
                raise AssemblyCommitteeCoverageError("committee-member list is empty")
            if expected_total is None:
                expected_total = total
                expected_pages = ceil(total / self.connector.page_size)
                if expected_pages > self.max_pages:
                    raise AssemblyCommitteeCoverageError(
                        "committee-member expected pages exceed the configured maximum"
                    )
            elif total != expected_total:
                raise AssemblyCommitteeCoverageError(
                    "committee-member total count changed during enumeration"
                )
            records = list(page_connector.parse_memberships(document))
            expected_rows = min(
                self.connector.page_size,
                expected_total - (page_index - 1) * self.connector.page_size,
            )
            if len(records) != expected_rows:
                raise AssemblyCommitteeCoverageError(
                    "committee-member page row count is incomplete"
                )
            pages.append((page_connector, document, records))
            if page_index == expected_pages:
                break
            page_index += 1

        seen: dict[str, AssemblyCommitteeMemberRecord] = {}
        for _, _, records in pages:
            for record in records:
                key = committee_membership_provider_key(record)
                if key in seen:
                    if seen[key] != record:
                        raise AssemblyCommitteeCoverageError(
                            "conflicting committee/member rows share one DEPT_CD:MONA_CD"
                        )
                    raise AssemblyCommitteeCoverageError(
                        "duplicate committee/member row in the member list"
                    )
                seen[key] = record
        assert expected_total is not None
        return expected_total, pages

    def enumerate(self) -> AssemblyCommitteeMembershipEnumerationResult:
        if self.connector.page_index != 1:
            raise AssemblyCommitteeCoverageError(
                "committee-member enumeration must start at page 1"
            )
        if self.policy.domain != self.connector.HOST:
            raise PolicyDenied("SourcePolicy domain does not match the committee-member connector")
        require_policy(self.policy, PolicyAction.FETCH)
        require_policy(self.policy, PolicyAction.STORE_METADATA)

        self.repository.assert_ready()
        run = self.repository.start_source_run(
            ASSEMBLY_COMMITTEE_MEMBERSHIP_FEEDER,
            ASSEMBLY_COMMITTEE_MEMBERSHIP_SCOPE,
            {"source_contract": ASSEMBLY_COMMITTEE_MEMBERSHIP_SOURCE_CONTRACT},
        )
        commits = 0
        try:
            total, pages = self._fetch_pages()
            seen_hashes: dict[str, str] = {}
            for page_connector, document, records in pages:
                ingestion = IngestionPipeline(page_connector).ingest_document(
                    document, self.policy
                )
                observations = []
                for record in records:
                    normalized = normalized_committee_membership(record)
                    content_hash = committee_membership_content_hash(normalized)
                    key = committee_membership_provider_key(record)
                    seen_hashes[key] = content_hash
                    observations.append(
                        FeederObservation(
                            feeder=ASSEMBLY_COMMITTEE_MEMBERSHIP_FEEDER,
                            scope_key=ASSEMBLY_COMMITTEE_MEMBERSHIP_SCOPE,
                            provider_record_key=key,
                            snapshot_id=ingestion.snapshot.id,
                            run_id=run.id,
                            semantic_scope=ASSEMBLY_COMMITTEE_MEMBERSHIP_SEMANTIC_SCOPE,
                            identity_hints={
                                "record_kind": "single_person_committee_membership",
                                "participants": [
                                    {
                                        "external_id_namespace": "assembly_mona_cd",
                                        "external_id": record.member_code,
                                        "role": "COMMITTEE_MEMBER",
                                    }
                                ],
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
                        "source_contract": ASSEMBLY_COMMITTEE_MEMBERSHIP_SOURCE_CONTRACT,
                        "page_size": self.connector.page_size,
                        "list_total_count": total,
                        "expected_pages": len(pages),
                        # Complete only once the final page is committed.
                        "seen_provider_hashes": dict(sorted(seen_hashes.items())),
                    },
                )
            completed = self.repository.finish_source_run(run.id, SourceRunStatus.SUCCESS)
            return AssemblyCommitteeMembershipEnumerationResult(
                run=completed,
                list_total_count=total,
                pages_committed=commits,
            )
        except Exception as exc:
            status = SourceRunStatus.PARTIAL if commits else SourceRunStatus.FAILED
            self.repository.finish_source_run(
                run.id,
                status,
                error_code=type(exc).__name__[:120],
                error_summary="Assembly committee-member enumeration did not complete",
            )
            raise


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Stage one privacy-minimized page from the official Assembly committee APIs, or "
            "persist the full committee-member list (acquisition only; no Claim publication)."
        )
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--sample",
        action="store_true",
        help="Use the official no-key sample mode (page 1, 5 rows).",
    )
    mode.add_argument(
        "--enumerate-members",
        action="store_true",
        help="Persist every committee-member row as immutable observations (requires a key).",
    )
    mode.add_argument(
        "--publish-roles",
        action="store_true",
        help="Publish 위원장/간사 Claims from the latest successful member-list enumeration.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="With --publish-roles: build and validate every Claim without writing.",
    )
    parser.add_argument("--page-index", type=int, default=1)
    parser.add_argument("--page-size", type=int, default=100)
    parser.add_argument("--database-url")
    return parser


def _enumerate_members(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    try:
        result = AssemblyCommitteeMembershipEnumerator(
            OpenAssemblyCommitteeMemberConnector(page_size=1000),
            SqlAlchemyRepository(args.database_url),
        ).enumerate()
    except (AssemblyApiError, PolicyDenied, ValueError, RuntimeError) as exc:
        parser.error(str(exc))
    print(
        json.dumps(
            {
                "run_id": str(result.run.id),
                "status": result.run.status.value,
                "scope_key": result.run.scope_key,
                "list_total_count": result.list_total_count,
                "pages_committed": result.pages_committed,
                "observations_created": result.run.observations_created,
                "observations_unchanged": result.run.observations_unchanged,
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def _publish_roles(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    try:
        result = AssemblyCommitteeRolePublisher(
            SqlAlchemyRepository(args.database_url)
        ).publish_latest_successful(dry_run=args.dry_run)
    except (AssemblyCommitteeRoleError, PolicyDenied, ValueError) as exc:
        parser.error(str(exc))
    print(
        json.dumps(
            {
                "dry_run": args.dry_run,
                "run_id": str(result.run_id),
                "observations_considered": result.observations_considered,
                "office_rows": result.office_rows,
                "published_claims": result.published_claims,
                "unchanged_claims": result.unchanged_claims,
                "unresolved_member_codes": list(result.unresolved_member_codes),
                "stale_claim_ids": [str(item) for item in result.stale_claim_ids],
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.dry_run and not args.publish_roles:
        parser.error("--dry-run applies only to --publish-roles")
    if args.enumerate_members:
        return _enumerate_members(args, parser)
    if args.publish_roles:
        return _publish_roles(args, parser)
    page_index = 1 if args.sample else args.page_index
    page_size = 5 if args.sample else args.page_size
    try:
        staged = AssemblyCommitteeRosterStager(
            OpenAssemblyCommitteeStatusConnector(
                page_index=page_index,
                page_size=page_size,
                sample_mode=args.sample,
            ),
            OpenAssemblyCommitteeMemberConnector(
                page_index=page_index,
                page_size=page_size,
                sample_mode=args.sample,
            ),
        ).stage()
    except (PolicyDenied, ValueError, RuntimeError) as exc:
        parser.error(str(exc))
    print(
        json.dumps(
            staged.to_dict(),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
