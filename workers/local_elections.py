from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from math import ceil

from packages.connectors.nec_local_elections import (
    LOCAL_ELECTION_TYPES,
    NecApiError,
    NecCandidateConnector,
    NecCandidateRecord,
    NecWinnerConnector,
    NecWinnerRecord,
    nec_local_election_policy,
)
from packages.domain.contracts import FeederObservation, SourcePolicy, SourceRun
from packages.domain.enums import SourceRunStatus
from packages.persistence import SqlAlchemyRepository
from packages.verification.identity import IdentityCandidate
from packages.verification.policy import PolicyAction, PolicyDenied, require_policy
from workers.ingest import IngestionPipeline


class NecCandidateCoverageError(NecApiError):
    pass


class NecWinnerCoverageError(NecApiError):
    pass


@dataclass(frozen=True)
class StagedLocalElectionCandidate:
    candidate: IdentityCandidate
    candidate_id: str
    election_id: str
    election_type: int
    election_type_name: str
    district_name: str
    province_name: str
    municipality_name: str | None
    party: str | None
    candidate_number: str | None
    candidate_sub_number: str | None
    registration_status: str | None
    public_job: str | None
    submitted_education: str | None
    submitted_careers: tuple[str, ...]
    outcome: str
    votes: int | None = None
    vote_rate: float | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "candidate_id": self.candidate_id,
            "canonical_name": self.candidate.canonical_name,
            "aliases": list(self.candidate.aliases),
            "birth_date": self.candidate.birth_date.isoformat()
            if self.candidate.birth_date
            else None,
            "election": {
                "election_id": self.election_id,
                "type_code": self.election_type,
                "type_name": self.election_type_name,
                "province": self.province_name,
                "municipality": self.municipality_name,
                "district": self.district_name,
                "party": self.party,
                "candidate_number": self.candidate_number,
                "candidate_sub_number": self.candidate_sub_number,
                "registration_status": self.registration_status,
                "outcome": self.outcome,
                "votes": self.votes,
                "vote_rate": self.vote_rate,
            },
            "candidate_submitted": {
                "public_job": self.public_job,
                "education": self.submitted_education,
                "careers": list(self.submitted_careers),
                "semantics": (
                    "후보자가 선거관리위원회에 제출해 공개된 정보이며, 독립 검증된 경력과는 구분한다."
                ),
            },
            "identity_anchors": list(self.candidate.career_anchors),
        }


@dataclass(frozen=True)
class NecEnumerationResult:
    run: SourceRun
    pages_committed: int
    unique_records: int


def candidate_to_identity(record: NecCandidateRecord) -> IdentityCandidate:
    aliases = (
        (record.name_hanja,) if record.name_hanja and record.name_hanja != record.name_ko else ()
    )
    jurisdiction = "/".join(
        value
        for value in (record.province_name, record.municipality_name, record.district_name)
        if value
    )
    anchors = (
        f"nec_candidate_id:{record.candidate_id}",
        f"election_id:{record.election_id}",
        f"election_type:{record.election_type}",
        f"election_jurisdiction:{jurisdiction}",
    )
    return IdentityCandidate(
        canonical_name=record.name_ko,
        aliases=aliases,
        birth_date=record.birth_date,
        office=f"{LOCAL_ELECTION_TYPES[record.election_type]} 후보",
        organization=record.party,
        career_anchors=anchors,
    )


def _coverage_complete(metadata: dict[str, str]) -> bool:
    total_text = metadata.get("total_count")
    if not total_text:
        return False
    try:
        total = int(total_text)
        page_no = int(metadata.get("page_no", "1"))
        page_size = int(metadata.get("page_size", "100"))
    except ValueError:
        return False
    return page_no == 1 and total <= page_size


def normalized_nec_candidate(record: NecCandidateRecord) -> dict[str, object]:
    aliases = [value for value in (record.name_hanja,) if value and value != record.name_ko]
    return {
        "candidate_id": record.candidate_id,
        "election_id": record.election_id,
        "election_type": record.election_type,
        "election_type_name": LOCAL_ELECTION_TYPES[record.election_type],
        "canonical_name": record.name_ko,
        "aliases": aliases,
        "birth_date": record.birth_date.isoformat() if record.birth_date else None,
        "province": record.province_name,
        "municipality": record.municipality_name,
        "district": record.district_name,
        "party": record.party,
        "candidate_number": record.candidate_number,
        "candidate_sub_number": record.candidate_sub_number,
        "public_job": record.public_job,
        "submitted_education": record.submitted_education,
        "submitted_careers": list(record.submitted_careers),
        "submission_semantics": "candidate_submitted_election_disclosure",
        "registration_status": record.registration_status,
    }


