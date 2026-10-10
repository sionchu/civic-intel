"""R-ONE national apartment/land sales: bounded source and canonical storage contract."""

from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from urllib.request import Request

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text

from packages.connectors.reb_market_statistics import (
    REGIONAL_SALE_TABLES,
    RebMarketStatError,
    parse_reb_national_sale_month,
    reb_market_l2_policy,
)
from packages.domain.db import SourcePolicyRow
from packages.persistence import SqlAlchemyRepository
from packages.verification.policy import PolicyDenied
from workers.reb_housing_import import (
    FEEDER,
    SALE_FEEDER,
    capture_one_month,
    commit_one_month,
    fetch_one_sale_month,
    scope_key,
)

SECRET = "DO_NOT_PRINT_FAKE_RONE_SECRET_FOR_TEST_ONLY"
MONTHS = {"apartment_sale": "202607", "land_sale": "202608"}
COUNTS = {"apartment_sale": 50129, "land_sale": 80776}


class _Page:
    def __init__(self, payload: dict, *, status: int = 200):
        self.status = status
        self._json = json.dumps(payload, ensure_ascii=False).encode()

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self, count: int):
        return self._json[:count]


def _provider(
    kind: str,
    month: str,
    *,
    count: int | None = None,
    total: int = 1,
    overrides: dict | None = None,
) -> dict:
    spec = REGIONAL_SALE_TABLES[kind]
    row = {
        "STATBL_ID": spec["statbl_id"],
        "DTACYCLE_CD": "MM",
        "WRTTIME_IDTFR_ID": month,
        "CLS_ID": 500001,
        "CLS_NM": "전국",
        "ITM_ID": 100001,
        "ITM_NM": spec["item_name"],
        "UI_NM": spec["unit"],
        "DTA_VAL": COUNTS[kind] if count is None else count,
        "exact_parcel_location": "SHOULD_DROP",
        "buyer_name": "SHOULD_DROP",
    }
    row.update(overrides or {})
    return {
        "SttsApiTblData": [
            {"head": [{"list_total_count": total}, {"RESULT": {"CODE": "INFO-000"}}]},
            {"row": [row]},
        ]
    }


@pytest.mark.parametrize("kind", ["apartment_sale", "land_sale"])
def test_official_national_sale_api_unit_and_bound_parameters(kind):
    called = []
    month = MONTHS[kind]

    def mock_open(request: Request) -> _Page:
        u = urlsplit(request.full_url)
        qs = parse_qs(u.query)
        called.append(qs)
        assert u.hostname == "www.reb.or.kr"
        assert u.path == "/r-one/openapi/SttsApiTblData.do"
        assert qs["KEY"] == [SECRET]
        assert qs["STATBL_ID"] == [REGIONAL_SALE_TABLES[kind]["statbl_id"]]
        assert qs["CLS_ID"] == ["500001"]
        assert qs["START_WRTTIME"] == qs["END_WRTTIME"] == [month]
        assert qs["pSize"] == qs["pIndex"] == ["1"]
        return _Page(_provider(kind, month))

    page = fetch_one_sale_month(
        kind=kind,
        month=month,
        policy=reb_market_l2_policy(),
        key=SECRET,
        opener=mock_open,
    )
    assert len(called) == 1
    assert page.provider_total_count == page.sampled_row_count == 1
    assert page.rows[0].count == COUNTS[kind]
    assert page.rows[0].region_label == "전국"
    assert page.publishable is False
    assert "SHOULD_DROP" not in repr(page)


@pytest.mark.parametrize("kind", ["apartment_sale", "land_sale"])
@pytest.mark.parametrize(
    "failure",
    [
        {"STATBL_ID": "NO_SUCH_CODE"},
        {"ITM_ID": 100002},
        {"UI_NM": "원"},
        {"CLS_ID": 500002},
        {"CLS_NM": "서울"},
        {"WRTTIME_IDTFR_ID": "202602"},
        {"DTA_VAL": "-9"},
        {"DTA_VAL": "unknown"},
    ],
)
def test_other_source_period_region_or_unit_fails_closed(kind, failure):
    with pytest.raises(RebMarketStatError):
        parse_reb_national_sale_month(
            _provider(kind, MONTHS[kind], overrides=failure),
            kind=kind,
            month=MONTHS[kind],
            policy=reb_market_l2_policy(),
        )


@pytest.mark.parametrize("kind", ["apartment_sale", "land_sale"])
def test_page_total_drift_and_no_key_mode_cannot_promote(kind):
    with pytest.raises(RebMarketStatError):
        parse_reb_national_sale_month(
            _provider(kind, MONTHS[kind], total=5),
            kind=kind,
            month=MONTHS[kind],
            policy=reb_market_l2_policy(),
        )
    with pytest.raises(RebMarketStatError):
        parse_reb_national_sale_month(
            {"RESULT": {"CODE": "INFO-200"}},
            kind=kind,
            month=MONTHS[kind],
            policy=reb_market_l2_policy(),
        )


def _db(tmp_path: Path):
    db = tmp_path / "official-market.sqlite"
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db.as_posix()}")
    command.upgrade(cfg, "head")
    repo = SqlAlchemyRepository(f"sqlite:///{db.as_posix()}")
    repo.assert_ready()
    policy = reb_market_l2_policy()
    data = policy.model_dump()
    data["id"] = str(policy.id)
    data["collection_mode"] = policy.collection_mode.value
    with repo.sessions() as session:
        session.add(SourcePolicyRow(**data))
        session.commit()
    return repo, db


def test_three_source_tables_one_canonical_source_three_snapshots_replay(tmp_path: Path):
    from packages.connectors.reb_market_statistics import parse_reb_housing_l2_month
    from tests.test_reb_housing_l2 import _response

    repo, db = _db(tmp_path)
    policy = reb_market_l2_policy()
    housing = parse_reb_housing_l2_month(
        _response(),
        month="202501",
        region_code="500001",
        policy=policy,
    )
    h1 = commit_one_month(repo, page=housing, month="202501", policy=policy)
    h2 = commit_one_month(repo, page=housing, month="202501", policy=policy)
    assert (h1["observations_created"], h2["observations_unchanged"]) == (1, 1)
    values = []
    for kind, month in MONTHS.items():
        page = parse_reb_national_sale_month(
            _provider(kind, month),
            kind=kind,
            month=month,
            policy=policy,
        )
        first = commit_one_month(
            repo,
            page=page,
            month=month,
            policy=policy,
            kind=kind,
        )
        rerun = commit_one_month(
            repo,
            page=page,
            month=month,
            policy=policy,
            kind=kind,
        )
        assert first["observations_created"] == 1
        assert rerun["observations_unchanged"] == 1
        assert first["snapshot_id"] == rerun["snapshot_id"]
        scoped = scope_key(month, table=REGIONAL_SALE_TABLES[kind]["statbl_id"])
        observation = repo.feeder_observations(SALE_FEEDER, scoped)[0]
        assert observation.normalized["reported_sale_units"] == COUNTS[kind]
        assert observation.normalized["unit"] == REGIONAL_SALE_TABLES[kind]["unit"]
        assert observation.normalized["person_linkage"] == "NONE"
        assert observation.normalized["publication"] == "NOT_APPROVED"
        assert observation.identity_hints == {}
        snapshot = repo.source_snapshot(observation.snapshot_id)
        assert snapshot and snapshot.fulltext is None
        values.append(observation.normalized["reported_sale_units"])
    assert values == [50129, 80776]
    with repo.sessions() as session:
        table_counts = {
            name: session.scalar(text(f"SELECT count(*) FROM {name}"))
            for name in (
                "source_policies",
                "sources",
                "source_snapshots",
                "feeder_observations",
                "source_runs",
                "source_checkpoints",
                "people",
                "claims",
                "person_observation_links",
            )
        }
    assert table_counts == {
        "source_policies": 1,
        "sources": 1,
        "source_snapshots": 3,
        "feeder_observations": 3,
        "source_runs": 6,
        "source_checkpoints": 3,
        "people": 0,
        "claims": 0,
        "person_observation_links": 0,
    }
    assert SECRET.encode() not in db.read_bytes()


def test_old_narrow_l2_policy_blocks_broader_unreviewed_scope(tmp_path: Path):
    repo, _ = _db(tmp_path)
    old = reb_market_l2_policy().model_copy(
        update={"policy_note": "previous only-housing local-review marker"}
    )
    page = parse_reb_national_sale_month(
        _provider("land_sale", "202608"),
        kind="land_sale",
        month="202608",
        policy=reb_market_l2_policy(),
    )
    with pytest.raises(PolicyDenied):
        commit_one_month(repo, page=page, month="202608", policy=old, kind="land_sale")
    assert repo.source_runs(feeder=FEEDER) == []


def test_rejected_query_and_missing_table():
    with pytest.raises(RebMarketStatError):
        fetch_one_sale_month(
            kind="unreviewed_market",
            month="202608",
            policy=reb_market_l2_policy(),
            key=SECRET,
            opener=lambda _request: (_ for _ in ()).throw(AssertionError("bad network")),
        )
    with pytest.raises(RebMarketStatError):
        capture_one_month(
            parse_reb_national_sale_month(
                _provider("land_sale", "202608"),
                kind="land_sale",
                month="202608",
                policy=reb_market_l2_policy(),
            ),
            month="202608",
            policy=reb_market_l2_policy(),
            run_id=__import__("uuid").uuid4(),
            kind="apartment_sale",
        )
