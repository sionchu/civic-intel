from __future__ import annotations

from pathlib import Path

import httpx
import pytest
from alembic import command
from alembic.config import Config

from packages.connectors.mois_organization_codes import (
    MoisOrganizationCodeApiError,
    MoisOrganizationCodeConnector,
    mois_organization_code_policy,
)
from packages.domain.enums import SourceCollectionMode, SourceRunStatus
from packages.verification.policy import PolicyDenied
from tests.support import ScenarioDatabase
from workers.mois_organization_codes import (
    MoisOrganizationCoverageError,
    MoisOrganizationEnumerator,
)

SECRET = "mois-batch-secret-must-not-persist"
SCOPE = "current:stop_selt=0"


def organization_row(code: str, name: str) -> dict[str, str]:
    return {
        "org_cd": code,
        "full_nm": name,
        "low_nm": name,
        "abbr_nm": "",
        "gap_no": "1",
        "rank_no": "001",
        "sub_chasu": "0",
        "high_cd": code,
        "highst_cd": code,
        "rep_cd": code,
        "typebig_nm": "테스트대분류",
        "typemid_nm": "테스트중분류",
        "typesml_nm": "테스트소분류",
        "locatstd_cd": "",
        "use_cd": code,
        "crt_de": "20200101",
        "cls_de": "",
        "stop_selt": "0",
        "chg_de": "20260101",
        "base_date": "20260101",
        "adpt_date": "20260101",
        "preorg_cd": "",
    }


class MoisApi:
    def __init__(self, pages: dict[int, list[dict[str, str]]]) -> None:
        self.pages = pages
        self.fail_pages: set[int] = set()
        self.calls: list[int] = []

    def handle(self, request: httpx.Request) -> httpx.Response:
        assert request.url.params["ServiceKey"] == SECRET
        assert request.url.params["stop_selt"] == "0"
        page = int(request.url.params["pageNo"])
        page_size = int(request.url.params["numOfRows"])
        self.calls.append(page)
        if page in self.fail_pages:
            return httpx.Response(503, text="synthetic provider failure")
        rows = self.pages.get(page, [])
        total = sum(len(items) for items in self.pages.values())
        return httpx.Response(
            200,
            json={
                "response": {
                    "header": {"resultCode": "INFO-0", "resultMsg": "NORMAL SERVICE"},
                    "body": {
                        "pageNo": page,
                        "numOfRows": page_size,
                        "totalCount": total,
                        "items": {"item": rows[:page_size]},
                    },
                }
            },
        )

    def connector(self, *, page_size: int = 2) -> MoisOrganizationCodeConnector:
        return MoisOrganizationCodeConnector(
            api_key=SECRET, page_size=page_size, transport=httpx.MockTransport(self.handle)
        )


def three_org_api() -> MoisApi:
    return MoisApi(
        {
            1: [
                organization_row("1741000", "행정안전부"),
                organization_row("B555544", "비숫자기관코드"),
            ],
            2: [organization_row("1Z00189", "영숫자기관코드")],
        }
    )


def migrated_repository(database: Path) -> ScenarioDatabase:
    database_url = f"sqlite:///{database.as_posix()}"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(config, "head")
    return ScenarioDatabase(database_url)


def enumerator(
    api: MoisApi, repository: ScenarioDatabase, *, policy=None
) -> MoisOrganizationEnumerator:
    return MoisOrganizationEnumerator(api.connector(), repository, policy=policy, max_pages=10)


def test_full_current_universe_is_complete_minimized_and_not_materialized(tmp_path: Path) -> None:
    api = three_org_api()
    repository = migrated_repository(tmp_path / "mois-full.db")
    worker = enumerator(api, repository)
    result = worker.enumerate()
    assert result.run.status == SourceRunStatus.SUCCESS
    assert worker.connector.page_no == 1
    assert result.pages_committed == 2
    assert result.unique_records == 3
    assert api.calls == [1, 2]
    checkpoint = repository.source_checkpoint(MoisOrganizationEnumerator.FEEDER, SCOPE)
    assert checkpoint is not None
    assert checkpoint.cursor == "2"
    assert checkpoint.metadata["total_count"] == 3
    assert checkpoint.metadata["expected_pages"] == 2
    assert checkpoint.metadata["page_size"] == 2
    assert checkpoint.metadata["seen_provider_count"] == 3
    assert len(checkpoint.metadata["seen_provider_manifest_sha256"]) == 64
    assert len(checkpoint.metadata["page_fingerprints"]) == 2
    assert "seen_provider_hashes" not in checkpoint.metadata
    observations = repository.feeder_observations(MoisOrganizationEnumerator.FEEDER, SCOPE)
    assert [item.provider_record_key for item in observations] == ["1741000", "B555544", "1Z00189"]
    assert observations[1].identity_hints["record_kind"] == "organization_registry_record"
    assert observations[1].identity_hints["external_ids"] == {"mois_org_cd": "B555544"}
    assert observations[1].identity_hints["materialization"] == "REVIEW_ONLY"
    assert observations[1].provider_observed_at is not None
    assert observations[1].provider_observed_at.date().isoformat() == "2026-01-01"
    assert (
        observations[1].normalized["identity_semantics"]
        == "PROVIDER_ORGANIZATION_KEY_NOT_CANONICAL_ORGANIZATION"
    )
    assert repository.organizations() == []


def test_unchanged_rerun_is_idempotent_and_changed_row_creates_version(tmp_path: Path) -> None:
    api = three_org_api()
    repository = migrated_repository(tmp_path / "mois-versions.db")
    worker = enumerator(api, repository)
    first = worker.enumerate()
    second = worker.enumerate()
    api.pages[1][0] = organization_row("1741000", "행정안전부 변경")
    changed = worker.enumerate()
    assert first.run.observations_created == 3
    assert second.run.observations_created == 0
    assert second.run.observations_unchanged == 3
    assert changed.run.observations_created == 1
    assert changed.run.observations_unchanged == 2
    versions = repository.feeder_observations(MoisOrganizationEnumerator.FEEDER, SCOPE, "1741000")
    assert len(versions) == 2
    assert {item.normalized["full_name"] for item in versions} == {"행정안전부", "행정안전부 변경"}


def test_partial_failure_resumes_from_committed_manifest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    api = three_org_api()
    api.fail_pages.add(2)
    repository = migrated_repository(tmp_path / "mois-resume.db")
    worker = enumerator(api, repository)
    with pytest.raises(MoisOrganizationCodeApiError):
        worker.enumerate()
    partial = repository.source_runs(MoisOrganizationEnumerator.FEEDER, SCOPE)[-1]
    checkpoint = repository.source_checkpoint(MoisOrganizationEnumerator.FEEDER, SCOPE)
    assert partial.status == SourceRunStatus.PARTIAL
    assert checkpoint is not None
    assert checkpoint.cursor == "1"
    assert checkpoint.metadata["seen_provider_count"] == 2
    manifest = repository.feeder_observation_hash_manifest(MoisOrganizationEnumerator.FEEDER, SCOPE)
    assert len(manifest) == 2
    assert len({provider_record_key for provider_record_key, _ in manifest}) == 2

    def forbid_full_observation_load(*args, **kwargs):
        pytest.fail("MOIS resume must not load full observation rows")

    monkeypatch.setattr(repository, "feeder_observations", forbid_full_observation_load)
    api.fail_pages.clear()
    resumed = worker.enumerate(resume=True)
    assert resumed.run.status == SourceRunStatus.SUCCESS
    assert resumed.pages_committed == 1
    assert resumed.unique_records == 3
    assert api.calls[-1] == 2


def test_resume_after_success_is_rejected(tmp_path: Path) -> None:
    api = three_org_api()
    repository = migrated_repository(tmp_path / "mois-success.db")
    worker = enumerator(api, repository)
    worker.enumerate()
    with pytest.raises(MoisOrganizationCoverageError, match="before the first successful"):
        worker.enumerate(resume=True)


def test_duplicate_org_code_across_pages_fails_closed(tmp_path: Path) -> None:
    api = MoisApi(
        {
            1: [organization_row("1741000", "행정안전부")],
            2: [organization_row("1741000", "행정안전부")],
        }
    )
    repository = migrated_repository(tmp_path / "mois-duplicate.db")
    with pytest.raises(MoisOrganizationCoverageError, match="duplicate MOIS org_cd"):
        MoisOrganizationEnumerator(api.connector(page_size=1), repository, max_pages=10).enumerate()
    assert repository.source_runs()[-1].status == SourceRunStatus.PARTIAL


def test_policy_denial_happens_before_network_or_run(tmp_path: Path) -> None:
    api = three_org_api()
    repository = migrated_repository(tmp_path / "mois-policy.db")
    blocked = mois_organization_code_policy().model_copy(
        update={"collection_mode": SourceCollectionMode.BLOCKED, "can_fetch": False}
    )
    with pytest.raises(PolicyDenied):
        enumerator(api, repository, policy=blocked).enumerate()
    assert api.calls == []
    assert repository.source_runs() == []


def test_schema_0007_blocks_mois_l3_write_before_network(tmp_path: Path) -> None:
    database = tmp_path / "mois-schema-0007.db"
    database_url = f"sqlite:///{database.as_posix()}"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(config, "0007")
    repository = ScenarioDatabase(database_url)
    api = three_org_api()
    with pytest.raises(MoisOrganizationCoverageError, match="revision 0008"):
        enumerator(api, repository).enumerate()
    assert api.calls == []
    assert repository.source_runs() == []


def test_zero_result_current_scope_fails_closed(tmp_path: Path) -> None:
    repository = migrated_repository(tmp_path / "mois-empty.db")
    api = MoisApi({})
    with pytest.raises(MoisOrganizationCoverageError, match="must not be empty"):
        enumerator(api, repository).enumerate()
    run = repository.source_runs(MoisOrganizationEnumerator.FEEDER, SCOPE)[-1]
    assert run.status == SourceRunStatus.FAILED
    assert repository.source_checkpoint(MoisOrganizationEnumerator.FEEDER, SCOPE) is None
