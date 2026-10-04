from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from packages.connectors.gukgam_reviewed_packet import (
    GukgamReviewedPacketError,
    parse_reviewed_gukgam_plan_packet,
)

FIXTURE = Path("tests/fixtures/gukgam_2026_health_plan_reviewed_packet.json")
PROVENANCE = json.loads(
    Path("tests/fixtures/gukgam_2026_plan_batch2_provenance.json").read_text(encoding="utf-8")
)
HEALTH = next(item for item in PROVENANCE["packets"] if item["slug"] == "health")
OFFICIAL_POST = "https://health.na.go.kr/cmmit/bbs/BCMT2002/view.do?nttId=3078730&menuNo=2000030"
# 지방식품의약품안전청 6곳: covered only by the printed "(지방청 포함)" note, not listed as targets.
UNLISTED_BRANCH_OFFICES = 6


def _draft() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _promoted_for_test() -> dict:
    """Synthetic stand-in for the human review step: status and rights mark only."""

    raw = copy.deepcopy(_draft())
    raw["review_status"] = "HUMAN_REVIEWED"
    raw["source"]["rights_mark"] = "SYNTHETIC_DRY_RUN_ONLY"
    return raw


def test_health_draft_is_anchored_to_the_official_post_but_stays_review_required() -> None:
    raw = _draft()
    source = raw["source"]

    assert raw["review_status"] == "REVIEW_REQUIRED"
    assert source["committee_name"] == "보건복지위원회"
    assert source["detail_url"].startswith(OFFICIAL_POST.split("&")[0])
    assert source["ntt_id"] == "3078730"
    assert source["published_date"] == "2026-09-29"
    assert source["atch_file_id"] == "11a174c538244b6eb2de554fa361a86d"
    assert source["file_sn"] == 2 and source["attachment_filename"].endswith(".pdf")
    assert source["rights_mark"] is None
    assert all(isinstance(row["page_number"], int) for row in raw["schedule"])
    assert raw["witness_rows_included"] is False
    with pytest.raises(GukgamReviewedPacketError, match="not human-reviewed"):
        parse_reviewed_gukgam_plan_packet(raw)


def test_health_hwp_cross_check_matches_the_owner_copy_hash_cited_in_pr_171() -> None:
    hwp = HEALTH["hwp_crosscheck"]

    # The official HWP is byte-identical to the owner-supplied copy the draft PR #171 was built from.
    assert hwp["sha256"] == "cfe379abe19544c974a607c87a2bfdcdffdb7e3732a0c1bdddfb0a695bc3fccd"
    assert hwp["sha256_matches_owner_copy_pr171"] is True
    # A second PDF (fileSn=3) exists on the post; its extracted text is identical to fileSn=2.
    assert HEALTH["alternate_pdf"]["attachment_url"].endswith("fileSn=3")
    assert HEALTH["alternate_pdf"]["extracted_text_identical_to_primary"] is True


def test_health_schedule_matches_printed_plan_once_review_fields_are_supplied() -> None:
    packet = parse_reviewed_gukgam_plan_packet(_promoted_for_test())

    assert packet.source.committee_name == "보건복지위원회"
    assert len(packet.schedule) == 8
    assert sum(len(row.audited_targets) for row in packet.schedule) == 53
    assert [row.audit_date.isoformat() for row in packet.schedule] == [
        "2026-10-07",
        "2026-10-08",
        "2026-10-08",
        "2026-10-13",
        "2026-10-14",
        "2026-10-16",
        "2026-10-20",
        "2026-10-22",
    ]
    assert [row.time_text for row in packet.schedule][:3] == ["10:00", "10:00", "14:00"]
    assert {row.page_number for row in packet.schedule} == {6}
    # 10. 8. is a two-row merged date/venue cell: the 14:00 row inherits 국회.
    assert packet.schedule[2].venue == "국회"
    assert packet.schedule[5].venue == "원주"
    unique = {t for row in packet.schedule for t in row.audited_targets}
    # The printed plan lists 57 audited institutions.
    assert len(unique) == 57 - UNLISTED_BRANCH_OFFICES
    assert "종합감사" not in unique
    assert not any("배석" in t or t.startswith("*") for t in unique)
    assert packet.witness_rows_included is False
    assert any(e["date_or_kind"] == "2026-10-27" for e in HEALTH["excluded"])
