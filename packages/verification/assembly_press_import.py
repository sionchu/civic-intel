"""One bounded official press metadata page; no text AI processing or name linkage."""
from __future__ import annotations

import json
import re
from datetime import date, datetime, time, timedelta, timezone
from typing import cast
from uuid import UUID, uuid5

from packages.connectors.base import ConnectorDocument
from packages.connectors.open_assembly_activity_metadata import (
    ACTIVITY_APIS,
    ACTIVITY_CONTRACT,
    LOCATOR_UNVERIFIED,
    normalize_activity_row,
    require_activity_policy,
)
from packages.connectors.open_assembly_press_releases import OpenAssemblyPressReleaseConnector
from packages.domain.contracts import (
    Claim,
    ClaimEvidence,
    FeederObservation,
    IdentityReviewItem,
    Person,
    PersonObservationLink,
    Source,
    SourcePolicy,
    SourceSnapshot,
)
from packages.domain.enums import PublicationStatus
from packages.verification.assembly_asset_import import (
    _require_reviewed_asset_subject,
    assembly_asset_observation_hash,
)
from packages.verification.claims import validate_claim_publication

PRESS_FEEDER = "national_assembly_press_metadata"
PRESS_CONTRACT = OpenAssemblyPressReleaseConnector.SOURCE_CONTRACT
PRESS_PREDICATE = "ASSEMBLY_OFFICIAL_PRESS_RECORD"
PRESS_SCOPE = "official_press_metadata_review_only"
_NS = UUID("160bdbda-c795-453f-9fd0-72a6a67d2732")


def build_activity_capture(raw: object, *, api_code: str, policy: SourcePolicy,
                           run_id: UUID) -> tuple[Source, SourceSnapshot, tuple[FeederObservation, ...]]:
    """Finite supplied page. Unknown stable provider locator blocks linkage/publication."""
    require_activity_policy(policy)
    if (api_code not in ACTIVITY_APIS or not isinstance(raw, dict)
            or set(raw) != {"page_index", "page_size", "list_total_count", "records"}
            or type(raw["page_index"]) is not int or raw["page_index"] < 1
            or type(raw["page_size"]) is not int or not 1 <= raw["page_size"] <= 100
            or type(raw["list_total_count"]) is not int or raw["list_total_count"] < 0
            or not isinstance(raw["records"], list)
            or len(raw["records"]) > min(raw["page_size"], raw["list_total_count"])):
        raise ValueError("ACTIVITY_PAGE_BOUNDARY_INVALID")
    rows = [normalize_activity_row(api_code, row, policy=policy) for row in raw["records"]]
    url = f"https://open.assembly.go.kr/portal/openapi/{api_code}"
    source = Source(id=uuid5(_NS, url), url=url, title="국회 공식 활동 메타데이터",
        publisher="국회사무처", policy_id=policy.id)
    metadata = {"source_contract": ACTIVITY_CONTRACT, "api_code": api_code,
        "page_index": raw["page_index"], "page_size": raw["page_size"],
        "list_total_count": raw["list_total_count"], "records": rows,
        "capture_mode": "SUPPLIED_SCOPED_PROVIDER_METADATA", "coverage": "SELECTED_PAGE_ONLY",
        "query_semantics": "UNVERIFIED_NOT_FETCHED", "record_identity_status": LOCATOR_UNVERIFIED}
    snapshot = SourceSnapshot(source_id=source.id, metadata=metadata, fulltext=None,
        content_hash=assembly_asset_observation_hash(metadata))
    observations = tuple(FeederObservation(feeder=PRESS_FEEDER,
        scope_key=f"activity:{api_code}:supplied-page:{raw['page_index']}",
        provider_record_key=f"staged:{api_code}:{raw['page_index']}:{index}",
        snapshot_id=snapshot.id, run_id=run_id, semantic_scope=PRESS_SCOPE,
        identity_hints={}, normalized=row, content_hash=assembly_asset_observation_hash(row))
        for index, row in enumerate(rows, start=1))
    return source, snapshot, observations


def normalize_press_record(raw: object, *, policy: SourcePolicy) -> dict[str, str]:
    """Closed metadata allowlist. CONTENT/identity hints never survive normalization."""
    OpenAssemblyPressReleaseConnector(policy=policy, written_on=date.min)._gate()
    if not isinstance(raw, dict) or set(raw) != {
        "record_key", "title", "written_date", "category", "source_url",
    }:
        raise ValueError("PRESS_METADATA_FIELDS_INVALID")
    if any(not isinstance(v, str) or not v.strip() or len(v) > 1000 for v in raw.values()):
        raise ValueError("PRESS_METADATA_VALUE_INVALID")
    key = raw["record_key"]
    if not re.fullmatch(r"[1-9][0-9]{0,19}", key):
        raise ValueError("PRESS_RECORD_KEY_INVALID")
    day = date.fromisoformat(raw["written_date"])
    if day.isoformat() != raw["written_date"] or raw["source_url"] != (
        OpenAssemblyPressReleaseConnector.BASE_URL + "?Type=json&NUM=" + key
    ):
        raise ValueError("PRESS_SOURCE_LOCATOR_INVALID")
    return dict(raw)


