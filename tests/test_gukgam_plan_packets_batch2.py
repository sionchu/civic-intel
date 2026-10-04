"""Agent-prepared (REVIEW_REQUIRED) plan packets for nine more 2026 Gukgam committees.

The packets were transcribed from the official 국정감사계획서 PDF attachments captured on
2026-10-04. They are *not* human-reviewed: the importer refuses them until a reviewer flips
``review_status`` and supplies the page-level ``rights_mark``. These tests pin counts, the
official locators and the known exclusions, and rehearse the importer on synthetic bytes.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

import pytest

from packages.connectors.gukgam_reviewed_packet import (
    GukgamReviewedPacketError,
    parse_reviewed_gukgam_plan_packet,
)
from packages.verification.gukgam_reviewed_plan_import import (
    ReviewedGukgamArtifactProof,
    build_reviewed_gukgam_plan_capture,
)
from workers.gukgam_reviewed_plan_import import main

FIXTURES = Path("tests/fixtures")
PROVENANCE = json.loads(
    (FIXTURES / "gukgam_2026_plan_batch2_provenance.json").read_text(encoding="utf-8")
)
BY_SLUG = {item["slug"]: item for item in PROVENANCE["packets"]}
ARTIFACT_BYTES = b"synthetic-artifact-bytes-not-the-real-pdf\n"
SYNTHETIC_RIGHTS = "SYNTHETIC_DRY_RUN_ONLY"

# slug -> (committee, schedule rows, audited-target mentions, excluded entries, audit dates)
EXPECTED = {
    "legislation": ("법제사법위원회", 15, 88, 6, 10),
    "policy": ("정무위원회", 8, 29, 10, 8),
    "education": ("교육위원회", 9, 69, 5, 7),
    "foreign": ("외교통일위원회", 3, 18, 3, 3),
    "industry": ("산업통상자원중소벤처기업위원회", 8, 44, 1, 8),
    "health": ("보건복지위원회", 8, 53, 9, 7),
    "climate": ("기후에너지환경노동위원회", 9, 104, 8, 9),
    "land": ("국토교통위원회", 8, 36, 5, 8),
    "intelligence": ("정보위원회", 5, 5, 1, 3),
}


def _draft(slug: str) -> dict:
    path = FIXTURES / f"gukgam_2026_{slug}_plan_reviewed_packet.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _promoted_for_test(slug: str) -> dict:
    """Synthetic stand-in for the human review step: status and rights mark only."""

    raw = copy.deepcopy(_draft(slug))
    raw["review_status"] = "HUMAN_REVIEWED"
    raw["source"]["rights_mark"] = SYNTHETIC_RIGHTS
    return raw


def _dates(raw: dict) -> list[str]:
    return [row["audit_date"] for row in raw["schedule"]]


def test_all_nine_committees_are_covered_by_provenance() -> None:
    assert set(BY_SLUG) == set(EXPECTED)
    assert PROVENANCE["page_number_convention"].startswith("1-based PDF page index")
    assert "no human review is claimed" in PROVENANCE["review_status_note"]


@pytest.mark.parametrize("slug", sorted(EXPECTED))
def test_draft_is_review_required_and_cannot_be_imported(slug: str) -> None:
    raw = _draft(slug)

    assert raw["review_status"] == "REVIEW_REQUIRED"
    assert raw["source"]["rights_mark"] is None
    assert raw["witness_rows_included"] is False
    with pytest.raises(GukgamReviewedPacketError, match="not human-reviewed"):
        parse_reviewed_gukgam_plan_packet(raw)

    # Flipping the status alone is not enough: the page-level rights mark is unverified.
    raw["review_status"] = "HUMAN_REVIEWED"
    with pytest.raises(GukgamReviewedPacketError, match="source.rights_mark"):
        parse_reviewed_gukgam_plan_packet(raw)


@pytest.mark.parametrize("slug", sorted(EXPECTED))
def test_source_locators_match_the_official_post_and_pdf_attachment(slug: str) -> None:
    source = _draft(slug)["source"]
    prov = BY_SLUG[slug]
    detail = urlparse(source["detail_url"])
    attachment = urlparse(prov["attachment_url"])
    query = parse_qs(attachment.query)

    assert source["committee_name"] == EXPECTED[slug][0] == prov["committee_name"]
    assert source["automation_gate"] == "AUTOMATED_COMMITTEE_HTML_BLOCKED"
    assert source["detail_url"] == prov["page_url"]
    assert detail.scheme == "https" and (detail.hostname or "").endswith(".na.go.kr")
    assert parse_qs(detail.query)["nttId"] == [source["ntt_id"]]
    assert attachment.hostname == detail.hostname
    assert query["atchFileId"] == [source["atch_file_id"]]
    assert query["fileSn"] == [str(source["file_sn"])]
    assert {"key", "authkey", "servicekey", "token"}.isdisjoint(k.casefold() for k in query)
    assert source["published_date"] == prov["posted_date"]
    assert source["title"] == prov["post_title"]
    assert source["attachment_filename"] == prov["attachment_filename"]
    assert source["attachment_filename"].endswith(".pdf")  # PDF preferred over HWP
    assert re.fullmatch(r"[0-9a-f]{64}", prov["attachment_sha256"])
    assert (
        prov["hwp_crosscheck"]["targets_found_in_hwp_text"]
        == prov["hwp_crosscheck"]["targets_checked"]
    )
    assert prov["hwp_crosscheck"]["attachment_url"].endswith("fileSn=1")


@pytest.mark.parametrize("slug", sorted(EXPECTED))
def test_schedule_counts_dates_and_pages_are_pinned(slug: str) -> None:
    committee, rows, mentions, excluded, n_dates = EXPECTED[slug]
    raw = _promoted_for_test(slug)
    packet = parse_reviewed_gukgam_plan_packet(raw)
    prov = BY_SLUG[slug]

    assert packet.source.committee_name == committee
    assert len(packet.schedule) == rows == prov["schedule_rows"]
    assert sum(len(row.audited_targets) for row in packet.schedule) == mentions
    assert mentions == prov["audited_target_mentions"]
    assert len(prov["excluded"]) == excluded
    assert len(set(_dates(raw))) == n_dates
    assert _dates(raw) == sorted(_dates(raw))
    assert all(date.startswith("2026-10-") for date in _dates(raw))
    assert all(1 <= row.page_number <= prov["pdf_pages"] for row in packet.schedule)
    assert sorted({row.page_number for row in packet.schedule}) == prov["schedule_pages"]
    assert packet.witness_rows_included is False
    for row in packet.schedule:
        assert row.audited_targets
        assert not any(t.startswith(("*", "-", "o ", "◦")) for t in row.audited_targets)
        assert "자료정리" not in row.audited_targets and "휴일" not in row.audited_targets


@pytest.mark.parametrize("slug", sorted(EXPECTED))
def test_importer_accepts_official_attachment_url_for_synthetic_bytes(slug: str) -> None:
    packet = parse_reviewed_gukgam_plan_packet(_promoted_for_test(slug))
    proof = ReviewedGukgamArtifactProof.from_bytes(
        packet,
        attachment_url=BY_SLUG[slug]["attachment_url"],
        artifact_bytes=ARTIFACT_BYTES,
    )
    capture = build_reviewed_gukgam_plan_capture(packet, artifact=proof)

    assert capture.scope_key == f"2026:{EXPECTED[slug][0]}"
    assert len(capture.observations(uuid4())) == EXPECTED[slug][1]


@pytest.mark.parametrize("slug", sorted(EXPECTED))
def test_worker_dry_run_counts_without_database(
    slug: str,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    packet_path = tmp_path / "packet.json"
    packet_path.write_text(
        json.dumps(_promoted_for_test(slug), ensure_ascii=False), encoding="utf-8"
    )
    artifact_path = tmp_path / "plan.pdf"
    artifact_path.write_bytes(ARTIFACT_BYTES)

    assert (
        main(
            [
                "--packet",
                str(packet_path),
                "--artifact",
                str(artifact_path),
                "--attachment-url",
                BY_SLUG[slug]["attachment_url"],
                "--confirm-exact-attachment-rights",
            ]
        )
        == 0
    )

    receipt = json.loads(capsys.readouterr().out)
    assert receipt["status"] == "DRY_RUN"
    assert receipt["committee_name"] == EXPECTED[slug][0]
    assert receipt["schedule_rows"] == EXPECTED[slug][1]
    assert receipt["audited_target_mentions"] == EXPECTED[slug][2]
    assert receipt["attachment_sha256"] == hashlib.sha256(ARTIFACT_BYTES).hexdigest()
    assert receipt["claim_publication"] is False
    assert receipt["person_materialization"] is False


def test_importer_rejects_attachment_url_of_another_file_sn() -> None:
    packet = parse_reviewed_gukgam_plan_packet(_promoted_for_test("education"))
    wrong = BY_SLUG["education"]["attachment_url"].replace("fileSn=2", "fileSn=1")

    with pytest.raises(Exception, match="fileSn does not match"):
        ReviewedGukgamArtifactProof.from_bytes(
            packet, attachment_url=wrong, artifact_bytes=ARTIFACT_BYTES
        )


# ---------------------------------------------------------------------------- per-committee


def test_legislation_splits_regional_teams_and_keeps_footnote_out_of_targets() -> None:
    rows = _draft("legislation")["schedule"]
    day20 = [r for r in rows if r["audit_date"] == "2026-10-20"]

    assert [r["time_text"] for r in day20] == ["10:00", "14:00", "10:00", "14:00"]
    assert [r["venue"] for r in day20] == [
        "광주고등법원 (지방1반)",
        "광주고등검찰청 (지방1반)",
        "대구고등법원 (지방2반)",
        "대구고등검찰청 (지방2반)",
    ]
    assert [len(r["audited_targets"]) for r in day20] == [12, 7, 11, 6]
    # Merged date/venue cells: 14:00 rows inherit the printed venue.
    assert [(r["time_text"], r["venue"]) for r in rows if r["audit_date"] == "2026-10-15"] == [
        ("10:00", "국회"),
        ("14:00", "국방부"),
    ]
    assert rows[-1]["section"].endswith("종합감사") and rows[-1]["audit_date"] == "2026-10-26"
    flat = {t for r in rows for t in r["audited_targets"]}
    assert not any("공소청" in t for t in flat)  # footnote about 공소청 is not a target
    assert any("공소청" in e["printed"] for e in BY_SLUG["legislation"]["excluded"])


def test_policy_has_no_printed_times_and_labels_comprehensive_audits() -> None:
    rows = _draft("policy")["schedule"]

    assert all(r["time_text"] is None for r in rows)
    assert rows[4]["venue"] == "부산국제금융센터 (부산)" and rows[4]["section"].endswith("현장국감")
    assert rows[-2]["section"].endswith("종합감사 - 비금융")
    assert rows[-1]["section"].endswith("종합감사 - 금융")
    assert rows[-1]["audited_targets"] == ["금융위원회", "금융감독원 등"]
    assert any(e["printed"].startswith("<현장시찰> 거제") for e in BY_SLUG["policy"]["excluded"])


def test_education_keeps_split_team_rows_and_second_page_numbers() -> None:
    rows = _draft("education")["schedule"]

    assert [r["page_number"] for r in rows] == [7, 7, 7, 7, 8, 8, 8, 8, 8]
    day20 = [r for r in rows if r["audit_date"] == "2026-10-20"]
    assert [len(r["audited_targets"]) for r in day20] == [6, 7]
    assert day20[1]["venue"] == "감사 2반 전남광주통합특별시교육청 전남청사(무안)"
    day21 = [r for r in rows if r["audit_date"] == "2026-10-21"]
    assert [len(r["audited_targets"]) for r in day21] == [9, 10]
    assert rows[-1]["audited_targets"] == ["교육부", "국가교육위원회 등 감사대상기관"]
    # The 2026-10-01 comprehensive inventory lists 한국교직원공제회 on 10-12; the plan does not.
    assert "한국교직원공제회" not in {t for r in rows for t in r["audited_targets"]}


def test_foreign_overseas_multi_day_ranges_are_recorded_as_excluded() -> None:
    raw = _draft("foreign")
    excluded = BY_SLUG["foreign"]["excluded"]

    assert _dates(raw) == ["2026-10-06", "2026-10-07", "2026-10-27"]
    assert not any(
        "대사관" in t or "총영사관" in t for r in raw["schedule"] for t in r["audited_targets"]
    )
    assert [e["date_or_kind"] for e in excluded] == [
        "2026-10-11/2026-10-22",
        "2026-10-11/2026-10-20",
        "2026-10-11/2026-10-21",
    ]
    assert all("multi-day range" in e["reason"] for e in excluded)
    assert [r["page_number"] for r in raw["schedule"]] == [10, 10, 12]
    assert raw["schedule"][1]["venue"] == "통일부 남북회담본부"


def test_industry_drops_star_markers_and_keeps_field_visit_label() -> None:
    rows = _draft("industry")["schedule"]
    day12 = next(r for r in rows if r["audit_date"] == "2026-10-12")

    assert all(r["time_text"] is None for r in rows)
    assert {"한국전력공사", "한국수력원자력"} <= set(day12["audited_targets"])
    assert not any(t.startswith("*") for r in rows for t in r["audited_targets"])
    day13 = next(r for r in rows if r["audit_date"] == "2026-10-13")
    assert day13["venue"] == "지식재산처 (대전)" and day13["section"].endswith("현장시찰")
    assert [r["audited_targets"] for r in rows[-2:]] == [
        ["산업통상부 및 소관기관"],
        ["중소벤처기업부ㆍ지식재산처 및 소관기관"],
    ]


def test_climate_row_spanning_two_pages_is_anchored_to_its_start_page() -> None:
    rows = _draft("climate")["schedule"]
    day16 = next(r for r in rows if r["audit_date"] == "2026-10-16")

    assert day16["page_number"] == 7
    assert len(day16["audited_targets"]) == 13
    assert day16["audited_targets"][:2] == [
        "경제사회노동위원회",
        "중앙노동위원회(12개 지방노동위원회 포함)",
    ]
    assert [r["section"].endswith("종합감사") for r in rows[-2:]] == [True, True]
    kinds = [e["date_or_kind"] for e in BY_SLUG["climate"]["excluded"]]
    assert "2026-10-20/2026-10-21" in kinds  # 제주 field visit, site names only


def test_land_keeps_two_venues_on_the_local_government_row_and_skips_site_visit() -> None:
    rows = _draft("land")["schedule"]
    day19 = next(r for r in rows if r["audit_date"] == "2026-10-19")

    assert day19["audited_targets"] == ["서울특별시", "경기도"]
    assert day19["venue"] == "서울특별시청(서울) / 경기도청(수원)"
    assert "2026-10-20" not in _dates({"schedule": rows})
    assert rows[-1]["section"].endswith("종합감사(확인감사)")


def test_intelligence_after_audit_row_keeps_printed_time_text() -> None:
    rows = _draft("intelligence")["schedule"]

    assert [r["audit_date"] for r in rows] == [
        "2026-10-28",
        "2026-10-28",
        "2026-10-29",
        "2026-10-30",
        "2026-10-30",
    ]
    assert rows[0]["audited_targets"] == ["국방정보본부(정보사령부, 777사령부 포함)"]
    assert rows[-1]["time_text"] == "국방방첩본부 감사 종료 후"
    assert rows[-1]["audited_targets"] == ["사이버작전사령부"]
    assert rows[-1]["venue"] == rows[-2]["venue"] == "국방방첩본부 국정감사장"
