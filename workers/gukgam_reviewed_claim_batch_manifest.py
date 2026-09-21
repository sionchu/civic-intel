from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from packages.domain.contracts import Organization
from packages.persistence import OrganizationClaimImportError, SqlAlchemyRepository
from packages.persistence.repository import OrganizationClaimBatchResult
from packages.rendering.gukgam_organization_binding_review import (
    GukgamOrganizationBindingPreflightError,
)
from packages.rendering.gukgam_organization_claim import (
    GUKGAM_AUDIT_TARGET_PREDICATE,
    GukgamOrganizationClaimError,
)
from workers.gukgam_reviewed_claim_import import (
    ReviewedGukgamClaimImport,
    prepare_reviewed_gukgam_claim_import,
)

GUKGAM_REVIEWED_CLAIM_BATCH_MANIFEST_SCHEMA = (
    "civic.gukgam.reviewed_claim_batch_manifest.v1"
)
GUKGAM_REVIEWED_CLAIM_BATCH_MANIFEST_SEMANTICS = (
    "REVIEWED_GUKGAM_CLAIM_BATCH_MANIFEST_DRY_RUN_V1"
)


@dataclass(frozen=True)
class ReviewedGukgamClaimManifestItem:
    review_key: str
    organization_id: UUID

    def to_dict(self) -> dict[str, str]:
        return {
            "review_key": self.review_key,
            "organization_id": str(self.organization_id),
        }


