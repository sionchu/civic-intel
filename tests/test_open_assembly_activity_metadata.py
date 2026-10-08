"""Four source-specific schemas, synthetic provider rows; no live requests."""
import json
from uuid import uuid4

import pytest

from packages.connectors.open_assembly import national_assembly_member_policy
from packages.connectors.open_assembly_activity_metadata import (
    ACTIVITY_APIS,
    LOCATOR_UNVERIFIED,
    normalize_activity_row,
)
from packages.domain import db
from packages.persistence.admin_workflow import AdminError
from packages.verification.assembly_press_import import build_activity_capture
from tests.test_assembly_press_import import setup
from workers.assembly_press_import import main


def policy():
    return national_assembly_member_policy().model_copy(update={"can_fetch": False, "can_send_to_ai": False})


def provider_row(api):
    fields = {
        "SPGRPPRESS": {"ARTC_TTL": "합성 안내", "WRT_DT": "2099-10-09", "CHM_DIV": "합성 구분"},
        "NAMEMBEREVENT": {"EV_TTL": "합성 행사", "EV_DTM": "2099-10-09", "NAAS_NM": "합성의원갑"},
        "nkulntiravezskrjd": {"V_TITLE": "합성 뉴스", "DATE_RELEASED": "2099-10-09"},
        "npeslxqbanwkimebr": {"TITLE": "합성 회의", "TAKING_DATE": "2099-10-09", "ESSENTIAL_PERSON": "합성의원갑"},
    }
    return fields[api] | {"LINK_URL": "https://www.na.go.kr/synthetic-public-record",
        "URL_LINK": "https://www.naon.go.kr/synthetic-public-record",
        "V_BODY": "FORBIDDEN_SYNTHETIC_ARTICLE_BODY", "CONTENT": "FORBIDDEN_SYNTHETIC_CONTENT",
        "EV_PLC": "FORBIDDEN_SYNTHETIC_ADDRESS", "KEY": "FORBIDDEN_SYNTHETIC_CREDENTIAL",
        "MONA_CD": "FORBIDDEN_UNVERIFIED_PERSON_ID", "unknown": "FORBIDDEN_UNKNOWN_FIELD"}


def page(api):
    return {"page_index": 1, "page_size": 5, "list_total_count": 8, "records": [provider_row(api)]}


@pytest.mark.parametrize("api", ACTIVITY_APIS)
def test_all_four_adapters_capture_safe_metadata_without_fetch_ai_or_identity(api):
    source, snapshot, observations = build_activity_capture(page(api), api_code=api, policy=policy(), run_id=uuid4())
    serialized = json.dumps(snapshot.model_dump(mode="json"), ensure_ascii=False)
    assert "FORBIDDEN" not in serialized
    assert snapshot.fulltext is None and observations[0].identity_hints == {}
    assert source.published_at is None
    assert snapshot.metadata["coverage"] == "SELECTED_PAGE_ONLY"
    assert snapshot.metadata["query_semantics"] == "UNVERIFIED_NOT_FETCHED"
    assert observations[0].normalized["record_identity_status"] == LOCATOR_UNVERIFIED
    assert "canonical_name" not in observations[0].normalized
    assert observations[0].provider_record_key.startswith("staged:")


@pytest.mark.parametrize("link", ["https://www.na.go.kr/record?KEY=FORBIDDEN", "https://user:pass@www.na.go.kr/record",
    "https://unreviewed.invalid/record", "http://www.na.go.kr/record", "https://www.na.go.kr/record#fragment"])
def test_unknown_or_credential_link_semantics_never_retained(link):
    raw = provider_row("SPGRPPRESS") | {"LINK_URL": link}
    row = normalize_activity_row("SPGRPPRESS", raw, policy=policy())
    assert row["source_link"] is None


@pytest.mark.parametrize("link", [
    "https://www.na.go.kr:UNTRUSTED_MARKER/record",
    "https://[UNTRUSTED_MARKER/record",
])
def test_malformed_link_errors_are_stable_and_content_free(link):
    raw = provider_row("SPGRPPRESS") | {"LINK_URL": link}
    with pytest.raises(ValueError) as error:
        normalize_activity_row("SPGRPPRESS", raw, policy=policy())
    assert str(error.value) == "ACTIVITY_LINK_INVALID"
    assert error.value.__suppress_context__


def test_unknown_date_format_remains_unknown_not_fabricated_timestamp():
    raw = provider_row("NAMEMBEREVENT") | {"EV_DTM": "2099.10.09 13:00"}
    row = normalize_activity_row("NAMEMBEREVENT", raw, policy=policy())
    assert row["written_date"] is None and row["date_status"] == "UNKNOWN"


@pytest.mark.parametrize("change", [{"page_size": 101}, {"page_index": True}, {"list_total_count": 0},
    {"extra": "unsupported-source-filter"}])
def test_unbounded_or_unknown_capture_scope_rejected(change):
    with pytest.raises(ValueError): build_activity_capture(page("SPGRPPRESS") | change,
        api_code="SPGRPPRESS", policy=policy(), run_id=uuid4())


def test_metadata_policy_gate_precedes_provider_parsing():
    with pytest.raises(PermissionError): build_activity_capture(object(), api_code="SPGRPPRESS",
        policy=policy().model_copy(update={"can_store_metadata": False}), run_id=uuid4())


@pytest.mark.parametrize("api", ACTIVITY_APIS)
def test_same_cli_no_write_boundary_for_all_adapters(tmp_path, monkeypatch, capsys, api):
    raw, governing = tmp_path / "page.json", tmp_path / "policy.json"
    raw.write_text(json.dumps(page(api), ensure_ascii=False), encoding="utf-8")
    governing.write_text(policy().model_dump_json(), encoding="utf-8")
    monkeypatch.delenv("CIVIC_DATABASE_URL", raising=False)
    assert main(["--metadata", str(raw), "--policy", str(governing), "--activity-api", api]) == 0
    stdout = capsys.readouterr().out
    assert "합성" not in stdout and "FORBIDDEN" not in stdout
    report = json.loads(stdout)
    assert not report["write_performed"] and not report["publication_eligible"]
    assert not report["identity_review_confirmed"] and not report["ai_processing"]


def test_canonical_capture_reuses_repository_but_unverified_locator_blocks_review_link(tmp_path, monkeypatch, capsys):
    repository, _, command = setup(tmp_path, monkeypatch, capsys)
    raw, governing = tmp_path / "alternative.json", tmp_path / "alternative-policy.json"
    raw.write_text(json.dumps(page("NAMEMBEREVENT"), ensure_ascii=False), encoding="utf-8")
    stored = repository.policies()[national_assembly_member_policy().id]
    governing.write_text(stored.model_dump_json(), encoding="utf-8")
    assert main(["--metadata", str(raw), "--policy", str(governing),
        "--activity-api", "NAMEMBEREVENT", "--commit"]) == 0
    captured = json.loads(capsys.readouterr().out)
    from uuid import UUID
    alternate = command.model_copy(update={"request_id": uuid4(), "record_ids": (UUID(captured["observation_ids"][0]),)})
    with pytest.raises(AdminError) as error:
        repository.admin_preview(alternate)
    assert error.value.code == "PRESS_RECORD_LOCATOR_UNVERIFIED"
    with repository.sessions() as session:
        assert session.get(db.FeederObservationRow, str(alternate.record_ids[0])) is not None
    assert not captured["claim_publication"]
