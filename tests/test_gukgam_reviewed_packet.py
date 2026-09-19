import json
from pathlib import Path

import pytest

from packages.connectors.gukgam_reviewed_packet import (
    AUTOMATION_GATE,
    PACKET_SCHEMA,
    GukgamReviewedPacketError,
    parse_reviewed_gukgam_plan_packet,
)

FIXTURE = Path("tests/fixtures/gukgam_2026_science_plan_metadata_packet.json")
REVIEWED_FIXTURE = Path("tests/fixtures/gukgam_2026_science_plan_reviewed_packet.json")
REVIEWED_PACKET_EXPECTATIONS = {
    Path("tests/fixtures/gukgam_2026_science_plan_reviewed_packet.json"): (
        "과학기술정보방송통신위원회", 8, 96, "4f74bf8b7f0dfae52ad6fafff646d0c5f78a2c602a3d53d1bf55796284c8a74d"
    ),
    Path("tests/fixtures/gukgam_2026_steering_plan_reviewed_packet.json"): (
        "국회운영위원회", 3, 10, "a70b01b4a9d7e6866ae6be5971c24ff999c88acc6d4d48db26c97a5e28e894a2"
    ),
    Path("tests/fixtures/gukgam_2026_adminhom_plan_reviewed_packet.json"): (
        "행정안전위원회", 12, 45, "b04504c596b81316d507fcf19a41c96958244f8e3e5bf7f51f6b097f5ce064ee"
    ),
    Path("tests/fixtures/gukgam_2026_culture_plan_reviewed_packet.json"): (
        "문화체육관광위원회", 7, 69, "13ea6574f5ebfc277ff698f247651c4195ad0a63e1dd88caae29cd14967f2eaa"
    ),
    Path("tests/fixtures/gukgam_2026_agri_plan_reviewed_packet.json"): (
        "농림축산식품해양수산위원회", 8, 49, "e8e3d884098cdf060e6ac30f966f74b7bf25012f2a45909621691ab94fc35b07"
    ),
    Path("tests/fixtures/gukgam_2026_finance_plan_reviewed_packet.json"): (
        "재정경제기획위원회", 10, 48, "5b73bd4fe6be4e52c5fa01417fcc476a89f425eb743e47d8a4b18c55703175f1"
    ),
    Path("tests/fixtures/gukgam_2026_defense_plan_reviewed_packet.json"): (
        "국방위원회", 9, 73, "2b53b491a4d453ed6f3490ada15297077587deb7cad929f66a92d7e0e04c3a53"
    ),
}


def _packet() -> dict:
    return {
        "schema": PACKET_SCHEMA,
        "review_status": "HUMAN_REVIEWED",
        "source": {
            "committee_name": "테스트위원회",
            "ntt_id": "123",
            "detail_url": (
                "https://test.na.go.kr/cmmit/bbs/BCMT2002/view.do"
                "?nttId=123&menuNo=2000030"
            ),
            "title": "2026년도 국정감사계획서",
            "published_date": "2026-09-15",
            "atch_file_id": "attachment-1",
            "file_sn": 2,
            "attachment_filename": "2026년도 국정감사계획서.pdf",
            "rights_mark": "KOGL_TYPE_1",
            "automation_gate": AUTOMATION_GATE,
        },
        "schedule": [
            {
                "ordinal": 1,
                "audit_date": "2026-10-06",
                "time_text": "10:00",
                "venue": "국회",
                "section": "감사일정",
                "audited_targets": ["테스트기관 A", "테스트기관 B"],
                "page_number": 3,
            },
            {
                "ordinal": 2,
                "audit_date": "2026-10-07",
                "time_text": None,
                "venue": None,
                "section": "감사일정",
                "audited_targets": ["테스트기관 C"],
                "page_number": 4,
            },
        ],
        "witness_rows_included": False,
    }


def test_pinned_science_plan_metadata_packet_is_parseable() -> None:
    packet = parse_reviewed_gukgam_plan_packet(
        json.loads(FIXTURE.read_text(encoding="utf-8"))
    )

    assert packet.source.committee_name == "과학기술정보방송통신위원회"
    assert packet.source.ntt_id == "3078699"
    assert packet.source.atch_file_id == "7938f3a874d5441892124093d19da1df"
    assert packet.source.file_sn == 2
    assert packet.schedule == ()
    assert packet.witness_rows_included is False


def test_pinned_science_plan_reviewed_packet_matches_reviewed_schedule() -> None:
    packet = parse_reviewed_gukgam_plan_packet(
        json.loads(REVIEWED_FIXTURE.read_text(encoding="utf-8"))
    )

    assert packet.source.committee_name == "과학기술정보방송통신위원회"
    assert packet.source.ntt_id == "3078699"
    assert len(packet.schedule) == 8
    assert sum(len(row.audited_targets) for row in packet.schedule) == 96
    assert packet.schedule[0].audit_date.isoformat() == "2026-10-06"
    assert packet.schedule[-1].audit_date.isoformat() == "2026-10-23"
    assert packet.schedule[5].venue == "대전"
    assert len(packet.schedule[5].audited_targets) == 54
    assert "한국방송공사" in packet.schedule[4].audited_targets
    assert packet.content_hash == "4f74bf8b7f0dfae52ad6fafff646d0c5f78a2c602a3d53d1bf55796284c8a74d"
    assert packet.witness_rows_included is False


@pytest.mark.parametrize(
    ("fixture", "expected"),
    REVIEWED_PACKET_EXPECTATIONS.items(),
)
def test_real_reviewed_packets_match_pinned_counts_and_hashes(
    fixture: Path,
    expected: tuple[str, int, int, str],
) -> None:
    committee_name, row_count, target_count, expected_hash = expected
    packet = parse_reviewed_gukgam_plan_packet(
        json.loads(fixture.read_text(encoding="utf-8"))
    )

    assert packet.source.committee_name == committee_name
    assert len(packet.schedule) == row_count
    assert sum(len(row.audited_targets) for row in packet.schedule) == target_count
    assert packet.content_hash == expected_hash
    assert packet.witness_rows_included is False


def test_schedule_packet_has_deterministic_record_keys_and_hash() -> None:
    packet = parse_reviewed_gukgam_plan_packet(_packet())
    packet_again = parse_reviewed_gukgam_plan_packet(_packet())

    assert packet.content_hash == packet_again.content_hash
    assert [
        packet.schedule_record_key(row) for row in packet.schedule
    ] == [
        "123:attachment-1:2:schedule:1",
        "123:attachment-1:2:schedule:2",
    ]
    assert packet.normalized()["schedule"][0]["audited_targets"] == [
        "테스트기관 A",
        "테스트기관 B",
    ]


def test_source_ntt_id_must_match_detail_url() -> None:
    raw = _packet()
    raw["source"]["ntt_id"] = "999"

    with pytest.raises(GukgamReviewedPacketError, match="ntt_id does not match"):
        parse_reviewed_gukgam_plan_packet(raw)


def test_plan_packet_rejects_embedded_witness_rows() -> None:
    raw = _packet()
    raw["witness_rows_included"] = True

    with pytest.raises(GukgamReviewedPacketError, match="must not embed witness"):
        parse_reviewed_gukgam_plan_packet(raw)


def test_packet_rejects_unknown_or_private_side_channel_fields() -> None:
    raw = _packet()
    raw["contacts"] = [{"phone": "010-0000-0000"}]

    with pytest.raises(GukgamReviewedPacketError, match="unsupported fields: contacts"):
        parse_reviewed_gukgam_plan_packet(raw)


def test_schedule_requires_unique_ordered_ordinals() -> None:
    raw = _packet()
    raw["schedule"][1]["ordinal"] = 1

    with pytest.raises(GukgamReviewedPacketError, match="ordinals must be unique"):
        parse_reviewed_gukgam_plan_packet(raw)


def test_schedule_rejects_duplicate_target_names_within_row() -> None:
    raw = _packet()
    raw["schedule"][0]["audited_targets"] = ["테스트기관 A", "테스트기관 A"]

    with pytest.raises(GukgamReviewedPacketError, match="audited_targets must be unique"):
        parse_reviewed_gukgam_plan_packet(raw)


def test_automation_gate_cannot_be_weakened_in_packet() -> None:
    raw = _packet()
    raw["source"]["automation_gate"] = "FETCH_ALLOWED"

    with pytest.raises(GukgamReviewedPacketError, match="reviewed blocked state"):
        parse_reviewed_gukgam_plan_packet(raw)
