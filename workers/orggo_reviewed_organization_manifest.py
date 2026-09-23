from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID, uuid5

from packages.domain.contracts import Organization
from packages.persistence import SqlAlchemyRepository

ORGGO_REVIEWED_ORGANIZATION_MANIFEST_SCHEMA = (
    "civic.orggo.reviewed_organization_manifest.v1"
)
ORGGO_REVIEWED_ORGANIZATION_DRY_RUN_SEMANTICS = (
    "REVIEWED_ORGGO_ORGANIZATION_MANIFEST_DRY_RUN_V1"
)
ORGGO_ORGANIZATION_NAMESPACE = UUID("5936f87c-1ef9-5103-b25d-0971ba976fb1")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class ReviewedOrgGoOrganizationManifestItem:
    organization_name: str
    category: str
    org_code: str
    chart_id: str
    source_locator: str

    def to_dict(self) -> dict[str, str]:
        return {
            "organization_name": self.organization_name,
            "category": self.category,
            "org_code": self.org_code,
            "chart_id": self.chart_id,
            "source_locator": self.source_locator,
        }


@dataclass(frozen=True)
class ReviewedOrgGoOrganizationManifest:
    proposal_core_sha256: str
    items: tuple[ReviewedOrgGoOrganizationManifestItem, ...]

    def canonical_payload(self) -> dict[str, object]:
        return {
            "schema": ORGGO_REVIEWED_ORGANIZATION_MANIFEST_SCHEMA,
            "proposal_core_sha256": self.proposal_core_sha256,
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


def organization_id_for_orggo_code(org_code: str) -> UUID:
    normalized = org_code.strip()
    if not re.fullmatch(r"[0-9]{7}", normalized):
        raise ValueError("org.go org_code must be seven digits")
    return uuid5(ORGGO_ORGANIZATION_NAMESPACE, normalized)


def _required_text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value.strip()


def _sha256_text(value: object, field: str) -> str:
    normalized = _required_text(value, field).casefold()
    if not _SHA256.fullmatch(normalized):
        raise ValueError(f"{field} must be 64 lowercase hex characters")
    return normalized


def parse_reviewed_orggo_organization_manifest(
    raw: object,
) -> ReviewedOrgGoOrganizationManifest:
    if not isinstance(raw, dict):
        raise TypeError("org.go Organization manifest must be a JSON object")
    if set(raw) != {"schema", "proposal_core_sha256", "items"}:
        raise ValueError("org.go Organization manifest fields changed unexpectedly")
    if raw.get("schema") != ORGGO_REVIEWED_ORGANIZATION_MANIFEST_SCHEMA:
        raise ValueError("org.go Organization manifest schema is invalid")
    proposal_sha = _sha256_text(raw.get("proposal_core_sha256"), "proposal_core_sha256")
    raw_items = raw.get("items")
    if not isinstance(raw_items, list) or not raw_items:
        raise ValueError("org.go Organization manifest items must be a non-empty list")

    items: list[ReviewedOrgGoOrganizationManifestItem] = []
    seen_codes: set[str] = set()
    seen_names: set[str] = set()
    expected_fields = {
        "organization_name",
        "category",
        "org_code",
        "chart_id",
        "source_locator",
    }
    for index, raw_item in enumerate(raw_items, start=1):
        if not isinstance(raw_item, dict):
            raise TypeError(f"org.go Organization manifest item {index} must be an object")
        if set(raw_item) != expected_fields:
            raise ValueError(
                f"org.go Organization manifest item {index} fields changed unexpectedly"
            )
        name = _required_text(raw_item.get("organization_name"), "organization_name")
        category = _required_text(raw_item.get("category"), "category")
        org_code = _required_text(raw_item.get("org_code"), "org_code")
        chart_id = _required_text(raw_item.get("chart_id"), "chart_id")
        source_locator = _required_text(raw_item.get("source_locator"), "source_locator")
        organization_id_for_orggo_code(org_code)
        if not chart_id.isdigit():
            raise ValueError("org.go chart_id must be numeric")
        if org_code in seen_codes:
            raise ValueError(f"org.go Organization manifest duplicates org_code: {org_code}")
        if name in seen_names:
            raise ValueError(f"org.go Organization manifest duplicates name: {name}")
        seen_codes.add(org_code)
        seen_names.add(name)
        items.append(
            ReviewedOrgGoOrganizationManifestItem(
                organization_name=name,
                category=category,
                org_code=org_code,
                chart_id=chart_id,
                source_locator=source_locator,
            )
        )
    return ReviewedOrgGoOrganizationManifest(
        proposal_core_sha256=proposal_sha,
        items=tuple(sorted(items, key=lambda item: item.org_code)),
    )


@dataclass(frozen=True)
class PreparedOrgGoOrganization:
    manifest_item: ReviewedOrgGoOrganizationManifestItem
    organization: Organization
    action: str

    def to_dict(self) -> dict[str, object]:
        return {
            **self.manifest_item.to_dict(),
            "organization_id": str(self.organization.id),
            "action": self.action,
            "organization_created": False,
        }


@dataclass(frozen=True)
class ReviewedOrgGoOrganizationDryRun:
    manifest: ReviewedOrgGoOrganizationManifest
    prepared_items: tuple[PreparedOrgGoOrganization, ...]
    current_organization_count: int

    def to_dict(self) -> dict[str, object]:
        return {
            "status": "DRY_RUN",
            "semantics": ORGGO_REVIEWED_ORGANIZATION_DRY_RUN_SEMANTICS,
            "schema": ORGGO_REVIEWED_ORGANIZATION_MANIFEST_SCHEMA,
            "manifest_sha256": self.manifest.sha256(),
            "proposal_core_sha256": self.manifest.proposal_core_sha256,
            "item_count": len(self.prepared_items),
            "current_organization_count": self.current_organization_count,
            "organizations_to_create": sum(
                item.action == "CREATE" for item in self.prepared_items
            ),
            "organizations_to_reuse": sum(
                item.action == "REUSE" for item in self.prepared_items
            ),
            "items": [item.to_dict() for item in self.prepared_items],
            "all_preflights_passed": True,
            "write_performed": False,
            "commit_available": False,
            "automatic_candidate_enumeration": False,
            "gukgam_claim_publication": False,
            "network_fetch": False,
        }


def _canonical_json_sha256(payload: object) -> str:
    raw = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _proposal_items_by_org_code(
    proposal_raw: object,
    expected_sha256: str,
) -> tuple[int, dict[str, dict[str, object]]]:
    if not isinstance(proposal_raw, dict):
        raise TypeError("org.go proposal artifact must be a JSON object")
    if _canonical_json_sha256(proposal_raw) != expected_sha256:
        raise ValueError("org.go proposal artifact SHA-256 does not match manifest")
    if proposal_raw.get("semantics") != "REVIEW_ONLY_ORGGO_ORGANIZATION_PROPOSAL_V1":
        raise ValueError("org.go proposal artifact semantics are invalid")
    if proposal_raw.get("status") != "REVIEW_ONLY":
        raise ValueError("org.go proposal artifact status is invalid")
    if proposal_raw.get("canonical_name_conflict_count") != 0:
        raise ValueError("org.go proposal artifact contains canonical-name conflicts")
    current_count = proposal_raw.get("current_organization_count")
    if not isinstance(current_count, int) or current_count < 0:
        raise ValueError("org.go proposal artifact current Organization count is invalid")
    raw_items = proposal_raw.get("items")
    if not isinstance(raw_items, list):
        raise TypeError("org.go proposal artifact items are invalid")
    by_code: dict[str, dict[str, object]] = {}
    for item in raw_items:
        if not isinstance(item, dict):
            raise TypeError("org.go proposal artifact item is invalid")
        provider = item.get("provider")
        if not isinstance(provider, dict):
            raise TypeError("org.go proposal artifact provider fields are invalid")
        code = provider.get("org_code")
        if not isinstance(code, str) or not code:
            raise ValueError("org.go proposal artifact org_code is invalid")
        if code in by_code:
            raise ValueError("org.go proposal artifact duplicates org_code")
        by_code[code] = item
    return current_count, by_code


def prepare_reviewed_orggo_organization_manifest(
    repository: SqlAlchemyRepository,
    manifest: ReviewedOrgGoOrganizationManifest,
    proposal_raw: object,
) -> ReviewedOrgGoOrganizationDryRun:
    proposal_current_count, proposal_by_code = _proposal_items_by_org_code(
        proposal_raw,
        manifest.proposal_core_sha256,
    )
    current = repository.organizations(current_only=True)
    current_by_id = {item.id: item for item in current}
    current_by_name: dict[str, list[Organization]] = {}
    for organization in current:
        current_by_name.setdefault(organization.name.strip(), []).append(organization)

    prepared: list[PreparedOrgGoOrganization] = []
    for item in manifest.items:
        proposal_item = proposal_by_code.get(item.org_code)
        if proposal_item is None:
            raise ValueError(
                f"org.go manifest org_code is absent from reviewed proposal: {item.org_code}"
            )
        provider = proposal_item.get("provider")
        assert isinstance(provider, dict)
        expected = {
            "organization_name": proposal_item.get("organization_name"),
            "category": provider.get("category"),
            "org_code": provider.get("org_code"),
            "chart_id": provider.get("chart_id"),
            "source_locator": provider.get("source_locator"),
        }
        if item.to_dict() != expected:
            raise ValueError(
                f"org.go manifest item differs from reviewed proposal: {item.org_code}"
            )
        if proposal_item.get("proposal_status") != "REVIEW_REQUIRED_NO_WRITE":
            raise ValueError("org.go reviewed proposal item status is invalid")
        if proposal_item.get("current_exact_canonical_match_count") != 0:
            raise ValueError("org.go reviewed proposal item has a canonical-name conflict")

        organization_id = organization_id_for_orggo_code(item.org_code)
        same_id = current_by_id.get(organization_id)
        same_name = current_by_name.get(item.organization_name, [])
        if len(same_name) > 1:
            raise ValueError(
                f"current canonical Organization name is duplicated: {item.organization_name}"
            )
        if same_id is not None and same_id.name != item.organization_name:
            raise ValueError(
                f"deterministic org.go Organization ID collides with another name: {item.org_code}"
            )
        if same_name and same_name[0].id != organization_id:
            raise ValueError(
                f"current canonical Organization already uses exact name with another ID: {item.organization_name}"
            )
        action = "REUSE" if same_id is not None else "CREATE"
        prepared.append(
            PreparedOrgGoOrganization(
                manifest_item=item,
                organization=Organization(
                    id=organization_id,
                    name=item.organization_name,
                ),
                action=action,
            )
        )
    reused_count = sum(item.action == "REUSE" for item in prepared)
    if len(current) != proposal_current_count + reused_count:
        raise ValueError(
            "current Organization universe changed outside this reviewed manifest"
        )
    return ReviewedOrgGoOrganizationDryRun(
        manifest=manifest,
        prepared_items=tuple(prepared),
        current_organization_count=len(current),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Preflight an explicit reviewed org.go Organization manifest without writes."
    )
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--proposal", required=True, type=Path)
    parser.add_argument("--database-url")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        manifest_raw = json.loads(args.manifest.read_text(encoding="utf-8"))
        proposal_raw = json.loads(args.proposal.read_text(encoding="utf-8"))
        manifest = parse_reviewed_orggo_organization_manifest(manifest_raw)
        repository = SqlAlchemyRepository(args.database_url)
        dry_run = prepare_reviewed_orggo_organization_manifest(
            repository,
            manifest,
            proposal_raw,
        )
    except (OSError, RuntimeError, TypeError, ValueError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    print(json.dumps(dry_run.to_dict(), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
