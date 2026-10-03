"""Materialize an explicitly reviewed MOIS Organization manifest.

Source-specific counterpart of the org.go reviewed Organization path. A manifest item is
accepted only when it equals an item of the pinned review-only MOIS proposal artifact, the
cited MOIS FeederObservation still exists with the same provider code and full name, and no
current canonical Organization already uses the name. The MOIS org_code stays a provider
identity; the canonical ID is a namespaced UUID derived from it. No Gukgam Claim is written.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID, uuid5

from packages.domain.contracts import Organization
from packages.persistence import OrganizationClaimImportError, SqlAlchemyRepository
from packages.rendering.mois_organization_proposal import (
    MOIS_FEEDER,
    MOIS_ORGANIZATION_PROPOSAL_SEMANTICS,
    MOIS_SCOPE_KEY,
)

MOIS_REVIEWED_ORGANIZATION_MANIFEST_SCHEMA = "civic.mois.reviewed_organization_manifest.v1"
MOIS_REVIEWED_ORGANIZATION_SEMANTICS = "REVIEWED_MOIS_ORGANIZATION_MATERIALIZATION_V1"
MOIS_ORGANIZATION_NAMESPACE = UUID("8d1f0c3e-7a52-5b8e-9e64-2f0d6c1a4b77")
_ORG_CODE = re.compile(r"^[A-Z0-9]{7}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_ITEM_FIELDS = {"organization_name", "org_code", "observation_id"}


def canonical_sha256(payload: object) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def organization_id_for_mois_code(org_code: str) -> UUID:
    if not _ORG_CODE.fullmatch(org_code):
        raise ValueError("MOIS org_code must be seven uppercase alphanumerics")
    return uuid5(MOIS_ORGANIZATION_NAMESPACE, org_code)


@dataclass(frozen=True)
class ReviewedMoisOrganizationItem:
    organization_name: str
    org_code: str
    observation_id: UUID

    def to_dict(self) -> dict[str, str]:
        return {
            "organization_name": self.organization_name,
            "org_code": self.org_code,
            "observation_id": str(self.observation_id),
        }


@dataclass(frozen=True)
class ReviewedMoisOrganizationManifest:
    proposal_core_sha256: str
    items: tuple[ReviewedMoisOrganizationItem, ...]

    def canonical_payload(self) -> dict[str, object]:
        return {
            "schema": MOIS_REVIEWED_ORGANIZATION_MANIFEST_SCHEMA,
            "proposal_core_sha256": self.proposal_core_sha256,
            "items": [item.to_dict() for item in self.items],
        }

    def sha256(self) -> str:
        return canonical_sha256(self.canonical_payload())


def manifest_from_proposal(proposal_raw: dict[str, object]) -> ReviewedMoisOrganizationManifest:
    """Build the full manifest for an owner decision covering every proposal item."""
    raw_items = proposal_raw.get("items")
    if not isinstance(raw_items, list):
        raise TypeError("MOIS proposal items are invalid")
    return parse_manifest(
        {
            "schema": MOIS_REVIEWED_ORGANIZATION_MANIFEST_SCHEMA,
            "proposal_core_sha256": canonical_sha256(proposal_raw),
            "items": [
                {
                    "organization_name": item["organization_name"],
                    "org_code": item["provider"]["org_code"],
                    "observation_id": item["provider"]["observation_id"],
                }
                for item in raw_items
            ],
        }
    )


def parse_manifest(raw: object) -> ReviewedMoisOrganizationManifest:
    if not isinstance(raw, dict) or set(raw) != {"schema", "proposal_core_sha256", "items"}:
        raise ValueError("MOIS Organization manifest fields changed unexpectedly")
    if raw["schema"] != MOIS_REVIEWED_ORGANIZATION_MANIFEST_SCHEMA:
        raise ValueError("MOIS Organization manifest schema is invalid")
    proposal_sha = str(raw["proposal_core_sha256"]).casefold()
    if not _SHA256.fullmatch(proposal_sha):
        raise ValueError("proposal_core_sha256 must be 64 hex characters")
    raw_items = raw["items"]
    if not isinstance(raw_items, list) or not raw_items:
        raise ValueError("MOIS Organization manifest items must be a non-empty list")
    items: list[ReviewedMoisOrganizationItem] = []
    for index, raw_item in enumerate(raw_items, start=1):
        if not isinstance(raw_item, dict) or set(raw_item) != _ITEM_FIELDS:
            raise ValueError(f"MOIS manifest item {index} fields changed unexpectedly")
        name = str(raw_item["organization_name"]).strip()
        code = str(raw_item["org_code"]).strip()
        if not name:
            raise ValueError(f"MOIS manifest item {index} has an empty name")
        organization_id_for_mois_code(code)
        items.append(
            ReviewedMoisOrganizationItem(name, code, UUID(str(raw_item["observation_id"])))
        )
    if len({item.org_code for item in items}) != len(items):
        raise ValueError("MOIS manifest duplicates org_code")
    if len({item.organization_name for item in items}) != len(items):
        raise ValueError("MOIS manifest duplicates organization_name")
    return ReviewedMoisOrganizationManifest(
        proposal_core_sha256=proposal_sha,
        items=tuple(sorted(items, key=lambda item: item.org_code)),
    )


@dataclass(frozen=True)
class PreparedMoisOrganization:
    item: ReviewedMoisOrganizationItem
    organization: Organization
    action: str


def prepare(
    repository: SqlAlchemyRepository,
    manifest: ReviewedMoisOrganizationManifest,
    proposal_raw: object,
    *,
    expected_manifest_sha256: str,
) -> tuple[PreparedMoisOrganization, ...]:
    if manifest.sha256() != expected_manifest_sha256.strip().casefold():
        raise ValueError("MOIS manifest SHA-256 does not match operator confirmation")
    if not isinstance(proposal_raw, dict):
        raise TypeError("MOIS proposal artifact must be a JSON object")
    if canonical_sha256(proposal_raw) != manifest.proposal_core_sha256:
        raise ValueError("MOIS proposal artifact SHA-256 does not match manifest")
    if proposal_raw.get("semantics") != MOIS_ORGANIZATION_PROPOSAL_SEMANTICS:
        raise ValueError("MOIS proposal artifact semantics are invalid")
    if proposal_raw.get("status") != "REVIEW_ONLY":
        raise ValueError("MOIS proposal artifact status is invalid")
    if proposal_raw.get("canonical_name_conflict_count") != 0:
        raise ValueError("MOIS proposal artifact contains canonical-name conflicts")
    proposal_by_code: dict[str, dict[str, object]] = {}
    for proposal_item in proposal_raw.get("items") or []:
        provider = proposal_item["provider"]
        proposal_by_code[str(provider["org_code"])] = proposal_item

    current = repository.organizations(current_only=True)
    current_by_id = {organization.id: organization for organization in current}
    current_names: dict[str, list[Organization]] = {}
    for organization in current:
        current_names.setdefault(organization.name.strip(), []).append(organization)

    prepared: list[PreparedMoisOrganization] = []
    for item in manifest.items:
        proposal_item = proposal_by_code.get(item.org_code)
        if proposal_item is None:
            raise ValueError(f"MOIS org_code is absent from the reviewed proposal: {item.org_code}")
        provider = proposal_item["provider"]
        assert isinstance(provider, dict)
        if (
            proposal_item.get("organization_name") != item.organization_name
            or provider.get("observation_id") != str(item.observation_id)
            or proposal_item.get("proposal_status") != "REVIEW_REQUIRED_NO_WRITE"
            or proposal_item.get("current_exact_canonical_match_count") != 0
        ):
            raise ValueError(f"MOIS manifest item differs from reviewed proposal: {item.org_code}")
        observation = repository.feeder_observation(item.observation_id)
        if (
            observation is None
            or observation.feeder != MOIS_FEEDER
            or observation.scope_key != MOIS_SCOPE_KEY
            or observation.provider_record_key != item.org_code
            or observation.normalized.get("full_name") != item.organization_name
        ):
            raise ValueError(f"MOIS provider observation no longer supports: {item.org_code}")
        organization_id = organization_id_for_mois_code(item.org_code)
        same_id = current_by_id.get(organization_id)
        same_name = current_names.get(item.organization_name, [])
        if same_id is not None and same_id.name != item.organization_name:
            raise ValueError(f"derived MOIS Organization ID collides: {item.org_code}")
        if same_name and same_name[0].id != organization_id:
            raise ValueError(
                f"canonical Organization already uses this exact name: {item.organization_name}"
            )
        prepared.append(
            PreparedMoisOrganization(
                item=item,
                organization=Organization(id=organization_id, name=item.organization_name),
                action="REUSE" if same_id is not None else "CREATE",
            )
        )
    actions = {entry.action for entry in prepared}
    if actions == {"CREATE", "REUSE"}:
        raise ValueError("MOIS commit refuses partially materialized manifest state")
    expected_current = proposal_raw.get("current_organization_count")
    reused = sum(entry.action == "REUSE" for entry in prepared)
    if len(current) != (expected_current or 0) + reused:
        raise ValueError("current Organization universe changed outside this reviewed manifest")
    return tuple(prepared)


def receipt(
    manifest: ReviewedMoisOrganizationManifest,
    prepared: tuple[PreparedMoisOrganization, ...],
    *,
    created: int,
    reused: int,
    write_performed: bool,
) -> dict[str, object]:
    return {
        "status": "COMMITTED" if created else ("DRY_RUN" if not write_performed else "REUSED"),
        "semantics": MOIS_REVIEWED_ORGANIZATION_SEMANTICS,
        "schema": MOIS_REVIEWED_ORGANIZATION_MANIFEST_SCHEMA,
        "manifest_sha256": manifest.sha256(),
        "proposal_core_sha256": manifest.proposal_core_sha256,
        "item_count": len(prepared),
        "organizations_to_create": sum(entry.action == "CREATE" for entry in prepared),
        "organizations_created": created,
        "organizations_reused": reused,
        "write_performed": write_performed,
        "gukgam_claim_publication": False,
        "network_fetch": False,
        "items": [
            {**entry.item.to_dict(), "organization_id": str(entry.organization.id), "action": entry.action}
            for entry in prepared
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--proposal", required=True, type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--write-full-manifest", type=Path)
    parser.add_argument("--expected-manifest-sha256")
    parser.add_argument("--database-url")
    parser.add_argument("--commit", action="store_true")
    args = parser.parse_args(argv)
    try:
        proposal_raw = json.loads(args.proposal.read_text(encoding="utf-8"))
        if args.write_full_manifest:
            manifest = manifest_from_proposal(proposal_raw)
            args.write_full_manifest.write_text(
                json.dumps(manifest.canonical_payload(), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            print(json.dumps({"manifest_sha256": manifest.sha256(), "item_count": len(manifest.items)}))
            return 0
        if args.manifest is None or args.expected_manifest_sha256 is None:
            parser.error("--manifest and --expected-manifest-sha256 are required")
        manifest = parse_manifest(json.loads(args.manifest.read_text(encoding="utf-8")))
        repository = SqlAlchemyRepository(args.database_url)
        prepared = prepare(
            repository, manifest, proposal_raw, expected_manifest_sha256=args.expected_manifest_sha256
        )
        if not args.commit:
            result = receipt(manifest, prepared, created=0, reused=0, write_performed=False)
        elif all(entry.action == "REUSE" for entry in prepared):
            result = receipt(manifest, prepared, created=0, reused=len(prepared), write_performed=False)
        else:
            batch = repository.import_organization_batch([entry.organization for entry in prepared])
            result = receipt(
                manifest,
                prepared,
                created=batch.organizations_created,
                reused=batch.organizations_reused,
                write_performed=batch.organizations_created > 0,
            )
    except (OrganizationClaimImportError, OSError, KeyError, TypeError, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
