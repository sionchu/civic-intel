from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime

from packages.connectors.mpm_key_positions import (
    RELEASE_AS_OF,
    MpmKeyPositionRecord,
    MpmKeyPositionsConnector,
    MpmKeyPositionsError,
    mpm_key_positions_policy,
    record_to_payload,
)
from packages.domain.contracts import FeederObservation, SourcePolicy, SourceRun
from packages.domain.enums import SourceRunStatus
from packages.persistence import SqlAlchemyRepository
from packages.verification.policy import PolicyAction, PolicyDenied, require_policy
from workers.ingest import IngestionPipeline


class MpmKeyPositionsCoverageError(MpmKeyPositionsError):
    pass


@dataclass(frozen=True)
class MpmKeyPositionsEnumerationResult:
    run: SourceRun
    attachments_committed: int
    unique_records: int


def normalized_mpm_key_position(record: MpmKeyPositionRecord) -> dict[str, object]:
    return record_to_payload(record)


def mpm_key_position_content_hash(normalized: dict[str, object]) -> str:
    canonical = json.dumps(
        normalized,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class MpmKeyPositionsEnumerator:
    FEEDER = "mpm_national_key_positions"
    SEMANTIC_SCOPE = "central_government_key_position_snapshot"
    SOURCE_CONTRACT = MpmKeyPositionsConnector.SOURCE_CONTRACT

    def __init__(
        self,
        connector: MpmKeyPositionsConnector,
        repository: SqlAlchemyRepository,
        policy: SourcePolicy | None = None,
    ) -> None:
        self.connector = connector
        self.repository = repository
        self.policy = policy or mpm_key_positions_policy()

    @property
    def scope_key(self) -> str:
        return f"as_of:{RELEASE_AS_OF.isoformat()}"

    def _verify_completed_attachments(
        self,
        completed_groups: tuple[str, ...],
        expected_hashes: dict[str, str],
    ) -> None:
        for group in completed_groups:
            document = self.connector.for_group(group).fetch(
                self.connector.for_group(group).discover()[0]
            )
            if document.metadata.get("raw_sha256") != expected_hashes.get(group):
                raise MpmKeyPositionsCoverageError(
                    "MPM completed attachment changed before resume"
                )

    def enumerate(self, *, resume: bool = False) -> MpmKeyPositionsEnumerationResult:
        if self.policy.domain != self.connector.HOST:
            raise PolicyDenied("SourcePolicy domain does not match the MPM connector")
        require_policy(self.policy, PolicyAction.FETCH)
        require_policy(self.policy, PolicyAction.STORE_METADATA)

        self.repository.assert_ready()
        prior_checkpoint = self.repository.source_checkpoint(self.FEEDER, self.scope_key)
        run = self.repository.start_source_run(
            self.FEEDER,
            self.scope_key,
            {
                "source_contract": self.SOURCE_CONTRACT,
                "as_of_date": RELEASE_AS_OF.isoformat(),
                "expected_groups": list(self.connector.GROUPS),
                "resume": resume,
            },
        )
        attachments_committed = 0
        try:
            start_index = 0
            committed_records = 0
            attachment_hashes: dict[str, str] = {}
            group_counts: dict[str, int] = {}
            if resume and prior_checkpoint is not None:
                if prior_checkpoint.cursor is None:
                    raise MpmKeyPositionsCoverageError(
                        "resume checkpoint lacks an attachment cursor"
                    )
                try:
                    start_index = int(prior_checkpoint.cursor)
                    attachment_hashes = dict(
                        prior_checkpoint.metadata["attachment_hashes"]
                    )
                    group_counts = {
                        str(key): int(value)
                        for key, value in dict(
                            prior_checkpoint.metadata["group_counts"]
                        ).items()
                    }
                    committed_records = int(
                        prior_checkpoint.metadata["committed_records"]
                    )
                except (KeyError, TypeError, ValueError):
                    raise MpmKeyPositionsCoverageError(
                        "resume checkpoint metadata is invalid"
                    ) from None
                expected_groups = list(self.connector.GROUPS)
                if prior_checkpoint.metadata.get("expected_groups") != expected_groups:
                    raise MpmKeyPositionsCoverageError(
                        "resume checkpoint attachment contract changed"
                    )
                if not 0 <= start_index <= len(expected_groups):
                    raise MpmKeyPositionsCoverageError(
                        "resume checkpoint cursor is invalid"
                    )
                completed_groups = tuple(expected_groups[:start_index])
                if set(attachment_hashes) != set(completed_groups):
                    raise MpmKeyPositionsCoverageError(
                        "resume checkpoint attachment hashes are incomplete"
                    )
                if set(group_counts) != set(completed_groups):
                    raise MpmKeyPositionsCoverageError(
                        "resume checkpoint group counts are incomplete"
                    )
                if sum(group_counts.values()) != committed_records:
                    raise MpmKeyPositionsCoverageError(
                        "resume checkpoint record count is inconsistent"
                    )
                if start_index == len(expected_groups):
                    raise MpmKeyPositionsCoverageError(
                        "resume checkpoint already covers the full MPM release"
                    )
                self._verify_completed_attachments(completed_groups, attachment_hashes)

            for group_index, group in enumerate(
                self.connector.GROUPS[start_index:],
                start=start_index + 1,
            ):
                group_connector = self.connector.for_group(group)
                document = group_connector.fetch(group_connector.discover()[0])
                if document.metadata.get("source_contract") != self.SOURCE_CONTRACT:
                    raise MpmKeyPositionsCoverageError(
                        "MPM source contract is inconsistent"
                    )
                if document.metadata.get("attachment_group") != group:
                    raise MpmKeyPositionsCoverageError(
                        "MPM attachment group is inconsistent"
                    )
                if document.metadata.get("as_of_date") != RELEASE_AS_OF.isoformat():
                    raise MpmKeyPositionsCoverageError(
                        "MPM release as-of date is inconsistent"
                    )
                if document.metadata.get("phone_retained") != "false":
                    raise MpmKeyPositionsCoverageError(
                        "MPM connector did not prove phone minimization"
                    )

                records = group_connector.parse_records(document)
                try:
                    expected_count = int(document.metadata["record_count"])
                except (KeyError, ValueError):
                    raise MpmKeyPositionsCoverageError(
                        "MPM attachment record count is unavailable"
                    ) from None
                if len(records) != expected_count or expected_count <= 0:
                    raise MpmKeyPositionsCoverageError(
                        "MPM attachment record coverage is incomplete"
                    )
                if len({item.provider_record_key for item in records}) != len(records):
                    raise MpmKeyPositionsCoverageError(
                        "MPM attachment provider keys are not unique"
                    )

                ingestion = IngestionPipeline(group_connector).ingest_document(
                    document, self.policy
                )
                observations = []
                for record in records:
                    normalized = normalized_mpm_key_position(record)
                    observations.append(
                        FeederObservation(
                            feeder=self.FEEDER,
                            scope_key=self.scope_key,
                            provider_record_key=record.provider_record_key,
                            snapshot_id=ingestion.snapshot.id,
                            run_id=run.id,
                            provider_observed_at=datetime.combine(
                                RELEASE_AS_OF,
                                datetime.min.time(),
                                tzinfo=UTC,
                            ),
                            semantic_scope=self.SEMANTIC_SCOPE,
                            identity_hints={},
                            normalized=normalized,
                            content_hash=mpm_key_position_content_hash(normalized),
                        )
                    )

                next_hashes = {
                    **attachment_hashes,
                    group: document.metadata["raw_sha256"],
                }
                next_counts = {**group_counts, group: len(records)}
                next_committed = committed_records + len(records)
                checkpoint_metadata = {
                    "source_contract": self.SOURCE_CONTRACT,
                    "as_of_date": RELEASE_AS_OF.isoformat(),
                    "expected_groups": list(self.connector.GROUPS),
                    "attachment_hashes": next_hashes,
                    "group_counts": next_counts,
                    "committed_records": next_committed,
                }
                self.repository.commit_source_page(
                    run_id=run.id,
                    policy=self.policy,
                    source=ingestion.source,
                    snapshot=ingestion.snapshot,
                    observations=observations,
                    cursor=str(group_index),
                    checkpoint_metadata=checkpoint_metadata,
                )
                attachments_committed += 1
                attachment_hashes = next_hashes
                group_counts = next_counts
                committed_records = next_committed

            if set(group_counts) != set(self.connector.GROUPS):
                raise MpmKeyPositionsCoverageError(
                    "MPM release attachment coverage is incomplete"
                )
            completed = self.repository.finish_source_run(run.id, SourceRunStatus.SUCCESS)
            return MpmKeyPositionsEnumerationResult(
                completed,
                attachments_committed,
                committed_records,
            )
        except Exception as exc:
            status = SourceRunStatus.PARTIAL if attachments_committed else SourceRunStatus.FAILED
            self.repository.finish_source_run(
                run.id,
                status,
                error_code=type(exc).__name__[:120],
                error_summary="MPM key-position enumeration did not complete",
            )
            raise


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Persist the reviewed 2026 H1 MPM national key-position release."
    )
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--database-url")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result = MpmKeyPositionsEnumerator(
            MpmKeyPositionsConnector(),
            SqlAlchemyRepository(args.database_url),
        ).enumerate(resume=args.resume)
    except (MpmKeyPositionsError, PolicyDenied, ValueError) as exc:
        parser.error(str(exc))
    print(
        json.dumps(
            {
                "run_id": str(result.run.id),
                "status": result.run.status.value,
                "scope_key": result.run.scope_key,
                "attachments_committed": result.attachments_committed,
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
