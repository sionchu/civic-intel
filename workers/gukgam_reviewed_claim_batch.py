from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from uuid import UUID

from packages.persistence import SqlAlchemyRepository
from workers.gukgam_reviewed_claim_import import (
    ReviewedGukgamClaimImport,
    prepare_reviewed_gukgam_claim_import,
)

GUKGAM_REVIEWED_CLAIM_BATCH_SCHEMA = "CIVIC_GUKGAM_REVIEWED_CLAIM_BATCH_V1"
GUKGAM_REVIEWED_CLAIM_BATCH_SEMANTICS = (
    "REVIEWED_OPERATOR_SUPPLIED_GUKGAM_CLAIM_BATCH_PREFLIGHT_V1"
)


class GukgamReviewedClaimBatchError(ValueError):
    pass


@dataclass(frozen=True)
class GukgamReviewedClaimBatchItem:
    review_key: str
    organization_id: UUID


@dataclass(frozen=True)
class GukgamReviewedClaimBatchManifest:
    items: tuple[GukgamReviewedClaimBatchItem, ...]
    digest: str


@dataclass(frozen=True)
class PreparedGukgamReviewedClaimBatch:
    manifest: GukgamReviewedClaimBatchManifest
    items: tuple[ReviewedGukgamClaimImport, ...]


def _canonical_manifest_payload(
    items: tuple[GukgamReviewedClaimBatchItem, ...],
) -> dict[str, object]:
    return {
        "schema": GUKGAM_REVIEWED_CLAIM_BATCH_SCHEMA,
        "items": [
            {
                "review_key": item.review_key,
                "organization_id": str(item.organization_id),
            }
            for item in sorted(
                items,
                key=lambda item: (item.review_key, str(item.organization_id)),
            )
        ],
    }


def parse_gukgam_reviewed_claim_batch_manifest(
    raw: object,
) -> GukgamReviewedClaimBatchManifest:
    if not isinstance(raw, dict):
        raise GukgamReviewedClaimBatchError("Gukgam batch manifest must be an object")
    if set(raw) != {"schema", "items"}:
        raise GukgamReviewedClaimBatchError(
            "Gukgam batch manifest fields changed unexpectedly"
        )
    if raw.get("schema") != GUKGAM_REVIEWED_CLAIM_BATCH_SCHEMA:
        raise GukgamReviewedClaimBatchError("Gukgam batch manifest schema is invalid")

    raw_items = raw.get("items")
    if not isinstance(raw_items, list) or not raw_items:
        raise GukgamReviewedClaimBatchError(
            "Gukgam batch manifest requires at least one reviewed item"
        )

    items: list[GukgamReviewedClaimBatchItem] = []
    seen_review_keys: set[str] = set()
    for raw_item in raw_items:
        if not isinstance(raw_item, dict) or set(raw_item) != {
            "review_key",
            "organization_id",
        }:
            raise GukgamReviewedClaimBatchError(
                "Gukgam batch manifest item fields changed unexpectedly"
            )
        review_key = raw_item.get("review_key")
        organization_id_text = raw_item.get("organization_id")
        if not isinstance(review_key, str) or not review_key.strip():
            raise GukgamReviewedClaimBatchError(
                "Gukgam batch manifest review_key must be non-empty"
            )
        if not isinstance(organization_id_text, str):
            raise GukgamReviewedClaimBatchError(
                "Gukgam batch manifest organization_id must be a UUID string"
            )
        try:
            organization_id = UUID(organization_id_text)
        except ValueError as exc:
            raise GukgamReviewedClaimBatchError(
                "Gukgam batch manifest organization_id is invalid"
            ) from exc
        normalized_review_key = review_key.strip()
        if normalized_review_key in seen_review_keys:
            raise GukgamReviewedClaimBatchError(
                "Gukgam batch manifest contains a duplicate review_key"
            )
        seen_review_keys.add(normalized_review_key)
        items.append(
            GukgamReviewedClaimBatchItem(
                review_key=normalized_review_key,
                organization_id=organization_id,
            )
        )

    normalized_items = tuple(
        sorted(
            items,
            key=lambda item: (item.review_key, str(item.organization_id)),
        )
    )
    canonical = json.dumps(
        _canonical_manifest_payload(normalized_items),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return GukgamReviewedClaimBatchManifest(
        items=normalized_items,
        digest=sha256(canonical).hexdigest(),
    )


def load_gukgam_reviewed_claim_batch_manifest(
    path: Path,
) -> GukgamReviewedClaimBatchManifest:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise GukgamReviewedClaimBatchError(
            "Gukgam batch manifest could not be read as JSON"
        ) from exc
    return parse_gukgam_reviewed_claim_batch_manifest(raw)


def prepare_gukgam_reviewed_claim_batch(
    repository: SqlAlchemyRepository,
    manifest: GukgamReviewedClaimBatchManifest,
) -> PreparedGukgamReviewedClaimBatch:
    prepared_items: list[ReviewedGukgamClaimImport] = []
    claim_ids: set[UUID] = set()
    evidence_ids: set[UUID] = set()

    for item in manifest.items:
        prepared = prepare_reviewed_gukgam_claim_import(
            repository,
            organization_id=item.organization_id,
            review_key=item.review_key,
        )
        if prepared.existing_claim is not None:
            raise GukgamReviewedClaimBatchError(
                "Gukgam batch preflight refuses an already published occurrence"
            )
        if prepared.claim.id in claim_ids:
            raise GukgamReviewedClaimBatchError(
                "Gukgam batch preflight produced a duplicate Claim ID"
            )
        if prepared.evidence.id in evidence_ids:
            raise GukgamReviewedClaimBatchError(
                "Gukgam batch preflight produced a duplicate Evidence ID"
            )
        claim_ids.add(prepared.claim.id)
        evidence_ids.add(prepared.evidence.id)
        prepared_items.append(prepared)

    return PreparedGukgamReviewedClaimBatch(
        manifest=manifest,
        items=tuple(prepared_items),
    )


def batch_receipt(prepared: PreparedGukgamReviewedClaimBatch) -> dict[str, object]:
    return {
        "status": "DRY_RUN",
        "semantics": GUKGAM_REVIEWED_CLAIM_BATCH_SEMANTICS,
        "manifest_schema": GUKGAM_REVIEWED_CLAIM_BATCH_SCHEMA,
        "manifest_sha256": prepared.manifest.digest,
        "item_count": len(prepared.items),
        "binding_committed": False,
        "claim_publication": False,
        "network_fetch": False,
        "items": [
            {
                "review_key": item.preflight.review_key,
                "organization_id": str(item.organization.id),
                "organization_name": item.organization.name,
                "committee_name": item.preflight.committee_name,
                "audit_date": item.preflight.audit_date,
                "audited_target": item.preflight.audited_target,
                "claim_id": str(item.claim.id),
                "evidence_id": str(item.evidence.id),
                "observation_id": str(item.observation.id),
                "snapshot_id": str(item.snapshot.id),
                "source_id": str(item.source.id),
                "claim_persisted": False,
            }
            for item in prepared.items
        ],
        "limitations": [
            "Every item must be explicitly supplied by the operator.",
            "Exact-name candidate discovery never adds items to this manifest.",
            "This command performs no Organization, Claim, Evidence, or source write.",
            "Batch commit is intentionally unavailable in this contract.",
        ],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Preflight an explicit reviewed Gukgam Claim batch manifest without writing."
        )
    )
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--database-url")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    repository = SqlAlchemyRepository(args.database_url)
    try:
        manifest = load_gukgam_reviewed_claim_batch_manifest(args.manifest)
        prepared = prepare_gukgam_reviewed_claim_batch(repository, manifest)
    except (TypeError, ValueError) as exc:
        parser.error(str(exc))

    print(
        json.dumps(
            batch_receipt(prepared),
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
