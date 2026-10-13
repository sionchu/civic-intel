"""R-ONE national apartment/land sales: bounded source and canonical storage contract."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from urllib.request import Request

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text

from packages.connectors.reb_market_statistics import (
    L2_SEOUL_REGION,
    REGIONAL_SALE_TABLES,
    RebMarketStatError,
    parse_reb_sale_month,
    reb_market_l2_policy,
    reb_sale_region_labels,
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
SEOUL_COUNTS = {"apartment_sale": 4589, "land_sale": 11282}


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
        parse_reb_sale_month(
            _provider(kind, MONTHS[kind], overrides=failure),
            kind=kind,
            month=MONTHS[kind],
            policy=reb_market_l2_policy(),
        )


@pytest.mark.parametrize("kind", ["apartment_sale", "land_sale"])
def test_page_total_drift_and_no_key_mode_cannot_promote(kind):
    with pytest.raises(RebMarketStatError):
        parse_reb_sale_month(
            _provider(kind, MONTHS[kind], total=5),
            kind=kind,
            month=MONTHS[kind],
            policy=reb_market_l2_policy(),
        )
    with pytest.raises(RebMarketStatError):
        parse_reb_sale_month(
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
        page = parse_reb_sale_month(
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
    page = parse_reb_sale_month(
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
            parse_reb_sale_month(
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


@pytest.mark.parametrize("kind", ["apartment_sale", "land_sale"])
def test_seoul_source_scope_and_bounded_single_month(kind):
    seen: list[dict] = []
    count = SEOUL_COUNTS[kind]

    def opener(request: Request) -> _Page:
        qs = parse_qs(urlsplit(request.full_url).query)
        seen.append(qs)
        assert qs["KEY"] == [SECRET]
        assert qs["CLS_ID"] == ["500002"]
        assert qs["STATBL_ID"] == [REGIONAL_SALE_TABLES[kind]["statbl_id"]]
        assert qs["START_WRTTIME"] == qs["END_WRTTIME"] == ["202608"]
        assert qs["pIndex"] == qs["pSize"] == ["1"]
        return _Page(
            _provider(
                kind,
                "202608",
                count=count,
                overrides={"CLS_ID": 500002, "CLS_NM": "서울"},
            )
        )

    page = fetch_one_sale_month(
        kind=kind,
        month="202608",
        region_code=L2_SEOUL_REGION,
        policy=reb_market_l2_policy(),
        key=SECRET,
        opener=opener,
    )
    assert len(seen) == 1
    assert page.provider_total_count == page.sampled_row_count == 1
    assert page.rows[0].count == count
    assert page.rows[0].region_label == "서울"
    assert page.publishable is False
    assert "SHOULD_DROP" not in repr(page)


@pytest.mark.parametrize("kind", ["apartment_sale", "land_sale"])
@pytest.mark.parametrize(
    ("code", "label"),
    [(500001, "전국"), (500003, "부산"), (500002, "전국"), (500018, "(구)제주"), (500019, "제주")],
)
def test_seoul_provider_scope_drift_blocks_capture(kind, code, label):
    with pytest.raises(RebMarketStatError):
        parse_reb_sale_month(
            _provider(kind, "202608", overrides={"CLS_ID": code, "CLS_NM": label}),
            kind=kind,
            month="202608",
            region_code=L2_SEOUL_REGION,
            policy=reb_market_l2_policy(),
        )


def test_historical_provider_code_and_housing_seoul_scope_still_forbidden():
    with pytest.raises(RebMarketStatError):
        scope_key("202608", region_code="500002")  # housing remains national
    with pytest.raises(RebMarketStatError):
        fetch_one_sale_month(
            kind="land_sale",
            month="202608",
            region_code="500006",  # historic Gwangju/Jeonnam classification
            policy=reb_market_l2_policy(),
            key=SECRET,
            opener=lambda _: (_ for _ in ()).throw(AssertionError("unexpected HTTP")),
        )
    with pytest.raises(RebMarketStatError):
        fetch_one_sale_month(
            kind="apartment_sale",
            month="202607",
            region_code="500003",  # province pilot is 202608 only
            policy=reb_market_l2_policy(),
            key=SECRET,
            opener=lambda _: (_ for _ in ()).throw(AssertionError("unexpected HTTP")),
        )


def test_seoul_both_sale_tables_share_source_but_not_observations(tmp_path: Path):
    repo, db = _db(tmp_path)
    policy = reb_market_l2_policy()
    for kind, count in SEOUL_COUNTS.items():
        table = REGIONAL_SALE_TABLES[kind]["statbl_id"]
        page = parse_reb_sale_month(
            _provider(kind, "202608", count=count, overrides={"CLS_ID": 500002, "CLS_NM": "서울"}),
            kind=kind,
            month="202608",
            region_code=L2_SEOUL_REGION,
            policy=policy,
        )
        first = commit_one_month(repo, page=page, month="202608", policy=policy, kind=kind)
        replay = commit_one_month(repo, page=page, month="202608", policy=policy, kind=kind)
        assert (first["observations_created"], replay["observations_unchanged"]) == (1, 1)
        assert first["snapshot_id"] == replay["snapshot_id"]
        scoped = scope_key("202608", table=table, region_code=L2_SEOUL_REGION)
        row = repo.feeder_observations(SALE_FEEDER, scoped)[0]
        assert row.normalized["reported_sale_units"] == count
        assert row.normalized["region_code"] == "500002"
        assert row.normalized["coverage"] == "ONE_SEOUL_MONTH_ONLY_NO_MAP_RELEASE"
        assert row.normalized["publication"] == "NOT_APPROVED"
        assert row.identity_hints == {}
        snap = repo.source_snapshot(row.snapshot_id)
        assert snap and snap.fulltext is None
        assert snap.metadata["query"]["CLS_ID"] == "500002"
        source = repo.source(snap.source_id)
        assert source and "?" not in str(source.url)
    with repo.sessions() as session:
        counts = {
            table: session.scalar(text(f"SELECT COUNT(*) FROM {table}"))
            for table in (
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
    assert counts == {
        "source_policies": 1,
        "sources": 1,
        "source_snapshots": 2,
        "feeder_observations": 2,
        "source_runs": 4,
        "source_checkpoints": 2,
        "people": 0,
        "claims": 0,
        "person_observation_links": 0,
    }
    assert SECRET.encode() not in db.read_bytes()


def test_forged_negative_sale_page_denied_before_source_run(tmp_path: Path):
    repo, _ = _db(tmp_path)
    policy = reb_market_l2_policy()
    page = parse_reb_sale_month(
        _provider("land_sale", "202608", overrides={"CLS_ID": 500002, "CLS_NM": "서울"}),
        kind="land_sale",
        month="202608",
        region_code=L2_SEOUL_REGION,
        policy=policy,
    )
    forged = replace(page, rows=(replace(page.rows[0], count=-1),))
    with pytest.raises(RebMarketStatError, match="nonnegative"):
        commit_one_month(repo, page=forged, month="202608", policy=policy, kind="land_sale")
    assert repo.source_runs(feeder=SALE_FEEDER) == []


@pytest.mark.parametrize("kind", ["apartment_sale", "land_sale"])
def test_exact_15_provinces_from_official_table_catalog_not_map_geometry(kind):
    mapping = reb_sale_region_labels(kind)
    assert len(mapping) == 16  # National + 15 unambiguous, no Gwangju/Jeonnam aliases.
    assert mapping["500001"] == "전국"
    assert mapping["500002"] == "서울"
    assert mapping["500003"] == "부산"
    assert "500006" not in mapping
    assert "500015" not in mapping
    assert all(
        label not in ("전남광주>(구)광주", "전남광주>(구)전남") for label in mapping.values()
    )
    if kind == "apartment_sale":
        assert mapping["500019"] == "제주"
        assert "500018" not in mapping  # (구)제주 is historical.
    else:
        assert mapping["500018"] == "제주"
        assert "500019" not in mapping


@pytest.mark.parametrize("kind", ["apartment_sale", "land_sale"])
def test_province_month_one_row_official_code_and_identity_separation(kind):
    region = "500003"
    month = "202608"
    label = reb_sale_region_labels(kind)[region]
    page = parse_reb_sale_month(
        _provider(kind, month, count=123, overrides={"CLS_ID": int(region), "CLS_NM": label}),
        kind=kind,
        month=month,
        region_code=region,
        policy=reb_market_l2_policy(),
    )
    assert page.rows[0].count == 123
    source, snap, obs = capture_one_month(
        page,
        month=month,
        kind=kind,
        policy=reb_market_l2_policy(),
        run_id=__import__("uuid").uuid4(),
    )
    assert obs.normalized["coverage"] == "ONE_PROVIDER_PROVINCE_MONTH_NO_GEOGRAPHY_JOIN_OR_RELEASE"
    assert obs.identity_hints == {}
    assert obs.normalized["person_linkage"] == "NONE"
    assert obs.normalized["publication"] == "NOT_APPROVED"
    assert snap.fulltext is None
    assert "?" not in str(source.url)
    assert obs.normalized["region_code"] == region
    assert obs.normalized["region_label"] == label


@pytest.mark.parametrize("kind", ["apartment_sale", "land_sale"])
def test_province_bad_month_and_ambiguous_names_blocked_pre_http(kind):
    for region, month in [("500003", "202607"), ("500006", "202608"), ("500015", "202608")]:
        with pytest.raises(RebMarketStatError):
            fetch_one_sale_month(
                kind=kind,
                month=month,
                region_code=region,
                policy=reb_market_l2_policy(),
                key=SECRET,
                opener=lambda _req: (_ for _ in ()).throw(AssertionError("unexpected request")),
            )
    with pytest.raises(RebMarketStatError):
        parse_reb_sale_month(
            _provider(kind, "202608", overrides={"CLS_ID": 500003, "CLS_NM": "서울"}),
            kind=kind,
            month="202608",
            region_code="500003",
            policy=reb_market_l2_policy(),
        )


def test_jeju_different_official_identifiers_never_interchanged():
    assert scope_key("202608", table="A_2024_00554", region_code="500019")
    assert scope_key("202608", table="A_2024_00536", region_code="500018")
    for table, wrong in (("A_2024_00554", "500018"), ("A_2024_00536", "500019")):
        with pytest.raises(RebMarketStatError):
            scope_key("202608", table=table, region_code=wrong)


def test_province_cross_kind_single_source_no_person_claims(tmp_path: Path):
    repo, db = _db(tmp_path)
    policy = reb_market_l2_policy()
    for kind, region_code in (("apartment_sale", "500019"), ("land_sale", "500018")):
        page = parse_reb_sale_month(
            _provider(
                kind,
                "202608",
                count=42,
                overrides={
                    "CLS_ID": int(region_code),
                    "CLS_NM": "제주",
                },
            ),
            kind=kind,
            month="202608",
            region_code=region_code,
            policy=policy,
        )
        first = commit_one_month(repo, page=page, month="202608", policy=policy, kind=kind)
        rerun = commit_one_month(repo, page=page, month="202608", policy=policy, kind=kind)
        assert first["observations_created"] == 1 and rerun["observations_unchanged"] == 1
        assert first["snapshot_id"] == rerun["snapshot_id"]
    with repo.sessions() as session:
        counts = {
            table: session.scalar(text(f"SELECT COUNT(*) FROM {table}"))
            for table in (
                "sources",
                "source_snapshots",
                "feeder_observations",
                "source_runs",
                "people",
                "claims",
                "person_observation_links",
            )
        }
    assert counts == {
        "sources": 1,
        "source_snapshots": 2,
        "feeder_observations": 2,
        "source_runs": 4,
        "people": 0,
        "claims": 0,
        "person_observation_links": 0,
    }
    assert SECRET.encode() not in db.read_bytes()


@pytest.mark.parametrize("change", ["append", "crlf"])
def test_changed_official_region_catalog_blocks_all_new_queries_before_http(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    change: str,
):
    from packages.connectors import reb_market_statistics as market

    fake = tmp_path / "changed-catalog.json"
    raw = market._SOURCE_CODE_CATALOG.read_bytes()
    changed = raw + b"\n" if change == "append" else raw.replace(b"\n", b"\r\n")
    assert changed != raw
    fake.write_bytes(changed)
    monkeypatch.setattr(market, "_SOURCE_CODE_CATALOG", fake)
    with pytest.raises(RebMarketStatError, match="digest changed"):
        fetch_one_sale_month(
            kind="apartment_sale",
            month="202608",
            region_code="500003",
            policy=reb_market_l2_policy(),
            key=SECRET,
            opener=lambda _req: (_ for _ in ()).throw(AssertionError("no HTTP permitted")),
        )


def test_older_national_and_seoul_month_review_scope_remains_compatible():
    # The newly added 202608 hard window applies only to the 13 additional
    # province codes; earlier nationwide and Seoul monthly queries retain
    # their existing reviewed per-call historical scope.
    assert scope_key("202607", table="A_2024_00554", region_code="500001")
    assert scope_key("202608", table="A_2024_00536", region_code="500001")
    assert scope_key("202607", table="A_2024_00554", region_code="500002")
    assert scope_key("202608", table="A_2024_00536", region_code="500002")
    with pytest.raises(RebMarketStatError):
        scope_key("202607", table="A_2024_00554", region_code="500003")
