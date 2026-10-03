from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from apps.api.main import create_app
from apps.cli.main import main, parse_command
from packages.connectors.gukgam_reviewed_packet import AUTOMATION_GATE
from packages.connectors.gukgam_witness_packet import (
    DRAFT,
    HUMAN_REVIEWED,
    WITNESS_PACKET_SCHEMA,
    GukgamWitnessPacketError,
    canonical_hash,
    parse_gukgam_witness_packet,
    parse_gukgam_witness_research,
)
from packages.domain.enums import SourceRunStatus
from packages.persistence.acquisition import AcquisitionRepository
from packages.rendering.gukgam_witness_review import (
    GukgamWitnessReviewError,
    load_current_gukgam_witness_review,
)
from packages.verification.gukgam_witness_import import (
    GUKGAM_WITNESS_FEEDER,
    build_reviewed_gukgam_witness_capture,
    verify_witness_artifact,
)
from tests.cli_support import cli_payload
from tests.test_gukgam_reviewed_plan_import import migrated_repository
from workers.gukgam_witness_import import persist_capture

RESEARCH = Path("docs/research/gukgam_2026_science_witness_linkage_2026-10-02.json")
ARTIFACT = b"%PDF synthetic witness fixture; no real human review\n"
SOURCE_KEY = "123:attachment-1:2"


def synthetic_packet() -> dict:
    """HUMAN_REVIEWED is a synthetic test state, never an attestation about real rows."""
    rows = []
    for number, category in enumerate(
        ("INSTITUTION_WITNESS", "GENERAL_WITNESS", "REFERENCE_PERSON"), start=1,
    ):
        institution = category == "INSTITUTION_WITNESS"
        key = (f"{SOURCE_KEY}:page:1:table:1:row:1" if institution
               else f"{SOURCE_KEY}:{category}:ordinal:1")
        rows.append({
            "record_key": key, "source_key": SOURCE_KEY, "page_number": 1,
            "table_number": number, "table_row_number": 1, "source_section": "합성 검토 표",
            "category": category, "printed_name": f"합성인물{number}",
            "printed_institution_group": "합성기관" if institution else None,
            "printed_role": "합성역할" if institution else None,
            "printed_affiliation_role": None if institution else "합성회사 합성직위",
            "printed_audited_target": None if institution else "합성피감기관",
            "requested_datetime_text": None if institution else "2026.10.6. 14:00",
            "decision_date_text": None if institution else "9.22.(화)",
            "printed_ordinal": None if institution else "1",
            "source_name_cell_key": f"{SOURCE_KEY}:page:1:table:1:name-row:1" if institution else key,
            "name_from_merged_cell": False,
            "relation": "SOURCE_LISTED_INSTITUTION_GROUP" if institution else "SOURCE_LISTED_AUDIT_CONTEXT",
        })
    return {
        "schema": WITNESS_PACKET_SCHEMA, "review_status": HUMAN_REVIEWED,
        "selection": "COMPLETE_ATTACHMENT", "page_count": 1,
        "attachment_sha256": hashlib.sha256(ARTIFACT).hexdigest(),
        "attachment_url": "https://test.na.go.kr/cmmit/cmmn/file/fileDown.do?atchFileId=attachment-1&fileSn=2",
        "source": {
            "committee_name": "합성위원회", "ntt_id": "123",
            "detail_url": "https://test.na.go.kr/cmmit/bbs/BCMT2004/view.do?nttId=123&menuNo=2000051",
            "title": "합성 증인 명단", "published_date": "2026-09-22",
            "atch_file_id": "attachment-1", "file_sn": 2,
            "attachment_filename": "synthetic.pdf", "rights_mark": "SYNTHETIC_TEST_RIGHTS",
            "automation_gate": AUTOMATION_GATE,
        },
        "rows": rows,
    }


def capture(raw: dict | None = None, artifact: bytes = ARTIFACT):
    packet = parse_gukgam_witness_packet(raw or synthetic_packet())
    proof = verify_witness_artifact(packet, artifact)
    return build_reviewed_gukgam_witness_capture(packet, artifact=proof)


def test_real_research_remains_draft_and_47_sample_is_not_412_coverage():
    packets = parse_gukgam_witness_research(json.loads(RESEARCH.read_text(encoding="utf-8")))
    assert [len(packet.rows) for packet in packets] == [370, 42]
    assert all(packet.review_status == DRAFT for packet in packets)
    institution, general = packets
    pilot_institution = [row for row in institution.rows if row.page_number == 3]
    pilot_requested = [row for row in general.rows if row.printed_audited_target == "과학기술정보통신부"]
    assert len(pilot_institution) == 32 and len(pilot_requested) == 15
    assert sum(row.category == "GENERAL_WITNESS" for row in pilot_requested) == 13
    assert sum(row.category == "REFERENCE_PERSON" for row in pilot_requested) == 2
    assert all(row.requested_datetime_text is None for row in pilot_institution)
    assert {row.requested_datetime_text for row in pilot_requested} == {"2026.10.6. 14:00"}
    merged = [row for row in institution.rows if row.name_from_merged_cell]
    assert len(merged) == 1
    siblings = [row for row in institution.rows if row.source_name_cell_key == merged[0].source_name_cell_key]
    assert len(siblings) == 2 and len({row.printed_name for row in siblings}) == 1
    assert len({row.printed_role for row in siblings}) == 2


@pytest.mark.parametrize("change", [
    "private_field", "institution_datetime", "institution_employer", "category", "duplicate",
    "source_key", "wrong_page", "wrong_cell", "string_page", "missing_field", "attendance",
])
def test_packet_fails_closed_on_unpermitted_or_inconsistent_rows(change):
    raw = synthetic_packet()
    row = raw["rows"][0]
    if change == "private_field": row["contact"] = "synthetic-forbidden"
    if change == "institution_datetime": row["requested_datetime_text"] = "2026.10.6. 14:00"
    if change == "institution_employer": row["printed_affiliation_role"] = "합성회사"
    if change == "category": row["category"] = "ACTUAL_ATTENDEE"
    if change == "duplicate": raw["rows"].append(copy.deepcopy(row))
    if change == "source_key": row["source_key"] = "another-source"
    if change == "wrong_page": row["page_number"] = 2
    if change == "wrong_cell": row["source_name_cell_key"] = "another-source:page:1:table:1:name-row:1"
    if change == "string_page": row["page_number"] = "1"
    if change == "missing_field": del row["printed_name"]
    if change == "attendance": row["actual_attendance"] = True
    with pytest.raises(ValueError): parse_gukgam_witness_packet(raw)


@pytest.mark.parametrize("url", [
    "https://example.com/cmmit/cmmn/file/fileDown.do?atchFileId=attachment-1&fileSn=2",
    "https://test.na.go.kr/cmmit/cmmn/file/fileDown.do?atchFileId=wrong&fileSn=2",
    "https://test.na.go.kr/cmmit/cmmn/file/fileDown.do?atchFileId=attachment-1&fileSn=1",
    "https://test.na.go.kr/cmmit/cmmn/file/fileDown.do?atchFileId=attachment-1&fileSn=2&token=synthetic",
    "https://user:synthetic@test.na.go.kr/cmmit/cmmn/file/fileDown.do?atchFileId=attachment-1&fileSn=2",
    "https://test.na.go.kr/cmmit/cmmn/file/fileDown.do?atchFileId=attachment-1&fileSn=2&historyBackUrl=synthetic",
])
def test_packet_rejects_inexact_or_credential_urls(url):
    raw = synthetic_packet()
    raw["attachment_url"] = url
    with pytest.raises(GukgamWitnessPacketError): parse_gukgam_witness_packet(raw)


def test_missing_printed_general_datetime_is_preserved_not_inferred():
    raw = synthetic_packet()
    raw["rows"][1]["requested_datetime_text"] = None
    assert parse_gukgam_witness_packet(raw).rows[1].requested_datetime_text is None


def test_draft_and_wrong_bytes_cannot_prepare_acquisition():
    raw = synthetic_packet()
    raw["review_status"] = DRAFT
    with pytest.raises(GukgamWitnessPacketError, match="actual human review"):
        capture(raw)
    with pytest.raises(GukgamWitnessPacketError, match="pinned hash"):
        capture(artifact=b"changed synthetic artifact")


def test_cli_research_inspection_never_opens_database(monkeypatch, capsys):
    monkeypatch.setattr("apps.cli.adapters.repository", lambda _: pytest.fail("DB opened"))
    assert main(["inspect", "gukgam-witness", "--allow-effect", "READ_ONLY",
                 "--research", str(RESEARCH)]) == 0
    report = cli_payload(capsys.readouterr().out)
    assert report["row_count"] == 412 and report["unique_person_count"] is None
    assert report["artifact_bytes_verified"] is False
    assert all(item["review_status"] == DRAFT for item in report["sources"])


