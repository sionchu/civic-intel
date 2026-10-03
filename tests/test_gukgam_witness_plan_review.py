from __future__ import annotations

import copy
import json
import socket

import pytest

from apps.cli import adapters
from apps.cli.main import main, parse_command
from packages.connectors.gukgam_reviewed_packet import parse_reviewed_gukgam_plan_packet
from packages.connectors.gukgam_witness_packet import DRAFT, parse_gukgam_witness_packet
from packages.rendering.gukgam_witness_plan_review import (
    MULTIPLE_EXACT,
    NO_CONTEXT,
    NO_EXACT,
    ONE_EXACT,
    GukgamWitnessPlanReviewError,
    build_gukgam_witness_plan_review,
)
from tests.cli_support import cli_payload
from tests.test_gukgam_reviewed_plan_import import packet_payload
from tests.test_gukgam_witness import ARTIFACT, RESEARCH, synthetic_packet


def inputs():
    witness = synthetic_packet()
    witness["review_status"] = DRAFT
    witness["source"]["rights_mark"] = "KOGL_TYPE_1"
    plan = packet_payload()
    plan["source"]["ntt_id"] = "456"
    plan["source"]["detail_url"] = plan["source"]["detail_url"].replace("123", "456")
    plan["source"]["committee_name"] = witness["source"]["committee_name"]
    plan["schedule"] = plan["schedule"][:1]
    plan["schedule"][0]["audited_targets"] = ["합성기관", "합성피감기관"]
    return witness, plan


def review(witness, plan):
    return build_gukgam_witness_plan_review(
        [parse_gukgam_witness_packet(witness)], [parse_reviewed_gukgam_plan_packet(plan)],
    )


def test_literal_contexts_and_dates_are_preserved_without_identity_or_attendance():
    witness, plan = inputs()
    result = review(witness, plan)
    assert result["match_class_counts"] == {ONE_EXACT: 3}
    institution = next(item for item in result["items"]
                       if item["witness_row"]["category"] == "INSTITUTION_WITNESS")
    assert institution["context_kind"] == "INSTITUTION_LIST_HEADING"
    assert institution["witness_row"]["requested_datetime_text"] is None
    general = next(item for item in result["items"]
                   if item["witness_row"]["category"] == "GENERAL_WITNESS")
    assert general["context_label"] == "합성피감기관"
    assert general["witness_row"]["printed_affiliation_role"] == "합성회사 합성직위"
    assert general["witness_row"]["requested_datetime_text"] == "2026.10.6. 14:00"
    assert general["plan_candidates"][0]["printed_time_text"] == "10:00"
    assert result["selected_plan_occurrences"] == 0
    assert result["canonical_identity_binding"] is result["claim_publication"] is False
    assert result["unique_person_count"] is None
    assert result["witness_sources"][0]["review_status"] == DRAFT
    assert result["plan_sources"][0]["artifact_bytes_verified"] is False
    assert all(item["attendance_state"] == "NOT_VERIFIED" for item in result["items"])
    assert "organization_id" not in json.dumps(result) and "person_id" not in json.dumps(result)


@pytest.mark.parametrize("mismatch", ["committee", "published_year", "audit_year", "label"])
def test_same_host_or_name_does_not_cross_scope(mismatch):
    witness, plan = inputs()
    if mismatch == "committee": plan["source"]["committee_name"] = "다른위원회"
    elif mismatch == "published_year": plan["source"]["published_date"] = "2025-09-15"
    elif mismatch == "audit_year": plan["schedule"][0]["audit_date"] = "2025-10-06"
    else: plan["schedule"][0]["audited_targets"] = ["합성 기관", "다른대상"]
    assert review(witness, plan)["match_class_counts"] == {NO_EXACT: 3}


def test_missing_target_and_employer_name_are_not_plan_targets():
    witness, plan = inputs()
    witness["rows"][1]["printed_audited_target"] = None
    witness["rows"][1]["printed_affiliation_role"] = "합성기관"
    witness["rows"][2]["printed_audited_target"] = "미확인대상"
    result = review(witness, plan)
    assert result["match_class_counts"] == {NO_CONTEXT: 1, NO_EXACT: 1, ONE_EXACT: 1}


def test_multiple_occurrences_preserve_all_candidates_without_selecting_by_date():
    witness, plan = inputs()
    second = copy.deepcopy(plan["schedule"][0])
    second.update(ordinal=2, audit_date="2026-10-22", section="종합감사")
    plan["schedule"].append(second)
    result = review(witness, plan)
    assert result["match_class_counts"] == {MULTIPLE_EXACT: 3}
    for item in result["items"]:
        assert {candidate["printed_audit_date"] for candidate in item["plan_candidates"]} == {
            "2026-10-06", "2026-10-22",
        }
        assert len({candidate["review_key"] for candidate in item["plan_candidates"]}) == 2
    assert result["selected_plan_occurrences"] == 0


@pytest.mark.parametrize("lane", ["witness", "plan"])
def test_duplicate_attachment_series_versions_fail_closed(lane):
    witness, plan = inputs()
    witnesses = [parse_gukgam_witness_packet(witness)]
    plans = [parse_reviewed_gukgam_plan_packet(plan)]
    if lane == "witness":
        witness["attachment_sha256"] = "b" * 64
        witnesses.append(parse_gukgam_witness_packet(witness))
    else:
        plan["schedule"][0]["time_text"] = "14:00"
        plans.append(parse_reviewed_gukgam_plan_packet(plan))
    with pytest.raises(GukgamWitnessPlanReviewError, match="duplicate"):
        build_gukgam_witness_plan_review(witnesses, plans)


@pytest.mark.parametrize("url", [
    "https://secret:test@test.na.go.kr/cmmit/bbs/BCMT2002/view.do?nttId=456",
    "https://test.na.go.kr/cmmit/bbs/BCMT2002/view.do?nttId=456&token=secret",
])
def test_plan_source_credentials_fail_without_echo(url):
    witness, plan = inputs()
    plan["source"]["detail_url"] = url
    with pytest.raises(GukgamWitnessPlanReviewError) as failure:
        review(witness, plan)
    assert "secret" not in str(failure.value)


@pytest.mark.parametrize("lane", ["witness", "plan"])
def test_unreviewed_rights_fail_closed(lane):
    witness, plan = inputs()
    (witness if lane == "witness" else plan)["source"]["rights_mark"] = "NOT_REVIEWED"
    with pytest.raises(GukgamWitnessPlanReviewError): review(witness, plan)


def test_real_research_counts_and_47_pilot_keep_ambiguity_and_merged_names(monkeypatch, capsys):
    monkeypatch.setattr(adapters, "repository", lambda _: pytest.fail("DB opened"))
    monkeypatch.setattr(socket.socket, "connect", lambda *_: pytest.fail("network opened"))
    plan = "tests/fixtures/gukgam_2026_science_plan_reviewed_packet.json"
    assert main(["inspect", "gukgam-witness", "--research", str(RESEARCH), "--plan-packet", plan]) == 0
    result = cli_payload(capsys.readouterr().out)
    linked = result["plan_linkage_review"]
    assert linked["row_count"] == 412 and result["artifact_bytes_verified"] is False
    assert linked["match_class_counts"] == {ONE_EXACT: 288, MULTIPLE_EXACT: 108, NO_EXACT: 16}
    pilot = [item for item in linked["items"] if item["context_label"] == "과학기술정보통신부"]
    assert len(pilot) == 47 and all(item["match_class"] == MULTIPLE_EXACT for item in pilot)
    merged = [item for item in linked["items"] if item["witness_row"]["printed_name"] == "권현준"]
    assert len(merged) == 2
    assert len({item["witness_row"]["source_name_cell_key"] for item in merged}) == 1
    assert all(source["review_status"] == DRAFT for source in linked["witness_sources"])


def test_single_packet_cli_checks_raw_witness_bytes_and_accepts_repeated_plans(tmp_path, monkeypatch, capsys):
    witness, plan = inputs()
    packet_path, artifact_path, plan_path = (tmp_path / name for name in ("w.json", "w.pdf", "p.json"))
    packet_path.write_text(json.dumps(witness), encoding="utf-8")
    artifact_path.write_bytes(ARTIFACT)
    plan_path.write_text(json.dumps(plan), encoding="utf-8")
    other = copy.deepcopy(plan)
    other["source"]["ntt_id"] = "789"
    other["source"]["detail_url"] = other["source"]["detail_url"].replace("456", "789")
    other_path = tmp_path / "other.json"
    other_path.write_text(json.dumps(other), encoding="utf-8")
    monkeypatch.setattr(adapters, "repository", lambda _: pytest.fail("DB opened"))
    monkeypatch.setattr(socket.socket, "connect", lambda *_: pytest.fail("network opened"))
    assert main(["inspect", "gukgam-witness", "--packet", str(packet_path),
                 "--artifact", str(artifact_path), "--plan-packet", str(plan_path),
                 "--plan-packet", str(other_path)]) == 0
    result = cli_payload(capsys.readouterr().out)
    assert result["artifact_bytes_verified"] is True
    assert result["plan_linkage_review"]["match_class_counts"] == {MULTIPLE_EXACT: 3}


def test_plan_review_flag_cannot_be_used_for_acquisition():
    with pytest.raises(SystemExit):
        parse_command(["observe", "gukgam-witness", "--allow-effect", "SOURCE_INGESTION",
                       "--packet", "w.json", "--artifact", "w.pdf",
                       "--confirm-exact-attachment-rights", "--plan-packet", "p.json"])
