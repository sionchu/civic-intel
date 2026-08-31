from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from packages.connectors.company_official_profiles import (
    CompanyOfficialSeniorProfileRecord,
    parse_company_official_profile_rows,
)
from packages.connectors.open_dart_corporate import (
    DartApiError,
    DartCompensationRecord,
    DartCorporateDataset,
    DartCorporationRecord,
    DartExecutiveRecord,
    DartOwnershipRecord,
    MissingDartApiKey,
    OpenDartCorpCodeConnector,
    OpenDartCorporateConnector,
    open_dart_corporate_policy,
)
from packages.domain.contracts import FeederObservation, SourcePolicy, SourceRun
from packages.domain.enums import SourceRunStatus
from packages.persistence import SqlAlchemyRepository
from packages.verification.identity import IdentityCandidate
from packages.verification.policy import PolicyAction, PolicyDenied, require_policy
from workers.ingest import IngestionPipeline


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
                "valid_from": self.record.valid_from.isoformat()
                if self.record.valid_from
                else None,
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


@dataclass(frozen=True)
class OpenDartExecutiveEnumerationResult:
    run: SourceRun
    corporations_committed: int
    corporations_covered: int
    companies_with_executives: int
    companies_without_executives: int
    unique_records: int


def normalized_dart_executive(
    corporation: DartCorporationRecord,
    record: DartExecutiveRecord,
    *,
    business_year: int,
    report_code: str,
    row_ordinal: int,
) -> dict[str, object]:
    return {
        "corp_code": record.corp_code,
        "corp_name": record.corp_name,
        "corp_master_name": corporation.corp_name,
        "stock_code": corporation.stock_code,
        "corp_master_modified_on": corporation.modified_on.isoformat(),
        "business_year": business_year,
        "report_code": report_code,
        "receipt_no": record.receipt_no,
        "executive_row_ordinal": row_ordinal,
        "canonical_name": record.name,
        "birth_year_month": record.birth_year_month,
        "position": record.position,
        "registered_status": record.registered_status,
        "full_time_status": record.full_time_status,
        "responsibility": record.responsibility,
        "reported_main_career": record.reported_main_career,
        "reported_main_career_semantics": "company_disclosed_not_independently_verified",
        "largest_shareholder_relation": record.largest_shareholder_relation,
        "tenure_text": record.tenure_text,
        "tenure_end_on": record.tenure_end_on.isoformat() if record.tenure_end_on else None,
        "settlement_date": record.settlement_date.isoformat(),
    }


