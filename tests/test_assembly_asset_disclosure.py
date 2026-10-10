from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import func, select

from packages.connectors.assembly_asset_packet import (
    VALUE_SEMANTICS,
    AssemblyAssetPacketError,
    parse_reviewed_assembly_asset_packet,
)
from packages.domain.db import (
    AssetDisclosureRow,
    AssetItemRow,
    ClaimRow,
    FeederObservationRow,
    PersonObservationLinkRow,
    PersonRow,
    SourcePolicyRow,
    SourceSnapshotRow,
)
from packages.domain.enums import SourceCollectionMode
from packages.persistence import SqlAlchemyRepository
from packages.verification.assembly_asset_import import (
    ASSEMBLY_ASSET_FEEDER,
    RECORD_KIND_ITEM,
    RECORD_KIND_MEMBER_TOTAL,
    AssemblyAssetImportError,
    build_assembly_asset_capture,
    gazette_asset_policy,
)
from packages.verification.materialization import MaterializationError
from workers.assembly_asset_import import main

FIXTURE = Path("tests/fixtures/assembly_asset_synthetic_reviewed_packet.json")
ARTIFACT_BYTES = b"%PDF-1.4\n% SYNTHETIC-ASSEMBLY-GAZETTE-ASSET-FIXTURE\n"
SCOPE = "gazette:2099-1:pdf:0"


def payload(status: str = "HUMAN_REVIEWED") -> dict:
    raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
    raw["review_status"] = status
    return raw


def first_item(raw: dict) -> dict:
    return raw["members"][0]["items"][0]


def migrated_repository(database: Path) -> tuple[SqlAlchemyRepository, str]:
    database_url = f"sqlite:///{database.as_posix()}"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(config, "head")
    return SqlAlchemyRepository(database_url), database_url


def write_inputs(tmp_path: Path, raw: dict | None = None) -> tuple[Path, Path]:
    packet = tmp_path / "packet.json"
    packet.write_text(json.dumps(raw or payload(), ensure_ascii=False), encoding="utf-8")
    artifact = tmp_path / "gazette.pdf"
    artifact.write_bytes(ARTIFACT_BYTES)
    return packet, artifact


def cli(packet: Path, artifact: Path, *extra: str) -> list[str]:
    return [
        "--packet",
        str(packet),
        "--artifact",
        str(artifact),
        "--confirm-gazette-rights-review",
        *extra,
    ]


def test_fixture_is_review_required_and_parses() -> None:
    packet = parse_reviewed_assembly_asset_packet(payload("REVIEW_REQUIRED"))
    assert not packet.is_human_reviewed
    assert len(packet.members) == 2
    assert packet.scope_key == SCOPE
    assert packet.record_key(packet.members[0].total_locator) == "2099-1:p3:t1:r1"
    assert hashlib.sha256(ARTIFACT_BYTES).hexdigest() == packet.source.artifact_sha256
    assert packet.source.canonical_url.endswith("pdfId=0")


@pytest.mark.parametrize(
    "suffix",
    [
        "&access_token=synthetic-private-canary",
        "&unknown=synthetic-private-canary",
        "#token=synthetic-private-canary",
        "#",
        "&pdfId=0",
        "&cntsDivCd=NAMGZN",
        "&menuNo=601019",
        "&pdfClsCd=CPR",
        "&menuNo=synthetic-private-canary",
    ],
)
def test_gazette_url_rejects_extra_or_duplicate_input_without_echoing_values(suffix: str) -> None:
    raw = payload()
    raw["source"]["page_url"] += suffix
    with pytest.raises(AssemblyAssetPacketError) as error:
        parse_reviewed_assembly_asset_packet(raw)
    assert "synthetic-private-canary" not in str(error.value)


@pytest.mark.parametrize(
    "authority",
    [
        "synthetic-private-canary@www.assembly.go.kr",
        "synthetic-private-canary:password@www.assembly.go.kr",
        "@www.assembly.go.kr",
        "www.assembly.go.kr:444",
        "www.assembly.go.kr:synthetic-private-canary",
    ],
)
def test_gazette_url_rejects_userinfo_and_non_default_port(authority: str) -> None:
    raw = payload()
    raw["source"]["page_url"] = raw["source"]["page_url"].replace("www.assembly.go.kr", authority)
    with pytest.raises(AssemblyAssetPacketError) as error:
        parse_reviewed_assembly_asset_packet(raw)
    assert "synthetic-private-canary" not in str(error.value)


@pytest.mark.parametrize("parameter", ["menuNo=other", "pdfClsCd=other"])
def test_gazette_url_rejects_wrong_official_query_values(parameter: str) -> None:
    raw = payload()
    raw["source"]["page_url"] = (
        "https://www.assembly.go.kr/portal/cnts/cntsCont/dataA.do?"
        f"cntsDivCd=NAMGZN&pdfId=0&{parameter}"
    )
    with pytest.raises(AssemblyAssetPacketError, match="unsupported query"):
        parse_reviewed_assembly_asset_packet(raw)


def test_gazette_url_canonicalizes_optional_navigation_parameters_before_capture() -> None:
    raw = payload()
    raw["source"]["page_url"] = (
        "https://www.assembly.go.kr:443/portal/cnts/cntsCont/dataA.do?pdfId=0&cntsDivCd=NAMGZN"
    )
    packet = parse_reviewed_assembly_asset_packet(raw)
    capture = build_assembly_asset_capture(packet, artifact_bytes=ARTIFACT_BYTES)
    assert packet.source.page_url == packet.source.canonical_url
    assert capture.snapshot.metadata["parent_page_url"] == packet.source.canonical_url
    assert str(capture.source.url) == packet.source.canonical_url


def test_worker_rejected_url_does_not_echo_private_query_in_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    raw = payload()
    raw["source"]["page_url"] += "&access_token=synthetic-private-canary"
    packet, artifact = write_inputs(tmp_path, raw)
    with pytest.raises(SystemExit):
        main(cli(packet, artifact))
    output = capsys.readouterr()
    assert "synthetic-private-canary" not in output.out + output.err
    assert "unsupported query" in output.err


def _set_amount(item: dict, field: str, text: str, value: int) -> None:
    item[field] = {"text": text, "value": value}


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        # forbidden fields: closed field sets
        (lambda p: first_item(p).update(location="서울특별시 강남구 무슨로 12"), "unsupported"),
        (lambda p: first_item(p).update(account_number="123-456-789012"), "unsupported"),
        (lambda p: first_item(p).update(change_reason="매도"), "unsupported"),
        (lambda p: first_item(p).update(holder_name="합성배우자"), "unsupported"),
        (lambda p: p["members"][0].update(family_names=["갑"]), "unsupported"),
        (lambda p: p.update(person_id="x"), "unsupported"),
        # address-/account-like text inside permitted fields
        (lambda p: first_item(p).update(item_kind="101동 1203호"), "address-like"),
        (lambda p: first_item(p).update(item_kind="무슨로 12"), "address-like"),
        (lambda p: first_item(p).update(item_kind="대지 330㎡"), "address-like"),
        (lambda p: first_item(p).update(item_kind="임야 12-3"), "address-like"),
        (lambda p: first_item(p).update(item_kind="서울특별시 강남구"), "address-like"),
        (lambda p: first_item(p).update(item_kind="계좌 1101-23-456789"), "account-like"),
        (lambda p: first_item(p).update(item_kind="1234567890123"), "account-like"),
        (lambda p: first_item(p).update(item_kind="a@b.co"), "contact details"),
        (lambda p: first_item(p).update(region_sido="서울특별시 강남구"), "시/도 name only"),
        (lambda p: p["members"][0]["items"][2].update(item_kind="예금"), "relative-held"),
        (lambda p: first_item(p).update(holder_relation="장남"), "holder_relation"),
        # amounts and totals
        (lambda p: _set_amount(first_item(p), "current_value", "120,000", 120001), "differs"),
        (
            lambda p: _set_amount(first_item(p), "current_value", "120,000(실거래)", 120000),
            "plain printed amount",
        ),
        (
            lambda p: _set_amount(first_item(p), "current_value", "120,001", 120001),
            "differ from declared total",
        ),
        (
            lambda p: _set_amount(
                p["members"][0]["declared_totals"], "prior_value", "160,001", 160001
            ),
            "differ from declared total",
        ),
        (lambda p: first_item(p).update(current_value=None), "current_value is required"),
        (lambda p: first_item(p).update(prior_value=None), "cannot be cross-checked"),
        # scope, identity and source
        (lambda p: p["members"][0].update(printed_position="사무총장"), "member-level only"),
        (lambda p: p["members"][0].update(report_type="퇴직"), "정기 issues"),
        (
            lambda p: p["members"][0].update(reviewer_stated_mona_cd="bad code"),
            "mona_cd is invalid",
        ),
        (lambda p: p["members"][0].update(mona_cd_basis=None), "stated together"),
        (
            lambda p: p["members"][1].update(
                reviewer_stated_mona_cd="SYNTH001", mona_cd_basis="dup"
            ),
            "repeats",
        ),
        (lambda p: p["members"][0]["items"][1]["locator"].update(table_row=2), "unique"),
        (lambda p: p.update(declared_member_count=3), "declared_member_count"),
        (lambda p: p["source"].update(page_url="https://example.com/x"), "official https"),
        (
            lambda p: p["source"].update(
                page_url="https://www.assembly.go.kr/portal/cnts/cntsCont/dataA.do?"
                "cntsDivCd=NAMGZN&pdfId=1"
            ),
            "pdf_id",
        ),
        (lambda p: p["source"].update(automation_gate="OPEN"), "automation gate"),
        (lambda p: p["source"].update(gazette_issue="2098-1"), "year differs"),
        (lambda p: p["source"].update(artifact_sha256="abc"), "artifact_sha256"),
        (lambda p: p.update(review_status="PUBLISHED"), "review_status"),
        (lambda p: p.update(coverage="EVERYTHING"), "coverage"),
    ],
)
def test_packet_rejects_unsafe_shapes(mutate, message: str) -> None:  # type: ignore[no-untyped-def]
    raw = copy.deepcopy(payload())
    mutate(raw)
    with pytest.raises(AssemblyAssetPacketError, match=message):
        parse_reviewed_assembly_asset_packet(raw)


def test_registration_reports_carry_only_current_value() -> None:
    raw = copy.deepcopy(payload())
    raw["source"]["disclosure_kind"] = "수시"
    raw["members"][1]["report_type"] = "최초등록"
    with pytest.raises(AssemblyAssetPacketError, match="registration reports"):
        parse_reviewed_assembly_asset_packet(raw)
    member = raw["members"][1]
    member["declared_totals"] = {
        "prior_value": None,
        "increase": None,
        "decrease": None,
        "current_value": {"text": "311,500", "value": 311500},
    }
    for item in member["items"]:
        item.update(prior_value=None, increase=None, decrease=None)
    packet = parse_reviewed_assembly_asset_packet(raw)
    assert packet.members[1].report_type == "최초등록"
    assert packet.members[1].declared_totals["prior_value"] is None


def test_zero_and_negative_amounts_are_distinct_from_blank() -> None:
    raw = copy.deepcopy(payload())
    packet = parse_reviewed_assembly_asset_packet(raw)
    decrease = packet.members[0].items[0].amounts["decrease"]
    assert decrease is not None and decrease.value == 0
    raw["members"][0]["declared_totals"]["decrease"] = {"text": "△15,000", "value": -15000}
    parsed = parse_reviewed_assembly_asset_packet(raw)
    declared = parsed.members[0].declared_totals["decrease"]
    assert declared is not None and declared.value == -15000


def test_capture_requires_human_review_pdf_and_exact_sha() -> None:
    with pytest.raises(AssemblyAssetImportError, match="HUMAN_REVIEWED"):
        build_assembly_asset_capture(
            parse_reviewed_assembly_asset_packet(payload("REVIEW_REQUIRED")),
            artifact_bytes=ARTIFACT_BYTES,
        )
    packet = parse_reviewed_assembly_asset_packet(payload())
    with pytest.raises(AssemblyAssetImportError, match="sha256"):
        build_assembly_asset_capture(packet, artifact_bytes=b"%PDF-1.4\nother\n")
    with pytest.raises(AssemblyAssetImportError, match="not a PDF"):
        build_assembly_asset_capture(packet, artifact_bytes=b"not a pdf")


def test_capture_observations_are_minimized_and_self_held_only() -> None:
    packet = parse_reviewed_assembly_asset_packet(payload())
    capture = build_assembly_asset_capture(packet, artifact_bytes=ARTIFACT_BYTES)
    assert capture.snapshot.fulltext is None
    assert capture.snapshot.content_hash == packet.source.artifact_sha256
    assert capture.snapshot.metadata["value_semantics"] == VALUE_SEMANTICS
    assert capture.policy.can_fetch is False
    assert capture.policy.can_store_fulltext is False
    assert capture.policy.can_send_to_ai is False
    assert str(capture.source.url).startswith("https://www.assembly.go.kr/")

    observations = capture.observations(uuid4())
    kinds = [o.normalized["record_kind"] for o in observations]
    assert kinds.count(RECORD_KIND_MEMBER_TOTAL) == 2
    # 4 + 2 printed items, of which 2 are relative-held and never persisted
    assert kinds.count(RECORD_KIND_ITEM) == 4
    assert capture.excluded_relative_item_count == 2
    items = [o for o in observations if o.normalized["record_kind"] == RECORD_KIND_ITEM]
    assert {o.normalized["holder_relation"] for o in items} == {"SELF"}
    assert "2099-1:p3:t1:r4" not in {o.provider_record_key for o in observations}
    for observation in observations:
        assert "canonical_name" not in observation.normalized
        assert observation.normalized["value_semantics"] == VALUE_SEMANTICS
        assert observation.normalized["amount_unit"] == "THOUSAND_KRW"
        text = json.dumps(observation.normalized, ensure_ascii=False)
        assert "SPOUSE" not in text and "LINEAL_DESCENDANT" not in text
    hints = {o.normalized.get("printed_member_name"): o.identity_hints for o in observations}
    assert hints["합성의원갑"]["link_mode"] == "REVIEW_ONLY_NO_AUTO_LINK"
    assert hints["합성의원을"] == {}


