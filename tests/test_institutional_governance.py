from datetime import UTC, date, datetime, timedelta
from uuid import uuid4

import pytest
from pydantic import ValidationError

from packages.domain.contracts import (
    BoardSeat,
    CommitteeMembershipEpisode,
    GovernanceRelation,
    GovernanceSelectionEvent,
    InstitutionalBody,
    OwnershipStake,
)
from packages.domain.enums import GovernanceRelationType, InstitutionalBodyType


def test_presidential_commission_is_time_bounded_and_source_backed() -> None:
    start = datetime(2025, 1, 1, tzinfo=UTC)
    body = InstitutionalBody(
        organization_id=uuid4(),
        body_type=InstitutionalBodyType.PRESIDENTIAL_COMMISSION,
        legal_basis="공식 설치 근거",
        standing=False,
        valid_from=start,
        valid_to=start + timedelta(days=365),
        source_ids=[uuid4()],
    )
    membership = CommitteeMembershipEpisode(
        person_id=uuid4(),
        institutional_body_id=body.id,
        role="VICE_CHAIR",
        valid_from=start,
        valid_to=start + timedelta(days=180),
        source_ids=[uuid4()],
    )

    assert body.body_type == InstitutionalBodyType.PRESIDENTIAL_COMMISSION
    assert membership.role == "VICE_CHAIR"


def test_committee_membership_requires_public_evidence() -> None:
    with pytest.raises(ValidationError, match="requires claim_ids or source_ids"):
        CommitteeMembershipEpisode(
            person_id=uuid4(),
            institutional_body_id=uuid4(),
            role="MEMBER",
        )


def test_policy_bank_and_state_linked_company_remain_distinct_types() -> None:
    policy_bank = InstitutionalBody(
        organization_id=uuid4(),
        body_type=InstitutionalBodyType.POLICY_BANK,
        source_ids=[uuid4()],
    )
    state_linked = InstitutionalBody(
        organization_id=uuid4(),
        body_type=InstitutionalBodyType.STATE_LINKED_COMPANY,
        source_ids=[uuid4()],
    )

    assert policy_bank.body_type != state_linked.body_type


def test_ownership_chain_supports_direct_and_indirect_public_stakes() -> None:
    public_entity_id = uuid4()
    policy_bank_id = uuid4()
    listed_company_id = uuid4()

    bank_stake = OwnershipStake(
        owner_organization_id=public_entity_id,
        target_organization_id=policy_bank_id,
        percentage=75.0,
        direct=True,
        as_of=date(2026, 8, 30),
        source_ids=[uuid4()],
    )
    company_stake = OwnershipStake(
        owner_organization_id=policy_bank_id,
        target_organization_id=listed_company_id,
        percentage=26.41,
        direct=True,
        as_of=date(2026, 8, 30),
        source_ids=[uuid4()],
    )
    indirect = GovernanceRelation(
        source_organization_id=public_entity_id,
        target_organization_id=listed_company_id,
        relation_type=GovernanceRelationType.INDIRECT_OWNERSHIP,
        as_of=date(2026, 8, 30),
        source_ids=[uuid4()],
    )

    assert bank_stake.percentage == 75.0
    assert company_stake.percentage == 26.41
    assert indirect.relation_type == GovernanceRelationType.INDIRECT_OWNERSHIP


def test_ownership_stake_requires_one_owner_and_a_measure() -> None:
    with pytest.raises(ValidationError, match="exactly one owner"):
        OwnershipStake(
            owner_organization_id=uuid4(),
            owner_person_id=uuid4(),
            target_organization_id=uuid4(),
            percentage=10.0,
            as_of=date(2026, 8, 30),
            source_ids=[uuid4()],
        )

    with pytest.raises(ValidationError, match="percentage or amount"):
        OwnershipStake(
            owner_organization_id=uuid4(),
            target_organization_id=uuid4(),
            as_of=date(2026, 8, 30),
            source_ids=[uuid4()],
        )


def test_board_selection_event_preserves_formal_mechanics() -> None:
    organization_id = uuid4()
    person_id = uuid4()
    event = GovernanceSelectionEvent(
        target_organization_id=organization_id,
        target_person_id=person_id,
        event_date=date(2026, 3, 18),
        selection_steps=["shareholder meeting approval", "board resolution"],
        approving_organization_id=organization_id,
        source_ids=[uuid4()],
    )
    seat = BoardSeat(
        organization_id=organization_id,
        person_id=person_id,
        board_type="BOARD_OF_DIRECTORS",
        role="REPRESENTATIVE_DIRECTOR",
        selection_event_id=event.id,
        source_ids=[uuid4()],
    )

    assert event.selection_steps == ["shareholder meeting approval", "board resolution"]
    assert seat.selection_event_id == event.id


def test_generic_government_control_relation_is_not_allowed() -> None:
    with pytest.raises(ValidationError):
        GovernanceRelation(
            source_organization_id=uuid4(),
            target_organization_id=uuid4(),
            relation_type="GOVERNMENT_CONTROLS",
            source_ids=[uuid4()],
        )


def test_historical_ownership_can_change_without_overwriting_prior_state() -> None:
    owner_id = uuid4()
    target_id = uuid4()
    older = OwnershipStake(
        owner_organization_id=owner_id,
        target_organization_id=target_id,
        percentage=30.0,
        direct=True,
        as_of=date(2025, 12, 31),
        source_ids=[uuid4()],
    )
    newer = OwnershipStake(
        owner_organization_id=owner_id,
        target_organization_id=target_id,
        percentage=26.41,
        direct=True,
        as_of=date(2026, 8, 30),
        source_ids=[uuid4()],
    )

    assert older.as_of < newer.as_of
    assert older.percentage != newer.percentage