def build_press_capture(document: ConnectorDocument, *, policy: SourcePolicy,
                        written_on: date, page_index: int, page_size: int,
                        run_id: UUID) -> tuple[Source, SourceSnapshot, tuple[FeederObservation, ...]]:
    connector = OpenAssemblyPressReleaseConnector(policy=policy, written_on=written_on,
        page_index=page_index, page_size=page_size)
    connector._gate()
    if document.url != connector.discover()[0] or document.published_at is not None:
        raise ValueError("PRESS_PAGE_SCOPE_INVALID")
    rows = json.loads(document.body)
    if not isinstance(rows, list) or len(rows) > page_size:
        raise ValueError("PRESS_PAGE_RECORDS_INVALID")
    records = [normalize_press_record(row, policy=policy) for row in rows]
    total = int(document.metadata["list_total_count"])
    if (document.metadata.get("source_contract") != PRESS_CONTRACT
            or document.metadata.get("row_count") != str(len(records))
            or total < len(records)
            or len({row["record_key"] for row in records}) != len(records)
            or any(row["written_date"] != written_on.isoformat() for row in records)):
        raise ValueError("PRESS_PAGE_PROVENANCE_INVALID")
    source = Source(id=uuid5(_NS, document.url), url=document.url,
        title="국회 공식 보도자료 메타데이터", publisher="국회사무처", policy_id=policy.id)
    metadata = {"source_contract": PRESS_CONTRACT, "written_date": written_on.isoformat(),
        "page_index": page_index, "page_size": page_size, "list_total_count": total,
        "records": records, "attribution": "국회사무처", "coverage": "SELECTED_PAGE_ONLY"}
    snapshot = SourceSnapshot(source_id=source.id,
        content_hash=assembly_asset_observation_hash(metadata), metadata=metadata, fulltext=None)
    observations = tuple(FeederObservation(feeder=PRESS_FEEDER,
        scope_key=f"press:{written_on.isoformat()}:selected-pages",
        provider_record_key=row["record_key"], snapshot_id=snapshot.id, run_id=run_id,
        semantic_scope=PRESS_SCOPE, normalized=row, identity_hints={},
        content_hash=assembly_asset_observation_hash(cast(dict[str, object], row))) for row in records)
    return source, snapshot, observations


def build_press_claim(source: Source, snapshot: SourceSnapshot, observation: FeederObservation,
                      *, policy: SourcePolicy, person: Person, link: PersonObservationLink,
                      review: IdentityReviewItem, publication_approved: bool = False
                      ) -> tuple[Claim, ClaimEvidence]:
    row = normalize_press_record(observation.normalized, policy=policy)
    metadata = snapshot.metadata
    if set(metadata) != {"source_contract", "written_date", "page_index", "page_size",
            "list_total_count", "records", "attribution", "coverage"}:
        raise ValueError("PRESS_IMMUTABLE_SOURCE_INVALID")
    try:
        day = date.fromisoformat(row["written_date"])
        connector = OpenAssemblyPressReleaseConnector(policy=policy, written_on=day,
            page_index=metadata["page_index"], page_size=metadata["page_size"])
        records = [normalize_press_record(r, policy=policy) for r in metadata["records"]]
    except (KeyError, TypeError, ValueError):
        raise ValueError("PRESS_IMMUTABLE_SOURCE_INVALID") from None
    if (source.policy_id != policy.id or str(source.url) != connector.discover()[0]
            or source.published_at is not None or snapshot.source_id != source.id
            or snapshot.fulltext is not None or metadata.get("source_contract") != PRESS_CONTRACT
            or metadata.get("written_date") != row["written_date"]
            or metadata.get("coverage") != "SELECTED_PAGE_ONLY"
            or metadata.get("attribution") != "국회사무처"
            or type(metadata.get("list_total_count")) is not int
            or metadata["list_total_count"] < len(records) or len(records) > connector.page_size
            or len({item["record_key"] for item in records}) != len(records)
            or any(item["written_date"] != row["written_date"] for item in records)
            or snapshot.content_hash != assembly_asset_observation_hash(metadata)
            or records.count(row) != 1 or observation.snapshot_id != snapshot.id
            or observation.content_hash != assembly_asset_observation_hash(cast(dict[str, object], row))
            or observation.provider_record_key != row["record_key"]
            or observation.feeder != PRESS_FEEDER or observation.semantic_scope != PRESS_SCOPE
            or observation.scope_key != f"press:{row['written_date']}:selected-pages"
            or observation.identity_hints):
        raise ValueError("PRESS_IMMUTABLE_SOURCE_INVALID")
    _require_reviewed_asset_subject(person, observation, link, review)
    claim = Claim(id=uuid5(_NS, f"{person.id}:{observation.provider_record_key}:{observation.content_hash}"),
        person_id=person.id, subject=person.canonical_name, predicate=PRESS_PREDICATE,
        proposition=f"국회 공식 보도자료 기록: {row['title']}", object_text=row["title"],
        qualifiers={"source_contract": PRESS_CONTRACT,
            "provider_record_key": observation.provider_record_key,
            "immutable_observation_hash": observation.content_hash,
            "review_item_id": str(review.id), "written_date": row["written_date"],
            "category": row["category"], "record_url": row["source_url"],
            "attribution": "국회사무처", "coverage": "REVIEWED_SELECTED_RECORD",
            "identity_basis": "REVIEWED_OFFICIAL_PRESS_SOURCE_CONTEXT"},
        epistemic_status="CLAIM", asserted_as_true=False,
        publication_status=PublicationStatus.PUBLISHED if publication_approved else PublicationStatus.DRAFT,
        valid_from=datetime.combine(day, time(), tzinfo=timezone(timedelta(hours=9))),
        recorded_at=observation.recorded_at)
    evidence = ClaimEvidence(id=uuid5(claim.id, str(observation.id)), claim_id=claim.id,
        source_id=source.id, snapshot_id=snapshot.id, feeder_observation_id=observation.id,
        stance="SUPPORT", excerpt=None)
    if publication_approved and not validate_claim_publication(claim, person, [evidence],
        {source.id: source}, {policy.id: policy}).publishable:
        raise ValueError("PRESS_PUBLICATION_GATE_REJECTED")
    return claim, evidence
