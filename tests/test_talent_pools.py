from uuid import uuid4

import pytest
from pydantic import ValidationError

from packages.domain.contracts import AppointmentTarget, RoleFitEvidence, TalentPoolEntry
from packages.domain.enums import RoleFitStatus, TalentPoolBucket


def target(*, slug: str, title: str, route: str, hearing_required: bool | None) -> AppointmentTarget:
    return AppointmentTarget(
        slug=slug,
        title=title,
        institution="대한민국 정부",
        appointment_route=route,
        hearing_required=hearing_required,
        role_fit_dimensions=["domain_experience", "organizational_leadership"],
        source_ids=[uuid4()],
    )


def evidenced(dimension: str) -> RoleFitEvidence:
    return RoleFitEvidence(
        dimension=dimension,
        status=RoleFitStatus.EVIDENCED,
        claim_ids=[uuid4()],
        note="공개 근거가 확인됨",
    )


def test_defense_minister_and_chief_of_staff_keep_distinct_appointment_routes() -> None:
    defense = target(
        slug="minister-national-defense",
        title="국방부 장관",
        route="PRESIDENTIAL_APPOINTMENT_CABINET_HEARING",
        hearing_required=True,
    )
    chief = target(
        slug="chief-of-staff",
        title="대통령비서실장",
        route="PRESIDENTIAL_EXECUTIVE_STAFF_APPOINTMENT",
        hearing_required=False,
    )

    assert defense.hearing_required is True
    assert chief.hearing_required is False
    assert defense.appointment_route != chief.appointment_route


def test_role_fit_evidence_fails_closed_without_evidence_or_unknown_note() -> None:
    with pytest.raises(ValidationError, match="requires claim_ids or source_ids"):
        RoleFitEvidence(dimension="defense_security_domain", status=RoleFitStatus.EVIDENCED)

    with pytest.raises(ValidationError, match="requires a note"):
        RoleFitEvidence(dimension="crisis_coordination", status=RoleFitStatus.UNKNOWN)


def test_talent_pool_entry_requires_explainable_evidence() -> None:
    person_id = uuid4()
    target_id = uuid4()

    with pytest.raises(ValidationError, match="at least one evidenced dimension"):
        TalentPoolEntry(
            person_id=person_id,
            appointment_target_id=target_id,
            bucket=TalentPoolBucket.EMERGING,
            inclusion_reason="관련 경력의 확인 범위를 검토 중",
            role_fit=[
                RoleFitEvidence(
                    dimension="domain_experience",
                    status=RoleFitStatus.UNKNOWN,
                    note="근거 부족",
                )
            ],
        )


def test_same_person_can_appear_in_multiple_target_pools() -> None:
    person_id = uuid4()
    defense_target_id = uuid4()
    security_target_id = uuid4()

    defense = TalentPoolEntry(
        person_id=person_id,
        appointment_target_id=defense_target_id,
        bucket=TalentPoolBucket.DOMAIN_SENIOR,
        inclusion_reason="국방·안보 영역의 고위 경력이 공개적으로 확인됨",
        role_fit=[evidenced("defense_security_domain")],
    )
    security = TalentPoolEntry(
        person_id=person_id,
        appointment_target_id=security_target_id,
        bucket=TalentPoolBucket.DIRECT_FEEDER,
        inclusion_reason="국가안보 관련 인접 고위직 경력이 확인됨",
        role_fit=[evidenced("security_strategy")],
    )

    assert defense.person_id == security.person_id
    assert defense.appointment_target_id != security.appointment_target_id


def test_contract_does_not_accept_appointment_probability_or_ideology_score() -> None:
    with pytest.raises(ValidationError):
        TalentPoolEntry(
            person_id=uuid4(),
            appointment_target_id=uuid4(),
            bucket=TalentPoolBucket.TECHNICAL_EXPERT,
            inclusion_reason="전문성이 확인됨",
            role_fit=[evidenced("technical_expertise")],
            candidate_probability=0.8,
        )

    with pytest.raises(ValidationError):
        TalentPoolEntry(
            person_id=uuid4(),
            appointment_target_id=uuid4(),
            bucket=TalentPoolBucket.POLITICAL_EXECUTIVE,
            inclusion_reason="정무 경력이 확인됨",
            role_fit=[evidenced("political_coordination")],
            ideology_score="favorable",
        )


def test_target_requires_unique_dimensions_and_source_backing() -> None:
    with pytest.raises(ValidationError, match="must be unique"):
        AppointmentTarget(
            slug="duplicate-dimensions",
            title="테스트 직위",
            institution="테스트 기관",
            appointment_route="TEST",
            role_fit_dimensions=["leadership", "leadership"],
            source_ids=[uuid4()],
        )

    with pytest.raises(ValidationError):
        AppointmentTarget(
            slug="unsourced-target",
            title="테스트 직위",
            institution="테스트 기관",
            appointment_route="TEST",
            role_fit_dimensions=["leadership"],
            source_ids=[],
        )
