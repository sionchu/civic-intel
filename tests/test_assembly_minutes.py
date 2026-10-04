from __future__ import annotations

import copy
import hashlib
import json
from collections.abc import Callable
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import func, select

from packages.connectors.assembly_minutes import (
    PARSER_REVISION,
    TEXT_FORM,
    AssemblyMinutesParseError,
    parse_minutes_packet,
    parse_minutes_pages,
)
from packages.domain.db import (
    ClaimRow,
    FeederObservationRow,
    PersonObservationLinkRow,
    PersonRow,
    SourceCheckpointRow,
    SourceSnapshotRow,
)
from packages.persistence import SqlAlchemyRepository
from packages.verification.assembly_minutes_import import (
    ASSEMBLY_MINUTES_FEEDER,
    AssemblyMinutesImportError,
    assembly_minutes_policy,
    build_assembly_minutes_capture,
)
from workers import assembly_minutes_import as worker

PAGES_FIXTURE = Path("tests/fixtures/assembly_minutes_synthetic_pages.json")
PACKET_FIXTURE = Path("tests/fixtures/assembly_minutes_synthetic_packet.json")
ARTIFACT_BYTES = b"SYNTHETIC-ASSEMBLY-MINUTES-PDF-FIXTURE\n"
EXTRACTOR = "synthetic-test-extractor"
SCOPE = f"22:99901:{PARSER_REVISION}"
COMPAT_LI = chr(0xF9E1)  # CJK Compatibility Ideograph as printed in real minutes


def pages() -> list[str]:
    return list(json.loads(PAGES_FIXTURE.read_text(encoding="utf-8"))["pages"])


def packet_raw() -> dict:
    return json.loads(PACKET_FIXTURE.read_text(encoding="utf-8"))


def capture(**overrides):  # type: ignore[no-untyped-def]
    kwargs = {
        "artifact_bytes": ARTIFACT_BYTES,
        "pages": pages(),
        "extractor": EXTRACTOR,
    } | overrides
    return build_assembly_minutes_capture(parse_minutes_packet(packet_raw()), **kwargs)


# ---------------------------------------------------------------- parser


def test_parser_returns_ordered_turns_with_exact_glyph_quotes() -> None:
    parsed = parse_minutes_pages(pages())
    assert parsed.header.committee_label == "합성시험"
    assert parsed.header.session == 901 and parsed.header.sitting == 2
    assert parsed.agenda_index == ("1.가나다법일부개정법률안", "2.2026년도국정감사서류제출요구의건")
    assert [t.ordinal for t in parsed.turns] == list(range(1, 10))
    labels = [t.speaker_label_raw for t in parsed.turns]
    assert labels[:3] == ["위원장가나다", "위원장가나다", "마바사위원"]

    opening = parsed.turns[0]
    assert opening.agenda_items == ()
    assert opening.segments == [
        "의석을정돈해주시기바랍니다.성원이되었으므로회의를개회하겠습니다.",
        "그러면의사일정에들어가겠습니다.",
    ]
    # Stage directions never become quote text.
    assert opening.stage_directions == ["(보고사항은끝에실음)"]
    assert "보고사항" not in opening.quote_text
    assert opening.quote_sha256 == hashlib.sha256(opening.quote_text.encode()).hexdigest()
    assert opening.quote_char_length == sum(len(s) for s in opening.segments)


def test_parser_stage_directions_agenda_and_time_markers() -> None:
    turns = parse_minutes_pages(pages()).turns
    vote = turns[1]
    assert vote.agenda_items == ("1.가나다법일부개정법률안",)
    assert vote.last_time_marker == "(10시01분)"
    assert vote.stage_directions == ["(「예」하는위원있음)"]
    assert vote.segments == ["의사일정제1항을상정합니다.이의없으십니까?", "가결되었음을선포합니다."]
    raised_hand = turns[2]
    assert raised_hand.segments == [] and raised_hand.quote_char_length == 0
    assert raised_hand.stage_directions == ["(손을듦)"]
    assert turns[-1].agenda_items == ("2.2026년도국정감사서류제출요구의건",)
    assert turns[-1].last_time_marker == "(10시05분)"


def test_parser_removes_page_headers_and_joins_lines_without_inserting_text() -> None:
    spanning = parse_minutes_pages(pages()).turns[4]
    assert (spanning.page_start, spanning.page_end) == (1, 2)
    assert (spanning.pdf_page_start, spanning.pdf_page_end) == (1, 2)
    # Layout whitespace (even inside a word) is dropped; no space is ever re-inserted.
    assert spanning.quote_text == "자료(별첨)를보면일부조문의정비가필요합니다."
    assert "제901회" not in spanning.quote_text
    assert spanning.contains_inline_parenthetical is True


def test_parser_classifies_printed_roles_and_keeps_compatibility_hanja() -> None:
    turns = parse_minutes_pages(pages()).turns
    hanja = turns[5]
    assert hanja.speaker_name == COMPAT_LI + "東一"  # kept as printed, not NFKC-normalized
    assert hanja.speaker_role == "위원"
    assert hanja.speaker_role_category == "COMMITTEE_MEMBER"
    assert (turns[6].speaker_role, turns[6].speaker_name) == ("합성부차관", "아자차")
    assert turns[6].speaker_role_category == "GOVERNMENT_TITLE_SUFFIX"
    assert turns[7].speaker_role_category == "HEARING_STATEMENT"
    assert turns[0].speaker_role_category == "PRESIDING_OFFICER"


def test_parser_excludes_cover_and_appendix() -> None:
    parsed = parse_minutes_pages(pages())
    assert parsed.open_marker == "(10시00분개의)"
    assert parsed.close_marker == "(10시06분산회)"
    assert parsed.appendix_line_count == 6
    joined = "".join(t.quote_text for t in parsed.turns)
    assert "합성청원인" not in joined and "하하하" not in joined
    assert all(t.speaker_label_raw != "출석위원(3인)" for t in parsed.turns)


HEADER_2 = "2  제901회-합성시험제2차(2026년9월28일)"


def _replace(page: int, old: str, new: str) -> Callable[[list[str]], list[str]]:
    def mutate(items: list[str]) -> list[str]:
        assert old in items[page]
        items[page] = items[page].replace(old, new, 1)
        return items

    return mutate


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (_replace(1, HEADER_2, "합성 머리말"), "official header"),
        (_replace(1, HEADER_2, HEADER_2.replace("2  ", "3  ", 1)), "out of order"),
        (_replace(1, HEADER_2, HEADER_2.replace("901", "902")), "another meeting"),
        (_replace(1, HEADER_2, HEADER_2 + " 2"), "ambiguous page"),
        (_replace(1, "(10시06분 산회)", "(10시06분)"), "산회"),
        (
            _replace(0, " 그러면 의사일정에", "                (10시00분 개의)\n 그러면 의사일정에"),
            "개의",
        ),
        (_replace(1, " 산회를 선포합니다.", "◯ 출석  위원(3인)"), "appendix label"),
        (_replace(1, "◯진술인  카타파", "◯가나 다라마바사아 카타파"), "not uniquely parseable"),
        (_replace(1, "◯진술인  카타파", "◯진술인  카"), "not uniquely parseable"),
        (
            _replace(0, " 1.가나다법  일부개정법률안\n", " 2.2026년도 국정감사 서류제출 요구의 건\n"),
            "out of index order",
        ),
        (
            _replace(
                0,
                "◯위원장  가나다   의사일정 제1항을 상정합니다.",
                " 의사일정 제1항을 상정합니다.",
            ),
            "no preceding speaker",
        ),
        (_replace(0, "   상정된 안건", "   안건 목록"), "상정된 안건"),
    ],
)
def test_parser_fails_closed_on_ambiguity(mutate, message: str) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(AssemblyMinutesParseError, match=message):
        parse_minutes_pages(mutate(pages()))


def test_parser_accepts_grouped_agenda_heading_block() -> None:
    items = pages()
    items[0] = items[0].replace(
        " 1.가나다법  일부개정법률안\n",
        " 1.가나다법  일부개정법률안\n 2.2026년도 국정감사  서류제출 요구의 건\n",
    )
    items[1] = items[1].replace("\n\n 2.2026년도  국정감사  서류제출  요구의  건\n", "\n")
    turns = parse_minutes_pages(items).turns
    assert turns[1].agenda_items == (
        "1.가나다법일부개정법률안",
        "2.2026년도국정감사서류제출요구의건",
    )


def test_parser_is_deterministic() -> None:
    assert parse_minutes_pages(pages()).turns_hash == parse_minutes_pages(pages()).turns_hash


# ---------------------------------------------------------------- packet


def _rows(raw: dict, key: str, old: str, new: str) -> None:
    for row in raw["api_rows"]:
        row[key] = row[key].replace(old, new)


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda raw: raw.update(extra=1), "unsupported fields"),
        (lambda raw: raw.update(schema="v0"), "schema"),
        (lambda raw: raw.update(artifact_sha256="abc"), "artifact_sha256"),
        (
            lambda raw: raw["api_rows"][0].update(
                PDF_LINK_URL=raw["api_rows"][0]["PDF_LINK_URL"].replace("99901", "99902")
            ),
            "disagree",
        ),
        (lambda raw: _rows(raw, "PDF_LINK_URL", "99901", "99902"), "PDF_LINK_URL"),
        (lambda raw: _rows(raw, "PDF_LINK_URL", "https://record.", "https://evil."), "PDF_LINK_URL"),
        (lambda raw: _rows(raw, "PDF_LINK_URL", "?id=", "?serviceKey=x&id="), "PDF_LINK_URL"),
        (lambda raw: _rows(raw, "TITLE", "합성시험", "다른"), "TITLE"),
        (lambda raw: raw["api_rows"][0].update(SECRET="x"), "unsupported fields"),
        (lambda raw: raw.update(api_rows=[]), "no Open Assembly rows"),
        (lambda raw: raw.update(received_via="ops@example.org"), "contacts"),
    ],
)
def test_packet_rejects_unsafe_shapes(mutate, message: str) -> None:  # type: ignore[no-untyped-def]
    raw = copy.deepcopy(packet_raw())
    mutate(raw)
    with pytest.raises(AssemblyMinutesParseError, match=message):
        parse_minutes_packet(raw)


def test_packet_aggregates_agenda_rows_into_one_meeting() -> None:
    meeting = parse_minutes_packet(packet_raw()).meeting
    assert (meeting.confer_num, meeting.session, meeting.sitting) == (99901, 901, 2)
    assert meeting.agenda_items == (
        "1. 가나다법 일부개정법률안",
        "2. 2026년도 국정감사 서류제출 요구의 건",
    )


# ---------------------------------------------------------------- capture / policy


def test_policy_is_official_record_without_fetch_fulltext_or_ai() -> None:
    policy = assembly_minutes_policy()
    assert policy.domain == "record.assembly.go.kr"
    assert policy.can_fetch is False
    assert policy.can_store_fulltext is False
    assert policy.can_send_to_ai is False
    assert policy.can_show_excerpt is True
    assert policy.id == assembly_minutes_policy().id


def test_capture_binds_exact_bytes_and_builds_policy_minimized_observations() -> None:
    built = capture()
    assert built.snapshot.content_hash == hashlib.sha256(ARTIFACT_BYTES).hexdigest()
    assert built.snapshot.fulltext is None
    assert built.snapshot.metadata["fulltext_retained"] is False
    assert built.snapshot.metadata["parser_revision"] == PARSER_REVISION
    assert str(built.source.url).endswith("pdf.do?id=99901")
    observations = built.observations(uuid4())
    assert [o.provider_record_key for o in observations] == [f"99901:{n}" for n in range(1, 10)]
    assert {o.scope_key for o in observations} == {SCOPE}
    assert all(o.identity_hints == {} for o in observations)
    first = observations[0].normalized
    assert first["text_form"] == TEXT_FORM
    assert first["speaker_person_link"] is None
    assert first["quote_text_retained"] is True
    assert first["quote_text"].startswith("의석을정돈해")
    assert first["extractor"] == EXTRACTOR


def test_capture_rejects_sha_mismatch_and_empty_artifact() -> None:
    with pytest.raises(AssemblyMinutesImportError, match="sha256"):
        capture(artifact_bytes=b"tampered")
    with pytest.raises(AssemblyMinutesImportError, match="empty"):
        capture(artifact_bytes=b"")
    with pytest.raises(AssemblyMinutesImportError, match="extractor"):
        capture(extractor=" ")


def test_capture_rejects_text_layer_of_another_meeting() -> None:
    raw = packet_raw()
    for row in raw["api_rows"]:
        row["TITLE"] = row["TITLE"].replace("합성시험위원회", "다른시험위원회")
        row["COMM_NAME"] = "다른시험위원회"
    with pytest.raises(AssemblyMinutesImportError, match="committee"):
        build_assembly_minutes_capture(
            parse_minutes_packet(raw),
            artifact_bytes=ARTIFACT_BYTES,
            pages=pages(),
            extractor=EXTRACTOR,
        )
    raw = packet_raw()
    raw["api_rows"][0]["SUB_NAME"] = "9. 없는 안건"
    with pytest.raises(AssemblyMinutesImportError, match="agenda"):
        build_assembly_minutes_capture(
            parse_minutes_packet(raw),
            artifact_bytes=ARTIFACT_BYTES,
            pages=pages(),
            extractor=EXTRACTOR,
        )


def test_policy_denial_withholds_quote_text_or_blocks_capture() -> None:
    no_excerpt = assembly_minutes_policy().model_copy(update={"can_show_excerpt": False})
    observations = capture(policy=no_excerpt).observations(uuid4())
    for observation in observations:
        assert observation.normalized["quote_text"] is None
        assert observation.normalized["quote_text_retained"] is False
        assert len(observation.normalized["quote_sha256"]) == 64
    assert observations[0].normalized["quote_char_length"] > 0

    no_metadata = assembly_minutes_policy().model_copy(update={"can_store_metadata": False})
    with pytest.raises(AssemblyMinutesImportError, match="metadata"):
        capture(policy=no_metadata)
    foreign = assembly_minutes_policy().model_copy(update={"domain": "example.org"})
    with pytest.raises(AssemblyMinutesImportError, match="policy"):
        capture(policy=foreign)


# ---------------------------------------------------------------- worker


def migrated_repository(database: Path) -> tuple[SqlAlchemyRepository, str]:
    database_url = f"sqlite:///{database.as_posix()}"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(config, "head")
    return SqlAlchemyRepository(database_url), database_url


@pytest.fixture
def inputs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path]:
    packet = tmp_path / "packet.json"
    packet.write_text(json.dumps(packet_raw(), ensure_ascii=False), encoding="utf-8")
    artifact = tmp_path / "minutes.pdf"
    artifact.write_bytes(ARTIFACT_BYTES)

    def fake_extract(data: bytes) -> tuple[list[str], str]:
        assert data == artifact.read_bytes()
        return pages(), EXTRACTOR

    monkeypatch.setattr(worker, "extract_layout_pages", fake_extract)
    return packet, artifact


def cli(packet: Path, artifact: Path, *extra: str) -> list[str]:
    return [
        "--packet",
        str(packet),
        "--artifact",
        str(artifact),
        "--confirm-official-minutes-copy",
        *extra,
    ]


def test_worker_dry_run_is_default_and_writes_nothing(
    tmp_path: Path, inputs: tuple[Path, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    repository, database_url = migrated_repository(tmp_path / "dry.db")
    assert worker.main(cli(*inputs, "--database-url", database_url)) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "DRY_RUN"
    assert report["turns"] == 9
    assert report["person_materialization"] is False
    assert report["claim_publication"] is False
    with repository.sessions() as session:
        assert session.scalar(select(func.count()).select_from(FeederObservationRow)) == 0
        assert session.scalar(select(func.count()).select_from(SourceSnapshotRow)) == 0


def test_worker_refuses_missing_confirmation_database_or_tampered_bytes(
    inputs: tuple[Path, Path],
) -> None:
    packet, artifact = inputs
    with pytest.raises(SystemExit):
        worker.main(["--packet", str(packet), "--artifact", str(artifact)])
    with pytest.raises(SystemExit):
        worker.main(cli(packet, artifact, "--commit"))
    artifact.write_bytes(b"tampered")
    with pytest.raises(SystemExit):
        worker.main(cli(packet, artifact))


def test_worker_commit_is_idempotent_and_never_creates_people_or_claims(
    tmp_path: Path, inputs: tuple[Path, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    repository, database_url = migrated_repository(tmp_path / "commit.db")
    args = cli(*inputs, "--database-url", database_url, "--commit")
    assert worker.main(args) == 0
    first = json.loads(capsys.readouterr().out)
    assert first["status"] == "COMMITTED"
    assert first["observations_created"] == 9
    assert worker.main(args) == 0
    second = json.loads(capsys.readouterr().out)
    assert second["observations_created"] == 0
    assert second["observations_unchanged"] == 9
    assert second["snapshot_id"] == first["snapshot_id"]

    with repository.sessions() as session:
        rows = list(session.scalars(select(FeederObservationRow)))
        assert len(rows) == 9
        assert {row.feeder for row in rows} == {ASSEMBLY_MINUTES_FEEDER}
        assert {row.scope_key for row in rows} == {SCOPE}
        assert all(row.identity_hints_json == {} for row in rows)
        assert session.scalar(select(func.count()).select_from(SourceSnapshotRow)) == 1
        snapshot = session.scalars(select(SourceSnapshotRow)).one()
        assert snapshot.fulltext is None
        checkpoint = session.scalars(select(SourceCheckpointRow)).one()
        assert checkpoint.cursor.startswith(hashlib.sha256(ARTIFACT_BYTES).hexdigest())
        assert session.scalar(select(func.count()).select_from(PersonRow)) == 0
        assert session.scalar(select(func.count()).select_from(PersonObservationLinkRow)) == 0
        assert session.scalar(select(func.count()).select_from(ClaimRow)) == 0