def test_worker_dry_run_is_default_and_writes_nothing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repository, database_url = migrated_repository(tmp_path / "dry.db")
    packet, artifact = write_inputs(tmp_path)
    assert main(cli(packet, artifact, "--database-url", database_url)) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "DRY_RUN"
    assert report["member_count"] == 2
    assert report["self_item_count"] == 4
    assert report["excluded_relative_item_count"] == 2
    assert report["person_materialization"] is False
    with repository.sessions() as session:
        assert session.scalar(select(func.count()).select_from(FeederObservationRow)) == 0
        assert session.scalar(select(func.count()).select_from(SourcePolicyRow)) == 0


def test_worker_refuses_unreviewed_tampered_or_unconfirmed(tmp_path: Path) -> None:
    packet, artifact = write_inputs(tmp_path, payload("REVIEW_REQUIRED"))
    with pytest.raises(SystemExit):
        main(cli(packet, artifact))
    packet, artifact = write_inputs(tmp_path)
    with pytest.raises(SystemExit):
        main(["--packet", str(packet), "--artifact", str(artifact)])
    with pytest.raises(SystemExit):
        main(cli(packet, artifact, "--commit"))
    artifact.write_bytes(b"%PDF-1.4\ntampered\n")
    with pytest.raises(SystemExit):
        main(cli(packet, artifact))


def test_worker_commit_writes_observations_only_and_is_idempotent(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repository, database_url = migrated_repository(tmp_path / "commit.db")
    packet, artifact = write_inputs(tmp_path)
    args = cli(packet, artifact, "--database-url", database_url, "--commit")
    assert main(args) == 0
    first = json.loads(capsys.readouterr().out)
    assert first["status"] == "COMMITTED"
    assert first["observations_created"] == 6
    assert main(args) == 0
    second = json.loads(capsys.readouterr().out)
    assert second["observations_created"] == 0
    assert second["observations_unchanged"] == 6

    with repository.sessions() as session:
        rows = list(session.scalars(select(FeederObservationRow)))
        assert len(rows) == 6
        assert {row.feeder for row in rows} == {ASSEMBLY_ASSET_FEEDER}
        assert session.scalar(select(func.count()).select_from(SourceSnapshotRow)) == 1
        snapshot = session.scalars(select(SourceSnapshotRow)).one()
        assert snapshot.fulltext is None
        for table in (
            PersonRow,
            PersonObservationLinkRow,
            AssetDisclosureRow,
            AssetItemRow,
            ClaimRow,
        ):
            assert session.scalar(select(func.count()).select_from(table)) == 0

    observations = repository.feeder_observations(ASSEMBLY_ASSET_FEEDER, SCOPE)
    with pytest.raises(MaterializationError, match="canonical_name"):
        repository.materialize_feeder_observation(observations[0].id)


def test_corrected_packet_appends_new_observation_without_overwriting(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repository, database_url = migrated_repository(tmp_path / "revision.db")
    packet, artifact = write_inputs(tmp_path)
    assert main(cli(packet, artifact, "--database-url", database_url, "--commit")) == 0
    corrected = payload()
    first_item(corrected)["item_kind"] = "전"
    packet.write_text(json.dumps(corrected, ensure_ascii=False), encoding="utf-8")
    assert main(cli(packet, artifact, "--database-url", database_url, "--commit")) == 0
    capsys.readouterr()
    versions = repository.feeder_observations(ASSEMBLY_ASSET_FEEDER, SCOPE, "2099-1:p3:t1:r2")
    assert sorted(o.normalized["item_kind"] for o in versions) == ["대지", "전"]


def _insert_policy(repository: SqlAlchemyRepository, **overrides: object) -> None:
    policy = gazette_asset_policy().model_copy(update=overrides)
    data = policy.model_dump()
    data["id"] = str(policy.id)
    data["collection_mode"] = policy.collection_mode.value
    with repository.sessions() as session:
        session.add(SourcePolicyRow(**data))
        session.commit()


@pytest.mark.parametrize(
    "overrides",
    [
        {"can_store_metadata": False},
        {"collection_mode": SourceCollectionMode.BLOCKED},
        {"can_fetch": True},
        {"id": uuid4()},
    ],
)
def test_worker_refuses_when_stored_policy_denies(
    tmp_path: Path, overrides: dict[str, object]
) -> None:
    repository, database_url = migrated_repository(tmp_path / "denied.db")
    _insert_policy(repository, **overrides)
    packet, artifact = write_inputs(tmp_path)
    with pytest.raises(SystemExit):
        main(cli(packet, artifact, "--database-url", database_url, "--commit"))
    with repository.sessions() as session:
        assert session.scalar(select(func.count()).select_from(FeederObservationRow)) == 0
