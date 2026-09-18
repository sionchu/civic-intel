from __future__ import annotations

import argparse
import json
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from uuid import UUID

from packages.domain.contracts import (
    Claim,
    ClaimEvidence,
    FeederObservation,
    Organization,
)
from packages.domain.enums import SourceRunStatus
from packages.persistence import OrganizationClaimImportError, SqlAlchemyRepository
from packages.rendering.alio_organization_content import (
    ALIO_CLASSIFICATION_PREDICATE,
    ALIO_EXECUTIVE_FEEDER,
    ALIO_EXECUTIVE_PREDICATE,
    ALIO_EXECUTIVE_SCOPE,
    ALIO_EXECUTIVE_SEMANTIC_SCOPE,
    ALIO_EXECUTIVE_SOURCE_CONTRACT,
    AlioOrganizationContentError,
    build_alio_classification_claim,
    build_alio_executive_claim,
    organization_id_for_alio_apba_id,
    validate_alio_item4_observation,
)


@dataclass(frozen=True)
class AlioOrganizationImportItem:
    organization: Organization
    claims: tuple[tuple[Claim, ClaimEvidence], ...]


@dataclass(frozen=True)
class PreparedAlioOrganizationImport:
    run_id: UUID
    observations: tuple[FeederObservation, ...]
    items: tuple[AlioOrganizationImportItem, ...]
    named_rows: int
    masked_rows: int
    organizations_created: int
    organizations_reused: int


def _metadata_text(metadata: dict, key: str) -> str:
    value = metadata.get(key)
    if not isinstance(value, str) or not value.strip():
        raise AlioOrganizationContentError(f"ALIO item-4 checkpoint metadata is invalid: {key}")
    return value.strip()


def _complete_item4_run(repository: SqlAlchemyRepository):
    checkpoint = repository.source_checkpoint(ALIO_EXECUTIVE_FEEDER, ALIO_EXECUTIVE_SCOPE)
    if checkpoint is None or checkpoint.last_run_id is None:
        raise AlioOrganizationContentError("ALIO organization import requires a committed item-4 checkpoint")
    run = repository.source_run(checkpoint.last_run_id)
    if (
        run is None
        or run.status != SourceRunStatus.SUCCESS
        or run.feeder != ALIO_EXECUTIVE_FEEDER
        or run.scope_key != ALIO_EXECUTIVE_SCOPE
        or run.metadata.get("source_contract") != ALIO_EXECUTIVE_SOURCE_CONTRACT
    ):
        raise AlioOrganizationContentError("ALIO organization import requires a successful item-4 run")
    if checkpoint.cursor is None or run.checkpoint_after != checkpoint.cursor:
        raise AlioOrganizationContentError("ALIO item-4 checkpoint and run are inconsistent")
    metadata = checkpoint.metadata
    if not isinstance(metadata, dict):
        raise AlioOrganizationContentError("ALIO item-4 checkpoint metadata is invalid")
    if _metadata_text(metadata, "source_contract") != ALIO_EXECUTIVE_SOURCE_CONTRACT:
        raise AlioOrganizationContentError("ALIO item-4 checkpoint source contract is invalid")
    try:
        institution_total = int(metadata["institution_total"])
        institution_codes = list(metadata["institution_codes"])
        seen_provider_hashes = dict(metadata["seen_provider_hashes"])
        seen_disclosures = dict(metadata["seen_current_disclosures"])
        no_current = set(metadata.get("no_current_disclosures", []))
    except (KeyError, TypeError, ValueError):
        raise AlioOrganizationContentError("ALIO item-4 checkpoint provider manifest is invalid") from None
    if (
        institution_total <= 0
        or checkpoint.cursor != str(institution_total)
        or len(institution_codes) != institution_total
        or len(set(institution_codes)) != institution_total
        or any(not isinstance(code, str) or not code.strip() for code in institution_codes)
        or any(
            not isinstance(key, str)
            or not key.strip()
            or not isinstance(value, str)
            or not value.strip()
            for key, value in seen_disclosures.items()
        )
        or len(set(seen_disclosures.values())) != len(seen_disclosures)
        or any(not isinstance(value, str) or not value.strip() for value in no_current)
        or set(seen_disclosures.values()) | no_current != set(institution_codes)
        or set(seen_disclosures.values()) & no_current
        or not isinstance(seen_provider_hashes, dict)
        or any(not isinstance(key, str) or not isinstance(value, str) for key, value in seen_provider_hashes.items())
    ):
        raise AlioOrganizationContentError("ALIO item-4 checkpoint does not cover the full institution universe")
    return checkpoint, run, seen_provider_hashes, set(institution_codes), seen_disclosures


