from __future__ import annotations

from collections.abc import Iterable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from packages.domain.admin import PERSON_ROLE_PREDICATE
from packages.domain.contracts import (
    Claim,
    ClaimEvidence,
    Organization,
    Person,
    Source,
    SourcePolicy,
    SourceSnapshot,
)
from packages.domain.enums import IdentityStatus, MaterializationDecisionClass, PublicationStatus
from packages.persistence.mapping import (
    _claim,
    _evidence,
    _organization,
    _person,
    _policy,
    _snapshot,
    _source,
)
from packages.persistence.models import (
    ClaimEvidenceRow,
    ClaimRow,
    DecisionEpisodeRow,
    FeederObservationRow,
    OrganizationRow,
    PersonObservationLinkRow,
    PersonRow,
    RelationshipRow,
    SourcePolicyRow,
    SourceRow,
    SourceSnapshotRow,
)
from packages.verification.claims import validate_claim_publication
from packages.verification.nec_person_materialization import NEC_CANDIDACY_PREDICATE


class PublicRepository:
    def __init__(self, session: Session):
        self._session = session

    def reviewed_person_role_contexts(
        self, *, person_id: UUID | None = None, organization_id: UUID | None = None
    ) -> list[tuple]:
        from packages.domain.admin import PERSON_ROLE_PREDICATE
        from packages.persistence.models import OrganizationRow

        conditions = [
            ClaimRow.predicate == PERSON_ROLE_PREDICATE,
            ClaimRow.publication_status == "PUBLISHED",
            ClaimRow.superseded_at.is_(None),
            PersonRow.superseded_at.is_(None),
            PersonRow.identity_status == "RESOLVED",
            OrganizationRow.superseded_at.is_(None),
            PersonObservationLinkRow.superseded_at.is_(None),
            FeederObservationRow.content_hash
            == ClaimRow.qualifiers["immutable_observation_hash"].as_string(),
            ClaimRow.qualifiers["source_contract"].as_string() == "alio_reviewed_person_role",
        ]
        if person_id:
            conditions.append(PersonRow.id == str(person_id))
        if organization_id:
            conditions.append(OrganizationRow.id == str(organization_id))
        session = self._session
        rows = session.execute(
            select(ClaimRow, PersonRow, OrganizationRow)
            .join(PersonRow, ClaimRow.person_id == PersonRow.id)
            .join(
                OrganizationRow,
                ClaimRow.qualifiers["organization_id"].as_string() == OrganizationRow.id,
            )
            .join(
                FeederObservationRow,
                ClaimRow.qualifiers["source_observation_id"].as_string() == FeederObservationRow.id,
            )
            .join(
                PersonObservationLinkRow,
                (PersonObservationLinkRow.person_id == PersonRow.id)
                & (PersonObservationLinkRow.observation_id == FeederObservationRow.id),
            )
            .where(*conditions)
            .order_by(ClaimRow.id)
            .limit(200)
        ).all()
        claim_ids = [row[0].id for row in rows]
        evidence = session.scalars(
            select(ClaimEvidenceRow).where(ClaimEvidenceRow.claim_id.in_(claim_ids))
        ).all()
        by_claim: dict[str, list[ClaimEvidence]] = {}
        for item in evidence:
            by_claim.setdefault(item.claim_id, []).append(_evidence(item))
        return [
            (
                _claim(claim),
                _person(person),
                _organization(organization),
                tuple(by_claim.get(claim.id, [])),
            )
            for claim, person, organization in rows
        ]

    def people(self) -> list[Person]:
        session = self._session
        return [_person(row) for row in session.scalars(select(PersonRow).order_by(PersonRow.id))]

    @staticmethod
    def _public_person_conditions():
        deterministic_link = (
            select(PersonObservationLinkRow.id)
            .where(
                PersonObservationLinkRow.person_id == PersonRow.id,
                PersonObservationLinkRow.superseded_at.is_(None),
                PersonObservationLinkRow.decision_class
                == MaterializationDecisionClass.DETERMINISTIC_SOURCE_CONTEXT.value,
            )
            .exists()
        )
        published_claim = (
            select(ClaimRow.id)
            .where(
                ClaimRow.person_id == PersonRow.id,
                (ClaimRow.predicate == PERSON_ROLE_PREDICATE)
                & (
                    ClaimRow.qualifiers["identity_scope"].as_string()
                    == "DETERMINISTIC_ALIO_SOURCE_CONTEXT"
                )
                | (ClaimRow.predicate == NEC_CANDIDACY_PREDICATE)
                & (
                    ClaimRow.qualifiers["identity_scope"].as_string()
                    == "DETERMINISTIC_NEC_CANDIDACY_SOURCE_CONTEXT"
                ),
                ClaimRow.superseded_at.is_(None),
                ClaimRow.publication_status == PublicationStatus.PUBLISHED.value,
            )
            .exists()
        )
        return (
            PersonRow.identity_status == IdentityStatus.RESOLVED.value,
            PersonRow.superseded_at.is_(None),
            ~deterministic_link | published_claim,
        )

    def public_people(self) -> list[Person]:
        """Return current resolved People eligible for the public Person surface."""
        statement = (
            select(PersonRow).where(*self._public_person_conditions()).order_by(PersonRow.id)
        )
        session = self._session
        return [_person(row) for row in session.scalars(statement)]

    def person_is_public(self, person_id: UUID) -> bool:
        statement = (
            select(PersonRow.id)
            .where(PersonRow.id == str(person_id), *self._public_person_conditions())
            .limit(1)
        )
        session = self._session
        return session.scalar(statement) is not None

    def organizations(self, *, current_only: bool = False) -> list[Organization]:
        statement = select(OrganizationRow)
        if current_only:
            statement = statement.where(OrganizationRow.superseded_at.is_(None))
        session = self._session
        return [
            _organization(row) for row in session.scalars(statement.order_by(OrganizationRow.id))
        ]

    def public_organizations(self) -> list[Organization]:
        """Return current Organizations with at least one current published Claim."""
        statement = (
            select(OrganizationRow)
            .join(ClaimRow, ClaimRow.organization_id == OrganizationRow.id)
            .where(
                OrganizationRow.superseded_at.is_(None),
                ClaimRow.publication_status == PublicationStatus.PUBLISHED.value,
                ClaimRow.superseded_at.is_(None),
            )
            .distinct()
            .order_by(OrganizationRow.id)
        )
        session = self._session
        return [_organization(row) for row in session.scalars(statement)]

    def published_person_claim_contexts(
        self, person_ids: Iterable[UUID]
    ) -> dict[UUID, tuple[tuple[Claim, ...], dict[UUID, tuple[ClaimEvidence, ...]]]]:
        """Load current published Person Claim/Evidence context in two bounded reads."""
        requested_ids = tuple(sorted({str(person_id) for person_id in person_ids}))
        if not requested_ids:
            return {}
        session = self._session
        claim_rows = list(
            session.scalars(
                select(ClaimRow)
                .where(
                    ClaimRow.person_id.in_(requested_ids),
                    ClaimRow.publication_status == PublicationStatus.PUBLISHED.value,
                    ClaimRow.superseded_at.is_(None),
                )
                .order_by(ClaimRow.person_id, ClaimRow.id)
            )
        )
        claims_by_person: dict[UUID, list[Claim]] = {
            UUID(person_id): [] for person_id in requested_ids
        }
        claims_by_id: dict[UUID, Claim] = {}
        for row in claim_rows:
            claim = _claim(row)
            assert claim.person_id is not None
            claims_by_person[claim.person_id].append(claim)
            claims_by_id[claim.id] = claim
        evidence_by_claim: dict[UUID, list[ClaimEvidence]] = {
            claim_id: [] for claim_id in claims_by_id
        }
        if claims_by_id:
            evidence_rows = session.scalars(
                select(ClaimEvidenceRow)
                .where(ClaimEvidenceRow.claim_id.in_([str(item) for item in claims_by_id]))
                .order_by(ClaimEvidenceRow.claim_id, ClaimEvidenceRow.id)
            )
            for evidence_row in evidence_rows:
                claim_id = UUID(evidence_row.claim_id)
                if claim_id in evidence_by_claim:
                    evidence_by_claim[claim_id].append(_evidence(evidence_row))
        return {
            person_id: (
                tuple(claims_by_person[person_id]),
                {
                    claim_id: tuple(items)
                    for claim_id, items in evidence_by_claim.items()
                    if claim_id in {claim.id for claim in claims_by_person[person_id]}
                },
            )
            for person_id in (UUID(item) for item in requested_ids)
        }

    def published_organization_claim_contexts(
        self, organization_ids: Iterable[UUID]
    ) -> dict[UUID, tuple[tuple[Claim, ...], dict[UUID, tuple[ClaimEvidence, ...]]]]:
        """Load current published Organization Claim/Evidence context in two bounded reads."""
        requested_ids = tuple(
            sorted({str(organization_id) for organization_id in organization_ids})
        )
        if not requested_ids:
            return {}
        session = self._session
        claim_rows = list(
            session.scalars(
                select(ClaimRow)
                .where(
                    ClaimRow.organization_id.in_(requested_ids),
                    ClaimRow.publication_status == PublicationStatus.PUBLISHED.value,
                    ClaimRow.superseded_at.is_(None),
                )
                .order_by(ClaimRow.organization_id, ClaimRow.id)
            )
        )
        claims_by_organization: dict[UUID, list[Claim]] = {
            UUID(organization_id): [] for organization_id in requested_ids
        }
        claims_by_id: dict[UUID, Claim] = {}
        for row in claim_rows:
            claim = _claim(row)
            assert claim.organization_id is not None
            claims_by_organization[claim.organization_id].append(claim)
            claims_by_id[claim.id] = claim
        evidence_by_claim: dict[UUID, list[ClaimEvidence]] = {
            claim_id: [] for claim_id in claims_by_id
        }
        if claims_by_id:
            evidence_rows = session.scalars(
                select(ClaimEvidenceRow)
                .where(ClaimEvidenceRow.claim_id.in_([str(item) for item in claims_by_id]))
                .order_by(ClaimEvidenceRow.claim_id, ClaimEvidenceRow.id)
            )
            for evidence_row in evidence_rows:
                claim_id = UUID(evidence_row.claim_id)
                if claim_id in evidence_by_claim:
                    evidence_by_claim[claim_id].append(_evidence(evidence_row))
        return {
            organization_id: (
                tuple(claims_by_organization[organization_id]),
                {
                    claim_id: tuple(items)
                    for claim_id, items in evidence_by_claim.items()
                    if claim_id in {claim.id for claim in claims_by_organization[organization_id]}
                },
            )
            for organization_id in (UUID(item) for item in requested_ids)
        }

    def person(self, person_id: UUID) -> Person | None:
        session = self._session
        row = session.get(PersonRow, str(person_id))
        return _person(row) if row else None

    def organization(self, organization_id: UUID) -> Organization | None:
        session = self._session
        row = session.get(OrganizationRow, str(organization_id))
        return _organization(row) if row else None

    def claims(
        self,
        person_id: UUID | None = None,
        published_only: bool = False,
        current_only: bool = False,
        *,
        organization_id: UUID | None = None,
    ) -> list[Claim]:
        if person_id is not None and organization_id is not None:
            raise ValueError("claims query accepts one subject filter")
        statement = select(ClaimRow)
        if person_id is not None:
            statement = statement.where(ClaimRow.person_id == str(person_id))
        if organization_id is not None:
            statement = statement.where(ClaimRow.organization_id == str(organization_id))
        if published_only:
            statement = statement.where(ClaimRow.publication_status == "PUBLISHED")
        if current_only:
            statement = statement.where(ClaimRow.superseded_at.is_(None))
        session = self._session
        return [_claim(row) for row in session.scalars(statement.order_by(ClaimRow.id))]

    def evidence_for(self, claim_id: UUID) -> list[ClaimEvidence]:
        session = self._session
        rows = session.scalars(
            select(ClaimEvidenceRow).where(ClaimEvidenceRow.claim_id == str(claim_id))
        )
        return [_evidence(row) for row in rows]

    def sources(self, source_ids: Iterable[UUID] | None = None) -> dict[UUID, Source]:
        statement = select(SourceRow)
        if source_ids is not None:
            statement = statement.where(SourceRow.id.in_([str(item) for item in source_ids]))
        session = self._session
        items = [_source(row) for row in session.scalars(statement)]
        return {item.id: item for item in items}

    def source(self, source_id: UUID) -> Source | None:
        return self.sources([source_id]).get(source_id)

    def public_source(self, source_id: UUID) -> Source | None:
        """Return a Source only through a currently publishable public Claim/Evidence path."""
        session = self._session
        source_row = session.get(SourceRow, str(source_id))
        if source_row is None:
            return None
        evidence_rows = list(
            session.scalars(
                select(ClaimEvidenceRow).where(ClaimEvidenceRow.source_id == str(source_id))
            )
        )
        for claim_id in {row.claim_id for row in evidence_rows}:
            claim_row = session.get(ClaimRow, claim_id)
            if (
                claim_row is None
                or claim_row.publication_status != PublicationStatus.PUBLISHED.value
                or claim_row.superseded_at is not None
            ):
                continue
            claim = _claim(claim_row)
            subject: Person | Organization
            if claim.person_id is not None:
                person_row = session.get(PersonRow, str(claim.person_id))
                if (
                    person_row is None
                    or person_row.identity_status != IdentityStatus.RESOLVED.value
                    or person_row.superseded_at is not None
                ):
                    continue
                subject = _person(person_row)
            elif claim.organization_id is not None:
                organization_row = session.get(OrganizationRow, str(claim.organization_id))
                if organization_row is None or organization_row.superseded_at is not None:
                    continue
                subject = _organization(organization_row)
            else:
                continue
            claim_evidence = [
                _evidence(row)
                for row in session.scalars(
                    select(ClaimEvidenceRow).where(ClaimEvidenceRow.claim_id == claim_id)
                )
            ]
            source_items = [
                _source(row)
                for row in session.scalars(
                    select(SourceRow).where(
                        SourceRow.id.in_([str(item.source_id) for item in claim_evidence])
                    )
                )
            ]
            sources = {item.id: item for item in source_items}
            policy_items = [
                _policy(row)
                for row in session.scalars(
                    select(SourcePolicyRow).where(
                        SourcePolicyRow.id.in_([str(item.policy_id) for item in sources.values()])
                    )
                )
            ]
            policies = {item.id: item for item in policy_items}
            if validate_claim_publication(
                claim, subject, claim_evidence, sources, policies
            ).publishable:
                return _source(source_row)
        return None

    def source_snapshot(self, snapshot_id: UUID) -> SourceSnapshot | None:
        session = self._session
        row = session.get(SourceSnapshotRow, str(snapshot_id))
        return _snapshot(row) if row else None

    def policies(self, policy_ids: Iterable[UUID] | None = None) -> dict[UUID, SourcePolicy]:
        statement = select(SourcePolicyRow)
        if policy_ids is not None:
            statement = statement.where(SourcePolicyRow.id.in_([str(item) for item in policy_ids]))
        session = self._session
        items = [_policy(row) for row in session.scalars(statement)]
        return {item.id: item for item in items}

    def relationships(self, person_id: UUID) -> list[dict]:
        session = self._session
        rows = session.scalars(
            select(RelationshipRow)
            .where(RelationshipRow.superseded_at.is_(None))
            .order_by(RelationshipRow.id)
        )
        return [row.payload for row in rows if row.payload["person_id"] == str(person_id)]

    def decision_episodes(self, person_id: UUID) -> list[dict]:
        session = self._session
        rows = session.scalars(
            select(DecisionEpisodeRow)
            .where(DecisionEpisodeRow.superseded_at.is_(None))
            .order_by(DecisionEpisodeRow.id)
        )
        return [row.payload for row in rows if row.payload["person_id"] == str(person_id)]

    def claim(self, claim_id: UUID) -> Claim | None:
        row = self._session.get(ClaimRow, str(claim_id))
        return _claim(row) if row is not None else None
