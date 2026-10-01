from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import insert, select
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from packages.application.results import OrganizationBatchResult, OrganizationClaimBatchResult
from packages.domain.contracts import (
    Claim,
    ClaimEvidence,
    FeederObservation,
    Organization,
    Source,
    SourcePolicy,
    SourceSnapshot,
)
from packages.domain.enums import PublicationStatus
from packages.persistence.errors import OrganizationClaimImportError
from packages.persistence.mapping import (
    _claim,
    _evidence,
    _observation,
    _organization,
    _policy,
    _snapshot,
    _source,
    _temporal,
)
from packages.persistence.models import (
    ClaimEvidenceRow,
    ClaimRow,
    FeederObservationRow,
    OrganizationRow,
    SourcePolicyRow,
    SourceRow,
    SourceSnapshotRow,
)
from packages.verification.claims import validate_claim_publication
from packages.verification.policy import PolicyAction, PolicyDenied, require_policy


@dataclass(frozen=True)
class _OrganizationClaimValidationContext:
    sources: dict[UUID, Source]
    policies: dict[UUID, SourcePolicy]
    snapshots: dict[UUID, SourceSnapshot]
    observations: dict[UUID, FeederObservation]
    version_hashes_by_observation_key: dict[tuple[str, str, str], set[str]]


