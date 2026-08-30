from __future__ import annotations

import json
from dataclasses import dataclass

from packages.connectors.presidential_personnel_records import (
    PresidentialPersonnelRecord,
    parse_presidential_personnel_rows,
)
from packages.verification.identity import IdentityCandidate


@dataclass(frozen=True)
class StagedPresidentialPersonnel:
    record: PresidentialPersonnelRecord
    candidate: IdentityCandidate | None

    def to_dict(self) -> dict[str, object]:
        return {
            "canonical_name": self.candidate.canonical_name if self.candidate else None,
            "identity_anchors": list(self.candidate.career_anchors) if self.candidate else [],
            "identity_semantics": (
                "PUBLIC_PERSONNEL_NAME_AVAILABLE"
                if self.candidate
                else "PERSON_NAME_NOT_PUBLIC_OR_USABLE"
            ),
            "personnel_action": {
                "record_id": self.record.record_id,
                "event_date": self.record.event_date.isoformat(),
                "action": self.record.action.value,
                "action_text": self.record.action_text,
                "role_scope": self.record.role_scope.value,
                "organization": self.record.organization,
                "role": self.record.role,
                "institutional_body_type": (
                    self.record.institutional_body_type.value
                    if self.record.institutional_body_type
                    else None
                ),
                "reported_prior_careers": list(self.record.reported_prior_careers),
                "reported_prior_careers_semantics": (
                    "대통령실 공식 인선 자료가 해당 인물의 경력으로 소개한 내용이다. "
                    "중요한 과거 CareerEpisode는 원 출처로 독립 검증해야 한다."
                ),
                "action_semantics": (
                    "공식 발표의 임명·지명·내정·위촉 상태를 그대로 보존하며 서로 대체하지 않는다."
                ),
                "source_ref": self.record.source_ref,
            },
        }


def personnel_record_to_identity(
    record: PresidentialPersonnelRecord,
) -> IdentityCandidate | None:
    if record.person_name is None:
        return None
    return IdentityCandidate(
        canonical_name=record.person_name,
        office=record.role,
        organization=record.organization,
        career_anchors=(
            f"presidential_personnel_record:{record.record_id}",
            f"presidential_personnel_date:{record.event_date.isoformat()}",
            f"presidential_personnel_action:{record.action.value}",
            f"presidential_role_scope:{record.role_scope.value}",
        ),
    )


def stage_presidential_personnel_rows(rows: list[dict]) -> list[StagedPresidentialPersonnel]:
    return [
        StagedPresidentialPersonnel(record, personnel_record_to_identity(record))
        for record in parse_presidential_personnel_rows(rows)
    ]


def render_presidential_personnel_json(rows: list[dict]) -> str:
    return json.dumps(
        [item.to_dict() for item in stage_presidential_personnel_rows(rows)],
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )
