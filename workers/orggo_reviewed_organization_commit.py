from __future__ import annotations

import re
from dataclasses import dataclass

from packages.application.context import Application
from workers.orggo_reviewed_organization_manifest import (
    ORGGO_REVIEWED_ORGANIZATION_MANIFEST_SCHEMA,
    PreparedOrgGoOrganization,
    ReviewedOrgGoOrganizationManifest,
    prepare_reviewed_orggo_organization_manifest,
)

ORGGO_REVIEWED_ORGANIZATION_COMMIT_SEMANTICS = "REVIEWED_ORGGO_ORGANIZATION_COMMIT_V1"
_SHA256 = re.compile("^[0-9a-f]{64}$")


@dataclass(frozen=True)
class ReviewedOrgGoOrganizationCommit:
    manifest: ReviewedOrgGoOrganizationManifest
    prepared_items: tuple[PreparedOrgGoOrganization, ...]

    @property
    def manifest_sha256(self) -> str:
        return self.manifest.sha256()

    @property
    def all_reused(self) -> bool:
        return all(item.action == "REUSE" for item in self.prepared_items)


def _expected_manifest_sha256(value: str) -> str:
    normalized = value.strip().casefold()
    if not _SHA256.fullmatch(normalized):
        raise ValueError("expected manifest SHA-256 must be 64 hex characters")
    return normalized


def prepare_reviewed_orggo_organization_commit(
    repository: Application,
    manifest: ReviewedOrgGoOrganizationManifest,
    proposal_raw: object,
    *,
    expected_manifest_sha256: str,
) -> ReviewedOrgGoOrganizationCommit:
    expected = _expected_manifest_sha256(expected_manifest_sha256)
    if manifest.sha256() != expected:
        raise ValueError(
            "org.go Organization manifest SHA-256 does not match operator confirmation"
        )
    dry_run = prepare_reviewed_orggo_organization_manifest(repository, manifest, proposal_raw)
    reused = tuple(item.action == "REUSE" for item in dry_run.prepared_items)
    if any(reused) and (not all(reused)):
        raise ValueError("org.go Organization commit refuses partially materialized manifest state")
    return ReviewedOrgGoOrganizationCommit(manifest=manifest, prepared_items=dry_run.prepared_items)


def _item_receipt(item: PreparedOrgGoOrganization) -> dict[str, object]:
    return {
        **item.manifest_item.to_dict(),
        "organization_id": str(item.organization.id),
        "organization_name": item.organization.name,
        "organization_persisted": True,
        "gukgam_claim_publication": False,
        "network_fetch": False,
    }


def commit_reviewed_orggo_organizations(
    repository: Application, prepared: ReviewedOrgGoOrganizationCommit
) -> dict[str, object]:
    item_count = len(prepared.prepared_items)
    if prepared.all_reused:
        status = "REUSED"
        organizations_created = 0
        organizations_reused = item_count
    else:
        result = repository.organizations.import_organization_batch(
            [item.organization for item in prepared.prepared_items]
        )
        status = "COMMITTED" if result.organizations_created else "REUSED"
        organizations_created = result.organizations_created
        organizations_reused = result.organizations_reused
    return {
        "status": status,
        "semantics": ORGGO_REVIEWED_ORGANIZATION_COMMIT_SEMANTICS,
        "schema": ORGGO_REVIEWED_ORGANIZATION_MANIFEST_SCHEMA,
        "manifest_sha256": prepared.manifest_sha256,
        "proposal_core_sha256": prepared.manifest.proposal_core_sha256,
        "item_count": item_count,
        "organizations_created": organizations_created,
        "organizations_reused": organizations_reused,
        "write_performed": organizations_created > 0,
        "automatic_candidate_enumeration": False,
        "gukgam_claim_publication": False,
        "network_fetch": False,
        "items": [_item_receipt(item) for item in prepared.prepared_items],
    }
