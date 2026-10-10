"""One R-ONE official national month: bounded request and canonical evidence gates."""

from __future__ import annotations

import io
import json
import logging
from pathlib import Path
from urllib.error import URLError
from urllib.parse import parse_qs, urlparse
from urllib.request import Request

import pytest
from alembic import command
from alembic.config import Config

from packages.connectors.reb_market_statistics import (
    L2_REGION,
    RebMarketStatError,
    parse_reb_housing_l2_month,
    reb_housing_l2_policy,
)
from packages.domain.db import SourcePolicyRow
from packages.persistence import SqlAlchemyRepository
from packages.verification.policy import PolicyDenied
from workers.reb_housing_import import (
    FEEDER,
    _NoProviderRedirect,
    capture_one_month,
    commit_one_month,
    fetch_one_month,
    read_issued_key_from_env_file,
    scope_key,
)

MONTH = "202501"
SECRET = "SYNTHETIC_DO_NOT_LEAK_123456789"


class _FakeResponse:
    """Tiny deterministic urllib-compatible page, without a network client."""

    def __init__(self, status: int, body: bytes):
        self.status = status
        self._contents = io.BytesIO(body)

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self._contents.close()

    def read(self, size: int = -1) -> bytes:
        return self._contents.read(size)


def _json_response(body: dict, *, status: int = 200) -> _FakeResponse:
    return _FakeResponse(status, json.dumps(body, ensure_ascii=False).encode())


def _row(*, month: str = MONTH, region: int = 500001, count: int = 64215) -> dict:
    return {
        "STATBL_ID": "A_2024_00546",
        "DTACYCLE_CD": "MM",
        "WRTTIME_IDTFR_ID": month,
        "CLS_ID": region,
        "CLS_NM": "전국",
        "ITM_ID": 100001,
        "ITM_NM": "동(호)수",
        "DTA_VAL": count,
        "UI_NM": "동(호)수",
        "private_provider_unused": "DISCARDED_RAW_NONALLOWLIST",
    }


def _response(rows: list[dict] | None = None, *, total: int = 1) -> dict:
    if rows is None:
        rows = [_row()]
    return {
        "SttsApiTblData": [
            {
                "head": [
                    {"list_total_count": total},
                    {"RESULT": {"CODE": "INFO-000", "MESSAGE": "정상 처리되었습니다."}},
                ]
            },
            {"row": rows},
        ]
    }


def _page():
    return parse_reb_housing_l2_month(
        _response(), month=MONTH, region_code=L2_REGION, policy=reb_housing_l2_policy()
    )


def test_exact_official_query_one_month_and_no_credential_in_records():
    captured = []

    def respond(request: Request) -> _FakeResponse:
        uri = urlparse(request.full_url)
        params = parse_qs(uri.query)
        captured.append({k: list(v) for k, v in params.items() if k != "KEY"})
        assert params["KEY"] == [SECRET]
        assert uri.hostname == "www.reb.or.kr"
        assert uri.path == "/r-one/openapi/SttsApiTblData.do"
        return _json_response(_response())

    page = fetch_one_month(
        month=MONTH,
        policy=reb_housing_l2_policy(),
        key=SECRET,
        opener=respond,
    )
    assert captured == [
        {
            "STATBL_ID": ["A_2024_00546"],
            "DTACYCLE_CD": ["MM"],
            "CLS_ID": ["500001"],
            "ITM_ID": ["100001"],
            "START_WRTTIME": ["202501"],
            "END_WRTTIME": ["202501"],
            "Type": ["json"],
            "pIndex": ["1"],
            "pSize": ["1"],
        }
    ]
    assert page.provider_total_count == page.sampled_row_count == 1
    assert page.publishable is False
    assert page.rows[0].reported_housing_units == 64215
    assert "DISCARDED_RAW_NONALLOWLIST" not in repr(page)


def test_stdlib_client_emits_no_key_at_info_level():
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    root = logging.getLogger()
    previous_level = root.level
    try:
        root.addHandler(handler)
        root.setLevel(logging.INFO)
        page = fetch_one_month(
            month=MONTH,
            policy=reb_housing_l2_policy(),
            key=SECRET,
            opener=lambda _req: _json_response(_response()),
        )
        recorded = stream.getvalue()
    finally:
        root.removeHandler(handler)
        root.setLevel(previous_level)
        handler.close()
    assert page.sampled_row_count == 1
    assert SECRET not in recorded
    assert "KEY=" not in recorded


def test_transport_error_with_secret_url_is_sanitized():
    def failed(_request: Request):
        raise URLError("https://www.reb.or.kr/r-one/openapi/SttsApiTblData.do?KEY=" + SECRET)

    with pytest.raises(RebMarketStatError) as error:
        fetch_one_month(
            month=MONTH,
            policy=reb_housing_l2_policy(),
            key=SECRET,
            opener=failed,
        )
    assert SECRET not in str(error.value)


def test_authenticated_query_must_not_follow_redirects():
    # A provider redirect must never forward the API key to a different host.
    assert (
        _NoProviderRedirect().redirect_request(
            Request("https://www.reb.or.kr/r-one/openapi/SttsApiTblData.do"),
            None,
            302,
            "found",
            {},
            "https://example.net/redirect",
        )
        is None
    )


def test_streaming_response_byte_limit_is_enforced():
    with pytest.raises(RebMarketStatError, match="size outside"):
        fetch_one_month(
            month=MONTH,
            policy=reb_housing_l2_policy(),
            key=SECRET,
            opener=lambda _req: _FakeResponse(200, b"X" * 120001),
        )


@pytest.mark.parametrize("error_status", [400, 403, 429, 500, 302])
def test_http_failures_redact_query_with_secret(error_status: int):
    def respond(_request: Request) -> _FakeResponse:
        return _FakeResponse(error_status, SECRET.encode())

    with pytest.raises(RebMarketStatError) as exc:
        fetch_one_month(
            month=MONTH,
            policy=reb_housing_l2_policy(),
            key=SECRET,
            opener=respond,
        )
    assert SECRET not in str(exc.value)


def test_policy_is_exact_not_domain_or_marker_text():
    p = reb_housing_l2_policy()

    def forbidden(_request: Request) -> _FakeResponse:
        raise AssertionError("network before full policy check")

    for modified in (
        p.model_copy(update={"can_fetch": False}),
        p.model_copy(update={"can_store_fulltext": True}),
        p.model_copy(update={"domain": "apis.data.go.kr"}),
        p.model_copy(update={"policy_note": p.policy_note + " fake approval"}),
        p.model_copy(update={"can_show_excerpt": True}),
    ):
        with pytest.raises(PolicyDenied):
            fetch_one_month(
                month=MONTH,
                policy=modified,
                key=SECRET,
                opener=forbidden,
            )


@pytest.mark.parametrize(
    "month,region,total,rows",
    [
        ("202502", L2_REGION, 1, [_row()]),
        (MONTH, "11110", 1, [_row()]),
        (MONTH, L2_REGION, 20, [_row()]),
        (MONTH, L2_REGION, 0, []),
        (MONTH, L2_REGION, 1, [_row(month="202402")]),
        (MONTH, L2_REGION, 1, [_row(region=510029)]),
    ],
)
def test_exact_month_page_scope_fails_closed(month, region, total, rows):
    with pytest.raises(RebMarketStatError):
        parse_reb_housing_l2_month(
            _response(rows, total=total),
            month=month,
            region_code=region,
            policy=reb_housing_l2_policy(),
        )


def test_missing_issued_key_and_secret_file_permissions(tmp_path: Path):
    credential = tmp_path / "secrets.env"
    credential.write_text("RONE_API_KEY='SYNTHETIC_DO_NOT_LEAK_123456789'\n")
    credential.chmod(0o600)
    assert read_issued_key_from_env_file(credential) == SECRET
    credential.chmod(0o644)
    with pytest.raises(RebMarketStatError):
        read_issued_key_from_env_file(credential)
    credential.chmod(0o600)
    credential.write_text("RONE_API_KEY=abc\nRONE_API_KEY=two\n")
    with pytest.raises(RebMarketStatError):
        read_issued_key_from_env_file(credential)


def _migrated_repo(tmp_path: Path) -> tuple[SqlAlchemyRepository, Path]:
    db = tmp_path / "l2.sqlite"
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db.as_posix()}")
    command.upgrade(cfg, "head")
    repo = SqlAlchemyRepository(f"sqlite:///{db.as_posix()}")
    repo.assert_ready()
    return repo, db


def _register_disposable_policy(repo: SqlAlchemyRepository) -> None:
    """Testing-only registration in a new disposable, migrated database."""
    policy = reb_housing_l2_policy()
    data = policy.model_dump()
    data["id"] = str(policy.id)
    data["collection_mode"] = policy.collection_mode.value
    with repo.sessions() as session:
        session.add(SourcePolicyRow(**data))
        session.commit()


def test_canonical_single_month_capture_idempotent_and_no_person_link(tmp_path: Path):
    repo, db = _migrated_repo(tmp_path)
    policy = reb_housing_l2_policy()
    page = _page()
    with pytest.raises(RebMarketStatError, match="stored"):
        commit_one_month(repo, page=page, month=MONTH, policy=policy)
    assert repo.source_runs(feeder=FEEDER) == []
    _register_disposable_policy(repo)
    first = commit_one_month(repo, page=page, month=MONTH, policy=policy)
    second = commit_one_month(repo, page=page, month=MONTH, policy=policy)
    assert (first["observations_created"], first["observations_unchanged"]) == (1, 0)
    assert (second["observations_created"], second["observations_unchanged"]) == (0, 1)
    assert first["snapshot_id"] == second["snapshot_id"]
    assert first["status"] == second["status"] == "SUCCESS"
    assert repo.source_checkpoint(FEEDER, scope_key(MONTH)).cursor == MONTH
    observations = repo.feeder_observations(FEEDER, scope_key(MONTH))
    assert len(observations) == 1
    obs = observations[0]
    assert obs.identity_hints == {}
    assert obs.normalized["reported_housing_units"] == 64215
    assert obs.normalized["person_linkage"] == "NONE"
    assert obs.normalized["publication"] == "NOT_APPROVED"
    snapshot = repo.source_snapshot(obs.snapshot_id)
    assert snapshot is not None
    assert snapshot.fulltext is None
    assert "KEY" not in json.dumps(snapshot.metadata, ensure_ascii=False)
    source = repo.source(snapshot.source_id)
    assert source is not None
    assert "?" not in str(source.url)
    assert "www.reb.or.kr" in str(source.url)
    assert SECRET.encode() not in db.read_bytes()
    with repo.sessions() as session:
        from sqlalchemy import text

        for name in ("people", "claims", "person_observation_links"):
            assert session.scalar(text(f"SELECT COUNT(*) FROM {name}")) == 0


def test_status_failure_after_committed_page_does_not_write_failed(tmp_path: Path):
    repo, _ = _migrated_repo(tmp_path)
    _register_disposable_policy(repo)
    original = repo.finish_source_run

    def fail_success(run_id, status, **kwargs):
        if status.value == "SUCCESS":
            raise RuntimeError("simulated status write failure")
        return original(run_id, status, **kwargs)

    repo.finish_source_run = fail_success  # type: ignore[method-assign]
    with pytest.raises(RuntimeError, match="status write"):
        commit_one_month(repo, page=_page(), month=MONTH, policy=reb_housing_l2_policy())
    assert len(repo.feeder_observations(FEEDER, scope_key(MONTH))) == 1
    runs = repo.source_runs(FEEDER, scope_key(MONTH))
    assert len(runs) == 1
    assert runs[0].status.value == "RUNNING"


def test_single_month_capture_contains_only_official_allowlist():
    policy = reb_housing_l2_policy()
    src, snapshot, observation = capture_one_month(
        _page(),
        month=MONTH,
        policy=policy,
        run_id=__import__("uuid").uuid4(),
    )
    assert src.policy_id == policy.id
    assert snapshot.content_hash == observation.content_hash
    assert snapshot.metadata["query"] == {
        "STATBL_ID": "A_2024_00546",
        "CLS_ID": "500001",
        "ITM_ID": "100001",
        "DTACYCLE_CD": "MM",
        "START_WRTTIME": "202501",
        "END_WRTTIME": "202501",
        "pIndex": "1",
        "pSize": "1",
    }
    safe_json = json.dumps(
        {"snapshot": snapshot.metadata, "row": observation.normalized}, ensure_ascii=False
    )
    assert "KEY" not in safe_json
    assert "DISCARDED_RAW_NONALLOWLIST" not in safe_json
    assert observation.identity_hints == {}
