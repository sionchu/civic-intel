from __future__ import annotations

import json
from dataclasses import dataclass

from packages.connectors.civil_service_records import (
    CivilServicePersonnelRecord,
    RetiredOfficialEmploymentReviewRecord,
    parse_employment_review_rows,
    parse_personnel_notice_rows,
)
from packages.verification.identity import IdentityCandidate


@dataclass(frozen=True)
class StagedCivilServiceCareer:
    candidate: IdentityCandidate
    record: CivilServicePersonnelRecord

    def to_dict(self) -> dict[str, object]:
        return {
            "canonical_name": self.candidate.canonical_name,
            "identity_anchors": list(self.candidate.career_anchors),
            "career": {
                "record_id": self.record.record_id,
                "event_date": self.record.event_date.isoformat(),
                "service_category": self.record.category.value,
                "event_type": self.record.event_type.value,
                "appointment_route": self.record.appointment_route.value,
                "organization": self.record.organization,
                "title": self.record.title,
                "grade": self.record.grade,
                "previous_organization": self.record.previous_organization,
                "previous_title": self.record.previous_title,
                "source_ref": self.record.source_ref,
            },
        }


@dataclass(frozen=True)
class StagedEmploymentReview:
    candidate: IdentityCandidate | None
    record: RetiredOfficialEmploymentReviewRecord

    def to_dict(self) -> dict[str, object]:
        return {
            "canonical_name": self.candidate.canonical_name if self.candidate else None,
            "identity_anchors": list(self.candidate.career_anchors) if self.candidate else [],
            "identity_semantics": (
                "PUBLIC_NAME_AVAILABLE" if self.candidate else "PERSON_NAME_NOT_PUBLIC"
            ),
            "employment_review": {
                "record_id": self.record.record_id,
                "review_date": self.record.review_date.isoformat(),
                "former_organization": self.record.former_organization,
                "former_title": self.record.former_title,
                "destination_organization": self.record.destination_organization,
                "destination_title": self.record.destination_title,
                "decision": self.record.decision.value,
                "decision_text": self.record.decision_text,
                "employment_start_date": (
                    self.record.employment_start_date.isoformat()
                    if self.record.employment_start_date
                    else None
                ),
                "source_ref": self.record.source_ref,
                "semantics": (
                    "정부공직자윤리위원회의 공개 취업심사 결정 자체를 기록하며, "
                    "취업가능·취업승인 결정을 위반이나 부당취업으로 해석하지 않는다."
                ),
            },
        }


def personnel_record_to_identity(record: CivilServicePersonnelRecord) -> IdentityCandidate:
    anchors = [
        f"civil_service_record:{record.record_id}",
        f"civil_service_date:{record.event_date.isoformat()}",
        f"civil_service_route:{record.appointment_route.value}",
    ]
    if record.previous_organization:
        anchors.append(f"previous_organization:{record.previous_organization}")
    if record.previous_title:
        anchors.append(f"previous_title:{record.previous_title}")
    return IdentityCandidate(
        canonical_name=record.person_name,
        office=record.title,
        organization=record.organization,
        career_anchors=tuple(anchors),
    )


def employment_review_to_identity(
    record: RetiredOfficialEmploymentReviewRecord,
) -> IdentityCandidate | None:
    if record.person_name is None:
        return None
    anchors = [
        f"employment_review_record:{record.record_id}",
        f"employment_review_date:{record.review_date.isoformat()}",
        f"former_organization:{record.former_organization}",
    ]
    if record.former_title:
        anchors.append(f"former_title:{record.former_title}")
    return IdentityCandidate(
        canonical_name=record.person_name,
        office=record.former_title,
        organization=record.former_organization,
        career_anchors=tuple(anchors),
    )


def stage_personnel_rows(rows: list[dict]) -> list[StagedCivilServiceCareer]:
    return [
        StagedCivilServiceCareer(personnel_record_to_identity(record), record)
        for record in parse_personnel_notice_rows(rows)
    ]


def stage_employment_review_rows(rows: list[dict]) -> list[StagedEmploymentReview]:
    return [
        StagedEmploymentReview(employment_review_to_identity(record), record)
        for record in parse_employment_review_rows(rows)
    ]


def render_civil_service_json(
    careers: list[StagedCivilServiceCareer], reviews: list[StagedEmploymentReview]
) -> str:
    return json.dumps(
        {
            "career_events": [item.to_dict() for item in careers],
            "employment_reviews": [item.to_dict() for item in reviews],
        },
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )
