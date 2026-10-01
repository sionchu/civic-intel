from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from packages.domain.contracts import (
    FeederObservation,
    Person,
    PersonObservationLink,
)
from packages.persistence import mapping
from packages.persistence.mapping import _person_observation_link
from packages.persistence.models import FeederObservationRow, PersonObservationLinkRow, PersonRow


class IdentityRepository:
    def __init__(self, session: Session):
        self._session = session

    def person_observation_links(
        self, person_id: UUID | None = None
    ) -> list[PersonObservationLink]:
        statement = select(PersonObservationLinkRow)
        if person_id is not None:
            statement = statement.where(PersonObservationLinkRow.person_id == str(person_id))
        session = self._session
        rows = session.scalars(statement.order_by(PersonObservationLinkRow.linked_at))
        return [_person_observation_link(row) for row in rows]

    def active_person_ids_by_observation(
        self, observation_ids: Sequence[UUID]
    ) -> dict[UUID, frozenset[UUID]]:
        if not observation_ids:
            return {}
        requested = [str(item) for item in observation_ids]
        statement = select(
            PersonObservationLinkRow.observation_id, PersonObservationLinkRow.person_id
        ).where(
            PersonObservationLinkRow.observation_id.in_(requested),
            PersonObservationLinkRow.superseded_at.is_(None),
        )
        grouped: dict[UUID, set[UUID]] = {}
        session = self._session
        for observation_id, person_id in session.execute(statement):
            grouped.setdefault(UUID(observation_id), set()).add(UUID(person_id))
        return {key: frozenset(value) for key, value in grouped.items()}

    def matching_people(
        self, observation: FeederObservation
    ) -> tuple[tuple[Person, ...], tuple[Person, ...]]:
        linked = self._session.scalars(
            select(PersonRow)
            .join(PersonObservationLinkRow, PersonObservationLinkRow.person_id == PersonRow.id)
            .join(
                FeederObservationRow,
                FeederObservationRow.id == PersonObservationLinkRow.observation_id,
            )
            .where(
                FeederObservationRow.feeder == observation.feeder,
                FeederObservationRow.scope_key == observation.scope_key,
                FeederObservationRow.provider_record_key == observation.provider_record_key,
                PersonObservationLinkRow.superseded_at.is_(None),
            )
        )
        same_name = self._session.scalars(
            select(PersonRow).where(
                PersonRow.canonical_name == observation.normalized.get("canonical_name"),
                PersonRow.superseded_at.is_(None),
            )
        )
        return (
            tuple(mapping._person(row) for row in linked),
            tuple(mapping._person(row) for row in same_name),
        )

    def add_person(self, person: Person) -> None:
        self._session.add(
            PersonRow(
                id=str(person.id),
                canonical_name=person.canonical_name,
                birth_date=person.birth_date,
                identity_status=person.identity_status.value,
                **mapping._temporal(person),
            )
        )

    def link_observation(self, link: PersonObservationLink) -> None:
        existing = self._session.scalar(
            select(PersonObservationLinkRow).where(
                PersonObservationLinkRow.person_id == str(link.person_id),
                PersonObservationLinkRow.observation_id == str(link.observation_id),
                PersonObservationLinkRow.superseded_at.is_(None),
            )
        )
        if existing is None:
            self._session.add(
                PersonObservationLinkRow(
                    id=str(link.id),
                    person_id=str(link.person_id),
                    observation_id=str(link.observation_id),
                    action=link.action.value,
                    decision_class=link.decision_class.value,
                    linked_at=link.linked_at,
                    superseded_at=None,
                    review_item_id=None,
                )
            )
