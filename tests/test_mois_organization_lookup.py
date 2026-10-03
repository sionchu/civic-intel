"""Synthetic bounded lookup regressions; no live provider data or credentials."""
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

import httpx
import pytest

from packages.connectors.mois_organization_codes import (
    MoisOrganizationCodeConnector,
    mois_organization_code_policy,
)
from packages.domain.enums import SourceRunStatus
from packages.verification.policy import PolicyDenied
from tests.test_batch_mois_organization_codes import migrated_repository, organization_row
from workers.mois_organization_codes import (
    MoisOrganizationCoverageError,
    MoisOrganizationEnumerator,
    MoisOrganizationLookup,
    mois_organization_content_hash,
)

SECRET = "synthetic-lookup-secret"
NAME = "합성검증기관"
CODE = "A123456"


class LookupApi:
    def __init__(self, rows: list[dict], total: int) -> None:
        self.rows, self.total = rows, total
        self.calls = 0
        self.status_code = 200
        self.page_no = 1
        self.extra = ""

    def handle(self, request: httpx.Request) -> httpx.Response:
        self.calls += 1
        assert request.url.params["ServiceKey"] == SECRET
        assert request.url.params["stop_selt"] == "0"
        return httpx.Response(self.status_code, json={"response": {
            "header": {"resultCode": "INFO-0", "ServiceKey": SECRET},
            "body": {"pageNo": self.page_no,
                     "numOfRows": int(request.url.params["numOfRows"]),
                     "totalCount": self.total, "items": {"item": self.rows}},
            "irrelevant_provider_field": self.extra,
        }})

    def connector(self, **kwargs) -> MoisOrganizationCodeConnector:
        return MoisOrganizationCodeConnector(
            api_key=SECRET, transport=httpx.MockTransport(self.handle), **kwargs
        )


def test_partial_name_page_does_not_assert_absence_or_uniqueness(tmp_path: Path) -> None:
    api = LookupApi([organization_row(CODE, NAME + " 하위기관")], 3670)
    repo = migrated_repository(tmp_path / "partial.db")
    worker = MoisOrganizationLookup(api.connector(full_name=NAME, page_size=1), repo,
                                    expected_full_name=NAME)
    result = worker.capture()
    assert api.calls == 1 and result.run.status == SourceRunStatus.SUCCESS
    assert (result.captured_rows, result.provider_total_count) == (1, 3670)
    assert result.exact_name_matches_in_capture == 0
    assert not result.filtered_query_complete
    assert result.coverage == "FIRST_FILTERED_PAGE_ONLY_NOT_L3"
    assert repo.source_checkpoint(MoisOrganizationEnumerator.FEEDER,
                                  MoisOrganizationEnumerator.SCOPE_KEY) is None
    assert repo.people() == [] and repo.organizations() == [] and repo.claims() == []


def test_code_candidate_preserves_exact_chain_minimization_and_manifest(tmp_path: Path) -> None:
    api = LookupApi([organization_row(CODE, NAME)], 1)
    repo = migrated_repository(tmp_path / "code.db")
    worker = MoisOrganizationLookup(api.connector(org_code=CODE, page_size=10), repo,
                                    expected_full_name=NAME)
    result = worker.capture()
    assert api.calls == 1 and result.filtered_query_complete
    assert result.exact_name_matches_in_capture == 1
    checkpoint = repo.source_checkpoint(MoisOrganizationEnumerator.FEEDER, worker.scope_key)
    assert checkpoint is not None and checkpoint.last_run_id == result.run.id
    assert checkpoint.cursor == "1" and checkpoint.metadata["provider_total_count"] == 1
    observations = repo.feeder_observations(MoisOrganizationEnumerator.FEEDER, worker.scope_key)
    assert len(observations) == 1
    row = observations[0]
    context = repo.feeder_observation_contexts([row.id])[row.id]
    _, snapshot, source, policy = context
    assert snapshot.fulltext is None and not policy.can_send_to_ai
    assert row.identity_hints == {}
    assert row.normalized["lookup_source_snapshot_hash"] == snapshot.content_hash
    assert row.content_hash == mois_organization_content_hash(row.normalized)
    assert checkpoint.metadata["row_manifest"] == [
        {"record_key": CODE, "content_hash": row.content_hash}
    ]
    assert SECRET not in str(source.url)
    assert SECRET not in json.dumps(snapshot.model_dump(mode="json"))
    assert SECRET not in json.dumps(row.model_dump(mode="json"))
    aggregate = json.dumps(asdict(result), default=str)
    assert CODE not in aggregate and NAME not in aggregate and SECRET not in aggregate
    assert repo.people() == [] and repo.organizations() == [] and repo.claims() == []


def test_identical_rerun_and_new_source_bytes_keep_immutable_provenance(tmp_path: Path) -> None:
    api = LookupApi([organization_row(CODE, NAME)], 1)
    repo = migrated_repository(tmp_path / "versions.db")
    worker = MoisOrganizationLookup(api.connector(org_code=CODE), repo, expected_full_name=NAME)
    first = worker.capture()
    second = worker.capture()
    assert first.run.observations_created == 1
    assert second.run.observations_created == 0 and second.run.observations_unchanged == 1
    api.extra = "different source bytes, same permitted row fields"
    third = worker.capture()
    assert third.run.observations_created == 1
    rows = repo.feeder_observations(MoisOrganizationEnumerator.FEEDER, worker.scope_key)
    assert len(rows) == 2
    assert len({r.normalized["lookup_source_snapshot_hash"] for r in rows}) == 2
    assert all("irrelevant_provider_field" not in row.normalized for row in rows)
    assert api.calls == 3


def test_empty_filtered_response_is_query_coverage_only(tmp_path: Path) -> None:
    api = LookupApi([], 0)
    repo = migrated_repository(tmp_path / "empty.db")
    result = MoisOrganizationLookup(api.connector(org_code=CODE), repo,
                                    expected_full_name=NAME).capture()
    assert result.filtered_query_complete and result.captured_rows == 0
    assert result.exact_name_matches_in_capture == 0
    assert result.coverage == "FIRST_FILTERED_PAGE_ONLY_NOT_L3"
    assert repo.organizations() == [] and repo.claims() == []


@pytest.mark.parametrize("case", ["duplicate", "wrong_code", "short", "wrong_page", "negative", "http"])
def test_bad_page_fails_before_source_commit_and_without_retry(tmp_path: Path, case: str) -> None:
    api = LookupApi([organization_row(CODE, NAME)], 1)
    if case == "duplicate":
        api.rows *= 2
        api.total = 2
    elif case == "wrong_code":
        api.rows[0]["org_cd"] = "B123456"
    elif case == "short":
        api.total = 2
    elif case == "wrong_page":
        api.page_no = 2
    elif case == "negative":
        api.total = -1
    elif case == "http":
        api.status_code = 503
    repo = migrated_repository(tmp_path / "bad.db")
    worker = MoisOrganizationLookup(api.connector(org_code=CODE), repo, expected_full_name=NAME)
    with pytest.raises(MoisOrganizationCoverageError, match="lookup failed"):
        worker.capture()
    assert api.calls == 1
    assert repo.source_runs()[-1].status == SourceRunStatus.FAILED
    assert repo.source_checkpoint(MoisOrganizationEnumerator.FEEDER, worker.scope_key) is None
    assert repo.sources() == {}
    assert repo.feeder_observations(MoisOrganizationEnumerator.FEEDER, worker.scope_key) == []


@pytest.mark.parametrize("override", [{"can_fetch": False}, {"can_store_metadata": False},
                                     {"domain": "invalid.example"}, {"can_store_fulltext": True},
                                     {"can_send_to_ai": True}])
def test_policy_denial_precedes_run_and_network(tmp_path: Path, override: dict) -> None:
    api = LookupApi([organization_row(CODE, NAME)], 1)
    repo = migrated_repository(tmp_path / "policy.db")
    policy = mois_organization_code_policy().model_copy(update=override)
    worker = MoisOrganizationLookup(api.connector(org_code=CODE), repo,
                                    expected_full_name=NAME, policy=policy)
    with pytest.raises(PolicyDenied):
        worker.capture()
    assert api.calls == 0 and repo.source_runs() == []


@pytest.mark.parametrize("kwargs", [{}, {"full_name": NAME, "org_code": CODE},
                                     {"org_code": CODE, "page_no": 2},
                                     {"org_code": CODE, "page_size": 101},
                                     {"full_name": NAME + " mismatch"}])
def test_invalid_scope_never_opens_repository_or_fetches(kwargs: dict) -> None:
    api = LookupApi([], 0)
    with pytest.raises(MoisOrganizationCoverageError):
        MoisOrganizationLookup(api.connector(**kwargs), None, expected_full_name=NAME)
    assert api.calls == 0


def test_commit_failure_leaves_no_checkpoint_or_source_data(tmp_path: Path, monkeypatch) -> None:
    api = LookupApi([organization_row(CODE, NAME)], 1)
    repo = migrated_repository(tmp_path / "rollback.db")
    worker = MoisOrganizationLookup(api.connector(org_code=CODE), repo, expected_full_name=NAME)

    def reject(**kwargs):
        raise RuntimeError("synthetic commit rejection")

    monkeypatch.setattr(repo.application.acquisition, "commit_source_page", reject)
    with pytest.raises(MoisOrganizationCoverageError):
        worker.capture()
    assert repo.source_runs()[-1].status == SourceRunStatus.FAILED
    assert repo.sources() == {}
    assert repo.source_checkpoint(MoisOrganizationEnumerator.FEEDER, worker.scope_key) is None
