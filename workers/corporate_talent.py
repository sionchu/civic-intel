from __future__ import annotations

import argparse
import json
from dataclasses import dataclass

from packages.connectors.company_official_profiles import (
    CompanyOfficialSeniorProfileRecord,
    parse_company_official_profile_rows,
)
from packages.connectors.open_dart_corporate import (
    DartApiError,
    DartCompensationRecord,
    DartCorporateDataset,
    DartExecutiveRecord,
    DartOwnershipRecord,
    MissingDartApiKey,
    OpenDartCorporateConnector,
    open_dart_corporate_policy,
)
from packages.domain.contracts import SourcePolicy
from packages.verification.identity import IdentityCandidate
from packages.verification.policy import PolicyAction, PolicyDenied, require_policy


@dataclass(frozen=True)
class StagedDartExecutive:
    candidate: IdentityCandidate
    record: DartExecutiveRecord

    def to_dict(self) -> dict[str, object]:
        return {
            "source_lane": "OPENDART_EXECUTIVE_STATUS",
            "canonical_name": self.candidate.canonical_name,
            "identity_anchors": list(self.candidate.career_anchors),
            "company": {"corp_code": self.record.corp_code, "name": self.record.corp_name},
            "executive": {
                "receipt_no": self.record.receipt_no,
                "birth_year_month": self.record.birth_year_month,
                "position": self.record.position,
                "registered_status": self.record.registered_status,
                "full_time_status": self.record.full_time_status,
                "responsibility": self.record.responsibility,
                "reported_main_career": self.record.reported_main_career,
                "reported_main_career_semantics": (
                    "DART 정기보고서 임원현황에 주요경력으로 공시된 내용이며, 과거 경력을 "
                    "각 원출처에서 독립적으로 검증한 것과는 구분한다."
                ),
                "largest_shareholder_relation": self.record.largest_shareholder_relation,
                "tenure_text": self.record.tenure_text,
                "tenure_end_on": (
                    self.record.tenure_end_on.isoformat() if self.record.tenure_end_on else None
                ),
                "settlement_date": self.record.settlement_date.isoformat(),
            },
            "provenance_semantics": (
                "OpenDART는 제출된 공시서류의 일부 정보를 추출해 제공하므로 접수번호를 "
                "원 공시 추적키로 보존한다."
            ),
        }


@dataclass(frozen=True)
class StagedDartOwnership:
    candidate: IdentityCandidate | None
    record: DartOwnershipRecord

    def to_dict(self) -> dict[str, object]:
        return {
            "source_lane": "OPENDART_OFFICER_MAJOR_HOLDER_OWNERSHIP",
            "canonical_name": self.candidate.canonical_name if self.candidate else None,
            "identity_anchors": list(self.candidate.career_anchors) if self.candidate else [],
            "identity_semantics": (
                "PUBLIC_OFFICER_OR_MAJOR_HOLDER"
                if self.candidate
                else "NO_PUBLIC_SENIOR_ROLE_IN_ROW"
            ),
            "ownership_disclosure": {
                "receipt_no": self.record.receipt_no,
                "receipt_date": self.record.receipt_date.isoformat(),
                "corp_code": self.record.corp_code,
                "corp_name": self.record.corp_name,
                "executive_registered_status": self.record.executive_registered_status,
                "executive_position": self.record.executive_position,
                "major_shareholder_relation": self.record.major_shareholder_relation,
                "security_count": self.record.security_count,
                "security_change_count": self.record.security_change_count,
                "security_rate": self.record.security_rate,
                "security_change_rate": self.record.security_change_rate,
                "semantics": (
                    "공시된 특정증권 소유상황이며 현재 순자산, 회사 지배력 전체 또는 "
                    "정책 이해충돌을 자동 의미하지 않는다."
                ),
            },
        }


@dataclass(frozen=True)
class StagedCompanyOfficialSeniorProfile:
    candidate: IdentityCandidate
    record: CompanyOfficialSeniorProfileRecord

    def to_dict(self) -> dict[str, object]:
        return {
            "source_lane": "COMPANY_OFFICIAL_PROFILE",
            "canonical_name": self.candidate.canonical_name,
            "identity_anchors": list(self.candidate.career_anchors),
            "company_profile": {
                "record_id": self.record.record_id,
                "company_name": self.record.company_name,
                "title": self.record.title,
                "public_scope": self.record.public_scope,
                "responsibility": self.record.responsibility,
                "valid_from": self.record.valid_from.isoformat() if self.record.valid_from else None,
                "valid_to": self.record.valid_to.isoformat() if self.record.valid_to else None,
                "source_url": self.record.source_url,
                "source_ref": self.record.source_ref,
                "source_policy_ref": self.record.source_policy_ref,
                "semantics": (
                    "회사가 공식적으로 공개한 고위 역할·책임을 기록한다. DART 등기임원 여부와 "
                    "별도 근거이며, 회사 전체 성과를 개인의 인과적 성과로 자동 귀속하지 않는다."
                ),
            },
        }


