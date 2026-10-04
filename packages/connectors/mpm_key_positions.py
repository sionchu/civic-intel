from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime
from io import BytesIO
from typing import ClassVar
from urllib.parse import urlparse
from uuid import UUID
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile

import httpx

from packages.domain.contracts import SourcePolicy
from packages.domain.enums import SourceCollectionMode

from .base import Connector, ConnectorDocument


class MpmKeyPositionsError(RuntimeError):
    pass


@dataclass(frozen=True)
class MpmKeyPositionsAttachment:
    group: str
    file_id: str
    filename: str
    path: str


@dataclass(frozen=True)
class MpmKeyPositionRecord:
    provider_record_key: str
    attachment_group: str
    attachment_file_id: str
    worksheet_index: int
    worksheet_name: str
    worksheet_row: int
    sequence: int
    as_of_date: date
    department_level_1: str
    department_level_2: str | None
    position_name: str
    person_name: str | None
    grade: str
    responsibilities: str | None
    vacant: bool


POLICY_ID = UUID("18000000-0000-0000-0000-000000000001")
RELEASE_AS_OF = date(2026, 4, 30)
RELEASE_PUBLISHED_AT = datetime(2026, 6, 29, tzinfo=UTC)
DATASET_CATALOG = "https://www.data.go.kr/data/15060548/fileData.do"
PROVIDER_POST = (
    "https://www.mpm.go.kr/mpm/info/hrInfo/hrInfoBoard/"
    "?boardId=bbs_0000000000000130&mode=view&cntId=44&category=&pageIdx="
)
ATTACHMENTS: tuple[MpmKeyPositionsAttachment, ...] = (
    MpmKeyPositionsAttachment(
        group="ministries",
        file_id="FILE_000000100069052",
        filename="2026년 상반기 국가주요직위명부(부).xlsx",
        path=(
            "/board/file/bbs_0000000000000130/44/"
            "FILE_000000100069052/a6f5555e93c259020"
        ),
    ),
    MpmKeyPositionsAttachment(
        group="other",
        file_id="FILE_000000100069053",
        filename="2026년 상반기 국가주요직위명부(처,원.실.위원회.기타).xlsx",
        path=(
            "/board/file/bbs_0000000000000130/44/"
            "FILE_000000100069053/55ff768586253c827"
        ),
    ),
    MpmKeyPositionsAttachment(
        group="agencies",
        file_id="FILE_000000100069054",
        filename="2026년 상반기 국가주요직위명부(청).xlsx",
        path=(
            "/board/file/bbs_0000000000000130/44/"
            "FILE_000000100069054/66e2be5fba5dc9ba2"
        ),
    ),
)
_ATTACHMENTS_BY_GROUP = {item.group: item for item in ATTACHMENTS}
_XLSX_NS = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
_REL_ID = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"


def mpm_key_positions_policy() -> SourcePolicy:
    return SourcePolicy(
        id=POLICY_ID,
        domain="www.mpm.go.kr",
        source_class="official_structured_disclosure",
        collection_mode=SourceCollectionMode.HTTP,
        can_fetch=True,
        can_store_metadata=True,
        can_store_fulltext=False,
        can_send_to_ai=False,
        can_show_excerpt=False,
        can_commercialize=True,
        robots_checked_at=datetime(2026, 10, 4, tzinfo=UTC),
        terms_checked_at=datetime(2026, 10, 4, tzinfo=UTC),
        license="이용허락범위 제한 없음 (data.go.kr dataset 15060548)",
        rate_limit="No published limit; exactly three fixed attachment fetches per reviewed release",
        policy_note=(
            "Dataset-specific review for MPM 국가주요직위명부, data.go.kr 15060548, "
            "and the provider post published 2026-06-29. The catalog licenses this dataset "
            "without use restriction. Civic Intel discards office phone before normalized "
            "content, hashes, observations, logs, or tests. This policy does not authorize "
            "unrelated www.mpm.go.kr pages or files."
        ),
    )


class MpmKeyPositionsConnector(Connector):
    HOST = "www.mpm.go.kr"
    SOURCE_CONTRACT = "mpm_national_key_positions_2026_h1_v1"
    TITLE = "인사혁신처_국가주요직위명부_20260430"
    GROUPS: ClassVar[tuple[str, ...]] = tuple(item.group for item in ATTACHMENTS)

    def __init__(
        self,
        *,
        group: str = "ministries",
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if group not in _ATTACHMENTS_BY_GROUP:
            raise ValueError("unsupported MPM key-position attachment group")
        self.group = group
        self._transport = transport

    @property
    def attachment(self) -> MpmKeyPositionsAttachment:
        return _ATTACHMENTS_BY_GROUP[self.group]

    def for_group(self, group: str) -> MpmKeyPositionsConnector:
        return MpmKeyPositionsConnector(group=group, transport=self._transport)

    def discover(self) -> list[str]:
        return [f"https://{self.HOST}{self.attachment.path}"]

    @classmethod
    def _validated_attachment(cls, url: str) -> MpmKeyPositionsAttachment:
        parsed = urlparse(url)
        if parsed.scheme != "https" or parsed.netloc != cls.HOST:
            raise ValueError("unsupported MPM key-position URL")
        if parsed.query or parsed.fragment:
            raise ValueError("MPM key-position attachment URL must not contain query or fragment")
        for item in ATTACHMENTS:
            if parsed.path == item.path:
                return item
        raise ValueError("unsupported MPM key-position attachment path")

    def fetch(self, url: str) -> ConnectorDocument:
        attachment = self._validated_attachment(url)
        if attachment.group != self.group:
            raise ValueError("MPM key-position URL does not match connector group")
        headers = {
            "User-Agent": os.getenv(
                "CIVIC_HTTP_USER_AGENT", "CivicIntel/0.1 (+contact@example.invalid)"
            )
        }
        try:
            with httpx.Client(transport=self._transport, timeout=30, headers=headers) as client:
                response = client.get(url)
                response.raise_for_status()
                content = response.content
        except httpx.HTTPError:
            raise MpmKeyPositionsError("MPM key-position attachment request failed") from None

        records, sheet_count = parse_mpm_key_positions_xlsx(
            content,
            attachment=attachment,
            as_of_date=RELEASE_AS_OF,
        )
        raw_sha256 = hashlib.sha256(content).hexdigest()
        body = json.dumps(
            [record_to_payload(item) for item in records],
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return ConnectorDocument(
            url=url,
            title=f"{self.TITLE} - {attachment.group}",
            publisher="인사혁신처",
            published_at=RELEASE_PUBLISHED_AT,
            body=body,
            metadata={
                "source_contract": self.SOURCE_CONTRACT,
                "dataset_catalog": DATASET_CATALOG,
                "provider_post": PROVIDER_POST,
                "attachment_group": attachment.group,
                "attachment_file_id": attachment.file_id,
                "attachment_filename": attachment.filename,
                "as_of_date": RELEASE_AS_OF.isoformat(),
                "sheet_count": str(sheet_count),
                "record_count": str(len(records)),
                "raw_sha256": raw_sha256,
                "phone_retained": "false",
            },
        )

    @staticmethod
    def parse_records(document: ConnectorDocument) -> tuple[MpmKeyPositionRecord, ...]:
        try:
            payload = json.loads(document.body)
        except json.JSONDecodeError:
            raise MpmKeyPositionsError("MPM key-position document is not valid JSON") from None
        if not isinstance(payload, list):
            raise MpmKeyPositionsError("MPM key-position document is malformed")
        records: list[MpmKeyPositionRecord] = []
        for row in payload:
            if not isinstance(row, dict):
                raise MpmKeyPositionsError("MPM key-position normalized row is malformed")
            records.append(
                MpmKeyPositionRecord(
                    provider_record_key=_required(row, "provider_record_key"),
                    attachment_group=_required(row, "attachment_group"),
                    attachment_file_id=_required(row, "attachment_file_id"),
                    worksheet_index=int(row["worksheet_index"]),
                    worksheet_name=_required(row, "worksheet_name"),
                    worksheet_row=int(row["worksheet_row"]),
                    sequence=int(row["sequence"]),
                    as_of_date=date.fromisoformat(_required(row, "as_of_date")),
                    department_level_1=_required(row, "department_level_1"),
                    department_level_2=_optional(row, "department_level_2"),
                    position_name=_required(row, "position_name"),
                    person_name=_optional(row, "person_name"),
                    grade=_required(row, "grade"),
                    responsibilities=_optional(row, "responsibilities"),
                    vacant=bool(row["vacant"]),
                )
            )
        return tuple(records)


def record_to_payload(record: MpmKeyPositionRecord) -> dict[str, object]:
    payload = asdict(record)
    payload["as_of_date"] = record.as_of_date.isoformat()
    return payload


def parse_mpm_key_positions_xlsx(
    content: bytes,
    *,
    attachment: MpmKeyPositionsAttachment,
    as_of_date: date,
) -> tuple[tuple[MpmKeyPositionRecord, ...], int]:
    try:
        with ZipFile(BytesIO(content)) as archive:
            shared_strings = _shared_strings(archive)
            workbook = ElementTree.fromstring(archive.read("xl/workbook.xml"))
            relations = ElementTree.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
            relation_targets = {
                item.attrib["Id"]: item.attrib["Target"]
                for item in relations
                if "Id" in item.attrib and "Target" in item.attrib
            }
            sheets = workbook.find("x:sheets", _XLSX_NS)
            if sheets is None:
                raise MpmKeyPositionsError("MPM workbook has no worksheets")
            records: list[MpmKeyPositionRecord] = []
            seen_keys: set[str] = set()
            sheet_count = 0
            for sheet_index, sheet in enumerate(sheets, start=1):
                sheet_count += 1
                name = sheet.attrib.get("name", "").strip()
                relation_id = sheet.attrib.get(_REL_ID)
                if not name or not relation_id or relation_id not in relation_targets:
                    raise MpmKeyPositionsError("MPM workbook worksheet metadata is malformed")
                target = relation_targets[relation_id]
                path = target.lstrip("/") if target.startswith("/") else f"xl/{target.lstrip('/')}"
                sheet_root = ElementTree.fromstring(archive.read(path))
                parsed = _parse_worksheet(
                    sheet_root,
                    shared_strings=shared_strings,
                    attachment=attachment,
                    worksheet_index=sheet_index,
                    worksheet_name=name,
                    as_of_date=as_of_date,
                )
                for record in parsed:
                    if record.provider_record_key in seen_keys:
                        raise MpmKeyPositionsError("duplicate MPM provider record key")
                    seen_keys.add(record.provider_record_key)
                    records.append(record)
    except (BadZipFile, KeyError, ElementTree.ParseError):
        raise MpmKeyPositionsError("MPM key-position XLSX is malformed") from None
    if not records or sheet_count == 0:
        raise MpmKeyPositionsError("MPM key-position workbook is empty")
    return tuple(records), sheet_count


def _shared_strings(archive: ZipFile) -> tuple[str, ...]:
    if "xl/sharedStrings.xml" not in archive.namelist():
        return ()
    root = ElementTree.fromstring(archive.read("xl/sharedStrings.xml"))
    values = []
    for item in root.findall("x:si", _XLSX_NS):
        values.append("".join(node.text or "" for node in item.iterfind(".//x:t", _XLSX_NS)))
    return tuple(values)


def _parse_worksheet(
    root: ElementTree.Element,
    *,
    shared_strings: tuple[str, ...],
    attachment: MpmKeyPositionsAttachment,
    worksheet_index: int,
    worksheet_name: str,
    as_of_date: date,
) -> tuple[MpmKeyPositionRecord, ...]:
    rows = root.findall(".//x:sheetData/x:row", _XLSX_NS)
    header_seen = False
    records: list[MpmKeyPositionRecord] = []
    for row in rows:
        row_number = int(row.attrib.get("r", "0"))
        cells = _row_values(row, shared_strings)
        if not header_seen:
            if _is_header(cells):
                header_seen = True
            continue
        sequence_text = cells.get(1, "").strip()
        if not sequence_text:
            continue
        if not sequence_text.isdigit():
            continue
        position = cells.get(4, "").strip()
        name = cells.get(5, "").strip()
        grade = cells.get(6, "").strip()
        department_1 = cells.get(2, "").strip()
        if not all((position, name, grade, department_1)):
            raise MpmKeyPositionsError(
                f"MPM worksheet {worksheet_name!r} row {row_number} lacks required fields"
            )
        vacant = name == "공석"
        person_name = None if vacant else name
        provider_key = (
            f"{attachment.file_id}:{worksheet_index}:{row_number}"
        )
        records.append(
            MpmKeyPositionRecord(
                provider_record_key=provider_key,
                attachment_group=attachment.group,
                attachment_file_id=attachment.file_id,
                worksheet_index=worksheet_index,
                worksheet_name=worksheet_name,
                worksheet_row=row_number,
                sequence=int(sequence_text),
                as_of_date=as_of_date,
                department_level_1=department_1,
                department_level_2=_none_if_blank(cells.get(3)),
                position_name=position,
                person_name=person_name,
                grade=grade,
                responsibilities=_none_if_blank(cells.get(7)),
                vacant=vacant,
            )
        )
    if not header_seen:
        raise MpmKeyPositionsError(f"MPM worksheet {worksheet_name!r} lacks the expected header")
    if not records:
        raise MpmKeyPositionsError(f"MPM worksheet {worksheet_name!r} has no data rows")
    return tuple(records)


def _row_values(
    row: ElementTree.Element,
    shared_strings: tuple[str, ...],
) -> dict[int, str]:
    values: dict[int, str] = {}
    for cell in row.findall("x:c", _XLSX_NS):
        column = _column_number(cell.attrib.get("r", ""))
        if column is None:
            continue
        if column > 8:
            break
        cell_type = cell.attrib.get("t")
        value_node = cell.find("x:v", _XLSX_NS)
        value = "" if value_node is None or value_node.text is None else value_node.text
        if cell_type == "s" and value:
            try:
                value = shared_strings[int(value)]
            except (ValueError, IndexError):
                raise MpmKeyPositionsError("MPM workbook shared-string reference is invalid") from None
        elif cell_type == "inlineStr":
            value = "".join(
                node.text or "" for node in cell.iterfind(".//x:t", _XLSX_NS)
            )
        values[column] = value.strip()
    return values


def _column_number(reference: str) -> int | None:
    match = re.match(r"([A-Z]+)", reference)
    if match is None:
        return None
    value = 0
    for char in match.group(1):
        value = value * 26 + ord(char) - 64
    return value


def _compact_header(value: str) -> str:
    return re.sub(r"\s+", "", value)


def _is_header(cells: dict[int, str]) -> bool:
    return (
        _compact_header(cells.get(1, "")) == "연번"
        and _compact_header(cells.get(2, "")).startswith("1)소속부서")
        and _compact_header(cells.get(4, "")).startswith("2)직위")
        and _compact_header(cells.get(5, "")).startswith("3)성명")
        and _compact_header(cells.get(6, "")).startswith("4)직급")
        and _compact_header(cells.get(7, "")).startswith("5)담당업무")
        and "전화번호" in _compact_header(cells.get(8, ""))
    )


def _required(row: dict[str, object], key: str) -> str:
    value = row.get(key)
    text = "" if value is None else str(value).strip()
    if not text:
        raise MpmKeyPositionsError(f"MPM normalized row lacks {key}")
    return text


def _optional(row: dict[str, object], key: str) -> str | None:
    value = row.get(key)
    return _none_if_blank(value)


def _none_if_blank(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
