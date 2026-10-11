"""Official R-ONE statistical classification snapshots, not a released geo crosswalk."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

CATALOG = Path(__file__).resolve().parents[1] / "docs/architecture/reb-provincial-code-catalog.json"


def _regions(kind: str) -> list[dict]:
    snapshot = json.loads(CATALOG.read_text("utf-8"))
    assert snapshot["geo_join_allowed"] is False
    return snapshot["tables"][kind]["regions"]


@pytest.mark.parametrize(
    ("kind", "table", "top_count"),
    [
        ("apartment_sale", "A_2024_00554", 19),
        ("land_sale", "A_2024_00536", 18),
    ],
)
def test_stat_table_specific_region_ids_are_official_and_all_geojoin_blocked(
    kind: str,
    table: str,
    top_count: int,
):
    catalog = json.loads(CATALOG.read_text("utf-8"))
    assert catalog["source_url"] == (
        "https://www.reb.or.kr/r-one/portal/openapi/selectOpenApiItmCd.do"
    )
    source = catalog["tables"][kind]
    assert source["statbl_id"] == table
    assert source["top_level_count"] == top_count
    assert len(source["response_sha256"]) == 64
    assert source["item_id"] == "100001"
    rows = _regions(kind)
    assert len(rows) == top_count
    assert len({row["cls_id"] for row in rows}) == top_count
    for row in rows:
        assert len(row["cls_id"]) == 6
        assert row["cls_id"].startswith("5000")
        assert row["provider_lawd_cd"].isdigit()
        assert row["geography_join_approved"] is False
        assert row["label_as_published"] != ""
    assert any(row["cls_id"] == "500001" for row in rows)


def test_jeju_table_code_differs_and_old_code_never_falls_back():
    apt = _regions("apartment_sale")
    land = _regions("land_sale")
    apt_jeju_new = [
        x for x in apt if x["provider_lawd_cd"] == "50000000" and not x["legacy_or_ambiguous"]
    ]
    land_jeju = [
        x for x in land if x["provider_lawd_cd"] == "50000000" and not x["legacy_or_ambiguous"]
    ]
    assert len(apt_jeju_new) == len(land_jeju) == 1
    assert apt_jeju_new[0]["cls_id"] == "500019"
    assert land_jeju[0]["cls_id"] == "500018"
    apt_jeju_old = [x for x in apt if x["cls_id"] == "500018"]
    assert len(apt_jeju_old) == 1
    assert apt_jeju_old[0]["provider_lawd_cd"] == "49000000"
    assert apt_jeju_old[0]["legacy_or_ambiguous"] is True


def test_legacy_ambiguous_regions_remain_unknown_for_public_map():
    for kind in ("apartment_sale", "land_sale"):
        rows = _regions(kind)
        flagged = [r for r in rows if r["legacy_or_ambiguous"]]
        assert len(flagged) >= 2
        assert all(not r["geography_join_approved"] for r in flagged)
        assert any("광주" in r["label_as_published"] for r in flagged)


def test_official_seoul_code_both_sale_tables_without_geometry_join():
    for kind in ("apartment_sale", "land_sale"):
        seoul = [r for r in _regions(kind) if r["cls_id"] == "500002"]
        assert len(seoul) == 1
        assert seoul[0]["label_as_published"] == "서울"
        assert seoul[0]["provider_lawd_cd"] == "11000000"
        assert seoul[0]["geography_join_approved"] is False
