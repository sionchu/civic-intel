from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from math import ceil
from uuid import UUID

from packages.connectors.open_assembly import (
    AssemblyApiError,
    AssemblyMemberRecord,
    OpenAssemblyMemberConnector,
    national_assembly_member_policy,
)
from packages.domain.contracts import FeederObservation, SourcePolicy, SourceRun
from packages.domain.enums import MaterializationAction, SourceRunStatus
from packages.persistence import SqlAlchemyRepository
from packages.verification.assembly_base_profile import (
    ASSEMBLY_BASE_PROFILE_FEEDER,
    ASSEMBLY_BASE_PROFILE_SCOPE,
    ASSEMBLY_BASE_PROFILE_SEMANTIC_SCOPE,
    ASSEMBLY_BASE_PROFILE_SOURCE_CONTRACT,
    AssemblyBaseProfilePublisher,
)
from packages.verification.identity import IdentityCandidate
from packages.verification.materialization import MaterializationError, MaterializationResult
from packages.verification.policy import PolicyAction, PolicyDenied, require_policy
from workers.ingest import IngestionPipeline


class AssemblyCoverageError(AssemblyApiError):
    pass


def assembly_member_to_identity_candidate(record: AssemblyMemberRecord) -> IdentityCandidate:
    aliases = tuple(
        value for value in (record.name_hanja, record.name_en) if value and value != record.name_ko
    )
    anchors = [f"assembly_member_code:{record.member_code}"]
    for label, value in (
        ("district", record.district),
        ("committees", record.committees),
        ("reelection", record.reelection),
        ("election_type", record.election_type),
    ):
        if value:
            anchors.append(f"{label}:{value}")
    return IdentityCandidate(
        canonical_name=record.name_ko,
        aliases=aliases,
        birth_date=record.birth_date,
        office="국회의원",
        organization=record.party,
        career_anchors=tuple(anchors),
    )


@dataclass(frozen=True)
class StagedAssemblyMember:
    member_code: str
    candidate: IdentityCandidate

    def to_dict(self) -> dict[str, object]:
        return {
            "member_code": self.member_code,
            "canonical_name": self.candidate.canonical_name,
            "aliases": list(self.candidate.aliases),
            "birth_date": (
                self.candidate.birth_date.isoformat() if self.candidate.birth_date else None
            ),
            "office": self.candidate.office,
            "organization": self.candidate.organization,
            "identity_anchors": list(self.candidate.career_anchors),
        }


class AssemblyRosterStager:
    def __init__(
        self,
        connector: OpenAssemblyMemberConnector,
        policy: SourcePolicy | None = None,
    ) -> None:
        self.connector = connector
        self.policy = policy or national_assembly_member_policy()

    def stage(self, url: str | None = None) -> list[StagedAssemblyMember]:
        if self.policy.domain != self.connector.HOST:
            raise PolicyDenied("SourcePolicy domain does not match the National Assembly connector")
        require_policy(self.policy, PolicyAction.FETCH)
        target = url or self.connector.discover()[0]
        document = self.connector.fetch(target)
        return [
            StagedAssemblyMember(record.member_code, assembly_member_to_identity_candidate(record))
            for record in self.connector.parse_members(document)
        ]


@dataclass(frozen=True)
class AssemblyEnumerationResult:
    run: SourceRun
    pages_committed: int
    unique_records: int
    observation_ids: tuple[UUID, ...] = ()


@dataclass(frozen=True)
class AssemblyRosterMaterializationResult:
    enumeration: AssemblyEnumerationResult
    materializations: tuple[MaterializationResult, ...]

    def outcome_counts(self) -> dict[str, int]:
        counts = {action.value: 0 for action in MaterializationAction}
        for result in self.materializations:
            counts[result.decision.action.value] += 1
        return counts


def normalized_assembly_member(record: AssemblyMemberRecord) -> dict[str, object]:
    return {
        "member_code": record.member_code,
        "canonical_name": record.name_ko,
        "aliases": [
            value
            for value in (record.name_hanja, record.name_en)
            if value and value != record.name_ko
        ],
        "birth_date": record.birth_date.isoformat() if record.birth_date else None,
        "party": record.party,
        "district": record.district,
        "reelection": record.reelection,
        "election_type": record.election_type,
        "committees": record.committees,
    }


