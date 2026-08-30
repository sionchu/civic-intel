from __future__ import annotations

import json
from dataclasses import dataclass

from packages.connectors.labor_union_records import LaborOrganizationRecord, parse_labor_union_rows
from packages.verification.identity import IdentityCandidate


@dataclass(frozen=True)
class StagedLaborOrganization:
    record: LaborOrganizationRecord
    leadership_candidate: IdentityCandidate | None

    def to_dict(self) -> dict[str, object]:
        return {
            "organization": {
                "record_id": self.record.record_id,
                "union_name": self.record.union_name,
                "union_form": self.record.union_form,
                "established_date": (
                    self.record.established_date.isoformat() if self.record.established_date else None
                ),
                "affiliated_federation": self.record.affiliated_federation,
                "membership_count": self.record.membership_count,
                "membership_count_semantics": "ORGANIZATION_LEVEL_ONLY",
                "workplace_name": self.record.workplace_name,
                "as_of": self.record.as_of.isoformat(),
                "source_ref": self.record.source_ref,
            },
            "leadership_candidate": (
                {
                    "canonical_name": self.leadership_candidate.canonical_name,
                    "office": self.leadership_candidate.office,
                    "organization": self.leadership_candidate.organization,
                    "identity_anchors": list(self.leadership_candidate.career_anchors),
                    "semantics": (
                        "공식 표준데이터가 공개한 노동조합 대표자 역할의 사람 후보이다. "
                        "일반 조합원 여부, 정치성향, 정당·계파 관계를 추론하지 않는다."
                    ),
                }
                if self.leadership_candidate
                else None
            ),
        }


def representative_to_identity(record: LaborOrganizationRecord) -> IdentityCandidate | None:
    if record.representative_name is None:
        return None
    return IdentityCandidate(
        canonical_name=record.representative_name,
        office="대표자(전국노동조합표준데이터)",
        organization=record.union_name,
        career_anchors=(
            f"labor_union_record:{record.record_id}",
            f"labor_union_name:{record.union_name}",
            f"labor_union_as_of:{record.as_of.isoformat()}",
        ),
    )


def stage_labor_union_rows(rows: list[dict]) -> list[StagedLaborOrganization]:
    return [
        StagedLaborOrganization(record, representative_to_identity(record))
        for record in parse_labor_union_rows(rows)
    ]


def render_labor_union_json(rows: list[dict]) -> str:
    return json.dumps(
        [item.to_dict() for item in stage_labor_union_rows(rows)],
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )
