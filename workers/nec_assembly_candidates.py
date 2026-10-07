"""Enumerate NEC National Assembly candidates (2004–2024 general elections) and publish matches.

``--enumerate`` persists one metadata-only observation per candidate row for each
(election, 지역구/비례대표) scope; address, gender and age are never stored. ``--publish
[--dry-run]`` attaches attributed education/career CLAIMs to exactly matching current or former
members (``packages.verification.nec_assembly_candidates``).
"""

from __future__ import annotations

import argparse
import hashlib
import json
from math import ceil

from packages.connectors.nec_local_elections import (
    NecApiError,
    NecAssemblyCandidateConnector,
    nec_local_election_policy,
)
from packages.domain.contracts import FeederObservation
from packages.domain.enums import SourceRunStatus
from packages.persistence import SqlAlchemyRepository
from packages.verification.nec_assembly_candidates import (
    ELECTION_TERMS,
    ELECTION_TYPES,
    NEC_ASSEMBLY_FEEDER,
    NEC_ASSEMBLY_SEMANTIC_SCOPE,
    NEC_ASSEMBLY_SOURCE_CONTRACT,
    NecAssemblyCandidateError,
    NecAssemblyCandidatePublisher,
    normalized_candidate,
    scope_key,
)
from packages.verification.policy import PolicyAction, PolicyDenied, require_policy
from workers.ingest import IngestionPipeline

PAGE_SIZE = 100


def _hash(normalized: dict[str, object]) -> str:
    text = json.dumps(normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def enumerate_scope(repository: SqlAlchemyRepository, election_id: str, election_type: int, *,
                    api_key: str | None = None, transport=None) -> tuple[str, int]:
    policy = nec_local_election_policy()
    require_policy(policy, PolicyAction.FETCH)
    require_policy(policy, PolicyAction.STORE_METADATA)
    scope = scope_key(election_id, election_type)
    run = repository.start_source_run(
        NEC_ASSEMBLY_FEEDER, scope, {"source_contract": NEC_ASSEMBLY_SOURCE_CONTRACT}
    )
    commits = 0
    seen: dict[str, str] = {}
    try:
        page, total = 1, None
        while True:
            connector = NecAssemblyCandidateConnector(
                election_id=election_id, election_type=election_type, api_key=api_key,
                page_no=page, page_size=PAGE_SIZE, transport=transport,
            )
            document = connector.fetch(connector.discover()[0])
            count = int(document.metadata.get("total_count") or 0)
            if count < 1 or (total is not None and count != total):
                raise NecApiError(f"{scope} total count is inconsistent")
            total = count
            records = connector.parse_candidates(document)
            if len(records) != min(PAGE_SIZE, total - (page - 1) * PAGE_SIZE):
                raise NecApiError(f"{scope} page {page} is incomplete")
            ingestion = IngestionPipeline(connector).ingest_document(document, policy)
            observations = []
            for record in records:
                normalized = normalized_candidate(record)
                content_hash = _hash(normalized)
                if record.candidate_id in seen and seen[record.candidate_id] != content_hash:
                    raise NecApiError(f"conflicting rows share huboid {record.candidate_id}")
                seen[record.candidate_id] = content_hash
                observations.append(FeederObservation(
                    feeder=NEC_ASSEMBLY_FEEDER, scope_key=scope,
                    provider_record_key=record.candidate_id, snapshot_id=ingestion.snapshot.id,
                    run_id=run.id, semantic_scope=NEC_ASSEMBLY_SEMANTIC_SCOPE,
                    identity_hints={"canonical_name": record.name_ko,
                                    "external_ids": {"nec_huboid": record.candidate_id}},
                    normalized=normalized, content_hash=content_hash,
                ))
            commits += 1
            repository.commit_source_page(
                run_id=run.id, policy=policy, source=ingestion.source, snapshot=ingestion.snapshot,
                observations=observations, cursor=str(page),
                checkpoint_metadata={
                    "source_contract": NEC_ASSEMBLY_SOURCE_CONTRACT, "total_count": total,
                    "seen_provider_hashes": dict(sorted(seen.items())),
                },
            )
            if page >= ceil(total / PAGE_SIZE):
                break
            page += 1
        if len(seen) != total:
            raise NecApiError(f"{scope} unique candidates {len(seen)} != total {total}")
        repository.finish_source_run(run.id, SourceRunStatus.SUCCESS)
        return scope, len(seen)
    except Exception as exc:
        repository.finish_source_run(
            run.id, SourceRunStatus.PARTIAL if commits else SourceRunStatus.FAILED,
            error_code=type(exc).__name__[:120],
            error_summary="NEC Assembly candidate enumeration did not complete",
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
            payload: dict[str, object] = {
                scope: rows
                for scope, rows in (
                    enumerate_scope(repository, election, kind)
                    for election in ELECTION_TERMS
                    for kind in ELECTION_TYPES
                )
            }
        else:
            payload = {"dry_run": args.dry_run,
                       **NecAssemblyCandidatePublisher(repository).publish(dry_run=args.dry_run).__dict__}
    except (NecApiError, NecAssemblyCandidateError, PolicyDenied, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