def dart_executive_to_identity(record: DartExecutiveRecord) -> IdentityCandidate:
    anchors = [
        f"dart_corp_code:{record.corp_code}",
        f"dart_receipt_no:{record.receipt_no}",
        f"dart_settlement_date:{record.settlement_date.isoformat()}",
    ]
    if record.birth_year_month:
        anchors.append(f"dart_birth_ym:{record.birth_year_month}")
    if record.registered_status:
        anchors.append(f"dart_registered_status:{record.registered_status}")
    return IdentityCandidate(
        canonical_name=record.name,
        office=record.responsibility or record.position,
        organization=record.corp_name,
        career_anchors=tuple(anchors),
    )


def dart_ownership_to_identity(record: DartOwnershipRecord) -> IdentityCandidate | None:
    if not record.public_person_scope:
        return None
    office = record.executive_position or "주요주주 공시보고자"
    return IdentityCandidate(
        canonical_name=record.reporter_name,
        office=office,
        organization=record.corp_name,
        career_anchors=(
            f"dart_corp_code:{record.corp_code}",
            f"dart_ownership_receipt:{record.receipt_no}",
            f"dart_ownership_receipt_date:{record.receipt_date.isoformat()}",
        ),
    )


def company_profile_to_identity(
    record: CompanyOfficialSeniorProfileRecord,
) -> IdentityCandidate:
    anchors = [
        f"company_official_record:{record.record_id}",
        f"company_official_scope:{record.public_scope}",
        f"company_official_source:{record.source_ref}",
    ]
    if record.valid_from:
        anchors.append(f"company_role_start:{record.valid_from.isoformat()}")
    return IdentityCandidate(
        canonical_name=record.person_name,
        office=record.title,
        organization=record.company_name,
        career_anchors=tuple(anchors),
    )


def stage_dart_executives(records: list[DartExecutiveRecord]) -> list[StagedDartExecutive]:
    return [StagedDartExecutive(dart_executive_to_identity(record), record) for record in records]


def stage_dart_ownership(records: list[DartOwnershipRecord]) -> list[StagedDartOwnership]:
    return [StagedDartOwnership(dart_ownership_to_identity(record), record) for record in records]


def stage_company_official_profiles(rows: list[dict]) -> list[StagedCompanyOfficialSeniorProfile]:
    return [
        StagedCompanyOfficialSeniorProfile(company_profile_to_identity(record), record)
        for record in parse_company_official_profile_rows(rows)
    ]


def compensation_to_dict(record: DartCompensationRecord) -> dict[str, object]:
    return {
        "source_lane": f"OPENDART_{record.dataset.value}",
        "receipt_no": record.receipt_no,
        "corp_code": record.corp_code,
        "corp_name": record.corp_name,
        "disclosed_name": record.name,
        "position": record.position,
        "fiscal_year_label": record.fiscal_year_label,
        "compensation_total_krw": record.compensation_total_krw,
        "settlement_date": record.settlement_date.isoformat(),
        "person_candidate": None,
        "person_link_semantics": "REQUIRES_SEPARATE_SENIOR_ROLE_IDENTITY_MATCH",
        "wealth_semantics": "DISCLOSED_COMPENSATION_NOT_TOTAL_WEALTH",
    }


class OpenDartCorporateStager:
    def __init__(
        self,
        connector: OpenDartCorporateConnector,
        policy: SourcePolicy | None = None,
    ) -> None:
        self.connector = connector
        self.policy = policy or open_dart_corporate_policy()

    def stage(self) -> dict[str, object]:
        if self.policy.domain != self.connector.HOST:
            raise PolicyDenied("SourcePolicy domain does not match OpenDART connector")
        require_policy(self.policy, PolicyAction.FETCH)
        document = self.connector.fetch(self.connector.discover()[0])
        records = self.connector.parse(document)
        if self.connector.dataset == DartCorporateDataset.EXECUTIVE_STATUS:
            executives = [record for record in records if isinstance(record, DartExecutiveRecord)]
            return {"executives": [item.to_dict() for item in stage_dart_executives(executives)]}
        if self.connector.dataset in {
            DartCorporateDataset.DIRECTOR_COMPENSATION_V2,
            DartCorporateDataset.TOP_COMPENSATION_V2,
        }:
            compensation = [record for record in records if isinstance(record, DartCompensationRecord)]
            return {"compensation": [compensation_to_dict(record) for record in compensation]}
        ownership = [record for record in records if isinstance(record, DartOwnershipRecord)]
        return {"ownership": [item.to_dict() for item in stage_dart_ownership(ownership)]}


def render_corporate_json(payload: dict[str, object]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Stage OpenDART corporate senior-person data.")
    parser.add_argument(
        "--dataset", required=True, choices=[item.value for item in DartCorporateDataset]
    )
    parser.add_argument("--corp-code", required=True)
    parser.add_argument("--business-year", type=int)
    parser.add_argument("--report-code")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    connector = OpenDartCorporateConnector(
        dataset=DartCorporateDataset(args.dataset),
        corp_code=args.corp_code,
        business_year=args.business_year,
        report_code=args.report_code,
    )
    try:
        payload = OpenDartCorporateStager(connector).stage()
    except (DartApiError, MissingDartApiKey, PolicyDenied, ValueError) as exc:
        raise SystemExit(str(exc)) from None
    print(render_corporate_json(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