@dataclass(frozen=True)
class ReviewedGukgamClaimBatchManifest:
    items: tuple[ReviewedGukgamClaimManifestItem, ...]

    def canonical_payload(self) -> dict[str, object]:
        return {
            "schema": GUKGAM_REVIEWED_CLAIM_BATCH_MANIFEST_SCHEMA,
            "items": [item.to_dict() for item in self.items],
        }

    def sha256(self) -> str:
        payload = json.dumps(
            self.canonical_payload(),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()


@dataclass(frozen=True)
class ReviewedGukgamClaimBatchDryRun:
    manifest: ReviewedGukgamClaimBatchManifest
    prepared_items: tuple[ReviewedGukgamClaimImport, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "status": "DRY_RUN",
            "semantics": GUKGAM_REVIEWED_CLAIM_BATCH_MANIFEST_SEMANTICS,
            "schema": GUKGAM_REVIEWED_CLAIM_BATCH_MANIFEST_SCHEMA,
            "manifest_sha256": self.manifest.sha256(),
            "item_count": len(self.prepared_items),
            "items": [_prepared_receipt(item) for item in self.prepared_items],
            "all_preflights_passed": True,
            "write_performed": False,
            "batch_commit_available": False,
            "automatic_candidate_enumeration": False,
            "network_fetch": False,
        }


def _required_text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value.strip()


def parse_reviewed_gukgam_claim_batch_manifest(
    raw: object,
) -> ReviewedGukgamClaimBatchManifest:
    if not isinstance(raw, dict):
        raise TypeError("Gukgam batch manifest must be a JSON object")
    if set(raw) != {"schema", "items"}:
        raise ValueError("Gukgam batch manifest fields changed unexpectedly")
    if raw.get("schema") != GUKGAM_REVIEWED_CLAIM_BATCH_MANIFEST_SCHEMA:
        raise ValueError("Gukgam batch manifest schema is invalid")

    raw_items = raw.get("items")
    if not isinstance(raw_items, list) or not raw_items:
        raise ValueError("Gukgam batch manifest items must be a non-empty list")

    items: list[ReviewedGukgamClaimManifestItem] = []
    seen_review_keys: set[str] = set()
    for index, raw_item in enumerate(raw_items, start=1):
        if not isinstance(raw_item, dict):
            raise TypeError(f"Gukgam batch manifest item {index} must be an object")
        if set(raw_item) != {"review_key", "organization_id"}:
            raise ValueError(
                f"Gukgam batch manifest item {index} fields changed unexpectedly"
            )
        review_key = _required_text(raw_item.get("review_key"), "review_key")
        organization_id_text = _required_text(
            raw_item.get("organization_id"),
            "organization_id",
        )
        try:
            organization_id = UUID(organization_id_text)
        except ValueError as exc:
            raise ValueError(
                f"Gukgam batch manifest item {index} organization_id is invalid"
            ) from exc
        if review_key in seen_review_keys:
            raise ValueError(
                f"Gukgam batch manifest contains duplicate review_key: {review_key}"
            )
        seen_review_keys.add(review_key)
        items.append(
            ReviewedGukgamClaimManifestItem(
                review_key=review_key,
                organization_id=organization_id,
            )
        )

    return ReviewedGukgamClaimBatchManifest(
        items=tuple(
            sorted(
                items,
                key=lambda item: (item.review_key, str(item.organization_id)),
            )
        )
    )


def _prepared_receipt(prepared: ReviewedGukgamClaimImport) -> dict[str, object]:
    return {
        "status": "DRY_RUN",
        "organization_id": str(prepared.organization.id),
        "organization_name": prepared.organization.name,
        "review_key": prepared.preflight.review_key,
        "predicate": GUKGAM_AUDIT_TARGET_PREDICATE,
        "committee_name": prepared.preflight.committee_name,
        "audit_date": prepared.preflight.audit_date,
        "audited_target": prepared.preflight.audited_target,
        "claim_id": str(prepared.claim.id),
        "evidence_id": str(prepared.evidence.id),
        "observation_id": str(prepared.observation.id),
        "snapshot_id": str(prepared.snapshot.id),
        "source_id": str(prepared.source.id),
        "binding_committed": False,
        "organization_created": False,
        "claim_persisted": False,
        "claim_created": False,
        "network_fetch": False,
    }


def prepare_reviewed_gukgam_claim_batch_manifest(
    repository: SqlAlchemyRepository,
    manifest: ReviewedGukgamClaimBatchManifest,
) -> ReviewedGukgamClaimBatchDryRun:
    prepared_items: list[ReviewedGukgamClaimImport] = []
    for item in manifest.items:
        prepared = prepare_reviewed_gukgam_claim_import(
            repository,
            organization_id=item.organization_id,
            review_key=item.review_key,
        )
        if prepared.existing_claim is not None:
            raise ValueError(
                "Gukgam batch manifest refuses already-published review_key: "
                f"{item.review_key}"
            )
        prepared_items.append(prepared)
    return ReviewedGukgamClaimBatchDryRun(
        manifest=manifest,
        prepared_items=tuple(prepared_items),
    )



def persist_prepared_reviewed_gukgam_claim_batch(
    repository: SqlAlchemyRepository,
    dry_run: ReviewedGukgamClaimBatchDryRun,
) -> OrganizationClaimBatchResult:
    expected = tuple(
        (item.review_key, item.organization_id)
        for item in dry_run.manifest.items
    )
    actual = tuple(
        (item.preflight.review_key, item.organization.id)
        for item in dry_run.prepared_items
    )
    if actual != expected:
        raise ValueError(
            "Gukgam prepared batch items do not match the canonical manifest"
        )
    if any(item.existing_claim is not None for item in dry_run.prepared_items):
        raise ValueError(
            "Gukgam prepared batch persistence refuses pre-existing Claims"
        )

    organizations_by_id: dict[UUID, Organization] = {}
    for item in dry_run.prepared_items:
        existing = organizations_by_id.get(item.organization.id)
        if existing is not None and existing != item.organization:
            raise ValueError(
                "Gukgam prepared batch has inconsistent duplicate Organization semantics"
            )
        organizations_by_id[item.organization.id] = item.organization

    return repository.import_organization_claim_batch(
        list(organizations_by_id.values()),
        [
            (item.organization, item.claim, [item.evidence])
            for item in dry_run.prepared_items
        ],
    )

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Preflight an explicit reviewed Gukgam Claim manifest without any writes."
        )
    )
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--database-url")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        raw = json.loads(args.manifest.read_text(encoding="utf-8"))
        manifest = parse_reviewed_gukgam_claim_batch_manifest(raw)
        repository = SqlAlchemyRepository(args.database_url)
        dry_run = prepare_reviewed_gukgam_claim_batch_manifest(repository, manifest)
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

    print(
        json.dumps(
            dry_run.to_dict(),
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
