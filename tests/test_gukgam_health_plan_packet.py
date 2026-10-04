from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

from packages.connectors.gukgam_reviewed_packet import (
    GukgamReviewedPacketError,
    parse_reviewed_gukgam_plan_packet,
)
from workers.gukgam_reviewed_plan_import import main

FIXTURE = Path("tests/fixtures/gukgam_2026_health_plan_reviewed_packet.json")
PENDING = "UNKNOWN_PENDING_OFFICIAL_LOCATION"
# Owner-supplied HWP copy (KakaoTalk, 2026-10-04) sha256 for the future exact-artifact proof:
# cfe379abe19544c974a607c87a2bfdcdffdb7e3732a0c1bdddfb0a695bc3fccd (official origin not located).
ATTACHMENT_URL = (
    "https://test.na.go.kr/cmmit/prevew/docsPreview/previewDocs.do"
    "?atchFileId=attachment-1&fileSn=2&viewType=CONTBODY"
)
ARTIFACT_BYTES = b"synthetic-artifact-bytes-not-the-real-hwp\n"
# 지방식품의약품안전청 6곳: covered only by the printed "(지방청 포함)" note, not listed as targets.
UNLISTED_BRANCH_OFFICES = 6


def _draft() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _promoted_for_test() -> dict:
    """Synthetic stand-in for the human review step: fills only what a reviewer must supply."""

    raw = copy.deepcopy(_draft())
    raw["review_status"] = "HUMAN_REVIEWED"
    raw["source"].update(
        {
            "ntt_id": "123",
            "detail_url": "https://test.na.go.kr/cmmit/bbs/BCMT2002/view.do?nttId=123&menuNo=1",
            "published_date": "2026-09-15",
            "atch_file_id": "attachment-1",
            "file_sn": 2,
            "attachment_filename": "synthetic.hwp",
            "rights_mark": "KOGL_TYPE_1",
        }
    )
    for row in raw["schedule"]:
        row["page_number"] = 4
    return raw


def test_health_draft_keeps_unknown_origin_explicit_and_unpublishable() -> None:
    raw = _draft()
    source = raw["source"]

    assert raw["review_status"] == "REVIEW_REQUIRED"
    assert source["committee_name"] == "보건복지위원회"
    assert source["detail_url"] == source["ntt_id"] == source["atch_file_id"] == PENDING
    assert source["published_date"] is None and source["file_sn"] is None
    assert all(row["page_number"] is None for row in raw["schedule"])
    assert raw["witness_rows_included"] is False
    with pytest.raises(GukgamReviewedPacketError, match="not human-reviewed"):
        parse_reviewed_gukgam_plan_packet(raw)


def test_health_draft_cannot_be_self_promoted_without_official_locator() -> None:
    raw = _draft()
    raw["review_status"] = "HUMAN_REVIEWED"
    # Row page numbers are unknown for the HWP copy, so the schedule gate fires first.
    with pytest.raises(GukgamReviewedPacketError, match="page_number is invalid"):
        parse_reviewed_gukgam_plan_packet(raw)

    for row in raw["schedule"]:
        row["page_number"] = 4
    with pytest.raises(GukgamReviewedPacketError, match="official https"):
        parse_reviewed_gukgam_plan_packet(raw)


def test_health_schedule_matches_printed_plan_once_locator_is_supplied() -> None:
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
    # 10. 8. is a two-row merged date/venue cell: the 14:00 row inherits 국회.
    assert packet.schedule[2].venue == "국회"
    assert packet.schedule[5].venue == "원주"
    unique = {t for row in packet.schedule for t in row.audited_targets}
    # The printed plan lists 57 audited institutions.
    assert len(unique) == 57 - UNLISTED_BRANCH_OFFICES
    assert "종합감사" not in unique
    assert not any("배석" in t or t.startswith("*") for t in unique)
    assert packet.witness_rows_included is False


def test_health_worker_dry_run_counts_without_database(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    packet_path = tmp_path / "packet.json"
    packet_path.write_text(json.dumps(_promoted_for_test(), ensure_ascii=False), encoding="utf-8")
    artifact_path = tmp_path / "plan.hwp"
    artifact_path.write_bytes(ARTIFACT_BYTES)

    assert main(
        [
            "--packet",
            str(packet_path),
            "--artifact",
            str(artifact_path),
            "--attachment-url",
            ATTACHMENT_URL,
            "--confirm-exact-attachment-rights",
        ]
    ) == 0

    receipt = json.loads(capsys.readouterr().out)
    assert receipt["status"] == "DRY_RUN"
    assert receipt["schedule_rows"] == 8
    assert receipt["audited_target_mentions"] == 53
    assert receipt["attachment_sha256"] == hashlib.sha256(ARTIFACT_BYTES).hexdigest()
    assert receipt["claim_publication"] is False