def _current_observations(
    repository: SqlAlchemyRepository,
    provider_hashes: dict[str, str],
) -> tuple[FeederObservation, ...]:
    all_versions = repository.feeder_observations(
        ALIO_EXECUTIVE_FEEDER,
        ALIO_EXECUTIVE_SCOPE,
    )
    versions_by_key: dict[str, list[FeederObservation]] = defaultdict(list)
    for observation in all_versions:
        versions_by_key[observation.provider_record_key].append(observation)

    selected: list[FeederObservation] = []
    for provider_key, content_hash in sorted(provider_hashes.items()):
        versions = versions_by_key.get(provider_key, [])
        matching = [item for item in versions if item.content_hash == content_hash]
        if len(matching) != 1:
            raise AlioOrganizationContentError(
                "ALIO item-4 checkpoint provider manifest does not resolve exactly one observation"
            )
        if len({item.content_hash for item in versions}) > 1:
            raise AlioOrganizationContentError(
                "ALIO item-4 immutable observation version requires explicit replacement"
            )
        selected.append(matching[0])
    return tuple(selected)


def _existing_alio_bindings(
    repository: SqlAlchemyRepository,
    organizations: Iterable[Organization],
) -> dict[str, tuple[Organization, ...]]:
    ids = [organization.id for organization in organizations]
    contexts = repository.published_organization_claim_contexts(ids)
    by_code: dict[str, list[Organization]] = defaultdict(list)
    for organization in organizations:
        claims, _ = contexts.get(organization.id, ((), {}))
        for claim in claims:
            if (
                claim.predicate not in {ALIO_CLASSIFICATION_PREDICATE, ALIO_EXECUTIVE_PREDICATE}
                or claim.qualifiers.get("source_contract") != ALIO_EXECUTIVE_SOURCE_CONTRACT
                or claim.qualifiers.get("source_scope") != ALIO_EXECUTIVE_SCOPE
                or claim.qualifiers.get("semantic_scope") != ALIO_EXECUTIVE_SEMANTIC_SCOPE
            ):
                continue
            apba_id = claim.qualifiers.get("alio_apba_id")
            if apba_id:
                by_code[apba_id].append(organization)
    return {code: tuple(items) for code, items in by_code.items()}


def _organization_for_group(
    code: str,
    name: str,
    organizations: tuple[Organization, ...],
    bindings: dict[str, tuple[Organization, ...]],
) -> Organization:
    exact = bindings.get(code, ())
    exact_ids = {organization.id for organization in exact}
    if len(exact_ids) > 1:
        raise AlioOrganizationContentError("ALIO apbaId has multiple exact canonical Organization bindings")
    if exact:
        organization = exact[0]
        if organization.name != name:
            raise AlioOrganizationContentError("ALIO exact Organization binding name conflicts with source")
        return organization

    deterministic_id = organization_id_for_alio_apba_id(code)
    deterministic = next(
        (organization for organization in organizations if organization.id == deterministic_id),
        None,
    )
    same_name = tuple(organization for organization in organizations if organization.name == name)
    if deterministic is not None:
        if deterministic.name != name:
            raise AlioOrganizationContentError("ALIO deterministic Organization id has a different name")
        if any(organization.id != deterministic.id for organization in same_name):
            raise AlioOrganizationContentError(
                "ALIO same-name Organization exists without an exact apbaId binding"
            )
        return deterministic
    if same_name:
        raise AlioOrganizationContentError(
            "ALIO same-name Organization exists without an exact apbaId binding"
        )
    return Organization(id=deterministic_id, name=name)


