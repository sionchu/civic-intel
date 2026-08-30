from __future__ import annotations

import json
from dataclasses import dataclass

from packages.connectors.legal_personnel_records import (
    LegalPersonnelRecord,
    parse_moj_prosecution_rows,
    parse_supreme_court_rows,
)
from packages.verification.identity import IdentityCandidate


@dataclass(frozen=True)
class StagedLegalCareer:
    candidate: IdentityCandidate
    record: LegalPersonnelRecord

    def to_dict(self) -> dict[str, object]:
        return {
            "canonical_name": self.candidate.canonical_name,
            "identity_anchors": list(self.candidate.career_anchors),
            "legal_career": {
                "record_id": self.record.record_id,
                "event_date": self.record.event_date.isoformat(),
                "career_type": self.record.career_type.value,
                "event_type": self.record.event_type.value,
                "organization": self.record.organization,
                "title": self.record.title,
                "previous_organization": self.record.previous_organization,
                "previous_title": self.record.previous_title,
                "public_assignment_domain": self.record.public_assignment_domain,
                "order_text": self.record.order_text,
                "source_lane": self.record.source_lane,
                "source_ref": self.record.source_ref,
                "semantics": (
                    "공식 인사자료가 증명하는 날짜·소속·보직·인사명령을 기록한다. "
                    "소속기관의 사건 전체에 대한 개인 책임, 정치성향 또는 사건 판단 성향을 "
                    "이 기록만으로 추론하지 않는다."
                ),
            },
        }


def legal_record_to_identity(record: LegalPersonnelRecord) -> IdentityCandidate:
    anchors = [
        f"legal_personnel_record:{record.record_id}",
        f"legal_personnel_date:{record.event_date.isoformat()}",
        f"legal_career_type:{record.career_type.value}",
        f"legal_source_lane:{record.source_lane}",
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


def stage_prosecution_rows(rows: list[dict]) -> list[StagedLegalCareer]:
    return [
        StagedLegalCareer(legal_record_to_identity(record), record)
        for record in parse_moj_prosecution_rows(rows)
    ]


def stage_judicial_rows(rows: list[dict]) -> list[StagedLegalCareer]:
    return [
        StagedLegalCareer(legal_record_to_identity(record), record)
        for record in parse_supreme_court_rows(rows)
    ]


def render_legal_career_json(prosecution_rows: list[dict], judicial_rows: list[dict]) -> str:
    return json.dumps(
        {
            "prosecution": [item.to_dict() for item in stage_prosecution_rows(prosecution_rows)],
            "judiciary": [item.to_dict() for item in stage_judicial_rows(judicial_rows)],
        },
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )
