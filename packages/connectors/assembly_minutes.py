"""National Assembly committee minutes (회의록): packet contract and speaker-turn parser.

The parser consumes the per-page *layout-mode* text layer of one exact official minutes PDF
(``record.assembly.go.kr``) and returns ordered speaker turns. It is deterministic and
conservative:

- The official PDF text layer encodes no space glyphs. Layout-mode whitespace is derived from
  glyph geometry and is not exact, so it is used only to classify lines and split the printed
  speaker label. Every stored text value is the exact glyph sequence with all whitespace
  removed (``PDF_GLYPH_SEQUENCE_NO_WHITESPACE``). Spaces are never re-inserted, lines are joined
  without inserting characters and nothing is de-hyphenated, repaired or synthesized.
- Page headers are removed only when they match the expected ``제N회-위원회제N차(날짜)`` form.
- Whole-line parenthesized stage directions (``(「예」하는위원있음)``, ``(14시07분)``) are kept
  separately and never become quote text.
- Cover pages (before ``(..시..분개의)``) and appendices (after ``(..시..분산회)``: 출석위원,
  보고사항, 제안설명서 ...) are excluded from turns.
- Any ambiguity fails closed with :class:`AssemblyMinutesParseError`.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date
from typing import Any
from urllib.parse import parse_qs, urlparse

PARSER_REVISION = "assembly-minutes-turns.r1"
TEXT_FORM = "PDF_GLYPH_SEQUENCE_NO_WHITESPACE"
MINUTES_PACKET_SCHEMA = "assembly-minutes-packet.v1"
ACQUISITION_CHANNEL = "OPERATOR_SUPPLIED_OFFICIAL_PDF"
MINUTES_HOST = "record.assembly.go.kr"
MINUTES_PDF_PATH = "/assembly/viewer/minutes/download/pdf.do"
SPEAKER_MARK = "◯"

# Exact Open Assembly `ncwgseseafwbuheph` (위원회 회의록) row fields.
API_ROW_FIELDS = frozenset(
    {
        "CONFER_NUM",
        "TITLE",
        "CLASS_NAME",
        "DAE_NUM",
        "COMM_NAME",
        "VODCOMM_CODE",
        "CONF_DATE",
        "SUB_NAME",
        "VOD_LINK_URL",
        "CONF_LINK_URL",
        "PDF_LINK_URL",
        "PDF_FILE_ID",
        "DEPT_CD",
        "CONF_ID",
    }
)
_MEETING_FIELDS = (
    "CONFER_NUM",
    "TITLE",
    "CLASS_NAME",
    "DAE_NUM",
    "COMM_NAME",
    "CONF_DATE",
    "PDF_LINK_URL",
    "PDF_FILE_ID",
    "CONF_ID",
)

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_WS = re.compile(r"\s+")
_HEADER = re.compile(
    r"^(?P<lead>\d{1,4})?제(?P<session>\d{1,4})회-(?P<committee>[^\d()]+?)"
    r"제(?P<sitting>\d{1,3})차\((?P<y>\d{4})년(?P<m>\d{1,2})월(?P<d>\d{1,2})일\)"
    r"(?P<trail>\d{1,4})?$"
)
_TITLE = re.compile(
    r"^제(?P<dae>\d{1,3})대제(?P<session>\d{1,4})회제(?P<sitting>\d{1,3})차"
    r"(?P<committee>.+?)\((?P<y>\d{4})년(?P<m>\d{2})월(?P<d>\d{2})일\)$"
)
_STAGE = re.compile(r"^\((?:[^()]|\([^()]*\))*\)$")
_OPEN = re.compile(r"^\((?P<h>\d{1,2})시(?P<min>\d{2})분개의\)$")
_CLOSE = re.compile(r"^\((?P<h>\d{1,2})시(?P<min>\d{2})분산회\)$")
_TIME = re.compile(r"^\(\d{1,2}시\d{2}분\)$")
_LEADER = re.compile(r"·{3,}(?P<page>\d{1,4})$")
# Hanja names may use CJK Compatibility Ideographs (e.g. U+F9E1); kept exactly as printed,
# never NFKC-normalized.
_NAME = re.compile(r"^(?:[가-힣]{2,4}|[\u4e00-\u9fff\uf900-\ufaff]{2,4})$")
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")

MEMBER_ROLES = frozenset({"위원", "의원"})
PRESIDING_ROLES = frozenset({"위원장", "위원장대리", "소위원장", "의장", "부의장"})
HEARING_ROLES = frozenset({"진술인", "공술인"})
WITNESS_ROLES = frozenset({"증인", "참고인"})
STAFF_ROLES = frozenset({"수석전문위원", "전문위원", "입법심의관", "입법조사관"})
# Printed government titles are matched by suffix only; the category is derived, not a fact.
GOVERNMENT_TITLE_SUFFIXES = (
    "장관",
    "차관",
    "청장",
    "처장",
    "원장",
    "실장",
    "국장",
    "본부장",
    "총장",
    "차장",
    "부장",
    "단장",
    "직무대리",
    "위원장",
)
# Appendix-only labels ("◯출석 위원", "◯청가 위원") must never appear inside the body.
APPENDIX_LABEL_TOKENS = frozenset({"출석", "청가", "출장", "결석"})


class AssemblyMinutesParseError(ValueError):
    """Minutes packet or text layer cannot be interpreted without guessing."""


def glyphs(text: str) -> str:
    """Exact glyph sequence: every whitespace character removed, nothing else changed."""

    return _WS.sub("", text)


def _canonical_hash(payload: object) -> str:
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()


# --------------------------------------------------------------------------- packet


@dataclass(frozen=True)
class MinutesMeeting:
    """One meeting, aggregated from its Open Assembly 위원회 회의록 rows."""

    confer_num: int
    conf_id: str
    dae_num: int
    class_name: str
    comm_name: str
    title: str
    conf_date: date
    session: int
    sitting: int
    pdf_link_url: str
    pdf_file_id: int
    agenda_items: tuple[str, ...]

    @property
    def meeting_key(self) -> str:
        return str(self.confer_num)

    def normalized(self) -> dict[str, object]:
        return {
            "confer_num": self.confer_num,
            "conf_id": self.conf_id,
            "dae_num": self.dae_num,
            "class_name": self.class_name,
            "comm_name": self.comm_name,
            "title": self.title,
            "conf_date": self.conf_date.isoformat(),
            "session": self.session,
            "sitting": self.sitting,
            "pdf_link_url": self.pdf_link_url,
            "pdf_file_id": self.pdf_file_id,
            "agenda_items": list(self.agenda_items),
        }


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise AssemblyMinutesParseError(f"minutes packet lacks {label}")
    if _EMAIL.search(value):
        raise AssemblyMinutesParseError(f"minutes packet {label} must not contain contacts")
    return value.strip()


def _int(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise AssemblyMinutesParseError(f"minutes packet {label} must be a positive integer")
    return value


def validate_minutes_pdf_url(url: str, confer_num: int) -> str:
    parsed = urlparse(url)
    query = parse_qs(parsed.query, keep_blank_values=True)
    if (
        parsed.scheme != "https"
        or parsed.hostname != MINUTES_HOST
        or parsed.path != MINUTES_PDF_PATH
        or parsed.username
        or parsed.password
        or parsed.fragment
        or set(query) != {"id"}
        or query["id"] != [str(confer_num)]
    ):
        raise AssemblyMinutesParseError(
            "minutes PDF_LINK_URL must be the exact official record.assembly.go.kr "
            "pdf.do?id=<CONFER_NUM> URL"
        )
    return url


def meeting_from_api_rows(rows: Sequence[Mapping[str, Any]]) -> MinutesMeeting:
    """Aggregate one meeting's API rows (one row per agenda item); all must agree."""

    if not rows:
        raise AssemblyMinutesParseError("minutes packet has no Open Assembly rows")
    for row in rows:
        if not isinstance(row, Mapping):
            raise AssemblyMinutesParseError("minutes packet row is malformed")
        unknown = sorted(set(row) - API_ROW_FIELDS)
        if unknown:
            raise AssemblyMinutesParseError(
                f"minutes packet row contains unsupported fields: {', '.join(unknown)}"
            )
    first = rows[0]
    for row in rows[1:]:
        for key in _MEETING_FIELDS:
            if row.get(key) != first.get(key):
                raise AssemblyMinutesParseError(
                    f"minutes packet rows disagree on {key}; one packet is one meeting"
                )
    confer_num = _int(first.get("CONFER_NUM"), "CONFER_NUM")
    dae_num = _int(first.get("DAE_NUM"), "DAE_NUM")
    title = _text(first.get("TITLE"), "TITLE")
    comm_name = _text(first.get("COMM_NAME"), "COMM_NAME")
    try:
        conf_date = date.fromisoformat(_text(first.get("CONF_DATE"), "CONF_DATE"))
    except ValueError:
        raise AssemblyMinutesParseError("minutes packet CONF_DATE is invalid") from None
    match = _TITLE.match(glyphs(title))
    if match is None:
        raise AssemblyMinutesParseError("minutes packet TITLE is not in the official form")
    if (
        int(match["dae"]) != dae_num
        or match["committee"] != glyphs(comm_name)
        or date(int(match["y"]), int(match["m"]), int(match["d"])) != conf_date
    ):
        raise AssemblyMinutesParseError("minutes packet TITLE disagrees with row fields")
    agenda: list[str] = []
    for row in rows:
        sub = row.get("SUB_NAME")
        if sub is not None:
            item = _text(sub, "SUB_NAME")
            if item not in agenda:
                agenda.append(item)
    return MinutesMeeting(
        confer_num=confer_num,
        conf_id=_text(first.get("CONF_ID"), "CONF_ID"),
        dae_num=dae_num,
        class_name=_text(first.get("CLASS_NAME"), "CLASS_NAME"),
        comm_name=comm_name,
        title=title,
        conf_date=conf_date,
        session=int(match["session"]),
        sitting=int(match["sitting"]),
        pdf_link_url=validate_minutes_pdf_url(
            _text(first.get("PDF_LINK_URL"), "PDF_LINK_URL"), confer_num
        ),
        pdf_file_id=_int(first.get("PDF_FILE_ID"), "PDF_FILE_ID"),
        agenda_items=tuple(agenda),
    )


@dataclass(frozen=True)
class MinutesPacket:
    meeting: MinutesMeeting
    artifact_sha256: str
    received_via: str

    def normalized(self) -> dict[str, object]:
        return {
            "schema": MINUTES_PACKET_SCHEMA,
            "acquisition_channel": ACQUISITION_CHANNEL,
            "artifact_sha256": self.artifact_sha256,
            "received_via": self.received_via,
            "meeting": self.meeting.normalized(),
        }

    @property
    def content_hash(self) -> str:
        return _canonical_hash(self.normalized())


def parse_minutes_packet(raw: Mapping[str, Any]) -> MinutesPacket:
    if not isinstance(raw, Mapping):
        raise AssemblyMinutesParseError("minutes packet is malformed")
    unknown = sorted(
        set(raw) - {"schema", "acquisition_channel", "artifact_sha256", "received_via", "api_rows"}
    )
    if unknown:
        raise AssemblyMinutesParseError(
            f"minutes packet contains unsupported fields: {', '.join(unknown)}"
        )
    if raw.get("schema") != MINUTES_PACKET_SCHEMA:
        raise AssemblyMinutesParseError("minutes packet schema is unsupported")
    if raw.get("acquisition_channel") != ACQUISITION_CHANNEL:
        raise AssemblyMinutesParseError("minutes packet acquisition_channel is unsupported")
    sha = raw.get("artifact_sha256")
    if not isinstance(sha, str) or not _SHA256.fullmatch(sha):
        raise AssemblyMinutesParseError("minutes packet artifact_sha256 is invalid")
    rows = raw.get("api_rows")
    if not isinstance(rows, list):
        raise AssemblyMinutesParseError("minutes packet api_rows must be a list")
    return MinutesPacket(
        meeting=meeting_from_api_rows(rows),
        artifact_sha256=sha,
        received_via=_text(raw.get("received_via"), "received_via"),
    )


# --------------------------------------------------------------------------- parser


@dataclass(frozen=True)
class PageHeader:
    printed_page: int
    session: int
    committee_label: str
    sitting: int
    meeting_date: date


@dataclass(frozen=True)
class _Line:
    pdf_page: int
    printed_page: int
    raw: str
    glyphs: str
    after_blank: bool


@dataclass
class SpeakerTurn:
    ordinal: int
    speaker_label_raw: str
    speaker_role: str
    speaker_name: str | None
    speaker_role_category: str
    agenda_items: tuple[str, ...]
    last_time_marker: str | None
    page_start: int
    page_end: int
    pdf_page_start: int
    pdf_page_end: int
    segments: list[str] = field(default_factory=list)
    stage_directions: list[str] = field(default_factory=list)

    @property
    def quote_text(self) -> str:
        """Segments split by in-turn stage directions, joined with a newline marker."""

        return "\n".join(self.segments)

    @property
    def quote_sha256(self) -> str:
        return hashlib.sha256(self.quote_text.encode("utf-8")).hexdigest()

    @property
    def quote_char_length(self) -> int:
        return sum(len(segment) for segment in self.segments)

    @property
    def contains_inline_parenthetical(self) -> bool:
        return any("(" in segment or ")" in segment for segment in self.segments)


@dataclass(frozen=True)
class ParsedMinutes:
    header: PageHeader
    pdf_page_count: int
    printed_page_first: int
    printed_page_last: int
    agenda_index: tuple[str, ...]
    open_marker: str
    close_marker: str
    appendix_line_count: int
    turns: tuple[SpeakerTurn, ...]

    @property
    def turns_hash(self) -> str:
        return _canonical_hash(
            [[t.ordinal, t.speaker_label_raw, t.quote_sha256] for t in self.turns]
        )


def parse_page_header(line: str) -> PageHeader:
    match = _HEADER.match(glyphs(line))
    if match is None:
        raise AssemblyMinutesParseError("minutes page does not start with the official header")
    lead, trail = match["lead"], match["trail"]
    if (lead is None) == (trail is None):
        raise AssemblyMinutesParseError("minutes page header has an ambiguous page number")
    return PageHeader(
        printed_page=int(lead or trail or 0),
        session=int(match["session"]),
        committee_label=match["committee"],
        sitting=int(match["sitting"]),
        meeting_date=date(int(match["y"]), int(match["m"]), int(match["d"])),
    )


def _lines(pages: Sequence[str]) -> tuple[PageHeader, list[_Line]]:
    if not pages:
        raise AssemblyMinutesParseError("minutes text layer has no pages")
    header: PageHeader | None = None
    out: list[_Line] = []
    for index, page in enumerate(pages, start=1):
        raw_lines = page.splitlines()
        cursor = 0
        while cursor < len(raw_lines) and not raw_lines[cursor].strip():
            cursor += 1
        if cursor == len(raw_lines):
            raise AssemblyMinutesParseError(f"minutes PDF page {index} has no text layer")
        page_header = parse_page_header(raw_lines[cursor])
        if header is None:
            header = page_header
            if page_header.printed_page != 1:
                raise AssemblyMinutesParseError("minutes must start at printed page 1")
        elif (
            page_header.session,
            page_header.committee_label,
            page_header.sitting,
            page_header.meeting_date,
        ) != (header.session, header.committee_label, header.sitting, header.meeting_date):
            raise AssemblyMinutesParseError(f"minutes PDF page {index} belongs to another meeting")
        if page_header.printed_page != index - 1 + header.printed_page:
            raise AssemblyMinutesParseError(f"minutes PDF page {index} printed page is out of order")
        blank = True
        for raw in raw_lines[cursor + 1 :]:
            if not raw.strip():
                blank = True
                continue
            out.append(
                _Line(
                    pdf_page=index,
                    printed_page=page_header.printed_page,
                    raw=raw,
                    glyphs=glyphs(raw),
                    after_blank=blank,
                )
            )
            blank = False
    assert header is not None
    return header, out


def _agenda_index(cover: Sequence[_Line]) -> tuple[str, ...]:
    start = next((i for i, line in enumerate(cover) if line.glyphs == "상정된안건"), None)
    if start is None:
        raise AssemblyMinutesParseError("minutes cover lacks the 상정된 안건 index")
    items: list[str] = []
    pending = ""
    for line in cover[start + 1 :]:
        leader = _LEADER.search(line.glyphs)
        if leader is None:
            pending += line.glyphs
            continue
        title = pending + line.glyphs[: leader.start()]
        pending = ""
        if not title:
            raise AssemblyMinutesParseError("minutes agenda index entry is empty")
        if title in items:
            raise AssemblyMinutesParseError("minutes agenda index repeats an entry")
        items.append(title)
    if pending or not items:
        raise AssemblyMinutesParseError("minutes agenda index is incomplete")
    return tuple(items)


def _role_category(role: str, *, member_form: bool) -> str:
    if member_form:
        return "COMMITTEE_MEMBER"
    if role in PRESIDING_ROLES:
        return "PRESIDING_OFFICER"
    if role in HEARING_ROLES:
        return "HEARING_STATEMENT"
    if role in WITNESS_ROLES:
        return "WITNESS_OR_REFERENCE"
    if role in STAFF_ROLES:
        return "COMMITTEE_STAFF"
    if role.endswith(GOVERNMENT_TITLE_SUFFIXES):
        return "GOVERNMENT_TITLE_SUFFIX"
    return "UNCLASSIFIED"


def _known_role(role: str) -> bool:
    return _role_category(role, member_form=False) != "UNCLASSIFIED"


def split_speaker_line(line: _Line) -> tuple[str, str, str | None, str, str]:
    """Return (label_glyphs, role, name, role_category, rest_glyphs) or fail closed."""

    body = line.raw.strip()
    if not body.startswith(SPEAKER_MARK):
        raise AssemblyMinutesParseError("speaker line lacks the ◯ marker")
    tokens = body[len(SPEAKER_MARK) :].split()
    where = f"PDF page {line.pdf_page}"
    if not tokens:
        raise AssemblyMinutesParseError(f"minutes speaker label is empty ({where})")
    if tokens[0] in APPENDIX_LABEL_TOKENS:
        raise AssemblyMinutesParseError(f"minutes appendix label inside the body ({where})")
    candidates: list[tuple[int, str, str, str]] = []
    # "윤용근 위원": printed name then member role.
    if len(tokens) >= 2 and tokens[1] in MEMBER_ROLES and _NAME.match(tokens[0]):
        candidates.append((2, tokens[1], tokens[0], _role_category(tokens[1], member_form=True)))
    # "위원장 한병도" / "행정안전부차관 김민재" / "대통령경호처 ...본부장직무대리 홍길동".
    for width in (1, 2):
        if len(tokens) > width:
            role = "".join(tokens[:width])
            name = tokens[width]
            if _known_role(role) and _NAME.match(name):
                candidates.append(
                    (width + 1, role, name, _role_category(role, member_form=False))
                )
                break
    if len(candidates) != 1:
        raise AssemblyMinutesParseError(
            f"minutes speaker label is not uniquely parseable ({where})"
        )
    width, role, name, category = candidates[0]
    label = "".join(tokens[:width])
    if not line.glyphs.startswith(SPEAKER_MARK + label):
        raise AssemblyMinutesParseError(f"minutes speaker label glyphs drifted ({where})")
    rest = line.glyphs[len(SPEAKER_MARK) + len(label) :]
    return label, role, name, category, rest


def parse_minutes_pages(pages: Sequence[str]) -> ParsedMinutes:
    """Parse per-page layout-mode text of exactly one official committee minutes PDF."""

    header, lines = _lines(pages)
    opens = [i for i, line in enumerate(lines) if _OPEN.match(line.glyphs)]
    closes = [i for i, line in enumerate(lines) if _CLOSE.match(line.glyphs)]
    if len(opens) != 1 or len(closes) != 1 or closes[0] <= opens[0]:
        raise AssemblyMinutesParseError(
            "minutes must contain exactly one 개의 marker followed by one 산회 marker"
        )
    open_at, close_at = opens[0], closes[0]
    agenda = _agenda_index(lines[:open_at])
    body = lines[open_at + 1 : close_at]

    turns: list[SpeakerTurn] = []
    current: SpeakerTurn | None = None
    agenda_cursor = 0
    agenda_block: tuple[str, ...] = ()
    in_heading_block = False
    time_marker: str | None = None
    segment_open = False
    index = 0
    while index < len(body):
        line = body[index]
        text = line.glyphs
        if text.startswith(SPEAKER_MARK) or _STAGE.match(text):
            in_heading_block = False
        if _STAGE.match(text):
            if _TIME.match(text):
                time_marker = text
            if current is not None:
                current.stage_directions.append(text)
            segment_open = False
            index += 1
            continue
        if text.startswith(SPEAKER_MARK):
            label, role, name, category, rest = split_speaker_line(line)
            current = SpeakerTurn(
                ordinal=len(turns) + 1,
                speaker_label_raw=label,
                speaker_role=role,
                speaker_name=name,
                speaker_role_category=category,
                agenda_items=agenda_block,
                last_time_marker=time_marker,
                page_start=line.printed_page,
                page_end=line.printed_page,
                pdf_page_start=line.pdf_page,
                pdf_page_end=line.pdf_page,
            )
            turns.append(current)
            segment_open = False
            if rest and _STAGE.match(rest):
                current.stage_directions.append(rest)
            elif rest:
                current.segments.append(rest)
                segment_open = True
            index += 1
            continue
        # Agenda heading: preceded by a blank line (or directly continuing a heading block
        # that takes up several items together) and exactly the next index entry, possibly
        # wrapped over consecutive lines. Anything else is turn text.
        if (line.after_blank or in_heading_block) and agenda_cursor < len(agenda):
            expected = agenda[agenda_cursor]
            joined, span = "", 0
            while index + span < len(body) and expected.startswith(
                joined + body[index + span].glyphs
            ):
                joined += body[index + span].glyphs
                span += 1
                if joined == expected:
                    break
            if joined == expected:
                agenda_block = (*agenda_block, expected) if in_heading_block else (expected,)
                in_heading_block = True
                agenda_cursor += 1
                current = None
                index += span
                continue
        if any(text == item for item in agenda[agenda_cursor:]):
            raise AssemblyMinutesParseError(
                f"minutes agenda heading out of index order (PDF page {line.pdf_page})"
            )
        if current is None:
            raise AssemblyMinutesParseError(
                f"minutes text has no preceding speaker (PDF page {line.pdf_page})"
            )
        if segment_open:
            current.segments[-1] += text
        else:
            current.segments.append(text)
            segment_open = True
        current.page_end = line.printed_page
        current.pdf_page_end = line.pdf_page
        index += 1

    if not turns:
        raise AssemblyMinutesParseError("minutes body contains no speaker turns")
    return ParsedMinutes(
        header=header,
        pdf_page_count=len(pages),
        printed_page_first=header.printed_page,
        printed_page_last=header.printed_page + len(pages) - 1,
        agenda_index=agenda,
        open_marker=lines[open_at].glyphs,
        close_marker=lines[close_at].glyphs,
        appendix_line_count=len(lines) - close_at - 1,
        turns=tuple(turns),
    )
