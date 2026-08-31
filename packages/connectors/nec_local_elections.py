from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import ClassVar
from urllib.parse import parse_qs, urlencode, urlparse
from uuid import UUID

import httpx

from packages.domain.contracts import SourcePolicy
from packages.domain.enums import SourceCollectionMode

from .base import Connector, ConnectorDocument


class NecApiError(RuntimeError):
    pass


class MissingNecApiKey(NecApiError):
    pass


LOCAL_ELECTION_TYPES: dict[int, str] = {
    3: "시·도지사",
    4: "구·시·군의 장",
    5: "시·도의회의원",
    6: "구·시·군의회의원",
    10: "교육의원",
    11: "교육감",
}

POLICY_ID = UUID("12000000-0000-0000-0000-000000000001")


def nec_local_election_policy() -> SourcePolicy:
    reviewed_at = datetime(2026, 8, 31, tzinfo=UTC)
    return SourcePolicy(
        id=POLICY_ID,
        domain="apis.data.go.kr",
        source_class="official_open_api",
        collection_mode=SourceCollectionMode.API,
        can_fetch=True,
        can_store_metadata=True,
        can_store_fulltext=False,
        can_send_to_ai=False,
        can_show_excerpt=False,
        can_commercialize=True,
        terms_checked_at=reviewed_at,
        license="이용허락범위 제한 없음",
        rate_limit=(
            "Development account 10,000 requests; operational account requires review approval"
        ),
        policy_note=(
            "Reviewed against data.go.kr dataset 15000864 on 2026-08-31 for the Central "
            "Election Commission winner API. Civic Intel discards candidate address and stores "
            "only public-interest election metadata."
        ),
    )


@dataclass(frozen=True)
class NecCandidateRecord:
    candidate_id: str
    election_id: str
    election_type: int
    district_name: str
    province_name: str
    municipality_name: str | None
    candidate_number: str | None
    candidate_sub_number: str | None
    party: str | None
    name_ko: str
    name_hanja: str | None
    birth_date: date | None
    public_job: str | None
    submitted_education: str | None
    submitted_careers: tuple[str, ...]
    registration_status: str | None


@dataclass(frozen=True)
class NecWinnerRecord:
    candidate_id: str
    election_id: str
    election_type: int
    district_name: str
    province_name: str
    municipality_name: str | None
    candidate_number: str | None
    candidate_sub_number: str | None
    party: str | None
    name_ko: str
    name_hanja: str | None
    birth_date: date | None
    public_job: str | None
    submitted_education: str | None
    submitted_careers: tuple[str, ...]
    votes: int | None
    vote_rate: float | None


class _NecApiConnector(Connector):
    HOST = "apis.data.go.kr"
    ALLOWED_QUERY: ClassVar[frozenset[str]] = frozenset(
        {
            "pageNo",
            "numOfRows",
            "resultType",
            "sgId",
            "sgTypecode",
            "sggName",
            "sdName",
            "jdName",
        }
    )
    PATH: str
    TITLE: str

    def __init__(
        self,
        *,
        election_id: str,
        election_type: int,
        api_key: str | None = None,
        page_no: int = 1,
        page_size: int = 100,
        district_name: str | None = None,
        province_name: str | None = None,
        party: str | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if election_type not in LOCAL_ELECTION_TYPES:
            raise ValueError("unsupported local election type")
        if page_no < 1:
            raise ValueError("page_no must be >= 1")
        if not 1 <= page_size <= 1000:
            raise ValueError("page_size must be between 1 and 1000")
        self.election_id = election_id
        self.election_type = election_type
        self._api_key = api_key
        self.page_no = page_no
        self.page_size = page_size
        self.district_name = district_name
        self.province_name = province_name
        self.party = party
        self._transport = transport

    @property
    def base_url(self) -> str:
        return f"https://{self.HOST}{self.PATH}"

    def _credential(self) -> str:
        value = self._api_key or os.getenv("NEC_API_KEY")
        if not value:
            raise MissingNecApiKey("NEC_API_KEY is required for live fetch")
        return value

    def discover(self) -> list[str]:
        params: dict[str, str] = {
            "pageNo": str(self.page_no),
            "numOfRows": str(self.page_size),
            "resultType": "json",
            "sgId": self.election_id,
            "sgTypecode": str(self.election_type),
        }
        if self.district_name:
            params["sggName"] = self.district_name
        if self.province_name:
            params["sdName"] = self.province_name
        if self.party:
            params["jdName"] = self.party
        return [f"{self.base_url}?{urlencode(params)}"]

    @classmethod
    def _validated_query(cls, url: str) -> dict[str, str]:
        parsed = urlparse(url)
        if parsed.scheme != "https" or parsed.netloc != cls.HOST or parsed.path != cls.PATH:
            raise ValueError("unsupported NEC API URL")
        raw = parse_qs(parsed.query, keep_blank_values=True)
        if {key.casefold() for key in raw} & {"servicekey", "key", "authkey"}:
            raise ValueError("credentials must not be embedded in connector URLs")
        unknown = set(raw) - cls.ALLOWED_QUERY
        if unknown:
            raise ValueError("unsupported NEC API query parameter")
        query = {key: values[-1] for key, values in raw.items()}
        if query.get("resultType", "json").lower() != "json":
            raise ValueError("connector requires JSON responses")
        if not query.get("sgId") or not query.get("sgTypecode"):
            raise ValueError("sgId and sgTypecode are required")
        return query

    @staticmethod
    def _redact_credentials(value):
        if isinstance(value, dict):
            return {
                key: _NecApiConnector._redact_credentials(item)
                for key, item in value.items()
                if key.casefold() not in {"servicekey", "key", "authkey"}
            }
        if isinstance(value, list):
            return [_NecApiConnector._redact_credentials(item) for item in value]
        return value

    @staticmethod
    def _response_parts(
        payload: dict, service_name: str
    ) -> tuple[list[dict], int | None, int | None, int | None]:
        response = payload.get("response")
        if isinstance(response, dict):
            header = response.get("header")
            if isinstance(header, dict) and str(header.get("resultCode") or "00") not in {"00", "0"}:
                raise NecApiError("NEC API returned a provider error")
            body = response.get("body")
            if not isinstance(body, dict):
                raise NecApiError("NEC API returned a malformed response")
            total = body.get("totalCount")
            try:
                total_count = int(total) if total is not None else None
            except (TypeError, ValueError):
                total_count = None
            try:
                provider_page_no = int(body["pageNo"])
            except (KeyError, TypeError, ValueError):
                provider_page_no = None
            try:
                provider_page_size = int(body["numOfRows"])
            except (KeyError, TypeError, ValueError):
                provider_page_size = None
            items = body.get("items")
            if not items:
                return [], total_count, provider_page_no, provider_page_size
            if isinstance(items, dict):
                candidate_rows = items.get("item", [])
                if isinstance(candidate_rows, dict):
                    return [candidate_rows], total_count, provider_page_no, provider_page_size
                if isinstance(candidate_rows, list):
                    return (
                        [item for item in candidate_rows if isinstance(item, dict)],
                        total_count,
                        provider_page_no,
                        provider_page_size,
                    )
            raise NecApiError("NEC API returned malformed items")

        legacy = payload.get(service_name)
        if isinstance(legacy, dict):
            candidate_rows = legacy.get("item", [])
            if isinstance(candidate_rows, dict):
                return [candidate_rows], None, None, None
            if isinstance(candidate_rows, list):
                return [item for item in candidate_rows if isinstance(item, dict)], None, None, None
        raise NecApiError("NEC API returned a malformed response")

    @staticmethod
    def _optional(row: dict, key: str) -> str | None:
        value = row.get(key)
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @classmethod
    def _birth_date(cls, row: dict) -> date | None:
        value = cls._optional(row, "birthday")
        if not value or len(value) != 8 or not value.isdigit():
            return None
        try:
            return date(int(value[:4]), int(value[4:6]), int(value[6:8]))
        except ValueError:
            return None

    @classmethod
    def _submitted_careers(cls, row: dict) -> tuple[str, ...]:
        return tuple(
            value
            for key in ("career1", "career2")
            if (value := cls._optional(row, key)) and value != "-"
        )

    def fetch(self, url: str) -> ConnectorDocument:
        query = self._validated_query(url)
        request_params = query | {"serviceKey": self._credential()}
        headers = {
            "User-Agent": os.getenv(
                "CIVIC_HTTP_USER_AGENT", "CivicIntel/0.1 (+contact@example.invalid)"
            )
        }
        try:
            with httpx.Client(transport=self._transport, timeout=15, headers=headers) as client:
                response = client.get(self.base_url, params=request_params)
                response.raise_for_status()
                payload = response.json()
        except (httpx.HTTPError, ValueError, json.JSONDecodeError):
            raise NecApiError("NEC API request failed") from None
        if not isinstance(payload, dict):
            raise NecApiError("NEC API returned a malformed response")
        payload = self._redact_credentials(payload)
        rows, total_count, provider_page_no, provider_page_size = self._response_parts(
            payload, self.service_name
        )
        metadata = {
            "service_name": self.service_name,
            "election_id": query["sgId"],
            "election_type": query["sgTypecode"],
            "page_no": query.get("pageNo", "1"),
            "page_size": query.get("numOfRows", "100"),
            "row_count": str(len(rows)),
            "total_count": "" if total_count is None else str(total_count),
            "provider_page_no": "" if provider_page_no is None else str(provider_page_no),
            "provider_page_size": "" if provider_page_size is None else str(provider_page_size),
        }
        for key in ("sggName", "sdName", "jdName"):
            if key in query:
                metadata[key] = query[key]
        return ConnectorDocument(
            url=url,
            title=self.TITLE,
            publisher="중앙선거관리위원회",
            published_at=None,
            body=json.dumps(payload, ensure_ascii=False, sort_keys=True),
            metadata=metadata,
        )

    @property
    def service_name(self) -> str:
        raise NotImplementedError


class NecCandidateConnector(_NecApiConnector):
    PATH = "/9760000/PofelcddInfoInqireService/getPofelcddRegistSttusInfoInqire"
    TITLE = "중앙선거관리위원회_후보자 정보"

    @property
    def service_name(self) -> str:
        return "getPofelcddRegistSttusInfoInqire"

    @classmethod
    def parse_candidates(cls, document: ConnectorDocument) -> list[NecCandidateRecord]:
        try:
            payload = json.loads(document.body)
        except json.JSONDecodeError:
            raise NecApiError("NEC candidate document is not valid JSON") from None
        if not isinstance(payload, dict):
            raise NecApiError("NEC candidate document is malformed")
        rows, _, _, _ = cls._response_parts(payload, "getPofelcddRegistSttusInfoInqire")
        records: list[NecCandidateRecord] = []
        for row in rows:
            candidate_id = cls._optional(row, "huboid")
            election_id = cls._optional(row, "sgId")
            election_type_text = cls._optional(row, "sgTypecode")
            district_name = cls._optional(row, "sggName")
            province_name = cls._optional(row, "sdName")
            name_ko = cls._optional(row, "name")
            if (
                candidate_id is None
                or election_id is None
                or election_type_text is None
                or district_name is None
                or province_name is None
                or name_ko is None
            ):
                raise NecApiError("NEC candidate row lacks required identity fields")
            try:
                election_type = int(election_type_text)
            except ValueError:
                raise NecApiError("NEC candidate row has invalid election type") from None
            if election_type not in LOCAL_ELECTION_TYPES:
                raise NecApiError("NEC candidate row is outside local-election scope")
            records.append(
                NecCandidateRecord(
                    candidate_id=candidate_id,
                    election_id=election_id,
                    election_type=election_type,
                    district_name=district_name,
                    province_name=province_name,
                    municipality_name=cls._optional(row, "wiwName"),
                    candidate_number=cls._optional(row, "giho"),
                    candidate_sub_number=cls._optional(row, "gihoSangse"),
                    party=cls._optional(row, "jdName"),
                    name_ko=name_ko,
                    name_hanja=cls._optional(row, "hanjaName"),
                    birth_date=cls._birth_date(row),
                    public_job=cls._optional(row, "job"),
                    submitted_education=cls._optional(row, "edu"),
                    submitted_careers=cls._submitted_careers(row),
                    registration_status=cls._optional(row, "status"),
                )
            )
        return records


class NecWinnerConnector(_NecApiConnector):
    PATH = "/9760000/WinnerInfoInqireService2/getWinnerInfoInqire"
    TITLE = "중앙선거관리위원회_당선인 정보"

    @property
    def service_name(self) -> str:
        return "getWinnerInfoInqire"

    @staticmethod
    def _int_value(value: object) -> int | None:
        if value in (None, ""):
            return None
        try:
            return int(str(value).replace(",", ""))
        except ValueError:
            return None

    @staticmethod
    def _float_value(value: object) -> float | None:
        if value in (None, ""):
            return None
        try:
            return float(str(value).replace("%", ""))
        except ValueError:
            return None

    @classmethod
    def parse_winners(cls, document: ConnectorDocument) -> list[NecWinnerRecord]:
        try:
            payload = json.loads(document.body)
        except json.JSONDecodeError:
            raise NecApiError("NEC winner document is not valid JSON") from None
        if not isinstance(payload, dict):
            raise NecApiError("NEC winner document is malformed")
        rows, _, _, _ = cls._response_parts(payload, "getWinnerInfoInqire")
        winners: list[NecWinnerRecord] = []
        for row in rows:
            candidate_id = cls._optional(row, "huboid")
            election_id = cls._optional(row, "sgId")
            election_type_text = cls._optional(row, "sgTypecode")
            district_name = cls._optional(row, "sggName")
            province_name = cls._optional(row, "sdName")
            name_ko = cls._optional(row, "name")
            if (
                candidate_id is None
                or election_id is None
                or election_type_text is None
                or district_name is None
                or province_name is None
                or name_ko is None
            ):
                raise NecApiError("NEC winner row lacks required identity fields")
            try:
                election_type = int(election_type_text)
            except ValueError:
                raise NecApiError("NEC winner row has invalid election type") from None
            if election_type not in LOCAL_ELECTION_TYPES:
                raise NecApiError("NEC winner row is outside local-election scope")
            winners.append(
                NecWinnerRecord(
                    candidate_id=candidate_id,
                    election_id=election_id,
                    election_type=election_type,
                    district_name=district_name,
                    province_name=province_name,
                    municipality_name=cls._optional(row, "wiwName"),
                    candidate_number=cls._optional(row, "giho"),
                    candidate_sub_number=cls._optional(row, "gihoSangse"),
                    party=cls._optional(row, "jdName"),
                    name_ko=name_ko,
                    name_hanja=cls._optional(row, "hanjaName"),
                    birth_date=cls._birth_date(row),
                    public_job=cls._optional(row, "job"),
                    submitted_education=cls._optional(row, "edu"),
                    submitted_careers=cls._submitted_careers(row),
                    votes=cls._int_value(row.get("dugsu")),
                    vote_rate=cls._float_value(row.get("dugyul")),
                )
            )
        return winners
