from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any
from uuid import UUID

from packages.domain.contracts import FeederObservation, now_utc

from .base import ConnectorDocument

HISTORICAL_API_CODE = "nfzegpkvaclgtscxt"
HISTORICAL_FEEDER = "assembly_historical_career_review"
HISTORICAL_SEMANTIC_SCOPE = "assembly_historical_member_career"
HISTORICAL_REVIEWED_INPUT_SCOPE = "assembly_historical_reviewed_packet"
SOURCE_RECORD_IDENTITY_UNAVAILABLE = "PROVIDER_ROW_ID_UNAVAILABLE"
NORMALIZATION_REVISION = "assembly-historical-career.v1"


class AssemblyHistoricalCareerError(ValueError):
    """A bounded historical-career packet cannot be interpreted safely."""


def _required_text(row: Mapping[str, Any], field: str) -> str:
    value = row.get(field)
    if value is None:
        raise AssemblyHistoricalCareerError(f"historical career row lacks {field}")
    text = str(value).strip()
    if not text:
        raise AssemblyHistoricalCareerError(f"historical career row has empty {field}")
    return text


def _parse_date(value: str) -> date:
    normalized = value.strip().replace(".", "-").replace("/", "-")
    try:
        return date.fromisoformat(normalized)
    except ValueError:
        raise AssemblyHistoricalCareerError(f"historical career date is invalid: {value}") from None


def _parse_date_range(value: str) -> tuple[date, date]:
    parts = re.split(r"\s*(?:~|～|–|—)\s*", value.strip())
    if len(parts) != 2:
        raise AssemblyHistoricalCareerError(
            "historical career FRTO_DATE must contain an explicit start and end"
        )
    start = _parse_date(parts[0])
    end = _parse_date(parts[1])
    if end < start:
        raise AssemblyHistoricalCareerError("historical career FRTO_DATE ends before it starts")
    return start, end


@dataclass(frozen=True)
class AssemblyHistoricalCareerRecord:
    """A typed row from the historical API, without inventing a row identity."""

    member_code: str
    name_ko: str
    profile_unit_code: str
    profile_unit_name: str
    frto_date: str
    profile_sj: str
    valid_from: date
    valid_to: date

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> AssemblyHistoricalCareerRecord:
        frto_date = _required_text(row, "FRTO_DATE")
        valid_from, valid_to = _parse_date_range(frto_date)
        return cls(
            member_code=_required_text(row, "MONA_CD"),
            name_ko=_required_text(row, "HG_NM"),
            profile_unit_code=_required_text(row, "PROFILE_UNIT_CD"),
            profile_unit_name=_required_text(row, "PROFILE_UNIT_NM"),
            frto_date=frto_date,
            profile_sj=_required_text(row, "PROFILE_SJ"),
            valid_from=valid_from,
            valid_to=valid_to,
        )

    @property
    def provider_record_key(self) -> str:
        """Return the provider-person/term group, not a claimed stable row ID."""

        return f"{self.member_code}:{self.profile_unit_code}"

    def normalized(self) -> dict[str, Any]:
        return {
            "source_fields": {
                "HG_NM": self.name_ko,
                "MONA_CD": self.member_code,
                "PROFILE_UNIT_CD": self.profile_unit_code,
                "PROFILE_UNIT_NM": self.profile_unit_name,
                "FRTO_DATE": self.frto_date,
                "PROFILE_SJ": self.profile_sj,
            },
            "parsed": {
                "frto_start": self.valid_from.isoformat(),
                "frto_end": self.valid_to.isoformat(),
            },
            "provider_record_group_key": self.provider_record_key,
            "provider_record_identity": SOURCE_RECORD_IDENTITY_UNAVAILABLE,
            "correction_semantics": "IMMUTABLE_SNAPSHOT_ONLY",
            "normalization_revision": NORMALIZATION_REVISION,
        }

    @property
    def content_hash(self) -> str:
        payload = json.dumps(
            self.normalized(), ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def to_observation(
        self,
        *,
        run_id: UUID,
        snapshot_id: UUID,
        scope_key: str,
        recorded_at: datetime | None = None,
    ) -> FeederObservation:
        return FeederObservation(
            feeder=HISTORICAL_FEEDER,
            scope_key=scope_key,
            provider_record_key=self.provider_record_key,
            snapshot_id=snapshot_id,
            run_id=run_id,
            recorded_at=recorded_at or now_utc(),
            semantic_scope=HISTORICAL_SEMANTIC_SCOPE,
            identity_hints={
                "canonical_name": self.name_ko,
                "external_ids": {"assembly_mona_cd": self.member_code},
                "provider_namespace": "open.assembly.go.kr",
            },
            normalized=self.normalized(),
            content_hash=self.content_hash,
        )


def parse_historical_career_records(
    document: ConnectorDocument,
) -> tuple[AssemblyHistoricalCareerRecord, ...]:
    """Parse only a supplied bounded API document; this function performs no fetching."""

    try:
        payload = json.loads(document.body)
    except json.JSONDecodeError:
        raise AssemblyHistoricalCareerError("historical career document is not valid JSON") from None
    if not isinstance(payload, dict):
        raise AssemblyHistoricalCareerError("historical career document is malformed")

    blocks = payload.get(HISTORICAL_API_CODE)
    if not isinstance(blocks, list) or not blocks:
        raise AssemblyHistoricalCareerError("historical career response block is missing")

    rows: list[AssemblyHistoricalCareerRecord] = []
    for block in blocks:
        if not isinstance(block, dict):
            continue
        candidate_rows = block.get("row")
        if not isinstance(candidate_rows, list):
            continue
        for row in candidate_rows:
            if not isinstance(row, dict):
                raise AssemblyHistoricalCareerError("historical career row is malformed")
            rows.append(AssemblyHistoricalCareerRecord.from_row(row))
    return tuple(rows)


def validate_reviewed_packet(
    records: tuple[AssemblyHistoricalCareerRecord, ...],
) -> tuple[AssemblyHistoricalCareerRecord, ...]:
    """Reject ambiguous same-person/term packets because the provider has no row key."""

    if not records:
        raise AssemblyHistoricalCareerError("reviewed historical career packet is empty")
    seen: set[str] = set()
    for record in records:
        if record.provider_record_key in seen:
            raise AssemblyHistoricalCareerError(
                "provider row identity is unavailable for repeated person/term group "
                f"{record.provider_record_key}"
            )
        seen.add(record.provider_record_key)
    return records