def nec_candidate_content_hash(normalized: dict[str, object]) -> str:
    canonical = json.dumps(
        normalized,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def normalized_nec_winner(record: NecWinnerRecord) -> dict[str, object]:
    aliases = [value for value in (record.name_hanja,) if value and value != record.name_ko]
    return {
        "candidate_id": record.candidate_id,
        "election_id": record.election_id,
        "election_type": record.election_type,
        "election_type_name": LOCAL_ELECTION_TYPES[record.election_type],
        "canonical_name": record.name_ko,
        "aliases": aliases,
        "birth_date": record.birth_date.isoformat() if record.birth_date else None,
        "province": record.province_name,
        "municipality": record.municipality_name,
        "district": record.district_name,
        "party": record.party,
        "candidate_number": record.candidate_number,
        "candidate_sub_number": record.candidate_sub_number,
        "public_job": record.public_job,
        "submitted_education": record.submitted_education,
        "submitted_careers": list(record.submitted_careers),
        "submission_semantics": "candidate_submitted_election_disclosure",
        "outcome": "WINNER",
        "votes": record.votes,
        "vote_rate": record.vote_rate,
    }


def nec_winner_content_hash(normalized: dict[str, object]) -> str:
    canonical = json.dumps(
        normalized,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _election_observed_at(election_id: str) -> datetime | None:
    try:
        return datetime.strptime(f"{election_id}+0000", "%Y%m%d%z")
    except ValueError:
        return None


class LocalElectionWinnerEnumerator:
    FEEDER = "nec_local_election_winners"
    SEMANTIC_SCOPE = "local_elected_office_winner"
    SOURCE_CONTRACT = "nec_local_election_winner_roster"

    def __init__(
        self,
        connector: NecWinnerConnector,
        repository: SqlAlchemyRepository,
        policy: SourcePolicy | None = None,
    ) -> None:
        self.connector = connector
        self.repository = repository
        self.policy = policy or nec_local_election_policy()

    @property
    def scope_key(self) -> str:
        return f"{self.connector.election_id}:{self.connector.election_type}"

    def enumerate(self, *, resume: bool = False) -> NecEnumerationResult:
        if any(
            (
                self.connector.district_name,
                self.connector.province_name,
                self.connector.party,
            )
        ):
            raise NecWinnerCoverageError("L3 NEC winner enumeration must be unfiltered")
        if self.policy.domain != self.connector.HOST:
            raise PolicyDenied("SourcePolicy domain does not match the NEC winner connector")
        require_policy(self.policy, PolicyAction.FETCH)
        require_policy(self.policy, PolicyAction.STORE_METADATA)

        self.repository.assert_ready()
        prior_checkpoint = self.repository.source_checkpoint(self.FEEDER, self.scope_key)
        run = self.repository.start_source_run(
            self.FEEDER,
            self.scope_key,
            {
                "source_contract": self.SOURCE_CONTRACT,
                "election_id": self.connector.election_id,
                "election_type": self.connector.election_type,
                "resume": resume,
            },
        )
        pages_committed = 0
        try:
            start_page = 1
            expected_total: int | None = None
            expected_pages: int | None = None
            seen_hashes: dict[str, str] = {}
            page_fingerprints: list[str] = []
            if resume and prior_checkpoint is not None:
                if prior_checkpoint.cursor is None:
                    raise NecWinnerCoverageError("resume checkpoint lacks a page cursor")
                try:
                    start_page = int(prior_checkpoint.cursor) + 1
                    expected_total = int(prior_checkpoint.metadata["total_count"])
                    expected_pages = int(prior_checkpoint.metadata["expected_pages"])
                    seen_hashes = dict(prior_checkpoint.metadata["seen_provider_hashes"])
                    page_fingerprints = list(prior_checkpoint.metadata["page_fingerprints"])
                except (KeyError, TypeError, ValueError):
                    raise NecWinnerCoverageError("resume checkpoint metadata is invalid") from None
                if start_page > expected_pages:
                    raise NecWinnerCoverageError(
                        "resume checkpoint already covers the full NEC winner scope"
                    )

            page_no = start_page
            while True:
                self.connector.page_no = page_no
                document = self.connector.fetch(self.connector.discover()[0])
                if document.metadata.get("service_name") != "getWinnerInfoInqire":
                    raise NecWinnerCoverageError("NEC winner source contract is inconsistent")
                if document.metadata.get("election_id") != self.connector.election_id:
                    raise NecWinnerCoverageError("NEC winner election id is inconsistent")
                if document.metadata.get("election_type") != str(self.connector.election_type):
                    raise NecWinnerCoverageError("NEC winner election type is inconsistent")
                if document.metadata.get("page_no") != str(page_no):
                    raise NecWinnerCoverageError("NEC winner requested page is inconsistent")
                if document.metadata.get("page_size") != str(self.connector.page_size):
                    raise NecWinnerCoverageError("NEC winner requested page size is inconsistent")
                if document.metadata.get("provider_page_no") != str(page_no):
                    raise NecWinnerCoverageError("NEC winner provider page is inconsistent")
                if document.metadata.get("provider_page_size") != str(self.connector.page_size):
                    raise NecWinnerCoverageError("NEC winner provider page size is inconsistent")
                try:
                    total_count = int(document.metadata["total_count"])
                except (KeyError, TypeError, ValueError):
                    raise NecWinnerCoverageError("NEC winner total count is unavailable") from None
                if total_count < 0:
                    raise NecWinnerCoverageError("NEC winner total count must not be negative")
                current_expected_pages = max(1, ceil(total_count / self.connector.page_size))
                if expected_total is None:
                    expected_total = total_count
                    expected_pages = current_expected_pages
                elif total_count != expected_total or current_expected_pages != expected_pages:
                    raise NecWinnerCoverageError(
                        "NEC winner total count changed during enumeration"
                    )
                assert expected_pages is not None
                if page_no > expected_pages:
                    raise NecWinnerCoverageError("NEC winner API returned an unexpected extra page")

                winners = self.connector.parse_winners(document)
                expected_row_count = min(
                    self.connector.page_size,
                    max(0, expected_total - ((page_no - 1) * self.connector.page_size)),
                )
                if len(winners) != expected_row_count:
                    raise NecWinnerCoverageError("NEC winner page row count is incomplete")

                page_hashes: dict[str, str] = {}
                normalized_by_key: dict[str, dict[str, object]] = {}
                for winner in winners:
                    if winner.election_id != self.connector.election_id:
                        raise NecWinnerCoverageError("NEC winner row election id is inconsistent")
                    if winner.election_type != self.connector.election_type:
                        raise NecWinnerCoverageError("NEC winner row election type is inconsistent")
                    normalized = normalized_nec_winner(winner)
                    content_hash = nec_winner_content_hash(normalized)
                    if winner.candidate_id in page_hashes:
                        if page_hashes[winner.candidate_id] != content_hash:
                            raise NecWinnerCoverageError(
                                "conflicting NEC huboid appears within one page"
                            )
                        raise NecWinnerCoverageError("duplicate NEC huboid appears within one page")
                    if winner.candidate_id in seen_hashes:
                        if seen_hashes[winner.candidate_id] != content_hash:
                            raise NecWinnerCoverageError(
                                "conflicting NEC huboid appears across pages"
                            )
                        raise NecWinnerCoverageError("duplicate NEC huboid appears across pages")
                    page_hashes[winner.candidate_id] = content_hash
                    normalized_by_key[winner.candidate_id] = normalized

                fingerprint_payload = json.dumps(
                    sorted(page_hashes.items()),
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
                page_fingerprint = hashlib.sha256(fingerprint_payload.encode("utf-8")).hexdigest()
                if page_fingerprint in page_fingerprints:
                    raise NecWinnerCoverageError("NEC winner API returned duplicate page content")

                ingestion = IngestionPipeline(self.connector).ingest_document(document, self.policy)
                observations = []
                for winner in winners:
                    normalized = normalized_by_key[winner.candidate_id]
                    aliases = [
                        value for value in (winner.name_hanja,) if value and value != winner.name_ko
                    ]
                    observations.append(
                        FeederObservation(
                            feeder=self.FEEDER,
                            scope_key=self.scope_key,
                            provider_record_key=winner.candidate_id,
                            snapshot_id=ingestion.snapshot.id,
                            run_id=run.id,
                            provider_observed_at=_election_observed_at(winner.election_id),
                            semantic_scope=self.SEMANTIC_SCOPE,
                            identity_hints={
                                "canonical_name": winner.name_ko,
                                "aliases": aliases,
                                "birth_date": normalized["birth_date"],
                                "external_ids": {"nec_huboid": winner.candidate_id},
                            },
                            normalized=normalized,
                            content_hash=page_hashes[winner.candidate_id],
                        )
                    )

                next_seen_hashes = seen_hashes | page_hashes
                next_page_fingerprints = [*page_fingerprints, page_fingerprint]
                checkpoint_metadata = {
                    "page_size": self.connector.page_size,
                    "expected_pages": expected_pages,
                    "total_count": expected_total,
                    "source_contract": self.SOURCE_CONTRACT,
                    "election_id": self.connector.election_id,
                    "election_type": self.connector.election_type,
                    "seen_provider_hashes": next_seen_hashes,
                    "page_fingerprints": next_page_fingerprints,
                }
                self.repository.commit_source_page(
                    run_id=run.id,
                    policy=self.policy,
                    source=ingestion.source,
                    snapshot=ingestion.snapshot,
                    observations=observations,
                    cursor=str(page_no),
                    checkpoint_metadata=checkpoint_metadata,
                )
                pages_committed += 1
                seen_hashes = next_seen_hashes
                page_fingerprints = next_page_fingerprints

                if page_no == expected_pages:
                    if len(seen_hashes) != expected_total:
                        raise NecWinnerCoverageError(
                            "NEC winner unique record coverage is incomplete"
                        )
                    break
                page_no += 1

            completed = self.repository.finish_source_run(run.id, SourceRunStatus.SUCCESS)
            return NecEnumerationResult(completed, pages_committed, len(seen_hashes))
        except Exception as exc:
            status = SourceRunStatus.PARTIAL if pages_committed else SourceRunStatus.FAILED
            self.repository.finish_source_run(
                run.id,
                status,
                error_code=type(exc).__name__[:120],
                error_summary="NEC winner enumeration did not complete",
            )
            raise


class LocalElectionCandidateEnumerator:
    FEEDER = "nec_local_election_candidates"
    SEMANTIC_SCOPE = "local_election_candidacy"
    SOURCE_CONTRACT = "nec_local_election_candidate_roster"

    def __init__(
        self,
        connector: NecCandidateConnector,
        repository: SqlAlchemyRepository,
        policy: SourcePolicy | None = None,
    ) -> None:
        self.connector = connector
        self.repository = repository
        self.policy = policy or nec_local_election_policy()

    @property
    def scope_key(self) -> str:
        return f"{self.connector.election_id}:{self.connector.election_type}"

    def enumerate(self, *, resume: bool = False) -> NecEnumerationResult:
        if any(
            (
                self.connector.district_name,
                self.connector.province_name,
                self.connector.party,
            )
        ):
            raise NecCandidateCoverageError("L3 NEC candidate enumeration must be unfiltered")
        if self.policy.domain != self.connector.HOST:
            raise PolicyDenied("SourcePolicy domain does not match the NEC candidate connector")
        require_policy(self.policy, PolicyAction.FETCH)
        require_policy(self.policy, PolicyAction.STORE_METADATA)

        self.repository.assert_ready()
        prior_checkpoint = self.repository.source_checkpoint(self.FEEDER, self.scope_key)
        run = self.repository.start_source_run(
            self.FEEDER,
            self.scope_key,
            {
                "source_contract": self.SOURCE_CONTRACT,
                "election_id": self.connector.election_id,
                "election_type": self.connector.election_type,
                "resume": resume,
            },
        )
        pages_committed = 0
        try:
            start_page = 1
            expected_total: int | None = None
            expected_pages: int | None = None
            seen_hashes: dict[str, str] = {}
            page_fingerprints: list[str] = []
            if resume and prior_checkpoint is not None:
                if prior_checkpoint.cursor is None:
                    raise NecCandidateCoverageError("resume checkpoint lacks a page cursor")
                try:
                    start_page = int(prior_checkpoint.cursor) + 1
                    expected_total = int(prior_checkpoint.metadata["total_count"])
                    expected_pages = int(prior_checkpoint.metadata["expected_pages"])
                    seen_hashes = dict(prior_checkpoint.metadata["seen_provider_hashes"])
                    page_fingerprints = list(prior_checkpoint.metadata["page_fingerprints"])
                except (KeyError, TypeError, ValueError):
                    raise NecCandidateCoverageError(
                        "resume checkpoint metadata is invalid"
                    ) from None
                if start_page > expected_pages:
                    raise NecCandidateCoverageError(
                        "resume checkpoint already covers the full NEC candidate scope"
                    )

            page_no = start_page
            while True:
                self.connector.page_no = page_no
                document = self.connector.fetch(self.connector.discover()[0])
                if document.metadata.get("service_name") != "getPofelcddRegistSttusInfoInqire":
                    raise NecCandidateCoverageError("NEC candidate source contract is inconsistent")
                if document.metadata.get("election_id") != self.connector.election_id:
                    raise NecCandidateCoverageError("NEC candidate election id is inconsistent")
                if document.metadata.get("election_type") != str(self.connector.election_type):
                    raise NecCandidateCoverageError("NEC candidate election type is inconsistent")
                if document.metadata.get("page_no") != str(page_no):
                    raise NecCandidateCoverageError("NEC candidate requested page is inconsistent")
                if document.metadata.get("page_size") != str(self.connector.page_size):
                    raise NecCandidateCoverageError(
                        "NEC candidate requested page size is inconsistent"
                    )
                if document.metadata.get("provider_page_no") != str(page_no):
                    raise NecCandidateCoverageError("NEC candidate provider page is inconsistent")
                if document.metadata.get("provider_page_size") != str(self.connector.page_size):
                    raise NecCandidateCoverageError(
                        "NEC candidate provider page size is inconsistent"
                    )
                try:
                    total_count = int(document.metadata["total_count"])
                except (KeyError, TypeError, ValueError):
                    raise NecCandidateCoverageError(
                        "NEC candidate total count is unavailable"
                    ) from None
                if total_count < 0:
                    raise NecCandidateCoverageError(
                        "NEC candidate total count must not be negative"
                    )
                current_expected_pages = max(1, ceil(total_count / self.connector.page_size))
                if expected_total is None:
                    expected_total = total_count
                    expected_pages = current_expected_pages
                elif total_count != expected_total or current_expected_pages != expected_pages:
                    raise NecCandidateCoverageError(
                        "NEC candidate total count changed during enumeration"
                    )
                assert expected_pages is not None
                if page_no > expected_pages:
                    raise NecCandidateCoverageError(
                        "NEC candidate API returned an unexpected extra page"
                    )

                candidates = self.connector.parse_candidates(document)
                expected_row_count = min(
                    self.connector.page_size,
                    max(0, expected_total - ((page_no - 1) * self.connector.page_size)),
                )
                if len(candidates) != expected_row_count:
                    raise NecCandidateCoverageError("NEC candidate page row count is incomplete")

                page_hashes: dict[str, str] = {}
                normalized_by_key: dict[str, dict[str, object]] = {}
                for candidate in candidates:
                    if candidate.election_id != self.connector.election_id:
                        raise NecCandidateCoverageError(
                            "NEC candidate row election id is inconsistent"
                        )
                    if candidate.election_type != self.connector.election_type:
                        raise NecCandidateCoverageError(
                            "NEC candidate row election type is inconsistent"
                        )
                    if candidate.registration_status is None:
                        raise NecCandidateCoverageError(
                            "NEC candidate row registration status is unavailable"
                        )
                    normalized = normalized_nec_candidate(candidate)
                    content_hash = nec_candidate_content_hash(normalized)
                    if candidate.candidate_id in page_hashes:
                        if page_hashes[candidate.candidate_id] != content_hash:
                            raise NecCandidateCoverageError(
                                "conflicting NEC huboid appears within one page"
                            )
                        raise NecCandidateCoverageError(
                            "duplicate NEC huboid appears within one page"
                        )
                    if candidate.candidate_id in seen_hashes:
                        if seen_hashes[candidate.candidate_id] != content_hash:
                            raise NecCandidateCoverageError(
                                "conflicting NEC huboid appears across pages"
                            )
                        raise NecCandidateCoverageError("duplicate NEC huboid appears across pages")
                    page_hashes[candidate.candidate_id] = content_hash
                    normalized_by_key[candidate.candidate_id] = normalized

                fingerprint_payload = json.dumps(
                    sorted(page_hashes.items()),
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
                page_fingerprint = hashlib.sha256(fingerprint_payload.encode("utf-8")).hexdigest()
                if page_fingerprint in page_fingerprints:
                    raise NecCandidateCoverageError(
                        "NEC candidate API returned duplicate page content"
                    )

                ingestion = IngestionPipeline(self.connector).ingest_document(document, self.policy)
                observations = []
                for candidate in candidates:
                    normalized = normalized_by_key[candidate.candidate_id]
                    aliases = [
                        value
                        for value in (candidate.name_hanja,)
                        if value and value != candidate.name_ko
                    ]
                    observations.append(
                        FeederObservation(
                            feeder=self.FEEDER,
                            scope_key=self.scope_key,
                            provider_record_key=candidate.candidate_id,
                            snapshot_id=ingestion.snapshot.id,
                            run_id=run.id,
                            provider_observed_at=_election_observed_at(candidate.election_id),
                            semantic_scope=self.SEMANTIC_SCOPE,
                            identity_hints={
                                "canonical_name": candidate.name_ko,
                                "aliases": aliases,
                                "birth_date": normalized["birth_date"],
                                "external_ids": {"nec_huboid": candidate.candidate_id},
                            },
                            normalized=normalized,
                            content_hash=page_hashes[candidate.candidate_id],
                        )
                    )

                next_seen_hashes = seen_hashes | page_hashes
                next_page_fingerprints = [*page_fingerprints, page_fingerprint]
                checkpoint_metadata = {
                    "page_size": self.connector.page_size,
                    "expected_pages": expected_pages,
                    "total_count": expected_total,
                    "source_contract": self.SOURCE_CONTRACT,
                    "election_id": self.connector.election_id,
                    "election_type": self.connector.election_type,
                    "seen_provider_hashes": next_seen_hashes,
                    "page_fingerprints": next_page_fingerprints,
                }
                self.repository.commit_source_page(
                    run_id=run.id,
                    policy=self.policy,
                    source=ingestion.source,
                    snapshot=ingestion.snapshot,
                    observations=observations,
                    cursor=str(page_no),
                    checkpoint_metadata=checkpoint_metadata,
                )
                pages_committed += 1
                seen_hashes = next_seen_hashes
                page_fingerprints = next_page_fingerprints

                if page_no == expected_pages:
                    if len(seen_hashes) != expected_total:
                        raise NecCandidateCoverageError(
                            "NEC candidate unique record coverage is incomplete"
                        )
                    break
                page_no += 1

            completed = self.repository.finish_source_run(run.id, SourceRunStatus.SUCCESS)
            return NecEnumerationResult(completed, pages_committed, len(seen_hashes))
        except Exception as exc:
            status = SourceRunStatus.PARTIAL if pages_committed else SourceRunStatus.FAILED
            self.repository.finish_source_run(
                run.id,
                status,
                error_code=type(exc).__name__[:120],
                error_summary="NEC candidate enumeration did not complete",
            )
            raise


class LocalElectionStager:
    def __init__(
        self,
        candidate_connector: NecCandidateConnector,
        winner_connector: NecWinnerConnector,
        policy: SourcePolicy | None = None,
    ) -> None:
        if (
            candidate_connector.election_id != winner_connector.election_id
            or candidate_connector.election_type != winner_connector.election_type
        ):
            raise ValueError("candidate and winner connectors must target the same election")
        self.candidate_connector = candidate_connector
        self.winner_connector = winner_connector
        self.policy = policy or nec_local_election_policy()

    def stage(self) -> list[StagedLocalElectionCandidate]:
        if self.policy.domain != self.candidate_connector.HOST:
            raise PolicyDenied("SourcePolicy domain does not match NEC connectors")
        require_policy(self.policy, PolicyAction.FETCH)

        candidate_document = self.candidate_connector.fetch(self.candidate_connector.discover()[0])
        winner_document = self.winner_connector.fetch(self.winner_connector.discover()[0])
        candidates = self.candidate_connector.parse_candidates(candidate_document)
        winners = {
            record.candidate_id: record
            for record in self.winner_connector.parse_winners(winner_document)
        }
        winner_coverage_complete = _coverage_complete(winner_document.metadata)

        staged: list[StagedLocalElectionCandidate] = []
        for record in candidates:
            winner = winners.get(record.candidate_id)
            outcome = (
                "WINNER" if winner else "NOT_WINNER" if winner_coverage_complete else "UNKNOWN"
            )
            staged.append(
                StagedLocalElectionCandidate(
                    candidate=candidate_to_identity(record),
                    candidate_id=record.candidate_id,
                    election_id=record.election_id,
                    election_type=record.election_type,
                    election_type_name=LOCAL_ELECTION_TYPES[record.election_type],
                    district_name=record.district_name,
                    province_name=record.province_name,
                    municipality_name=record.municipality_name,
                    party=record.party,
                    candidate_number=record.candidate_number,
                    candidate_sub_number=record.candidate_sub_number,
                    registration_status=record.registration_status,
                    public_job=record.public_job,
                    submitted_education=record.submitted_education,
                    submitted_careers=record.submitted_careers,
                    outcome=outcome,
                    votes=winner.votes if winner else None,
                    vote_rate=winner.vote_rate if winner else None,
                )
            )
        return staged


def render_local_election_json(items: list[StagedLocalElectionCandidate]) -> str:
    return json.dumps(
        [item.to_dict() for item in items], ensure_ascii=False, indent=2, sort_keys=True
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Stage NEC local-election candidates for review.")
    parser.add_argument("--election-id", required=True)
    parser.add_argument("--type", required=True, type=int, choices=sorted(LOCAL_ELECTION_TYPES))
    parser.add_argument("--province")
    parser.add_argument("--district")
    parser.add_argument("--party")
    parser.add_argument("--page-no", type=int, default=1)
    parser.add_argument("--page-size", type=int, default=100)
    parser.add_argument(
        "--enumerate-candidates",
        action="store_true",
        help="Persist and validate the complete unfiltered candidate roster for this scope.",
    )
    parser.add_argument(
        "--enumerate-winners",
        action="store_true",
        help="Persist and validate the complete unfiltered winner roster for this scope.",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume the selected enumeration; defaults to winners for compatibility.",
    )
    parser.add_argument("--database-url")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.enumerate_candidates and args.enumerate_winners:
        parser.error("select exactly one NEC L3 enumeration mode")
    candidate_mode = bool(args.enumerate_candidates)
    winner_mode = bool(args.enumerate_winners or (args.resume and not candidate_mode))
    if (candidate_mode or winner_mode) and any((args.province, args.district, args.party)):
        parser.error("NEC L3 enumeration does not accept province, district, or party filters")
    try:
        if candidate_mode:
            candidate_connector = NecCandidateConnector(
                election_id=args.election_id,
                election_type=args.type,
                page_no=args.page_no,
                page_size=args.page_size,
            )
            result = LocalElectionCandidateEnumerator(
                candidate_connector,
                SqlAlchemyRepository(args.database_url),
            ).enumerate(resume=args.resume)
            print(
                json.dumps(
                    {
                        "run_id": str(result.run.id),
                        "status": result.run.status.value,
                        "scope_key": result.run.scope_key,
                        "pages_committed": result.pages_committed,
                        "unique_records": result.unique_records,
                    },
                    ensure_ascii=False,
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0
        if winner_mode:
            winner_connector = NecWinnerConnector(
                election_id=args.election_id,
                election_type=args.type,
                page_no=args.page_no,
                page_size=args.page_size,
            )
            result = LocalElectionWinnerEnumerator(
                winner_connector,
                SqlAlchemyRepository(args.database_url),
            ).enumerate(resume=args.resume)
            print(
                json.dumps(
                    {
                        "run_id": str(result.run.id),
                        "status": result.run.status.value,
                        "scope_key": result.run.scope_key,
                        "pages_committed": result.pages_committed,
                        "unique_records": result.unique_records,
                    },
                    ensure_ascii=False,
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0
        candidate_connector = NecCandidateConnector(
            election_id=args.election_id,
            election_type=args.type,
            page_no=args.page_no,
            page_size=args.page_size,
            district_name=args.district,
            province_name=args.province,
            party=args.party,
        )
        winner_connector = NecWinnerConnector(
            election_id=args.election_id,
            election_type=args.type,
            page_no=args.page_no,
            page_size=args.page_size,
            district_name=args.district,
            province_name=args.province,
        )
        staged = LocalElectionStager(candidate_connector, winner_connector).stage()
    except (NecApiError, PolicyDenied, ValueError) as exc:
        parser.error(str(exc))
    print(render_local_election_json(staged))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