def prepare_import(repository: SqlAlchemyRepository) -> PreparedAlioOrganizationImport:
    """Build the entire ALIO organization publication operation without writing."""

    repository.assert_ready()
    _, run, provider_hashes, institution_codes, seen_disclosures = _complete_item4_run(repository)
    observations = _current_observations(repository, provider_hashes)
    contexts = repository.feeder_observation_contexts(item.id for item in observations)
    if len(contexts) != len(observations):
        raise AlioOrganizationContentError("ALIO item-4 observation provenance is incomplete")

    groups: dict[str, list[tuple[FeederObservation, dict[str, str]]]] = defaultdict(list)
    for observation in observations:
        context = contexts.get(observation.id)
        if context is None:
            raise AlioOrganizationContentError("ALIO item-4 observation provenance is unavailable")
        _, snapshot, source, policy = context
        fields = validate_alio_item4_observation(
            observation,
            snapshot=snapshot,
            source=source,
            policy=policy,
        )
        if (
            fields["alio_apba_id"] not in institution_codes
            or seen_disclosures.get(fields["disclosure_no"]) != fields["alio_apba_id"]
        ):
            raise AlioOrganizationContentError(
                "ALIO item-4 observation is outside the complete checkpoint manifest"
            )
        if fields["name_status"] == "NOT_PUBLISHED":
            raise AlioOrganizationContentError("ALIO current item-4 manifest contains a non-published row")
        groups[fields["alio_apba_id"]].append((observation, fields))

    current_organizations = tuple(repository.organizations(current_only=True))
    bindings = _existing_alio_bindings(repository, current_organizations)
    current_organization_ids = {organization.id for organization in current_organizations}
    items: list[AlioOrganizationImportItem] = []
    named_rows = 0
    masked_rows = 0
    for code, grouped in sorted(groups.items()):
        names = {fields["institution_name"] for _, fields in grouped}
        classifications = {
            (fields["classification"], fields["classification_text"])
            for _, fields in grouped
        }
        if len(names) != 1 or len(classifications) != 1:
            raise AlioOrganizationContentError("ALIO apbaId has conflicting institution identity fields")
        name = next(iter(names))
        organization = _organization_for_group(code, name, current_organizations, bindings)
        grouped_sorted = sorted(grouped, key=lambda item: item[0].provider_record_key)
        claims: list[tuple[Claim, ClaimEvidence]] = []
        representative = grouped_sorted[0][0]
        representative_context = contexts[representative.id]
        _, snapshot, source, policy = representative_context
        claims.append(
            build_alio_classification_claim(
                organization,
                representative,
                source=source,
                snapshot=snapshot,
                policy=policy,
            )
        )
        for observation, fields in grouped_sorted:
            if fields["name_status"] == "PUBLIC":
                named_rows += 1
                _, snapshot, source, policy = contexts[observation.id]
                claims.append(
                    build_alio_executive_claim(
                        organization,
                        observation,
                        source=source,
                        snapshot=snapshot,
                        policy=policy,
                    )
                )
            elif fields["name_status"] == "MASKED_OR_VACANT":
                masked_rows += 1

        items.append(AlioOrganizationImportItem(organization=organization, claims=tuple(claims)))

    organizations_created = sum(
        item.organization.id not in current_organization_ids for item in items
    )

    return PreparedAlioOrganizationImport(
        run_id=run.id,
        observations=observations,
        items=tuple(items),
        named_rows=named_rows,
        masked_rows=masked_rows,
        organizations_created=organizations_created,
        organizations_reused=len(items) - organizations_created,
    )


def _receipt(
    prepared: PreparedAlioOrganizationImport,
    *,
    status: str,
    result=None,
) -> dict[str, object]:
    claims = [claim for item in prepared.items for claim, _ in item.claims]
    return {
        "status": status,
        "source": ALIO_EXECUTIVE_FEEDER,
        "scope": ALIO_EXECUTIVE_SCOPE,
        "run_id": str(prepared.run_id),
        "observed_count": len(prepared.observations),
        "named_rows": prepared.named_rows,
        "masked_or_vacant_rows": prepared.masked_rows,
        "organizations": len(prepared.items),
        "claims": len(claims),
        "claim_ids": [str(claim.id) for claim in claims],
        "organizations_created": (
            result.organizations_created if result else prepared.organizations_created
        ),
        "organizations_reused": (
            result.organizations_reused if result else prepared.organizations_reused
        ),
        "claims_created": result.claims_created if result else 0,
        "claims_reused": result.claims_reused if result else 0,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Import ALIO item-4 observations into canonical Organization Claims."
    )
    parser.add_argument("--database-url")
    parser.add_argument("--commit", action="store_true", help="persist the preflighted operation")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    repository = SqlAlchemyRepository(args.database_url)
    try:
        prepared = prepare_import(repository)
        status = "DRY_RUN"
        result = None
        if args.commit:
            organizations = [item.organization for item in prepared.items]
            claim_items = [
                (item.organization, claim, [evidence])
                for item in prepared.items
                for claim, evidence in item.claims
            ]
            result = repository.import_organization_claim_batch(organizations, claim_items)
            status = "COMMITTED"
        print(json.dumps(_receipt(prepared, status=status, result=result), ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    except (AlioOrganizationContentError, OrganizationClaimImportError, ValueError) as exc:
        parser.error(str(exc))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