def assembly_member_content_hash(normalized: dict[str, object]) -> str:
    canonical = json.dumps(
        normalized,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class AssemblyRosterEnumerator:
    FEEDER = ASSEMBLY_BASE_PROFILE_FEEDER
    SCOPE_KEY = ASSEMBLY_BASE_PROFILE_SCOPE
    SEMANTIC_SCOPE = ASSEMBLY_BASE_PROFILE_SEMANTIC_SCOPE
    SOURCE_CONTRACT = ASSEMBLY_BASE_PROFILE_SOURCE_CONTRACT

    def __init__(
        self,
        connector: OpenAssemblyMemberConnector,
        repository: SqlAlchemyRepository,
        policy: SourcePolicy | None = None,
    ) -> None:
        self.connector = connector
        self.repository = repository
        self.policy = policy or national_assembly_member_policy()

    def _checkpoint_observation_ids(
        self, seen_hashes: dict[str, str]
    ) -> dict[str, UUID]:
        if not seen_hashes:
            return {}
        current: dict[str, UUID] = {}
        for observation in self.repository.feeder_observations(self.FEEDER, self.SCOPE_KEY):
            expected_hash = seen_hashes.get(observation.provider_record_key)
            if (
                expected_hash is None
                or expected_hash != observation.content_hash
                or observation.semantic_scope != self.SEMANTIC_SCOPE
            ):
                continue
            existing = current.get(observation.provider_record_key)
            if existing is not None and existing != observation.id:
                raise AssemblyCoverageError(
                    "checkpoint provider identity maps to multiple observations"
                )
            current[observation.provider_record_key] = observation.id
        if set(current) != set(seen_hashes):
            raise AssemblyCoverageError(
                "checkpoint observations do not match the committed provider manifest"
            )
        return current

    def enumerate(self, *, resume: bool = False) -> AssemblyEnumerationResult:
        if any((self.connector.name, self.connector.party, self.connector.district)):
            raise AssemblyCoverageError("L3 roster enumeration must be unfiltered")
        if self.policy.domain != self.connector.HOST:
            raise PolicyDenied("SourcePolicy domain does not match the National Assembly connector")
        require_policy(self.policy, PolicyAction.FETCH)
        require_policy(self.policy, PolicyAction.STORE_METADATA)

        self.repository.assert_ready()
        prior_checkpoint = self.repository.source_checkpoint(self.FEEDER, self.SCOPE_KEY)
        run = self.repository.start_source_run(
            self.FEEDER,
            self.SCOPE_KEY,
            {"source_contract": self.SOURCE_CONTRACT, "resume": resume},
        )
        pages_committed = 0
        try:
            start_page = 1
            expected_total: int | None = None
            expected_pages: int | None = None
            seen_hashes: dict[str, str] = {}
            page_fingerprints: list[str] = []
            current_observation_ids: dict[str, UUID] = {}
            if resume and prior_checkpoint is not None:
                if prior_checkpoint.cursor is None:
                    raise AssemblyCoverageError("resume checkpoint lacks a page cursor")
                try:
                    start_page = int(prior_checkpoint.cursor) + 1
                    expected_total = int(prior_checkpoint.metadata["list_total_count"])
                    expected_pages = int(prior_checkpoint.metadata["expected_pages"])
                    seen_hashes = dict(prior_checkpoint.metadata["seen_provider_hashes"])
                    page_fingerprints = list(prior_checkpoint.metadata["page_fingerprints"])
                except (KeyError, TypeError, ValueError):
                    raise AssemblyCoverageError("resume checkpoint metadata is invalid") from None
                if start_page > expected_pages:
                    raise AssemblyCoverageError("resume checkpoint already covers the full roster")
                current_observation_ids = self._checkpoint_observation_ids(seen_hashes)

            page_index = start_page
            while True:
                self.connector.page_index = page_index
                target = self.connector.discover()[0]
                document = self.connector.fetch(target)
                if document.metadata.get("page_index") != str(page_index):
                    raise AssemblyCoverageError("National Assembly page index is inconsistent")
                if document.metadata.get("page_size") != str(self.connector.page_size):
                    raise AssemblyCoverageError("National Assembly page size is inconsistent")
                try:
                    total_count = int(document.metadata["list_total_count"])
                except (KeyError, TypeError, ValueError):
                    raise AssemblyCoverageError("National Assembly total count is unavailable") from None
                if total_count <= 0:
                    raise AssemblyCoverageError("National Assembly roster total must be positive")
                current_expected_pages = ceil(total_count / self.connector.page_size)
                if expected_total is None:
                    expected_total = total_count
                    expected_pages = current_expected_pages
                elif total_count != expected_total or current_expected_pages != expected_pages:
                    raise AssemblyCoverageError("National Assembly total count changed during enumeration")
                assert expected_pages is not None
                if page_index > expected_pages:
                    raise AssemblyCoverageError("National Assembly returned an unexpected extra page")

                members = self.connector.parse_members(document)
                expected_row_count = min(
                    self.connector.page_size,
                    expected_total - ((page_index - 1) * self.connector.page_size),
                )
                if len(members) != expected_row_count:
                    raise AssemblyCoverageError("National Assembly page row count is incomplete")

                page_hashes: dict[str, str] = {}
                normalized_by_key: dict[str, dict[str, object]] = {}
                for member in members:
                    normalized = normalized_assembly_member(member)
                    content_hash = assembly_member_content_hash(normalized)
                    if member.member_code in page_hashes:
                        if page_hashes[member.member_code] != content_hash:
                            raise AssemblyCoverageError("conflicting MONA_CD appears within one page")
                        raise AssemblyCoverageError("duplicate MONA_CD appears within one page")
                    if member.member_code in seen_hashes:
                        if seen_hashes[member.member_code] != content_hash:
                            raise AssemblyCoverageError("conflicting MONA_CD appears across pages")
                        raise AssemblyCoverageError("duplicate MONA_CD appears across pages")
                    page_hashes[member.member_code] = content_hash
                    normalized_by_key[member.member_code] = normalized

                fingerprint_payload = json.dumps(
                    sorted(page_hashes.items()),
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
                page_fingerprint = hashlib.sha256(
                    fingerprint_payload.encode("utf-8")
                ).hexdigest()
                if page_fingerprint in page_fingerprints:
                    raise AssemblyCoverageError("National Assembly returned duplicate page content")

                ingestion = IngestionPipeline(self.connector).ingest_document(
                    document, self.policy
                )
                observations = []
                for member in members:
                    normalized = normalized_by_key[member.member_code]
                    aliases = [
                        value
                        for value in (member.name_hanja, member.name_en)
                        if value and value != member.name_ko
                    ]
                    observations.append(
                        FeederObservation(
                            feeder=self.FEEDER,
                            scope_key=self.SCOPE_KEY,
                            provider_record_key=member.member_code,
                            snapshot_id=ingestion.snapshot.id,
                            run_id=run.id,
                            semantic_scope=self.SEMANTIC_SCOPE,
                            identity_hints={
                                "canonical_name": member.name_ko,
                                "aliases": aliases,
                                "birth_date": normalized["birth_date"],
                                "external_ids": {
                                    "assembly_mona_cd": member.member_code
                                },
                            },
                            normalized=normalized,
                            content_hash=page_hashes[member.member_code],
                        )
                    )

                next_seen_hashes = seen_hashes | page_hashes
                next_page_fingerprints = [*page_fingerprints, page_fingerprint]
                checkpoint_metadata = {
                    "page_size": self.connector.page_size,
                    "expected_pages": expected_pages,
                    "list_total_count": expected_total,
                    "source_contract": self.SOURCE_CONTRACT,
                    "seen_provider_hashes": next_seen_hashes,
                    "page_fingerprints": next_page_fingerprints,
                }
                commit_result = self.repository.commit_source_page(
                    run_id=run.id,
                    policy=self.policy,
                    source=ingestion.source,
                    snapshot=ingestion.snapshot,
                    observations=observations,
                    cursor=str(page_index),
                    checkpoint_metadata=checkpoint_metadata,
                )
                if len(commit_result.observation_ids) != len(members):
                    raise AssemblyCoverageError(
                        "National Assembly page persistence returned incomplete observations"
                    )
                for member, observation_id in zip(
                    members, commit_result.observation_ids, strict=True
                ):
                    current_observation_ids[member.member_code] = observation_id
                pages_committed += 1
                seen_hashes = next_seen_hashes
                page_fingerprints = next_page_fingerprints

                if page_index == expected_pages:
                    if len(seen_hashes) != expected_total:
                        raise AssemblyCoverageError(
                            "National Assembly unique record coverage is incomplete"
                        )
                    if set(current_observation_ids) != set(seen_hashes):
                        raise AssemblyCoverageError(
                            "National Assembly observation coverage is incomplete"
                        )
                    break
                page_index += 1

            completed = self.repository.finish_source_run(run.id, SourceRunStatus.SUCCESS)
            return AssemblyEnumerationResult(
                completed,
                pages_committed,
                len(seen_hashes),
                tuple(current_observation_ids[key] for key in sorted(current_observation_ids)),
            )
        except Exception as exc:
            status = (
                SourceRunStatus.PARTIAL if pages_committed else SourceRunStatus.FAILED
            )
            self.repository.finish_source_run(
                run.id,
                status,
                error_code=type(exc).__name__[:120],
                error_summary="Assembly enumeration did not complete",
            )
            raise

    def enumerate_and_materialize(
        self, *, resume: bool = False
    ) -> AssemblyRosterMaterializationResult:
        enumeration = self.enumerate(resume=resume)
        if enumeration.run.status != SourceRunStatus.SUCCESS:
            raise AssemblyCoverageError("only a successful full roster may be materialized")
        if (
            len(enumeration.observation_ids) != enumeration.unique_records
            or len(set(enumeration.observation_ids)) != enumeration.unique_records
        ):
            raise AssemblyCoverageError(
                "successful Assembly enumeration lacks a deterministic observation set"
            )
        for observation_id in enumeration.observation_ids:
            observation = self.repository.feeder_observation(observation_id)
            if observation is None:
                raise AssemblyCoverageError(
                    "successful Assembly enumeration references a missing observation"
                )
            if (
                observation.feeder != self.FEEDER
                or observation.scope_key != self.SCOPE_KEY
                or observation.semantic_scope != self.SEMANTIC_SCOPE
            ):
                raise AssemblyCoverageError(
                    "successful Assembly enumeration references an incompatible observation"
                )
        materializations = tuple(
            self.repository.materialize_feeder_observation(observation_id)
            for observation_id in enumeration.observation_ids
        )
        return AssemblyRosterMaterializationResult(enumeration, materializations)


def render_staged_json(items: list[StagedAssemblyMember]) -> str:
    return json.dumps(
        [item.to_dict() for item in items],
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Stage National Assembly member rows as identity candidates."
    )
    parser.add_argument("--page-index", type=int, default=1)
    parser.add_argument("--page-size", type=int, default=100)
    parser.add_argument("--name")
    parser.add_argument("--party")
    parser.add_argument("--district")
    parser.add_argument(
        "--enumerate",
        action="store_true",
        help="Persist and validate the complete unfiltered roster.",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume full enumeration from the last committed page.",
    )
    parser.add_argument(
        "--materialize",
        action="store_true",
        help="Materialize the exact current roster after a successful full enumeration.",
    )
    parser.add_argument(
        "--publish-base-profile",
        action="store_true",
        help="Publish the four source-specific base-profile fields from the latest successful roster.",
    )
    parser.add_argument("--database-url")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.materialize and not (args.enumerate or args.resume):
        parser.error("--materialize requires --enumerate or --resume")
    if args.publish_base_profile and any(
        (args.enumerate, args.resume, args.materialize, args.name, args.party, args.district)
    ):
        parser.error("--publish-base-profile is a separate operation and accepts no roster filters")
    connector = OpenAssemblyMemberConnector(
        page_index=args.page_index,
        page_size=args.page_size,
        name=args.name,
        party=args.party,
        district=args.district,
    )
    try:
        if args.publish_base_profile:
            result = AssemblyBaseProfilePublisher(
                SqlAlchemyRepository(args.database_url)
            ).publish_latest_successful()
            print(
                json.dumps(
                    {
                        "run_id": str(result.run_id),
                        "status": "SUCCESS",
                        "observations_considered": result.observations_considered,
                        "observations_published": result.observations_published,
                        "published_claims": result.published_claims,
                        "unchanged_claims": result.unchanged_claims,
                        "missing_field_counts": result.missing_field_counts,
                        "skipped_observation_ids": [
                            str(item) for item in result.skipped_observation_ids
                        ],
                    },
                    ensure_ascii=False,
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0
        if args.enumerate or args.resume:
            enumerator = AssemblyRosterEnumerator(
                connector,
                SqlAlchemyRepository(args.database_url),
            )
            materialization_outcomes: dict[str, int] | None = None
            if args.materialize:
                materialized = enumerator.enumerate_and_materialize(resume=args.resume)
                enumeration = materialized.enumeration
                materialization_outcomes = materialized.outcome_counts()
            else:
                enumeration = enumerator.enumerate(resume=args.resume)
            payload: dict[str, object] = {
                "run_id": str(enumeration.run.id),
                "status": enumeration.run.status.value,
                "pages_committed": enumeration.pages_committed,
                "unique_records": enumeration.unique_records,
            }
            if materialization_outcomes is not None:
                payload["materialization_outcomes"] = materialization_outcomes
            print(
                json.dumps(
                    payload,
                    ensure_ascii=False,
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0
        staged = AssemblyRosterStager(connector).stage()
    except (AssemblyApiError, MaterializationError, PolicyDenied, ValueError) as exc:
        parser.error(str(exc))
    print(render_staged_json(staged))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