class OrganizationsRepository:
    def __init__(self, session: Session):
        self._session = session

    @staticmethod
    def _claim_import_key(claim: Claim) -> tuple[UUID, str, str, str]:
        source_contract = claim.qualifiers.get("source_contract")
        provider_record_key = claim.qualifiers.get("provider_record_key")
        if claim.organization_id is None or not source_contract or (not provider_record_key):
            raise OrganizationClaimImportError(
                "organization claim import requires source contract and provider record key"
            )
        return (claim.organization_id, claim.predicate, source_contract, provider_record_key)

    @staticmethod
    def _claim_import_semantics(claim: Claim) -> dict:
        return {
            "person_id": claim.person_id,
            "organization_id": claim.organization_id,
            "proposition": claim.proposition,
            "subject": claim.subject,
            "predicate": claim.predicate,
            "object_text": claim.object_text,
            "qualifiers": claim.qualifiers,
            "epistemic_status": claim.epistemic_status,
            "publication_status": claim.publication_status,
            "asserted_as_true": claim.asserted_as_true,
            "resolution_note": claim.resolution_note,
        }

    @staticmethod
    def _organization_claim_id_chunks(
        ids: Iterable[UUID | str], *, chunk_size: int = 500
    ) -> Iterable[tuple[str, ...]]:
        values = tuple(sorted({str(item) for item in ids}))
        for start in range(0, len(values), chunk_size):
            yield values[start : start + chunk_size]

    @staticmethod
    def _load_organization_claim_rows_by_ids(
        session: Session, row_type: Any, ids: Iterable[UUID | str]
    ) -> dict[str, Any]:
        rows: dict[str, Any] = {}
        for chunk in OrganizationsRepository._organization_claim_id_chunks(ids):
            if not chunk:
                continue
            loaded_rows: list[Any] = list(
                session.scalars(select(row_type).where(row_type.id.in_(chunk)))
            )
            for row in loaded_rows:
                rows[str(row.id)] = row
        return rows

    @staticmethod
    def _load_organization_claim_evidence_by_claim(
        session: Session, claim_ids: Iterable[UUID | str]
    ) -> dict[str, list[ClaimEvidenceRow]]:
        evidence_by_claim: dict[str, list[ClaimEvidenceRow]] = {}
        for chunk in OrganizationsRepository._organization_claim_id_chunks(claim_ids):
            if not chunk:
                continue
            rows = session.scalars(
                select(ClaimEvidenceRow).where(ClaimEvidenceRow.claim_id.in_(chunk))
            )
            for row in rows:
                evidence_by_claim.setdefault(row.claim_id, []).append(row)
        return evidence_by_claim

    @staticmethod
    def _load_organization_claim_observation_versions(
        session: Session, observation_rows: Iterable[FeederObservationRow]
    ) -> dict[tuple[str, str, str], set[str]]:
        keys_by_group: dict[tuple[str, str], set[str]] = {}
        for row in observation_rows:
            keys_by_group.setdefault((row.feeder, row.scope_key), set()).add(
                row.provider_record_key
            )
        versions_by_key: dict[tuple[str, str, str], set[str]] = {}
        for (feeder, scope_key), provider_keys in sorted(keys_by_group.items()):
            for chunk in OrganizationsRepository._organization_claim_id_chunks(provider_keys):
                if not chunk:
                    continue
                rows = session.scalars(
                    select(FeederObservationRow).where(
                        FeederObservationRow.feeder == feeder,
                        FeederObservationRow.scope_key == scope_key,
                        FeederObservationRow.provider_record_key.in_(chunk),
                    )
                )
                for row in rows:
                    key = (row.feeder, row.scope_key, row.provider_record_key)
                    versions_by_key.setdefault(key, set()).add(row.content_hash)
        return versions_by_key

    def _load_organization_claim_validation_context(
        self, session: Session, evidence: Sequence[ClaimEvidence]
    ) -> _OrganizationClaimValidationContext:
        source_rows = self._load_organization_claim_rows_by_ids(
            session, SourceRow, (item.source_id for item in evidence)
        )
        sources = {UUID(row_id): _source(row) for row_id, row in source_rows.items()}
        policy_rows = self._load_organization_claim_rows_by_ids(
            session, SourcePolicyRow, (row.policy_id for row in source_rows.values())
        )
        policies = {UUID(row_id): _policy(row) for row_id, row in policy_rows.items()}
        snapshot_rows = self._load_organization_claim_rows_by_ids(
            session,
            SourceSnapshotRow,
            (item.snapshot_id for item in evidence if item.snapshot_id is not None),
        )
        snapshots = {UUID(row_id): _snapshot(row) for row_id, row in snapshot_rows.items()}
        observation_rows = self._load_organization_claim_rows_by_ids(
            session,
            FeederObservationRow,
            (item.feeder_observation_id for item in evidence if item.feeder_observation_id),
        )
        observations = {UUID(row_id): _observation(row) for row_id, row in observation_rows.items()}
        return _OrganizationClaimValidationContext(
            sources=sources,
            policies=policies,
            snapshots=snapshots,
            observations=observations,
            version_hashes_by_observation_key=self._load_organization_claim_observation_versions(
                session, observation_rows.values()
            ),
        )

    def _validate_organization_claim_semantics(
        self,
        organization: Organization,
        claim: Claim,
        evidence: Sequence[ClaimEvidence],
        *,
        stored_organization: Organization,
        context: _OrganizationClaimValidationContext,
    ) -> Organization:
        if claim.person_id is not None or claim.organization_id != organization.id:
            raise OrganizationClaimImportError(
                "organization claim must target exactly the supplied Organization"
            )
        if claim.publication_status != PublicationStatus.PUBLISHED:
            raise OrganizationClaimImportError(
                "organization claim import requires PUBLISHED status"
            )
        if not evidence:
            raise OrganizationClaimImportError("organization claim requires evidence")
        if any(item.claim_id != claim.id for item in evidence):
            raise OrganizationClaimImportError("organization evidence references another claim")
        if len({item.id for item in evidence}) != len(evidence):
            raise OrganizationClaimImportError("organization claim contains duplicate evidence IDs")
        if (
            stored_organization.name != organization.name
            or stored_organization.superseded_at is not None
        ):
            raise OrganizationClaimImportError(
                "organization claim Organization is not the current canonical row"
            )
        for item in evidence:
            source = context.sources.get(item.source_id)
            if source is None:
                raise OrganizationClaimImportError(
                    f"organization claim references missing source: {item.source_id}"
                )
            policy = context.policies.get(source.policy_id)
            if policy is None:
                raise OrganizationClaimImportError(
                    f"organization claim references missing SourcePolicy: {source.policy_id}"
                )
            try:
                require_policy(policy, PolicyAction.STORE_METADATA)
                if item.excerpt:
                    require_policy(policy, PolicyAction.SHOW_EXCERPT)
            except PolicyDenied as exc:
                raise OrganizationClaimImportError(
                    f"SourcePolicy forbids organization claim evidence: {item.id}"
                ) from exc
            if item.snapshot_id is not None:
                snapshot = context.snapshots.get(item.snapshot_id)
                if snapshot is None or snapshot.source_id != source.id:
                    raise OrganizationClaimImportError(
                        f"organization evidence snapshot does not match source: {item.id}"
                    )
            if item.feeder_observation_id is None:
                continue
            if item.snapshot_id is None:
                raise OrganizationClaimImportError(
                    f"organization evidence with observation requires snapshot: {item.id}"
                )
            observation = context.observations.get(item.feeder_observation_id)
            if observation is None:
                raise OrganizationClaimImportError(
                    f"organization claim references missing feeder observation: {item.feeder_observation_id}"
                )
            if observation.snapshot_id != item.snapshot_id:
                raise OrganizationClaimImportError(
                    f"organization evidence snapshot does not match observation: {item.id}"
                )
            version_key = (
                observation.feeder,
                observation.scope_key,
                observation.provider_record_key,
            )
            if len(context.version_hashes_by_observation_key.get(version_key, set())) > 1:
                raise OrganizationClaimImportError(
                    "organization claim cannot publish across multiple immutable observation versions"
                )
        gate = validate_claim_publication(
            claim, stored_organization, list(evidence), context.sources, context.policies
        )
        if not gate.publishable:
            raise OrganizationClaimImportError(
                f"organization claim failed publication gate: {gate.failures}"
            )
        return stored_organization

    def _validate_organization_claim(
        self,
        session: Session,
        organization: Organization,
        claim: Claim,
        evidence: Sequence[ClaimEvidence],
    ) -> Organization:
        organization_row = session.get(OrganizationRow, str(organization.id))
        if organization_row is None:
            raise OrganizationClaimImportError(
                "organization claim requires an existing canonical Organization"
            )
        context = self._load_organization_claim_validation_context(session, evidence)
        return self._validate_organization_claim_semantics(
            organization,
            claim,
            evidence,
            stored_organization=_organization(organization_row),
            context=context,
        )

    @staticmethod
    def _organization_claim_row(claim: Claim) -> ClaimRow:
        return ClaimRow(
            id=str(claim.id),
            person_id=None,
            organization_id=str(claim.organization_id),
            proposition=claim.proposition,
            subject=claim.subject,
            predicate=claim.predicate,
            object_text=claim.object_text,
            qualifiers=claim.qualifiers,
            epistemic_status=claim.epistemic_status.value,
            publication_status=claim.publication_status.value,
            asserted_as_true=claim.asserted_as_true,
            resolution_note=claim.resolution_note,
            **_temporal(claim),
        )

    @staticmethod
    def _organization_claim_evidence_row(item: ClaimEvidence) -> ClaimEvidenceRow:
        return ClaimEvidenceRow(
            id=str(item.id),
            claim_id=str(item.claim_id),
            source_id=str(item.source_id),
            snapshot_id=str(item.snapshot_id) if item.snapshot_id else None,
            feeder_observation_id=str(item.feeder_observation_id)
            if item.feeder_observation_id
            else None,
            stance=item.stance.value,
            excerpt=item.excerpt,
        )

    @staticmethod
    def _add_organization_claim_rows(
        session: Session, claim: Claim, evidence: Sequence[ClaimEvidence], *, flush: bool = True
    ) -> None:
        session.add(OrganizationsRepository._organization_claim_row(claim))
        if flush:
            session.flush()
        for item in evidence:
            session.add(OrganizationsRepository._organization_claim_evidence_row(item))

    def import_organization_claim(
        self, organization: Organization, claim: Claim, evidence: Sequence[ClaimEvidence]
    ) -> Claim:
        """Persist one reviewed organization Claim through the canonical validation seam."""
        session = self._session
        self._validate_organization_claim(session, organization, claim, evidence)
        if session.get(ClaimRow, str(claim.id)) is not None:
            raise OrganizationClaimImportError(
                "organization claim ID already exists; reviewed import does not upsert"
            )
        for item in evidence:
            if session.get(ClaimEvidenceRow, str(item.id)) is not None:
                raise OrganizationClaimImportError(
                    f"organization evidence ID already exists: {item.id}"
                )
        self._add_organization_claim_rows(session, claim, evidence)
        session.flush()
        return claim

    def import_organization_claim_pair(
        self,
        organization: Organization,
        claim_pairs: Sequence[tuple[Claim, Sequence[ClaimEvidence]]],
    ) -> tuple[Claim, Claim]:
        session = self._session
        requested_keys = [self._claim_import_key(claim) for claim, _ in claim_pairs]
        if len(set(requested_keys)) != 2:
            raise OrganizationClaimImportError(
                "organization claim pair requires two distinct source record keys"
            )
        organization_rows = list(
            session.scalars(
                select(ClaimRow).where(
                    ClaimRow.organization_id == str(organization.id),
                    ClaimRow.superseded_at.is_(None),
                )
            )
        )
        existing_by_key: dict[tuple[UUID, str, str, str], list[ClaimRow]] = {}
        for row in organization_rows:
            stored_claim = _claim(row)
            try:
                key = self._claim_import_key(stored_claim)
            except OrganizationClaimImportError:
                continue
            existing_by_key.setdefault(key, []).append(row)
        results: list[Claim] = []
        for (claim, evidence), key in zip(claim_pairs, requested_keys, strict=True):
            self._validate_organization_claim(session, organization, claim, evidence)
            matching = existing_by_key.get(key, [])
            if len(matching) > 1:
                raise OrganizationClaimImportError(
                    "organization claim import found duplicate canonical source record keys"
                )
            if matching:
                stored = _claim(matching[0])
                stored_evidence = [
                    _evidence(row)
                    for row in session.scalars(
                        select(ClaimEvidenceRow).where(ClaimEvidenceRow.claim_id == str(stored.id))
                    )
                ]
                if self._claim_import_semantics(stored) != self._claim_import_semantics(
                    claim
                ) or _evidence_import_semantics(stored_evidence) != _evidence_import_semantics(
                    evidence
                ):
                    raise OrganizationClaimImportError(
                        "organization claim source record key conflicts with stored semantics"
                    )
                results.append(stored)
                continue
            self._add_organization_claim_rows(session, claim, evidence)
            results.append(claim)
        session.flush()
        return (results[0], results[1])

    @staticmethod
    def _add_organization_row(session: Session, organization: Organization) -> None:
        session.add(
            OrganizationRow(
                id=str(organization.id), name=organization.name, **_temporal(organization)
            )
        )

    def import_organization_claim_batch(
        self,
        organizations: Sequence[Organization],
        items: Sequence[tuple[Organization, Claim, Sequence[ClaimEvidence]]],
    ) -> OrganizationClaimBatchResult:
        """Atomically materialize supplied Organizations and import exact Claim/Evidence rows.

        The caller owns source-specific identity decisions. This seam only persists the supplied
        current canonical rows and applies the existing organization publication validation.
        """
        organization_by_id = {organization.id: organization for organization in organizations}
        if len(organization_by_id) != len(organizations):
            raise OrganizationClaimImportError("organization batch contains duplicate ids")
        if any((organization.id not in organization_by_id for organization, _, _ in items)):
            raise OrganizationClaimImportError("organization claim batch has an unknown subject")
        requested_keys = [self._claim_import_key(claim) for _, claim, _ in items]
        if len(set(requested_keys)) != len(requested_keys):
            raise OrganizationClaimImportError(
                "organization claim batch contains duplicate source keys"
            )
        requested_claim_ids = [claim.id for _, claim, _ in items]
        if len(set(requested_claim_ids)) != len(requested_claim_ids):
            raise OrganizationClaimImportError(
                "organization claim batch contains duplicate Claim IDs"
            )
        requested_evidence_ids = [
            evidence_item.id for _, _, evidence_items in items for evidence_item in evidence_items
        ]
        if len(set(requested_evidence_ids)) != len(requested_evidence_ids):
            raise OrganizationClaimImportError(
                "organization claim batch contains duplicate Evidence IDs"
            )
        session = self._session
        try:
            created_organizations = 0
            reused_organizations = 0
            requested_organization_rows = self._load_organization_claim_rows_by_ids(
                session, OrganizationRow, organization_by_id
            )
            missing_organization_names = {
                organization.name
                for organization in organizations
                if str(organization.id) not in requested_organization_rows
            }
            if len(missing_organization_names) != sum(
                1
                for organization in organizations
                if str(organization.id) not in requested_organization_rows
            ):
                raise OrganizationClaimImportError(
                    "organization batch refuses duplicate incoming Organization names"
                )
            same_name_rows = (
                list(
                    session.scalars(
                        select(OrganizationRow).where(
                            OrganizationRow.name.in_(missing_organization_names),
                            OrganizationRow.superseded_at.is_(None),
                        )
                    )
                )
                if missing_organization_names
                else []
            )
            current_names = {row.name for row in same_name_rows}
            stored_organizations: dict[UUID, Organization] = {}
            pending_organization_rows: list[OrganizationRow] = []
            for organization in organizations:
                organization_row = requested_organization_rows.get(str(organization.id))
                if organization_row is None:
                    if organization.name in current_names:
                        raise OrganizationClaimImportError(
                            "organization batch refuses a same-name canonical row without an exact binding"
                        )
                    pending_organization_rows.append(
                        OrganizationRow(
                            id=str(organization.id),
                            name=organization.name,
                            **_temporal(organization),
                        )
                    )
                    stored_organizations[organization.id] = organization
                    created_organizations += 1
                else:
                    stored_organization = _organization(organization_row)
                    if (
                        stored_organization.name != organization.name
                        or stored_organization.superseded_at is not None
                    ):
                        raise OrganizationClaimImportError(
                            "organization batch Organization is not the current canonical row"
                        )
                    stored_organizations[organization.id] = stored_organization
                    reused_organizations += 1
            existing_rows = list(
                session.scalars(
                    select(ClaimRow).where(
                        ClaimRow.organization_id.is_not(None), ClaimRow.superseded_at.is_(None)
                    )
                )
            )
            existing_by_key: dict[tuple[UUID, str, str, str], list[ClaimRow]] = {}
            source_key_owners: dict[tuple[str, str, str], set[UUID]] = {}
            for claim_row in existing_rows:
                stored_claim = _claim(claim_row)
                try:
                    key = self._claim_import_key(stored_claim)
                except OrganizationClaimImportError:
                    continue
                existing_by_key.setdefault(key, []).append(claim_row)
                source_key_owners.setdefault(key[1:], set()).add(key[0])
            matching_claim_ids = [
                row.id for key in requested_keys for row in existing_by_key.get(key, [])
            ]
            evidence_rows_by_claim = self._load_organization_claim_evidence_by_claim(
                session, matching_claim_ids
            )
            requested_claim_rows = self._load_organization_claim_rows_by_ids(
                session, ClaimRow, requested_claim_ids
            )
            requested_evidence_rows = self._load_organization_claim_rows_by_ids(
                session, ClaimEvidenceRow, requested_evidence_ids
            )
            all_evidence = tuple(
                (
                    evidence_item
                    for _, _, evidence_items in items
                    for evidence_item in evidence_items
                )
            )
            validation_context = self._load_organization_claim_validation_context(
                session, all_evidence
            )
            results: list[Claim] = []
            created_claims = 0
            reused_claims = 0
            pending_claim_rows: list[ClaimRow] = []
            pending_evidence_rows: list[ClaimEvidenceRow] = []
            for organization, claim, evidence in items:
                key = self._claim_import_key(claim)
                owners = source_key_owners.get(key[1:], set())
                if owners and owners != {organization.id}:
                    raise OrganizationClaimImportError(
                        "organization claim source record key is bound to another Organization"
                    )
                self._validate_organization_claim_semantics(
                    organization,
                    claim,
                    evidence,
                    stored_organization=stored_organizations[organization.id],
                    context=validation_context,
                )
                matching = existing_by_key.get(key, [])
                if len(matching) > 1:
                    raise OrganizationClaimImportError(
                        "organization claim batch found duplicate canonical source record keys"
                    )
                if matching:
                    stored = _claim(matching[0])
                    requested_claim_row = requested_claim_rows.get(str(claim.id))
                    if requested_claim_row is not None and requested_claim_row.id != str(stored.id):
                        raise OrganizationClaimImportError(
                            "organization claim ID already exists with different semantics"
                        )
                    stored_evidence_rows = evidence_rows_by_claim.get(str(stored.id), [])
                    for item in evidence:
                        requested_evidence_row = requested_evidence_rows.get(str(item.id))
                        if (
                            requested_evidence_row is not None
                            and requested_evidence_row.claim_id != str(stored.id)
                        ):
                            raise OrganizationClaimImportError(
                                f"organization evidence ID already exists: {item.id}"
                            )
                    stored_evidence = [_evidence(row) for row in stored_evidence_rows]
                    if self._claim_import_semantics(stored) != self._claim_import_semantics(
                        claim
                    ) or _evidence_import_semantics(stored_evidence) != _evidence_import_semantics(
                        evidence
                    ):
                        raise OrganizationClaimImportError(
                            "organization claim source record key conflicts with stored semantics"
                        )
                    results.append(stored)
                    reused_claims += 1
                    continue
                if str(claim.id) in requested_claim_rows:
                    raise OrganizationClaimImportError(
                        "organization claim ID already exists with different semantics"
                    )
                for item in evidence:
                    if str(item.id) in requested_evidence_rows:
                        raise OrganizationClaimImportError(
                            f"organization evidence ID already exists: {item.id}"
                        )
                pending_claim_rows.append(self._organization_claim_row(claim))
                pending_evidence_rows.extend(
                    self._organization_claim_evidence_row(item) for item in evidence
                )
                source_key_owners.setdefault(key[1:], set()).add(organization.id)
                results.append(claim)
                created_claims += 1
            if pending_organization_rows:
                session.add_all(pending_organization_rows)
                session.flush()
            if pending_claim_rows:
                session.execute(
                    insert(ClaimRow),
                    [
                        {
                            column.name: getattr(row, column.name)
                            for column in ClaimRow.__table__.columns
                        }
                        for row in pending_claim_rows
                    ],
                )
            if pending_evidence_rows:
                session.execute(
                    insert(ClaimEvidenceRow),
                    [
                        {
                            column.name: getattr(row, column.name)
                            for column in ClaimEvidenceRow.__table__.columns
                        }
                        for row in pending_evidence_rows
                    ],
                )
            session.flush()
            return OrganizationClaimBatchResult(
                claims=tuple(results),
                organizations_created=created_organizations,
                organizations_reused=reused_organizations,
                claims_created=created_claims,
                claims_reused=reused_claims,
            )
        except (IntegrityError, OperationalError) as exc:
            raise OrganizationClaimImportError(
                "organization claim batch database commit failed"
            ) from exc
        except Exception:
            raise

    def import_organization_batch(
        self, organizations: Sequence[Organization]
    ) -> OrganizationBatchResult:
        """Atomically create or reuse an explicit Organization batch without Claims."""
        if not organizations:
            raise OrganizationClaimImportError("organization batch must not be empty")
        result = self.import_organization_claim_batch(organizations, ())
        if result.claims or result.claims_created or result.claims_reused:
            raise OrganizationClaimImportError(
                "organization-only batch unexpectedly produced Claim results"
            )
        return OrganizationBatchResult(
            organizations_created=result.organizations_created,
            organizations_reused=result.organizations_reused,
        )


from packages.verification.import_semantics import _evidence_import_semantics
