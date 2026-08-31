from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass, replace
from datetime import UTC, datetime

from packages.connectors.alio_disclosures import (
    AlioCompensationRecord,
    AlioExecutiveDisclosureConnector,
    AlioExecutiveRecord,
    AlioInstitutionRecord,
    AlioRecordError,
    AlioReemploymentRecord,
    alio_public_institution_policy,
    parse_compensation_rows,
    parse_executive_rows,
    parse_institution_rows,
    parse_reemployment_rows,
)
from packages.domain.contracts import FeederObservation, SourcePolicy, SourceRun
from packages.domain.enums import SourceRunStatus
from packages.persistence import SqlAlchemyRepository
from packages.verification.identity import IdentityCandidate
from packages.verification.policy import PolicyAction, PolicyDenied, require_policy
from workers.ingest import IngestionPipeline


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


@dataclass(frozen=True)
class AlioExecutiveEnumerationResult:
    run: SourceRun
    institutions_committed: int
    unique_records: int


def normalized_alio_executive(record: AlioExecutiveRecord) -> dict[str, object]:
    return {
        "institution_code": record.institution_code,
        "institution_name": record.institution_name,
        "classification": record.classification.value,
        "classification_text": record.classification_text,
        "disclosure_no": record.source_ref,
        "executive_row_key": record.record_id,
        "canonical_name": record.person_name,
        "position_text": record.position_text,
        "title": record.title,
        "executive_kind": record.executive_kind.value,
        "term_start": record.term_start.isoformat(),
        "term_end": record.term_end.isoformat() if record.term_end else None,
        "reported_careers": list(record.reported_careers),
        "reported_careers_semantics": "institution_disclosed_not_independently_verified",
        "selection_procedure": record.selection_procedure,
        "selection_rule": record.selection_rule,
        "as_of": record.as_of.isoformat(),
    }


