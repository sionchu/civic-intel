from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path

from packages.persistence import OrganizationClaimImportError, SqlAlchemyRepository
from packages.rendering.gukgam_organization_binding_review import (
    GukgamOrganizationBindingPreflightError,
)
from packages.rendering.gukgam_organization_claim import GukgamOrganizationClaimError
from workers.gukgam_reviewed_claim_batch_manifest import (
    GUKGAM_REVIEWED_CLAIM_BATCH_MANIFEST_SCHEMA,
    ReviewedGukgamClaimBatchDryRun,
    ReviewedGukgamClaimBatchManifest,
    parse_reviewed_gukgam_claim_batch_manifest,
    persist_prepared_reviewed_gukgam_claim_batch,
)
from workers.gukgam_reviewed_claim_import import (
    ReviewedGukgamClaimImport,
    prepare_reviewed_gukgam_claim_import,
)

GUKGAM_REVIEWED_CLAIM_BATCH_COMMIT_SEMANTICS = (
    "REVIEWED_GUKGAM_CLAIM_BATCH_COMMIT_V1"
)
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class ReviewedGukgamClaimBatchCommit:
    manifest: ReviewedGukgamClaimBatchManifest
    prepared_items: tuple[ReviewedGukgamClaimImport, ...]

    @property
    def manifest_sha256(self) -> str:
        return self.manifest.sha256()

    @property
    def all_reused(self) -> bool:
        return all(item.existing_claim is not None for item in self.prepared_items)


def _expected_manifest_sha256(value: str) -> str:
    normalized = value.strip().casefold()
    if not _SHA256.fullmatch(normalized):
        raise ValueError("expected manifest SHA-256 must be 64 hex characters")
    return normalized


def prepare_reviewed_gukgam_claim_batch_commit(
    repository: SqlAlchemyRepository,
    manifest: ReviewedGukgamClaimBatchManifest,
    *,
    expected_manifest_sha256: str,
) -> ReviewedGukgamClaimBatchCommit:
    expected = _expected_manifest_sha256(expected_manifest_sha256)
    actual = manifest.sha256()
    if actual != expected:
        raise ValueError("Gukgam batch manifest SHA-256 does not match operator confirmation")

    prepared = tuple(
        prepare_reviewed_gukgam_claim_import(
            repository,
            organization_id=item.organization_id,
            review_key=item.review_key,
        )
        for item in manifest.items
    )
    published = tuple(item.existing_claim is not None for item in prepared)
    if any(published) and not all(published):
        raise ValueError(
            "Gukgam batch commit refuses partially published manifest state"
        )
    return ReviewedGukgamClaimBatchCommit(
        manifest=manifest,
        prepared_items=prepared,
    )


def _item_receipt(
    prepared: ReviewedGukgamClaimImport,
) -> dict[str, object]:
    stored_claim = prepared.existing_claim or prepared.claim
    return {
        "organization_id": str(prepared.organization.id),
        "organization_name": prepared.organization.name,
        "review_key": prepared.preflight.review_key,
        "committee_name": prepared.preflight.committee_name,
        "audit_date": prepared.preflight.audit_date,
        "audited_target": prepared.preflight.audited_target,
        "claim_id": str(stored_claim.id),
        "evidence_id": str(prepared.evidence.id),
        "observation_id": str(prepared.observation.id),
        "snapshot_id": str(prepared.snapshot.id),
        "source_id": str(prepared.source.id),
        "claim_persisted": True,
        "binding_committed": False,
        "organization_created": False,
        "network_fetch": False,
    }


def commit_reviewed_gukgam_claim_batch(
    repository: SqlAlchemyRepository,
    prepared: ReviewedGukgamClaimBatchCommit,
) -> dict[str, object]:
    item_count = len(prepared.prepared_items)
    if prepared.all_reused:
        status = "REUSED"
        organizations_created = 0
        organizations_reused = item_count
        claims_created = 0
        claims_reused = item_count
    else:
        result = persist_prepared_reviewed_gukgam_claim_batch(
            repository,
            ReviewedGukgamClaimBatchDryRun(
                manifest=prepared.manifest,
                prepared_items=prepared.prepared_items,
            ),
        )
        if result.organizations_created != 0:
            raise OrganizationClaimImportError(
                "Gukgam batch commit unexpectedly created an Organization"
            )
        status = "COMMITTED" if result.claims_created else "REUSED"
        organizations_created = result.organizations_created
        organizations_reused = result.organizations_reused
        claims_created = result.claims_created
        claims_reused = result.claims_reused

    return {
        "status": status,
        "semantics": GUKGAM_REVIEWED_CLAIM_BATCH_COMMIT_SEMANTICS,
        "schema": GUKGAM_REVIEWED_CLAIM_BATCH_MANIFEST_SCHEMA,
        "manifest_sha256": prepared.manifest_sha256,
        "item_count": item_count,
        "organizations_created": organizations_created,
        "organizations_reused": organizations_reused,
        "claims_created": claims_created,
        "claims_reused": claims_reused,
        "write_performed": claims_created > 0,
        "automatic_candidate_enumeration": False,
        "network_fetch": False,
        "items": [
            _item_receipt(item)
            for item in prepared.prepared_items
        ],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Commit one explicitly reviewed Gukgam Claim batch after confirming the exact manifest SHA."
        )
    )
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--expected-manifest-sha256", required=True)
    parser.add_argument("--database-url")
    parser.add_argument(
        "--commit",
        action="store_true",
        help="Required explicit write confirmation for the reviewed manifest.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.commit:
        parser.error("Gukgam batch commit requires explicit --commit")

    try:
        raw = json.loads(args.manifest.read_text(encoding="utf-8"))
        manifest = parse_reviewed_gukgam_claim_batch_manifest(raw)
        repository = SqlAlchemyRepository(args.database_url)
        prepared = prepare_reviewed_gukgam_claim_batch_commit(
            repository,
            manifest,
            expected_manifest_sha256=args.expected_manifest_sha256,
        )
        receipt = commit_reviewed_gukgam_claim_batch(repository, prepared)
    except (
        GukgamOrganizationBindingPreflightError,
        GukgamOrganizationClaimError,
        OrganizationClaimImportError,
        OSError,
        RuntimeError,
        TypeError,
        ValueError,
        json.JSONDecodeError,
    ) as exc:
        parser.error(str(exc))

    print(json.dumps(receipt, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
