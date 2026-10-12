from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass

from packages.connectors.seoul_personnel_notices import (
    SeoulPersonnelNoticeAttachment,
    SeoulPersonnelNoticeConnector,
    SeoulPersonnelNoticeError,
    record_to_payload,
    seoul_personnel_notice_policy,
)
from packages.domain.contracts import FeederObservation, SourcePolicy, SourceRun
from packages.domain.enums import SourceRunStatus
from packages.persistence import SqlAlchemyRepository
from packages.verification.policy import PolicyAction, PolicyDenied, require_policy
from workers.ingest import IngestionPipeline


class SeoulPersonnelCoverageError(SeoulPersonnelNoticeError):
    pass


@dataclass(frozen=True)
class SeoulPersonnelEnumerationResult:
    run: SourceRun
    unique_records: int


def normalized_seoul_personnel_notice(
    record: SeoulPersonnelNoticeAttachment,
) -> dict[str, object]:
    return record_to_payload(record)


def seoul_personnel_content_hash(normalized: dict[str, object]) -> str:
    canonical = json.dumps(
        normalized,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class SeoulPersonnelNoticeEnumerator:
    FEEDER = "seoul_personnel_notice_attachments"
    SCOPE_KEY = "dataset:OA-2483"
    SEMANTIC_SCOPE = "local_civil_service_personnel_notice_attachment"
    SOURCE_CONTRACT = SeoulPersonnelNoticeConnector.SOURCE_CONTRACT

    def __init__(
        self,
        connector: SeoulPersonnelNoticeConnector,
        repository: SqlAlchemyRepository,
        policy: SourcePolicy | None = None,
    ) -> None:
        self.connector = connector
        self.repository = repository
        self.policy = policy or seoul_personnel_notice_policy()

    def enumerate(self) -> SeoulPersonnelEnumerationResult:
        if self.policy.domain != self.connector.HOST:
            raise PolicyDenied("SourcePolicy domain does not match the Seoul personnel connector")
        require_policy(self.policy, PolicyAction.FETCH)
        require_policy(self.policy, PolicyAction.STORE_METADATA)

        self.repository.assert_ready()
        run = self.repository.start_source_run(
            self.FEEDER,
            self.SCOPE_KEY,
            {
                "source_contract": self.SOURCE_CONTRACT,
                "full_download": True,
            },
        )
        try:
            document = self.connector.fetch(self.connector.discover()[0])
            if document.metadata.get("source_contract") != self.SOURCE_CONTRACT:
                raise SeoulPersonnelCoverageError("Seoul source contract is inconsistent")
            if document.metadata.get("full_download") != "true":
                raise SeoulPersonnelCoverageError("Seoul source is not marked as a full download")
            for key in (
                "author_retained",
                "phone_retained",
                "email_retained",
                "contents_retained",
                "read_count_retained",
            ):
                if document.metadata.get(key) != "false":
                    raise SeoulPersonnelCoverageError(
                        "Seoul connector did not prove privacy/content minimization"
                    )

            records = self.connector.parse_records(document)
            try:
                expected_count = int(document.metadata["record_count"])
            except (KeyError, ValueError):
                raise SeoulPersonnelCoverageError(
                    "Seoul personnel record count is unavailable"
                ) from None
            if expected_count <= 0 or len(records) != expected_count:
                raise SeoulPersonnelCoverageError(
                    "Seoul personnel download coverage is incomplete"
                )

            hashes: dict[str, str] = {}
            normalized_by_key: dict[str, dict[str, object]] = {}
            for record in records:
                normalized = normalized_seoul_personnel_notice(record)
                content_hash = seoul_personnel_content_hash(normalized)
                if record.board_id in hashes:
                    raise SeoulPersonnelCoverageError(
                        "duplicate Seoul BOARD_ID in normalized release"
                    )
                hashes[record.board_id] = content_hash
                normalized_by_key[record.board_id] = normalized

            manifest_payload = json.dumps(
                sorted(hashes.items()),
                ensure_ascii=False,
                separators=(",", ":"),
            )
            manifest_sha256 = hashlib.sha256(
                manifest_payload.encode("utf-8")
            ).hexdigest()

            ingestion = IngestionPipeline(self.connector).ingest_document(
                document, self.policy
            )
            observations = [
                FeederObservation(
                    feeder=self.FEEDER,
                    scope_key=self.SCOPE_KEY,
                    provider_record_key=record.board_id,
                    snapshot_id=ingestion.snapshot.id,
                    run_id=run.id,
                    provider_observed_at=None,
                    semantic_scope=self.SEMANTIC_SCOPE,
                    identity_hints={},
                    normalized=normalized_by_key[record.board_id],
                    content_hash=hashes[record.board_id],
                )
                for record in records
            ]
            self.repository.commit_source_page(
                run_id=run.id,
                policy=self.policy,
                source=ingestion.source,
                snapshot=ingestion.snapshot,
                observations=observations,
                cursor="complete",
                checkpoint_metadata={
                    "source_contract": self.SOURCE_CONTRACT,
                    "record_count": expected_count,
                    "manifest_sha256": manifest_sha256,
                    "full_download": True,
                },
            )
            completed = self.repository.finish_source_run(
                run.id, SourceRunStatus.SUCCESS
            )
            return SeoulPersonnelEnumerationResult(completed, len(records))
        except Exception as exc:
            self.repository.finish_source_run(
                run.id,
                SourceRunStatus.FAILED,
                error_code=type(exc).__name__[:120],
                error_summary="Seoul personnel enumeration did not complete",
            )
            raise


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Persist the complete Seoul OA-2483 personnel-notice attachment dataset."
    )
    parser.add_argument("--database-url")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result = SeoulPersonnelNoticeEnumerator(
            SeoulPersonnelNoticeConnector(),
            SqlAlchemyRepository(args.database_url),
        ).enumerate()
    except (SeoulPersonnelNoticeError, PolicyDenied, ValueError) as exc:
        parser.error(str(exc))
    print(
        json.dumps(
            {
                "run_id": str(result.run.id),
                "status": result.run.status.value,
                "scope_key": result.run.scope_key,
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