def alio_executive_content_hash(normalized: dict[str, object]) -> str:
    canonical = json.dumps(
        normalized,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _directory_fingerprint(institutions: tuple) -> str:
    payload = [
        {
            "institution_code": item.institution_code,
            "institution_name": item.institution_name,
            "institution_type_code": item.institution_type_code,
            "classification": item.classification.value,
            "classification_text": item.classification_text,
        }
        for item in institutions
    ]
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class AlioExecutiveEnumerator:
    FEEDER = "alio_public_institution_executives"
    SCOPE_KEY = "item_4_current_all_institutions"
    SEMANTIC_SCOPE = "public_institution_executive_disclosure"
    SOURCE_CONTRACT = "alio_item_4_current_executive_roster"

    def __init__(
        self,
        connector: AlioExecutiveDisclosureConnector,
        repository: SqlAlchemyRepository,
        policy: SourcePolicy | None = None,
    ) -> None:
        self.connector = connector
        self.repository = repository
        self.policy = policy or alio_public_institution_policy()

    def enumerate(self, *, resume: bool = False) -> AlioExecutiveEnumerationResult:
        if self.policy.domain != self.connector.HOST:
            raise PolicyDenied("SourcePolicy domain does not match the ALIO connector")
        require_policy(self.policy, PolicyAction.FETCH)
        require_policy(self.policy, PolicyAction.STORE_METADATA)

        self.repository.assert_ready()
        prior_checkpoint = self.repository.source_checkpoint(self.FEEDER, self.SCOPE_KEY)
        if resume and prior_checkpoint is None:
            raise AlioRecordError("ALIO resume requires a committed checkpoint")
        run = self.repository.start_source_run(
            self.FEEDER,
            self.SCOPE_KEY,
            {"source_contract": self.SOURCE_CONTRACT, "resume": resume},
        )
        institutions_committed = 0
        chunks_committed = 0
        try:
            directory_document = self.connector.fetch(self.connector.discover()[0])
            directory = self.connector.parse_directory_body(directory_document.body)
            if directory.total_count <= 0:
                raise AlioRecordError("ALIO item 4 institution universe must not be empty")
            directory_fingerprint = _directory_fingerprint(directory.institutions)
            institution_codes = [item.institution_code for item in directory.institutions]
            start_index = 0
            seen_hashes: dict[str, str] = {}
            seen_disclosures: dict[str, str] = {}

            if resume:
                assert prior_checkpoint is not None
                if prior_checkpoint.cursor is None:
                    raise AlioRecordError("ALIO resume checkpoint lacks an institution cursor")
                try:
                    start_index = int(prior_checkpoint.cursor)
                    checkpoint_fingerprint = str(prior_checkpoint.metadata["directory_fingerprint"])
                    checkpoint_total = int(prior_checkpoint.metadata["institution_total"])
                    checkpoint_codes = list(prior_checkpoint.metadata["institution_codes"])
                    seen_hashes = dict(prior_checkpoint.metadata["seen_provider_hashes"])
                    seen_disclosures = dict(prior_checkpoint.metadata["seen_current_disclosures"])
                except (KeyError, TypeError, ValueError):
                    raise AlioRecordError("ALIO resume checkpoint metadata is invalid") from None
                if (
                    checkpoint_fingerprint != directory_fingerprint
                    or checkpoint_total != directory.total_count
                    or checkpoint_codes != institution_codes
                ):
                    raise AlioRecordError("ALIO institution universe changed before resume")
                if start_index < 0 or start_index >= directory.total_count:
                    raise AlioRecordError("ALIO resume checkpoint already covers the universe")
            else:
                ingestion = IngestionPipeline(self.connector).ingest_document(
                    directory_document, self.policy
                )
                self.repository.commit_source_page(
                    run_id=run.id,
                    policy=self.policy,
                    source=ingestion.source,
                    snapshot=ingestion.snapshot,
                    observations=[],
                    cursor="0",
                    checkpoint_metadata={
                        "source_contract": self.SOURCE_CONTRACT,
                        "directory_fingerprint": directory_fingerprint,
                        "institution_total": directory.total_count,
                        "institution_codes": institution_codes,
                        "seen_provider_hashes": {},
                        "seen_current_disclosures": {},
                    },
                )
                chunks_committed += 1

            for index, institution in enumerate(directory.institutions, start=1):
                if index <= start_index:
                    continue
                list_document = self.connector.fetch(
                    self.connector.report_list_url(institution, page_no=1)
                )
                report_page = self.connector.parse_report_page_body(
                    list_document.body,
                    institution_code=institution.institution_code,
                    requested_page=1,
                )
                disclosure = self.connector.current_disclosure(report_page)
                prior_institution = seen_disclosures.get(disclosure.disclosure_no)
                if prior_institution is not None:
                    if prior_institution != institution.institution_code:
                        raise AlioRecordError(
                            "ALIO current disclosure is reused across institutions"
                        )
                    raise AlioRecordError("duplicate ALIO current disclosure")

                report_document = self.connector.fetch(self.connector.report_url(disclosure))
                report_document = replace(
                    report_document,
                    published_at=datetime.combine(
                        disclosure.disclosure_date, datetime.min.time(), tzinfo=UTC
                    ),
                    metadata={
                        **report_document.metadata,
                        "institution_code": institution.institution_code,
                        "institution_name": institution.institution_name,
                        "institution_type_code": institution.institution_type_code,
                        "classification": institution.classification.value,
                        "classification_text": institution.classification_text,
                        "disclosure_date": disclosure.disclosure_date.isoformat(),
                    },
                )
                records = self.connector.parse_executives(
                    report_document,
                    institution=institution,
                    disclosure=disclosure,
                )
                page_hashes: dict[str, str] = {}
                normalized_by_key: dict[str, dict[str, object]] = {}
                for record in records:
                    normalized = normalized_alio_executive(record)
                    content_hash = alio_executive_content_hash(normalized)
                    if record.record_id in page_hashes:
                        raise AlioRecordError("duplicate ALIO executive row key in report")
                    if record.record_id in seen_hashes:
                        if seen_hashes[record.record_id] != content_hash:
                            raise AlioRecordError("conflicting ALIO executive row key")
                        raise AlioRecordError("duplicate ALIO executive row key")
                    page_hashes[record.record_id] = content_hash
                    normalized_by_key[record.record_id] = normalized

                ingestion = IngestionPipeline(self.connector).ingest_document(
                    report_document, self.policy
                )
                observations = [
                    FeederObservation(
                        feeder=self.FEEDER,
                        scope_key=self.SCOPE_KEY,
                        provider_record_key=record.record_id,
                        snapshot_id=ingestion.snapshot.id,
                        run_id=run.id,
                        provider_observed_at=datetime.combine(
                            record.as_of, datetime.min.time(), tzinfo=UTC
                        ),
                        semantic_scope=self.SEMANTIC_SCOPE,
                        identity_hints={
                            "canonical_name": record.person_name,
                            "institution_code": record.institution_code,
                            "organization": record.institution_name,
                            "office": record.title,
                            "position_text": record.position_text,
                            "term_start": record.term_start.isoformat(),
                            "disclosure_no": disclosure.disclosure_no,
                            "provider_person_id": None,
                        },
                        normalized=normalized_by_key[record.record_id],
                        content_hash=page_hashes[record.record_id],
                    )
                    for record in records
                ]

                next_seen_hashes = seen_hashes | page_hashes
                next_seen_disclosures = {
                    **seen_disclosures,
                    disclosure.disclosure_no: institution.institution_code,
                }
                self.repository.commit_source_page(
                    run_id=run.id,
                    policy=self.policy,
                    source=ingestion.source,
                    snapshot=ingestion.snapshot,
                    observations=observations,
                    cursor=str(index),
                    checkpoint_metadata={
                        "source_contract": self.SOURCE_CONTRACT,
                        "directory_fingerprint": directory_fingerprint,
                        "institution_total": directory.total_count,
                        "institution_codes": institution_codes,
                        "last_institution_code": institution.institution_code,
                        "report_page_size": report_page.page_size,
                        "seen_provider_hashes": next_seen_hashes,
                        "seen_current_disclosures": next_seen_disclosures,
                    },
                )
                institutions_committed += 1
                chunks_committed += 1
                seen_hashes = next_seen_hashes
                seen_disclosures = next_seen_disclosures

            checkpoint = self.repository.source_checkpoint(self.FEEDER, self.SCOPE_KEY)
            if (
                checkpoint is None
                or checkpoint.cursor != str(directory.total_count)
                or len(seen_disclosures) != directory.total_count
            ):
                raise AlioRecordError("ALIO current executive roster coverage is incomplete")
            completed = self.repository.finish_source_run(run.id, SourceRunStatus.SUCCESS)
            return AlioExecutiveEnumerationResult(
                completed, institutions_committed, len(seen_hashes)
            )
        except Exception as exc:
            status = SourceRunStatus.PARTIAL if chunks_committed else SourceRunStatus.FAILED
            self.repository.finish_source_run(
                run.id,
                status,
                error_code=type(exc).__name__[:120],
                error_summary="ALIO item 4 current-roster enumeration did not complete",
            )
            raise


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Enumerate the unfiltered ALIO item 4 current executive roster."
    )
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--database-url")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result = AlioExecutiveEnumerator(
            AlioExecutiveDisclosureConnector(),
            SqlAlchemyRepository(args.database_url),
        ).enumerate(resume=args.resume)
    except (AlioRecordError, PolicyDenied, ValueError) as exc:
        parser.error(str(exc))
    print(
        json.dumps(
            {
                "run_id": str(result.run.id),
                "status": result.run.status.value,
                "scope_key": result.run.scope_key,
                "institutions_committed": result.institutions_committed,
                "unique_records": result.unique_records,
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
