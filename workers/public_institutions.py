from __future__ import annotations

import json
from dataclasses import dataclass

from packages.connectors.alio_disclosures import (
    AlioCompensationRecord,
    AlioExecutiveRecord,
    AlioInstitutionRecord,
    AlioReemploymentRecord,
    parse_compensation_rows,
    parse_executive_rows,
    parse_institution_rows,
    parse_reemployment_rows,
)
from packages.verification.identity import IdentityCandidate


@dataclass(frozen=True)
class StagedPublicInstitutionExecutive:
    candidate: IdentityCandidate
    record: AlioExecutiveRecord

    def to_dict(self) -> dict[str, object]:
        return {
            "canonical_name": self.candidate.canonical_name,
            "identity_anchors": list(self.candidate.career_anchors),
            "institution": {
                "code": self.record.institution_code,
                "name": self.record.institution_name,
                "classification": self.record.classification.value,
                "classification_text": self.record.classification_text,
            },
            "executive": {
                "record_id": self.record.record_id,
                "kind": self.record.executive_kind.value,
                "position_text": self.record.position_text,
                "title": self.record.title,
                "term_start": self.record.term_start.isoformat(),
                "term_end": self.record.term_end.isoformat() if self.record.term_end else None,
                "reported_careers": list(self.record.reported_careers),
                "reported_careers_semantics": (
                    "ALIO 임원현황에 주요경력으로 공시된 내용이며, 각 과거 경력을 독립적으로 "
                    "검증한 사실과는 구분한다."
                ),
                "selection_procedure": self.record.selection_procedure,
                "selection_rule": self.record.selection_rule,
                "selection_semantics": (
                    "공시된 공식 선임절차를 보존하며, 별도 근거 없이 정치적 임명 또는 "
                    "정부의 실질 통제로 재해석하지 않는다."
                ),
                "as_of": self.record.as_of.isoformat(),
                "source_ref": self.record.source_ref,
            },
        }


@dataclass(frozen=True)
class StagedPublicInstitutionReemployment:
    candidate: IdentityCandidate | None
    record: AlioReemploymentRecord

    def to_dict(self) -> dict[str, object]:
        return {
            "canonical_name": self.candidate.canonical_name if self.candidate else None,
            "identity_anchors": list(self.candidate.career_anchors) if self.candidate else [],
            "identity_semantics": (
                "PUBLIC_EXECUTIVE_NAME_AVAILABLE"
                if self.candidate
                else "NON_EXECUTIVE_OR_NAME_NOT_STAGED"
            ),
            "reemployment": {
                "record_id": self.record.record_id,
                "institution_code": self.record.institution_code,
                "institution_name": self.record.institution_name,
                "former_kind": self.record.former_kind,
                "former_title": self.record.former_title,
                "retirement_date": self.record.retirement_date.isoformat(),
                "destination_organization": self.record.destination_organization,
                "reemployment_date": self.record.reemployment_date.isoformat(),
                "relationship": self.record.relationship,
                "as_of": self.record.as_of.isoformat(),
                "source_ref": self.record.source_ref,
                "semantics": (
                    "ALIO가 공시한 실제 재취업 현황이다. 정부공직자윤리위원회의 취업심사 "
                    "결정과는 별도 사건이며, 위반·특혜 여부를 자동 판정하지 않는다."
                ),
            },
        }


def executive_to_identity(record: AlioExecutiveRecord) -> IdentityCandidate:
    anchors = [
        f"alio_institution_code:{record.institution_code}",
        f"alio_executive_record:{record.record_id}",
        f"public_institution_classification:{record.classification.value}",
        f"executive_kind:{record.executive_kind.value}",
        f"term_start:{record.term_start.isoformat()}",
    ]
    return IdentityCandidate(
        canonical_name=record.person_name,
        office=record.title,
        organization=record.institution_name,
        career_anchors=tuple(anchors),
    )


def reemployment_to_identity(record: AlioReemploymentRecord) -> IdentityCandidate | None:
    if not record.executive_person_scope or record.person_name is None:
        return None
    return IdentityCandidate(
        canonical_name=record.person_name,
        office=record.former_title,
        organization=record.institution_name,
        career_anchors=(
            f"alio_institution_code:{record.institution_code}",
            f"alio_reemployment_record:{record.record_id}",
            f"retirement_date:{record.retirement_date.isoformat()}",
        ),
    )


def stage_executive_rows(rows: list[dict]) -> list[StagedPublicInstitutionExecutive]:
    return [
        StagedPublicInstitutionExecutive(executive_to_identity(record), record)
        for record in parse_executive_rows(rows)
    ]


def stage_reemployment_rows(rows: list[dict]) -> list[StagedPublicInstitutionReemployment]:
    return [
        StagedPublicInstitutionReemployment(reemployment_to_identity(record), record)
        for record in parse_reemployment_rows(rows)
    ]


def render_public_institution_json(
    institution_rows: list[dict],
    executive_rows: list[dict],
    compensation_rows: list[dict],
    reemployment_rows: list[dict],
) -> str:
    institutions: list[AlioInstitutionRecord] = parse_institution_rows(institution_rows)
    executives = stage_executive_rows(executive_rows)
    compensation: list[AlioCompensationRecord] = parse_compensation_rows(compensation_rows)
    reemployment = stage_reemployment_rows(reemployment_rows)
    return json.dumps(
        {
            "institutions": [
                {
                    "institution_code": item.institution_code,
                    "institution_name": item.institution_name,
                    "classification": item.classification.value,
                    "classification_text": item.classification_text,
                    "as_of": item.as_of.isoformat(),
                    "source_ref": item.source_ref,
                }
                for item in institutions
            ],
            "executives": [item.to_dict() for item in executives],
            "compensation": [
                {
                    "record_id": item.record_id,
                    "institution_code": item.institution_code,
                    "institution_name": item.institution_name,
                    "classification": item.classification.value,
                    "executive_kind": item.executive_kind.value,
                    "fiscal_year": item.fiscal_year,
                    "basis": item.basis,
                    "total_thousand_krw": item.total_thousand_krw,
                    "person_id": None,
                    "person_attribution": "ROLE_CATEGORY_ONLY",
                    "as_of": item.as_of.isoformat(),
                    "source_ref": item.source_ref,
                }
                for item in compensation
            ],
            "reemployment": [item.to_dict() for item in reemployment],
        },
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )
