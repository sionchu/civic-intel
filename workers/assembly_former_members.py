"""Enumerate former National Assembly member terms (17–22대) and materialize former members.

``--enumerate`` persists one metadata-only observation per provider row (MONA_CD, names, term
dates and the term label; nothing else). ``--publish [--dry-run]`` applies the owner-approved
MONA_CD AUTO_CREATE rule in ``packages.verification.assembly_former_members``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from math import ceil

from packages.connectors.open_assembly import AssemblyApiError, national_assembly_member_policy
from packages.connectors.open_assembly_historical import (
    HISTORICAL_API_CODE,
    AssemblyHistoricalCareerError,
    AssemblyHistoricalCareerRecord,
    OpenAssemblyHistoricalMemberConnector,
)
from packages.domain.contracts import FeederObservation
from packages.domain.enums import SourceRunStatus
from packages.persistence import SqlAlchemyRepository
from packages.verification.assembly_former_members import (
    FORMER_MEMBER_FEEDER,
    FORMER_MEMBER_SCOPE,
    FORMER_MEMBER_SEMANTIC_SCOPE,
    FORMER_MEMBER_SOURCE_CONTRACT,
    IN_SCOPE_PROFILE_UNITS,
    AssemblyFormerMemberError,
    AssemblyFormerMemberPublisher,
    normalized_term,
    provider_record_key,
)
from packages.verification.policy import PolicyAction, PolicyDenied, require_policy
from workers.ingest import IngestionPipeline


def _hash(normalized: dict[str, object]) -> str:
    text = json.dumps(normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def enumerate_terms(repository: SqlAlchemyRepository, *, api_key: str | None = None,
                    transport=None, units=IN_SCOPE_PROFILE_UNITS, page_size: int = 1000):
    policy = national_assembly_member_policy()
    require_policy(policy, PolicyAction.FETCH)
    require_policy(policy, PolicyAction.STORE_METADATA)
    repository.assert_ready()
    run = repository.start_source_run(
        FORMER_MEMBER_FEEDER, FORMER_MEMBER_SCOPE, {"source_contract": FORMER_MEMBER_SOURCE_CONTRACT}
    )
    commits = 0
    seen: dict[str, str] = {}
    try:
        pages = []
        for unit in units:
            index, total = 1, None
            while True:
                connector = OpenAssemblyHistoricalMemberConnector(
                    unit, api_key=api_key, page_index=index, page_size=page_size, transport=transport
                )
                document = connector.fetch(connector.discover()[0])
                count = int(document.metadata.get("list_total_count") or 0)
                if count < 1 or (total is not None and count != total):
                    raise AssemblyHistoricalCareerError(f"unit {unit} total count is inconsistent")
                total = count
                payload = json.loads(document.body)
                rows = [
                    row
                    for block in payload.get(HISTORICAL_API_CODE, [])
                    if isinstance(block, dict)
                    for row in block.get("row", []) or []
                ]
                if len(rows) != min(page_size, total - (index - 1) * page_size):
                    raise AssemblyHistoricalCareerError(f"unit {unit} page {index} is incomplete")
                pages.append((connector, document, rows))
                if index >= ceil(total / page_size):
                    break
                index += 1
        for connector, document, rows in pages:
            ingestion = IngestionPipeline(connector).ingest_document(document, policy)
            observations: dict[str, FeederObservation] = {}
            for row in rows:
                record = AssemblyHistoricalCareerRecord.from_row(row)
                hanja = str(row.get("HJ_NM") or "").strip() or None
                normalized = normalized_term(record, hanja)
                content_hash = _hash(normalized)
                key = provider_record_key(record)
                if key in seen and seen[key] != content_hash:
                    raise AssemblyHistoricalCareerError(f"conflicting rows share key {key}")
                seen[key] = content_hash
                observations[key] = FeederObservation(
                    feeder=FORMER_MEMBER_FEEDER,
                    scope_key=FORMER_MEMBER_SCOPE,
                    provider_record_key=key,
                    snapshot_id=ingestion.snapshot.id,
                    run_id=run.id,
                    semantic_scope=FORMER_MEMBER_SEMANTIC_SCOPE,
                    identity_hints={
                        "canonical_name": record.name_ko,
                        "external_ids": {"assembly_mona_cd": record.member_code},
                    },
                    normalized=normalized,
                    content_hash=content_hash,
                )
            commits += 1
            repository.commit_source_page(
                run_id=run.id,
                policy=policy,
                source=ingestion.source,
                snapshot=ingestion.snapshot,
                observations=list(observations.values()),
                cursor=str(commits),
                checkpoint_metadata={
                    "source_contract": FORMER_MEMBER_SOURCE_CONTRACT,
                    "profile_units": list(units),
                    "row_total": len(seen),
                    "seen_provider_hashes": dict(sorted(seen.items())),
                },
            )
        return repository.finish_source_run(run.id, SourceRunStatus.SUCCESS), len(seen)
    except Exception as exc:
        repository.finish_source_run(
            run.id,
            SourceRunStatus.PARTIAL if commits else SourceRunStatus.FAILED,
            error_code=type(exc).__name__[:120],
            error_summary="Former-member term enumeration did not complete",
        )
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--enumerate", action="store_true")
    mode.add_argument("--publish", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--database-url")
    args = parser.parse_args(argv)
    repository = SqlAlchemyRepository(args.database_url)
    try:
        if args.enumerate:
            run, rows = enumerate_terms(repository)
            payload: dict[str, object] = {
                "run_id": str(run.id), "status": run.status.value, "rows": rows,
                "observations_created": run.observations_created,
                "observations_unchanged": run.observations_unchanged,
            }
        else:
            result = AssemblyFormerMemberPublisher(repository).publish(dry_run=args.dry_run)
            payload = {"dry_run": args.dry_run, **{k: str(v) if k == "run_id" else v for k, v in result.__dict__.items()}}
    except (AssemblyApiError, AssemblyHistoricalCareerError, AssemblyFormerMemberError, PolicyDenied, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
