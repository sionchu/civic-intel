"""Metadata-only preparation; this resource has no authoritative Person identifier.

Reviewed resource OBX2DO001030E516625: KOGL attribution, 2026-10-09.
No publication/identity decisions or persistence are performed here. CONTENT and
unreviewed CONTENT_URL routes never cross the ConnectorDocument boundary.
"""

from __future__ import annotations

import json
import os
import re
from datetime import date
from urllib.parse import parse_qs, urlencode, urlsplit

import httpx

from packages.domain.contracts import SourcePolicy
from packages.domain.enums import SourceCollectionMode
from packages.verification.policy import PolicyAction, PolicyDenied, require_policy

from .base import Connector, ConnectorDocument
from .open_assembly import POLICY_ID, AssemblyApiError, MissingAssemblyApiKey


class OpenAssemblyPressReleaseConnector(Connector):
    API_CODE = "ninnagrlaelvtzfnt"
    BASE_URL = f"https://open.assembly.go.kr/portal/openapi/{API_CODE}"
    SOURCE_CONTRACT = "national_assembly_press_release_metadata_v1"

    def __init__(
        self,
        *,
        policy: SourcePolicy,
        written_on: date,
        page_index: int = 1,
        page_size: int = 100,
        api_key: str | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if type(page_index) is not int or page_index < 1:
            raise ValueError("invalid page index")
        if type(page_size) is not int or not 1 <= page_size <= 100:
            raise ValueError("invalid page size")
        if type(written_on) is not date:
            raise ValueError("an exact written date is required")
        self.policy, self.written_on = policy, written_on
        self.page_index, self.page_size = page_index, page_size
        self._api_key, self._transport = api_key, transport

    def _gate(self) -> None:
        require_policy(self.policy, PolicyAction.FETCH)
        require_policy(self.policy, PolicyAction.STORE_METADATA)
        if (
            self.policy.id != POLICY_ID
            or self.policy.domain != "open.assembly.go.kr"
            or self.policy.source_class != "official_open_api"
            or self.policy.collection_mode != SourceCollectionMode.API
        ):
            raise PolicyDenied("press metadata requires the existing Assembly API policy")

    def discover(self) -> list[str]:
        self._gate()
        return [
            self.BASE_URL
            + "?"
            + urlencode(
                {
                    "Type": "json",
                    "pIndex": self.page_index,
                    "pSize": self.page_size,
                    "WRITE_DATE": self.written_on.isoformat(),
                }
            )
        ]

    def fetch(self, url: str) -> ConnectorDocument:
        self._gate()
        # Only this connector's exact date/page request is eligible; no caller URL,
        # credentials, extra filters, duplicate query keys or redirects are accepted.
        parsed = urlsplit(url)
        expected = parse_qs(urlsplit(self.discover()[0]).query)
        if (
            parsed.scheme != "https"
            or parsed.netloc != "open.assembly.go.kr"
            or parsed.path != f"/portal/openapi/{self.API_CODE}"
            or parsed.fragment
            or parse_qs(parsed.query, keep_blank_values=True) != expected
        ):
            raise ValueError("unsupported press metadata URL")
        key = self._api_key or os.getenv("ASSEMBLY_API_KEY")
        if not key:
            raise MissingAssemblyApiKey("ASSEMBLY_API_KEY is required for live fetch")
        params = {name: values[0] for name, values in expected.items()} | {"KEY": key}
        try:
            with httpx.Client(
                transport=self._transport, timeout=15, follow_redirects=False
            ) as client:
                response = client.get(self.BASE_URL, params=params)
                response.raise_for_status()
                payload = response.json()
        except (httpx.HTTPError, ValueError):
            raise AssemblyApiError("Assembly press metadata request failed") from None
        if not isinstance(payload, dict) or not isinstance(payload.get(self.API_CODE), list):
            raise AssemblyApiError("malformed Assembly press metadata response")
        rows, codes, totals = [], [], []
        for block in payload[self.API_CODE]:
            if not isinstance(block, dict):
                raise AssemblyApiError("malformed Assembly press metadata block")
            heads = block.get("head", [])
            if not isinstance(heads, list):
                raise AssemblyApiError("malformed Assembly press metadata head")
            for head in heads:
                if not isinstance(head, dict):
                    raise AssemblyApiError("malformed Assembly press metadata head")
                if "RESULT" in head:
                    result = head["RESULT"]
                    if not isinstance(result, dict):
                        raise AssemblyApiError("malformed Assembly press metadata result")
                    codes.append(result.get("CODE"))
                if "list_total_count" in head:
                    total = head["list_total_count"]
                    if type(total) is not int or total < 0:
                        raise AssemblyApiError("invalid Assembly press metadata count")
                    totals.append(total)
            raw_rows = block.get("row", [])
            if not isinstance(raw_rows, list):
                raise AssemblyApiError("malformed Assembly press metadata rows")
            rows.extend(raw_rows)
        if codes not in (["INFO-000"], ["DATA-000"]) or len(totals) != 1:
            raise AssemblyApiError("Assembly press metadata response is not successful")
        if (
            len(rows) > self.page_size
            or len(rows) > totals[0]
            or (codes == ["DATA-000"] and (rows or totals != [0]))
        ):
            raise AssemblyApiError("Assembly press metadata page exceeds its bounds")
        normalized = [self._normalize(row) for row in rows]
        if len({row["record_key"] for row in normalized}) != len(normalized):
            raise AssemblyApiError("duplicate Assembly press metadata record")
        metadata = {
            "source_contract": self.SOURCE_CONTRACT,
            "api_code": self.API_CODE,
            "list_total_count": str(totals[0]),
            "row_count": str(len(normalized)),
            "attribution": "국회사무처, 열린국회정보 보도자료, 공공누리 출처표시",
            "identity_status": "ENTITY_UNRESOLVED",
        }
        return ConnectorDocument(
            url=url,
            title="국회사무처 보도자료 메타데이터",
            publisher="국회사무처",
            published_at=None,
            body=json.dumps(normalized, ensure_ascii=False, sort_keys=True),
            metadata=metadata,
        )

    def _normalize(self, row: object) -> dict[str, str]:
        if not isinstance(row, dict):
            raise AssemblyApiError("malformed Assembly press metadata row")
        number = row.get("NUM")
        if type(number) is int:
            number = str(number)
        if not isinstance(number, str) or not re.fullmatch(r"[1-9][0-9]{0,19}", number):
            raise AssemblyApiError("invalid Assembly press metadata record key")
        fields = {}
        for name in ("TITLE", "WRITE_DATE", "BBS_TITLE"):
            value = row.get(name)
            if not isinstance(value, str) or not value.strip() or len(value) > 1000:
                raise AssemblyApiError("invalid Assembly press metadata field")
            fields[name] = value.strip()
        if fields["WRITE_DATE"] != self.written_on.isoformat():
            raise AssemblyApiError("Assembly press metadata date is outside the requested date")
        # NUM is provider record identity, never Person identity. A provider CONTENT_URL
        # route has not been reviewed; use the bounded official record API provenance.
        return {
            "record_key": number,
            "title": fields["TITLE"],
            "written_date": fields["WRITE_DATE"],
            "category": fields["BBS_TITLE"],
            "source_url": self.BASE_URL + "?" + urlencode({"Type": "json", "NUM": number}),
        }