def dart_executive_content_hash(normalized: dict[str, object]) -> str:
    canonical = json.dumps(
        normalized,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def dart_corporation_universe_fingerprint(
    corporations: tuple[DartCorporationRecord, ...],
) -> str:
    payload = [
        {
            "corp_code": item.corp_code,
            "corp_name": item.corp_name,
            "corp_eng_name": item.corp_eng_name,
            "stock_code": item.stock_code,
            "modified_on": item.modified_on.isoformat(),
        }
        for item in corporations
    ]
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def dart_executive_rows_with_keys(
    records: list[DartExecutiveRecord],
) -> list[tuple[str, int, DartExecutiveRecord]]:
    receipt_ordinals: dict[str, int] = {}
    keyed: list[tuple[str, int, DartExecutiveRecord]] = []
    for record in records:
        ordinal = receipt_ordinals.get(record.receipt_no, 0) + 1
        receipt_ordinals[record.receipt_no] = ordinal
        provider_key = f"{record.corp_code}:{record.receipt_no}:{ordinal}"
        keyed.append((provider_key, ordinal, record))
    return keyed


DartExecutiveConnectorFactory = Callable[[str], OpenDartCorporateConnector]


class OpenDartExecutiveEnumerator:
    FEEDER = "opendart_disclosed_executives"
    SEMANTIC_SCOPE = "corporate_executive_disclosure"
    SOURCE_CONTRACT = "opendart_corp_master_executive_status"

    def __init__(
        self,
        universe_connector: OpenDartCorpCodeConnector,
        repository: SqlAlchemyRepository,
        *,
        business_year: int,
        report_code: str,
        executive_connector_factory: DartExecutiveConnectorFactory | None = None,
        policy: SourcePolicy | None = None,
    ) -> None:
        if business_year < 2015 or business_year > 9999:
            raise ValueError("OpenDART business_year must be a 4-digit year from 2015")
        if report_code not in {"11011", "11012", "11013", "11014"}:
            raise ValueError("unsupported OpenDART report code")
        self.universe_connector = universe_connector
        self.repository = repository
        self.business_year = business_year
        self.report_code = report_code
        self.scope_key = f"all_corporations:{business_year}:{report_code}"
        self.executive_connector_factory = executive_connector_factory or (
            lambda corp_code: OpenDartCorporateConnector(
                dataset=DartCorporateDataset.EXECUTIVE_STATUS,
                corp_code=corp_code,
                business_year=business_year,
                report_code=report_code,
            )
        )
        self.policy = policy or open_dart_corporate_policy()

    def _executive_connector(self, corp_code: str) -> OpenDartCorporateConnector:
        connector = self.executive_connector_factory(corp_code)
        if (
            connector.dataset != DartCorporateDataset.EXECUTIVE_STATUS
            or connector.corp_code != corp_code
            or connector.business_year != self.business_year
            or connector.report_code != self.report_code
        ):
            raise DartApiError("OpenDART executive connector does not match enumeration scope")
        return connector

    def enumerate(self, *, resume: bool = False) -> OpenDartExecutiveEnumerationResult:
        if self.policy.domain != self.universe_connector.HOST:
            raise PolicyDenied("SourcePolicy domain does not match the OpenDART connector")
        require_policy(self.policy, PolicyAction.FETCH)
        require_policy(self.policy, PolicyAction.STORE_METADATA)

        self.repository.assert_ready()
        prior_checkpoint = self.repository.source_checkpoint(self.FEEDER, self.scope_key)
        if resume and prior_checkpoint is None:
            raise DartApiError("OpenDART resume requires a committed checkpoint")
        run = self.repository.start_source_run(
            self.FEEDER,
            self.scope_key,
            {
                "source_contract": self.SOURCE_CONTRACT,
                "business_year": self.business_year,
                "report_code": self.report_code,
                "resume": resume,
            },
        )
        corporations_committed = 0
        chunks_committed = 0
        try:
            universe_document = self.universe_connector.fetch(self.universe_connector.discover()[0])
            corporations = self.universe_connector.parse_corporations(universe_document)
            if not corporations:
                raise DartApiError("OpenDART corporation universe must not be empty")
            universe_fingerprint = dart_corporation_universe_fingerprint(corporations)
            corporation_total = len(corporations)
            start_index = 0
            companies_with_executives = 0
            companies_without_executives = 0
            executive_rows_seen = 0

            if resume:
                assert prior_checkpoint is not None
                if prior_checkpoint.cursor is None:
                    raise DartApiError("OpenDART resume checkpoint lacks a corporation cursor")
                try:
                    start_index = int(prior_checkpoint.cursor)
                    checkpoint_fingerprint = str(prior_checkpoint.metadata["universe_fingerprint"])
                    checkpoint_total = int(prior_checkpoint.metadata["corporation_total"])
                    checkpoint_year = int(prior_checkpoint.metadata["business_year"])
                    checkpoint_report = str(prior_checkpoint.metadata["report_code"])
                    companies_with_executives = int(
                        prior_checkpoint.metadata["companies_with_executives"]
                    )
                    companies_without_executives = int(
                        prior_checkpoint.metadata["companies_without_executives"]
                    )
                    executive_rows_seen = int(prior_checkpoint.metadata["executive_rows_seen"])
                except (KeyError, TypeError, ValueError):
                    raise DartApiError("OpenDART resume checkpoint metadata is invalid") from None
                if (
                    checkpoint_fingerprint != universe_fingerprint
                    or checkpoint_total != corporation_total
                    or checkpoint_year != self.business_year
                    or checkpoint_report != self.report_code
                ):
                    raise DartApiError("OpenDART corporation universe changed before resume")
                if start_index < 0 or start_index >= corporation_total:
                    raise DartApiError("OpenDART resume checkpoint already covers the universe")
                if companies_with_executives + companies_without_executives != start_index:
                    raise DartApiError("OpenDART resume coverage counters are inconsistent")
            else:
                universe_ingestion = IngestionPipeline(self.universe_connector).ingest_document(
                    universe_document, self.policy
                )
                self.repository.commit_source_page(
                    run_id=run.id,
                    policy=self.policy,
                    source=universe_ingestion.source,
                    snapshot=universe_ingestion.snapshot,
                    observations=[],
                    cursor="0",
                    checkpoint_metadata={
                        "source_contract": self.SOURCE_CONTRACT,
                        "business_year": self.business_year,
                        "report_code": self.report_code,
                        "universe_fingerprint": universe_fingerprint,
                        "corporation_total": corporation_total,
                        "last_corp_code": None,
                        "companies_with_executives": 0,
                        "companies_without_executives": 0,
                        "executive_rows_seen": 0,
                    },
                )
                chunks_committed += 1

            for index, corporation in enumerate(corporations, start=1):
                if index <= start_index:
                    continue
                connector = self._executive_connector(corporation.corp_code)
                document = connector.fetch(connector.discover()[0])
                parsed = connector.parse(document)
                if any(not isinstance(record, DartExecutiveRecord) for record in parsed):
                    raise DartApiError("OpenDART executive endpoint returned an unexpected record")
                records = [record for record in parsed if isinstance(record, DartExecutiveRecord)]
                keyed_records = dart_executive_rows_with_keys(records)
                page_keys: set[str] = set()
                observations: list[FeederObservation] = []
                ingestion = IngestionPipeline(connector).ingest_document(document, self.policy)
                for provider_key, row_ordinal, record in keyed_records:
                    if record.corp_code != corporation.corp_code:
                        raise DartApiError("OpenDART executive row corporation code mismatch")
                    if provider_key in page_keys:
                        raise DartApiError("duplicate OpenDART executive disclosure row key")
                    page_keys.add(provider_key)
                    normalized = normalized_dart_executive(
                        corporation,
                        record,
                        business_year=self.business_year,
                        report_code=self.report_code,
                        row_ordinal=row_ordinal,
                    )
                    observations.append(
                        FeederObservation(
                            feeder=self.FEEDER,
                            scope_key=self.scope_key,
                            provider_record_key=provider_key,
                            snapshot_id=ingestion.snapshot.id,
                            run_id=run.id,
                            provider_observed_at=datetime.combine(
                                record.settlement_date, datetime.min.time(), tzinfo=UTC
                            ),
                            semantic_scope=self.SEMANTIC_SCOPE,
                            identity_hints={
                                "canonical_name": record.name,
                                "organization": record.corp_name,
                                "office": record.responsibility or record.position,
                                "birth_year_month": record.birth_year_month,
                                "corp_code": record.corp_code,
                                "receipt_no": record.receipt_no,
                                "provider_person_id": None,
                            },
                            normalized=normalized,
                            content_hash=dart_executive_content_hash(normalized),
                        )
                    )

                next_with = companies_with_executives + (1 if records else 0)
                next_without = companies_without_executives + (0 if records else 1)
                next_rows = executive_rows_seen + len(records)
                self.repository.commit_source_page(
                    run_id=run.id,
                    policy=self.policy,
                    source=ingestion.source,
                    snapshot=ingestion.snapshot,
                    observations=observations,
                    cursor=str(index),
                    checkpoint_metadata={
                        "source_contract": self.SOURCE_CONTRACT,
                        "business_year": self.business_year,
                        "report_code": self.report_code,
                        "universe_fingerprint": universe_fingerprint,
                        "corporation_total": corporation_total,
                        "last_corp_code": corporation.corp_code,
                        "companies_with_executives": next_with,
                        "companies_without_executives": next_without,
                        "executive_rows_seen": next_rows,
                    },
                )
                corporations_committed += 1
                chunks_committed += 1
                companies_with_executives = next_with
                companies_without_executives = next_without
                executive_rows_seen = next_rows

            checkpoint = self.repository.source_checkpoint(self.FEEDER, self.scope_key)
            if (
                checkpoint is None
                or checkpoint.cursor != str(corporation_total)
                or companies_with_executives + companies_without_executives != corporation_total
            ):
                raise DartApiError("OpenDART executive universe coverage is incomplete")
            completed = self.repository.finish_source_run(run.id, SourceRunStatus.SUCCESS)
            return OpenDartExecutiveEnumerationResult(
                run=completed,
                corporations_committed=corporations_committed,
                corporations_covered=corporation_total,
                companies_with_executives=companies_with_executives,
                companies_without_executives=companies_without_executives,
                unique_records=executive_rows_seen,
            )
        except Exception as exc:
            status = SourceRunStatus.PARTIAL if chunks_committed else SourceRunStatus.FAILED
            self.repository.finish_source_run(
                run.id,
                status,
                error_code=type(exc).__name__[:120],
                error_summary="OpenDART executive full-scope enumeration did not complete",
            )
            raise


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
            compensation = [
                record for record in records if isinstance(record, DartCompensationRecord)
            ]
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
    parser.add_argument("--corp-code")
    parser.add_argument("--business-year", type=int)
    parser.add_argument("--report-code")
    parser.add_argument(
        "--enumerate",
        action="store_true",
        help="Persist the complete corp-code-master executive scope for one report period.",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume a partially committed full-scope executive enumeration.",
    )
    parser.add_argument("--database-url")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    dataset = DartCorporateDataset(args.dataset)
    if args.enumerate or args.resume:
        if dataset != DartCorporateDataset.EXECUTIVE_STATUS:
            parser.error("full enumeration supports only EXECUTIVE_STATUS")
        if args.corp_code is not None:
            parser.error("full enumeration uses the unfiltered corp-code master")
        if args.business_year is None or args.report_code is None:
            parser.error("full enumeration requires --business-year and --report-code")
        try:
            result = OpenDartExecutiveEnumerator(
                OpenDartCorpCodeConnector(),
                SqlAlchemyRepository(args.database_url),
                business_year=args.business_year,
                report_code=args.report_code,
            ).enumerate(resume=args.resume)
        except (DartApiError, MissingDartApiKey, PolicyDenied, ValueError) as exc:
            parser.error(str(exc))
        print(
            json.dumps(
                {
                    "run_id": str(result.run.id),
                    "status": result.run.status.value,
                    "scope_key": result.run.scope_key,
                    "corporations_committed": result.corporations_committed,
                    "corporations_covered": result.corporations_covered,
                    "companies_with_executives": result.companies_with_executives,
                    "companies_without_executives": result.companies_without_executives,
                    "unique_records": result.unique_records,
                },
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    if args.corp_code is None:
        parser.error("single-pull staging requires --corp-code")
    connector = OpenDartCorporateConnector(
        dataset=dataset,
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
