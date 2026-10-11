from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import ClassVar
from urllib.parse import urlparse
from uuid import UUID

import httpx

from packages.domain.contracts import SourcePolicy
from packages.domain.enums import SourceCollectionMode

from .base import Connector, ConnectorDocument


class SeoulPersonnelNoticeError(RuntimeError):
    pass


@dataclass(frozen=True)
class SeoulPersonnelNoticeAttachment:
    board_id: str
    title: str
    create_date: str | None
    update_date: str | None
    organ: str | None
    position: str | None
    start_date: str | None
    end_date: str | None
    date_check: str | None
    file_count: int | None
    file_appd_id: str | None
    appd_file_name: str | None
    file_size: int | None
    file_url: str | None


POLICY_ID = UUID("19000000-0000-0000-0000-000000000001")
DATASET_ID = "OA-2483"
DATASET_PAGE = "https://data.seoul.go.kr/dataList/OA-2483/S/1/datasetView.do"


def seoul_personnel_notice_policy() -> SourcePolicy:
    reviewed_at = datetime(2026, 10, 5, tzinfo=UTC)
    return SourcePolicy(
        id=POLICY_ID,
        domain="datafile.seoul.go.kr",
        source_class="official_open_data_download",
        collection_mode=SourceCollectionMode.HTTP,
        can_fetch=True,
        can_store_metadata=True,
        can_store_fulltext=False,
        can_send_to_ai=False,
        can_show_excerpt=False,
        can_commercialize=True,
        robots_checked_at=reviewed_at,
        terms_checked_at=reviewed_at,
        license="공공누리 제1유형: 출처표시 (상업적 이용 및 변경 가능)",
        rate_limit="No published download-specific limit; one bounded full JSON download per refresh",
        policy_note=(
            "Reviewed on 2026-10-05 against Seoul Open Data Plaza OA-2483 and "
            "data.go.kr dataset 15125788. The dataset declares Seoul Metropolitan Government "
            "as copyright owner, no third-party copyright holder, and KOGL Type 1. "
            "datafile.seoul.go.kr/robots.txt returned 404; the reviewed dataset UI itself "
            "exposes the credential-free JSON download POST. Civic Intel discards author, "
            "phone, email, contents and view count before normalized storage/hashing."
        ),
    )


class SeoulPersonnelNoticeConnector(Connector):
    HOST = "datafile.seoul.go.kr"
    PATH = "/bigfile/iot/sheet/json/download.do"
    DOWNLOAD_URL = f"https://{HOST}{PATH}"
    SOURCE_CONTRACT = "seoul_personnel_oa2483_json_v1"
    TITLE = "서울특별시_인사발령 정보"

    POST_DATA: ClassVar[dict[str, str]] = {
        "srvType": "S",
        "infId": DATASET_ID,
        "serviceKind": "1",
        "pageNo": "1",
        "strWhere": "",
        "strOrderby": "CREATE_DATE DESC",
        "filterCol": "필터선택",
        "txtFilter": "",
    }
    _REQUIRED_SOURCE_FIELDS: ClassVar[frozenset[str]] = frozenset(
        {
            "board_id", "title", "create_date", "update_date", "organ", "position",
            "tel", "email", "contents", "read_cnt", "start_date", "end_date",
            "date_check", "file_count", "file_appd_id", "appd_file_name", "file_size",
            "file_url",
        }
    )

    def __init__(self, *, transport: httpx.BaseTransport | None = None) -> None:
        self._transport = transport

    def discover(self) -> list[str]:
        return [self.DOWNLOAD_URL]

    @classmethod
    def _validate_url(cls, url: str) -> None:
        parsed = urlparse(url)
        if (
            parsed.scheme != "https"
            or parsed.netloc != cls.HOST
            or parsed.path != cls.PATH
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("unsupported Seoul personnel-download URL")

    def fetch(self, url: str) -> ConnectorDocument:
        self._validate_url(url)
        headers = {
            "User-Agent": os.getenv(
                "CIVIC_HTTP_USER_AGENT", "CivicIntel/0.1 (+contact@example.invalid)"
            )
        }
        try:
            with httpx.Client(transport=self._transport, timeout=30, headers=headers) as client:
                response = client.post(url, data=self.POST_DATA)
                response.raise_for_status()
                payload = response.json()
        except (httpx.HTTPError, json.JSONDecodeError, ValueError):
            raise SeoulPersonnelNoticeError("Seoul personnel dataset request failed") from None

        records = self._parse_provider_payload(payload)
        body = json.dumps(
            [record_to_payload(item) for item in records],
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return ConnectorDocument(
            url=url,
            title=self.TITLE,
            publisher="서울특별시",
            published_at=None,
            body=body,
            metadata={
                "source_contract": self.SOURCE_CONTRACT,
                "dataset_id": DATASET_ID,
                "dataset_page": DATASET_PAGE,
                "record_count": str(len(records)),
                "full_download": "true",
                "author_retained": "false",
                "phone_retained": "false",
                "email_retained": "false",
                "contents_retained": "false",
                "read_count_retained": "false",
            },
        )

    @classmethod
    def _parse_provider_payload(
        cls, payload: object
    ) -> tuple[SeoulPersonnelNoticeAttachment, ...]:
        if not isinstance(payload, dict):
            raise SeoulPersonnelNoticeError("Seoul personnel download is malformed")
        description = payload.get("DESCRIPTION")
        rows = payload.get("DATA")
        if not isinstance(description, dict) or not isinstance(rows, list):
            raise SeoulPersonnelNoticeError("Seoul personnel download lacks DESCRIPTION/DATA")
        if not rows:
            raise SeoulPersonnelNoticeError("Seoul personnel download is empty")

        records: list[SeoulPersonnelNoticeAttachment] = []
        seen: set[str] = set()
        for row in rows:
            if not isinstance(row, dict):
                raise SeoulPersonnelNoticeError("Seoul personnel row is malformed")
            missing = cls._REQUIRED_SOURCE_FIELDS - {str(key) for key in row}
            if missing:
                raise SeoulPersonnelNoticeError("Seoul personnel row lacks reviewed source fields")
            board_id = _required(row, "board_id")
            if board_id in seen:
                raise SeoulPersonnelNoticeError("duplicate Seoul personnel BOARD_ID")
            seen.add(board_id)
            records.append(
                SeoulPersonnelNoticeAttachment(
                    board_id=board_id,
                    title=_required(row, "title"),
                    create_date=_optional(row, "create_date"),
                    update_date=_optional(row, "update_date"),
                    organ=_optional(row, "organ"),
                    position=_optional(row, "position"),
                    start_date=_optional(row, "start_date"),
                    end_date=_optional(row, "end_date"),
                    date_check=_optional(row, "date_check"),
                    file_count=_optional_int(row, "file_count"),
                    file_appd_id=_optional(row, "file_appd_id"),
                    appd_file_name=_optional(row, "appd_file_name"),
                    file_size=_optional_int(row, "file_size"),
                    file_url=_optional(row, "file_url"),
                )
            )
        return tuple(records)

    @staticmethod
    def parse_records(
        document: ConnectorDocument,
    ) -> tuple[SeoulPersonnelNoticeAttachment, ...]:
        try:
            payload = json.loads(document.body)
        except json.JSONDecodeError:
            raise SeoulPersonnelNoticeError(
                "Seoul personnel normalized document is invalid JSON"
            ) from None
        if not isinstance(payload, list) or not payload:
            raise SeoulPersonnelNoticeError("Seoul personnel normalized document is malformed")
        records: list[SeoulPersonnelNoticeAttachment] = []
        seen: set[str] = set()
        for row in payload:
            if not isinstance(row, dict):
                raise SeoulPersonnelNoticeError("Seoul personnel normalized row is malformed")
            board_id = _required(row, "board_id")
            if board_id in seen:
                raise SeoulPersonnelNoticeError("duplicate normalized Seoul personnel BOARD_ID")
            seen.add(board_id)
            records.append(
                SeoulPersonnelNoticeAttachment(
                    board_id=board_id,
                    title=_required(row, "title"),
                    create_date=_optional(row, "create_date"),
                    update_date=_optional(row, "update_date"),
                    organ=_optional(row, "organ"),
                    position=_optional(row, "position"),
                    start_date=_optional(row, "start_date"),
                    end_date=_optional(row, "end_date"),
                    date_check=_optional(row, "date_check"),
                    file_count=_optional_int(row, "file_count"),
                    file_appd_id=_optional(row, "file_appd_id"),
                    appd_file_name=_optional(row, "appd_file_name"),
                    file_size=_optional_int(row, "file_size"),
                    file_url=_optional(row, "file_url"),
                )
            )
        return tuple(records)


def record_to_payload(record: SeoulPersonnelNoticeAttachment) -> dict[str, object]:
    return asdict(record)


def _required(row: dict, key: str) -> str:
    value = row.get(key)
    text = "" if value is None else str(value).strip()
    if not text:
        raise SeoulPersonnelNoticeError(f"Seoul personnel row lacks {key}")
    return text


def _optional(row: dict, key: str) -> str | None:
    value = row.get(key)
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _optional_int(row: dict, key: str) -> int | None:
    value = row.get(key)
    if value in (None, ""):
        return None
    try:
        number = float(str(value))
    except (TypeError, ValueError):
        raise SeoulPersonnelNoticeError(f"Seoul personnel row has invalid {key}") from None
    if not number.is_integer() or number < 0:
        raise SeoulPersonnelNoticeError(f"Seoul personnel row has invalid {key}")
    return int(number)