def test_cli_draft_import_fails_before_any_database_access(tmp_path, monkeypatch, capsys):
    raw = synthetic_packet()
    raw["review_status"] = DRAFT
    packet = tmp_path / "packet.json"
    packet.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
    artifact = tmp_path / "synthetic.pdf"
    artifact.write_bytes(ARTIFACT)
    monkeypatch.setattr("apps.cli.adapters.repository", lambda _: pytest.fail("DB opened"))
    with pytest.raises(SystemExit):
        main(["observe", "gukgam-witness", "--allow-effect", "SOURCE_INGESTION",
              "--packet", str(packet), "--artifact", str(artifact),
              "--confirm-exact-attachment-rights"])
    assert json.loads(capsys.readouterr().out)["error_code"] == "COMMAND_FAILED"


@pytest.mark.parametrize("args", [
    ["observe", "gukgam-witness", "--allow-effect", "READ_ONLY"],
    ["inspect", "gukgam-witness", "--allow-effect", "READ_ONLY", "--packet", "synthetic.json"],
    ["materialize", "gukgam-witness", "--allow-effect", "IDENTITY_MATERIALIZATION"],
    ["publish", "gukgam-witness", "--allow-effect", "CLAIM_PUBLICATION"],
])
def test_no_mixed_effect_or_unsupported_downstream_command(args):
    with pytest.raises(SystemExit): parse_command(args)


def test_acquisition_is_idempotent_metadata_only_and_has_zero_identity_effects(tmp_path):
    repository = migrated_repository(tmp_path / "witness.db")
    first = persist_capture(repository.application, capture())
    second = persist_capture(repository.application, capture())
    assert first["observations_created"] == 3 and second["observations_unchanged"] == 3
    assert second["observations_created"] == 0 and first["snapshot_id"] == second["snapshot_id"]
    assert repository.people() == [] and repository.organizations() == [] and repository.claims() == []
    assert repository.person_observation_links() == [] and repository.identity_review_items() == []
    report = load_current_gukgam_witness_review(repository.acquisition)
    rows = report["documents"][0]["rows"]
    assert report["row_count"] == 3 and rows[0]["printed_affiliation_role"] is None
    assert rows[1]["printed_affiliation_role"] != rows[1]["printed_audited_target"]
    assert all(row["attendance_state"] == "NOT_VERIFIED" for row in rows)
    scope = capture().scope_key
    observations = repository.feeder_observations(GUKGAM_WITNESS_FEEDER, scope)
    contexts = repository.feeder_observation_contexts(item.id for item in observations)
    assert all(item[1].fulltext is None and item[0].identity_hints == {} for item in contexts.values())
    assert len(repository.sources()) == 1


def test_byte_changed_pdf_with_identical_fields_keeps_exact_new_snapshot(tmp_path):
    repository = migrated_repository(tmp_path / "version.db")
    first = persist_capture(repository.application, capture())
    revised = ARTIFACT + b"metadata revision\n"
    raw = synthetic_packet()
    raw["attachment_sha256"] = hashlib.sha256(revised).hexdigest()
    second = persist_capture(repository.application, capture(raw, revised))
    assert first["snapshot_id"] != second["snapshot_id"]
    assert second["observations_created"] == 3 and second["observations_unchanged"] == 0
    report = load_current_gukgam_witness_review(repository.acquisition)
    assert report["row_count"] == 3
    assert report["documents"][0]["source"]["snapshot_id"] == second["snapshot_id"]
    assert len(repository.feeder_observations(GUKGAM_WITNESS_FEEDER, capture().scope_key)) == 6


def test_explicit_review_subset_does_not_resurrect_prior_rows(tmp_path):
    repository = migrated_repository(tmp_path / "subset.db")
    persist_capture(repository.application, capture())
    raw = synthetic_packet()
    raw["selection"] = "EXPLICIT_REVIEW_SUBSET"
    raw["rows"] = raw["rows"][:1]
    persist_capture(repository.application, capture(raw))
    report = load_current_gukgam_witness_review(repository.acquisition)
    assert report["row_count"] == 1
    assert report["documents"][0]["selection"] == "EXPLICIT_REVIEW_SUBSET"
    assert len(repository.feeder_observations(GUKGAM_WITNESS_FEEDER, capture().scope_key)) == 3


def test_atomic_failure_does_not_advance_checkpoint_or_leave_source_data(tmp_path, monkeypatch):
    repository = migrated_repository(tmp_path / "atomic.db")
    original = AcquisitionRepository.commit_source_page

    def fail_after_flush(self, **kwargs):
        original(self, **kwargs)
        raise ValueError("synthetic failure after flush")

    monkeypatch.setattr(AcquisitionRepository, "commit_source_page", fail_after_flush)
    with pytest.raises(ValueError): persist_capture(repository.application, capture())
    assert repository.source_checkpoints(GUKGAM_WITNESS_FEEDER) == []
    assert repository.sources() == {} or repository.sources() == []
    assert repository.feeder_observations(GUKGAM_WITNESS_FEEDER, capture().scope_key) == []
    runs = repository.source_runs(GUKGAM_WITNESS_FEEDER)
    assert len(runs) == 1 and runs[0].status == SourceRunStatus.FAILED
    assert runs[0].error_summary == "Reviewed witness acquisition failed."


def test_private_review_api_and_public_boundary(tmp_path):
    repository = migrated_repository(tmp_path / "api.db")
    persist_capture(repository.application, capture())
    token = "SYNTHETIC_LOCAL_OPERATOR_TOKEN_0123456789"
    with TestClient(create_app(repository)) as public:
        assert public.get("/admin/gukgam/2026/witnesses").status_code == 404
        assert public.get("/sources/" + str(next(iter(repository.sources().values())).id)).status_code == 404
    with TestClient(create_app(repository, enable_review_surface=True, operator_token=token),
                    base_url="http://127.0.0.1") as private:
        assert private.get("/admin/gukgam/2026/witnesses").status_code == 403
        response = private.get("/admin/gukgam/2026/witnesses", headers={"x-civic-operator-token": token})
        assert response.status_code == 200 and response.json()["row_count"] == 3
        assert response.headers["Cache-Control"] == "private, no-store"
        assert response.headers["X-Robots-Tag"] == "noindex, nofollow"
        assert "claim_id" not in json.dumps(response.json())


def test_checkpoint_corruption_fails_closed_with_safe_api_error(tmp_path, monkeypatch):
    repository = migrated_repository(tmp_path / "corrupt.db")
    persist_capture(repository.application, capture())
    checkpoint = repository.source_checkpoints(GUKGAM_WITNESS_FEEDER)[0]
    checkpoint.metadata["witness_row_count"] = 99
    with repository(read_only=True) as uow:
        monkeypatch.setattr(uow.acquisition, "source_checkpoints", lambda _: [checkpoint])
        with pytest.raises(GukgamWitnessReviewError):
            load_current_gukgam_witness_review(uow.acquisition)
    monkeypatch.setattr(AcquisitionRepository, "source_checkpoints", lambda self, _: [checkpoint])
    request_id = "99999999-1111-4111-8111-111111111111"
    monkeypatch.setattr("apps.api.main.uuid4", lambda: request_id)
    with TestClient(create_app(repository, enable_review_surface=True)) as client:
        response = client.get("/admin/gukgam/2026/witnesses")
    assert response.status_code == 409
    payload = response.json()
    assert set(payload) == {"error"}
    assert set(payload["error"]) == {"code", "message", "request_id"}
    assert payload["error"]["code"] == "SOURCE_VERSION_CONFLICT"
    assert payload["error"]["request_id"] == request_id
    assert "99" not in payload["error"]["message"]


def test_research_heading_count_corruption_is_rejected():
    raw = json.loads(RESEARCH.read_text(encoding="utf-8"))
    raw["institution_heading_checks"][0]["expected_named_cells"] += 1
    with pytest.raises(GukgamWitnessPacketError, match="heading coverage"):
        parse_gukgam_witness_research(raw)


def test_research_tampering_never_silently_becomes_reviewed():
    raw = json.loads(RESEARCH.read_text(encoding="utf-8"))
    raw["records"][0]["printed_name"] = "합성변경"
    with pytest.raises(GukgamWitnessPacketError, match="normalization hash"):
        parse_gukgam_witness_research(raw)
    raw["records"][0]["normalization_hash"] = canonical_hash({
        key: value for key, value in raw["records"][0].items() if key != "normalization_hash"
    })
    raw["review_status"] = HUMAN_REVIEWED
    with pytest.raises(GukgamWitnessPacketError, match="unreviewed"):
        parse_gukgam_witness_research(raw)
