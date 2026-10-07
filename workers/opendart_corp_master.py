"""Persist the OpenDART corporation-code master (all filers, listed and unlisted) as observations.

Each observation keeps only ``corp_code``, Korean/English name, stock code and modify date. The
master is an Organization-name registry for exact biography binding; it creates no Organization,
Person or Claim.
"""

from __future__ import annotations

import argparse
import hashlib
import json

from packages.connectors.open_dart_corporate import (
    DartApiError,
    OpenDartCorpCodeConnector,
    open_dart_corporate_policy,
)
from packages.domain.contracts import FeederObservation
from packages.domain.enums import SourceRunStatus
from packages.persistence import SqlAlchemyRepository
from packages.verification.policy import PolicyAction, PolicyDenied, require_policy
from workers.ingest import IngestionPipeline

CORP_MASTER_FEEDER = "opendart_corp_master"
CORP_MASTER_SCOPE = "corp_code_master:current"
CORP_MASTER_SEMANTIC_SCOPE = "corporation_code_registry"
CORP_MASTER_CONTRACT = "opendart_corp_code_master"


def enumerate_master(repository: SqlAlchemyRepository, *, api_key: str | None = None, transport=None):
    policy = open_dart_corporate_policy()
    require_policy(policy, PolicyAction.FETCH)
    require_policy(policy, PolicyAction.STORE_METADATA)
    repository.assert_ready()
    run = repository.start_source_run(CORP_MASTER_FEEDER, CORP_MASTER_SCOPE, {"source_contract": CORP_MASTER_CONTRACT})
    try:
        connector = OpenDartCorpCodeConnector(api_key=api_key, transport=transport)
        document = connector.fetch(connector.discover()[0])
        records = connector.parse_corporations(document)
        ingestion = IngestionPipeline(connector).ingest_document(document, policy)
        observations, seen = [], {}
        for record in records:
            normalized = {
                "corp_code": record.corp_code,
                "corp_name": record.corp_name,
                "corp_eng_name": record.corp_eng_name,
                "stock_code": record.stock_code,
                "modify_date": record.modified_on.isoformat(),
                "identity_semantics": "PROVIDER_ORGANIZATION_KEY_NOT_CANONICAL_ORGANIZATION",
            }
            text = json.dumps(normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
            seen[record.corp_code] = content_hash
            observations.append(FeederObservation(
                feeder=CORP_MASTER_FEEDER, scope_key=CORP_MASTER_SCOPE,
                provider_record_key=record.corp_code, snapshot_id=ingestion.snapshot.id,
                run_id=run.id, semantic_scope=CORP_MASTER_SEMANTIC_SCOPE, identity_hints={},
                normalized=normalized, content_hash=content_hash,
            ))
        repository.commit_source_page(
            run_id=run.id, policy=policy, source=ingestion.source, snapshot=ingestion.snapshot,
            observations=observations, cursor="1",
            checkpoint_metadata={"source_contract": CORP_MASTER_CONTRACT, "record_count": len(seen)},
        )
        return repository.finish_source_run(run.id, SourceRunStatus.SUCCESS), len(seen)
    except Exception as exc:
        repository.finish_source_run(run.id, SourceRunStatus.FAILED, error_code=type(exc).__name__[:120],
                                     error_summary="OpenDART corporation master did not complete")
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url")
    args = parser.parse_args(argv)
    try:
        run, count = enumerate_master(SqlAlchemyRepository(args.database_url))
    except (DartApiError, PolicyDenied, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps({"run_id": str(run.id), "status": run.status.value, "corporations": count,
                      "observations_created": run.observations_created,
                      "observations_unchanged": run.observations_unchanged}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
