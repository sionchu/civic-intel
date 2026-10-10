"""Single R-ONE official housing-volume month, local-only L2 evidence capture.

No scheduled sync, Person association, operational database writes, or public map
publication. The only live request is explicitly scoped to one national month.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping
from contextlib import suppress
from datetime import date
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, HTTPSHandler, Request, build_opener
from uuid import UUID, uuid5

from sqlalchemy.exc import SQLAlchemyError

from packages.connectors.reb_market_statistics import (
    HOUSING_ENDPOINT,
    HOUSING_TABLE,
    L2_REGION,
    L2_SOURCE_CONTRACT,
    REGIONAL_SALE_TABLES,
    RebHousingResearchPage,
    RebMarketStatError,
    RebRegionalSalesPage,
    parse_reb_housing_l2_month,
    parse_reb_national_sale_month,
    require_reb_market_l2_policy,
)
from packages.domain.contracts import (
    FeederObservation,
    Source,
    SourcePolicy,
    SourceSnapshot,
)
from packages.domain.enums import SourceRunStatus
from packages.persistence import SqlAlchemyRepository
from packages.persistence.repository import source_policy_semantics_equal

# Preserve existing canonical housing SourceRun/checkpoint identity.
FEEDER = "reb_reporting_date_housing_volume"
SALE_FEEDER = "reb_reporting_date_sales_volume"
SEMANTIC_SCOPE = "regional_official_trade_statistics_not_person_ownership"
_NAMESPACE = UUID("47a82e65-5668-4f17-964d-15654e345a0b")
MAX_JSON_BYTES = 120_000


def _month(value: str) -> str:
    if not isinstance(value, str) or len(value) != 6 or not value.isascii() or not value.isdigit():
        raise RebMarketStatError("requested R-ONE reporting month must be six digits")
    try:
        date(int(value[:4]), int(value[4:]), 1)
    except ValueError:
        raise RebMarketStatError("invalid R-ONE reporting month") from None
    return value


def scope_key(month: str, *, table: str = HOUSING_TABLE) -> str:
    allowed = {HOUSING_TABLE} | {x["statbl_id"] for x in REGIONAL_SALE_TABLES.values()}
    if table not in allowed:
        raise RebMarketStatError("R-ONE source table is not in the reviewed catalog")
    return f"{table}:CLS:{L2_REGION}:ITM:100001:MM:{_month(month)}"


class _NoProviderRedirect(HTTPRedirectHandler):
    """R-ONE authenticated requests must never follow cross-host redirects."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _fetch_one_page(
    *,
    table: str,
    month: str,
    policy: SourcePolicy,
    key: str,
    opener: Callable[[Request], Any] | None,
) -> Mapping[str, Any]:
    """One reviewed metadata-only R-ONE query, with no request URL logging."""
    require_reb_market_l2_policy(policy)
    scope_key(month, table=table)
    if not isinstance(key, str) or not 8 <= len(key) <= 512 or any(c.isspace() for c in key):
        raise RebMarketStatError("R-ONE issued key is missing or malformed")
    query = {
        "KEY": key,
        "STATBL_ID": table,
        "DTACYCLE_CD": "MM",
        "CLS_ID": L2_REGION,
        "ITM_ID": "100001",
        "START_WRTTIME": month,
        "END_WRTTIME": month,
        "Type": "json",
        "pIndex": "1",
        "pSize": "1",
    }
    request = Request(HOUSING_ENDPOINT + "?" + urlencode(query))
    try:
        if opener is None:
            with build_opener(HTTPSHandler(debuglevel=0), _NoProviderRedirect()).open(
                request, timeout=18
            ) as response:
                if response.status != 200:
                    raise RebMarketStatError("R-ONE response was not HTTP 200")
                content = response.read(MAX_JSON_BYTES + 1)
        else:
            with opener(request) as response:
                if response.status != 200:
                    raise RebMarketStatError("R-ONE response was not HTTP 200")
                content = response.read(MAX_JSON_BYTES + 1)
        if not 0 < len(content) <= MAX_JSON_BYTES:
            raise RebMarketStatError("R-ONE response size outside bounded limit")
        result: Any = json.loads(content)
    except (URLError, OSError, ValueError) as exc:
        if isinstance(exc, RebMarketStatError):
            raise
        raise RebMarketStatError("R-ONE request or response failed") from None
    if not isinstance(result, Mapping):
        raise RebMarketStatError("R-ONE response must be a JSON object")
    return result


def fetch_one_month(
    *,
    month: str,
    policy: SourcePolicy,
    key: str,
    opener: Callable[[Request], Any] | None = None,
) -> RebHousingResearchPage:
    """Original all-housing-volume source lane."""
    result = _fetch_one_page(
        table=HOUSING_TABLE, month=month, policy=policy, key=key, opener=opener
    )
    return parse_reb_housing_l2_month(result, month=month, region_code=L2_REGION, policy=policy)


def fetch_one_sale_month(
    *,
    kind: str,
    month: str,
    policy: SourcePolicy,
    key: str,
    opener: Callable[[Request], Any] | None = None,
) -> RebRegionalSalesPage:
    """Exact one-table/one-month nationwide apartment/land sale data."""
    if kind not in REGIONAL_SALE_TABLES:
        raise RebMarketStatError("R-ONE regional sale kind not approved")
    result = _fetch_one_page(
        table=REGIONAL_SALE_TABLES[kind]["statbl_id"],
        month=month,
        policy=policy,
        key=key,
        opener=opener,
    )
    return parse_reb_national_sale_month(result, kind=kind, month=month, policy=policy)


def capture_one_month(
    page: RebHousingResearchPage | RebRegionalSalesPage,
    *,
    month: str,
    policy: SourcePolicy,
    run_id: UUID,
    kind: str = "housing_volume",
) -> tuple[Source, SourceSnapshot, FeederObservation]:
    """Minimize a reviewed R-ONE market row; never retain source fulltext or identities."""
    require_reb_market_l2_policy(policy)
    _month(month)
    if page.publishable or page.provider_total_count != 1 or len(page.rows) != 1:
        raise RebMarketStatError("one-month capture requires exactly one nonpublishable row")
    if kind == "housing_volume":
        if not isinstance(page, RebHousingResearchPage):
            raise RebMarketStatError("housing contract and response type differ")
        table = HOUSING_TABLE
        contract = L2_SOURCE_CONTRACT
        unit = "동(호)수"
        quantity_name = "reported_housing_units"
        housing_row = page.rows[0]
        if housing_row.month != month or housing_row.region_code != L2_REGION:
            raise RebMarketStatError("R-ONE housing capture scope mismatch")
        region_label = housing_row.region_label
        quantity = housing_row.reported_housing_units
    else:
        if (
            kind not in REGIONAL_SALE_TABLES
            or not isinstance(page, RebRegionalSalesPage)
            or page.kind != kind
            or page.rows[0].kind != kind
        ):
            raise RebMarketStatError("sale type and official R-ONE page do not match")
        spec = REGIONAL_SALE_TABLES[kind]
        table = spec["statbl_id"]
        unit = spec["unit"]
        contract = f"reb_{kind}_reporting_date_l2"
        quantity_name = "reported_sale_units"
        sale_row = page.rows[0]
        if sale_row.month != month or sale_row.region_code != L2_REGION:
            raise RebMarketStatError("R-ONE sale capture scope mismatch")
        region_label = sale_row.region_label
        quantity = sale_row.count
    source = Source(
        id=uuid5(_NAMESPACE, "reb-housing-official-api"),
        url=HOUSING_ENDPOINT,  # NEVER include KEY or any request query.
        title="한국부동산원 R-ONE 부동산 거래현황 공식 통계 API",
        publisher="한국부동산원",
        published_at=None,
        policy_id=policy.id,
    )
    normalized: dict[str, Any] = {
        "source_contract": contract,
        "provider_table": table,
        "item_id": "100001",
        "unit": unit,
        "reported_month": month,
        "region_namespace": "RONE_CLS_ID_NOT_MOLIT_LAWD_CD",
        "region_code": L2_REGION,
        "region_label": region_label,
        quantity_name: quantity,
        "statistical_basis": "RONE_REPORTED_DATE",
        "coverage": "ONE_NATIONAL_MONTH_ONLY",
        "publication": "NOT_APPROVED",
        "person_linkage": "NONE",
    }
    payload = json.dumps(
        normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode()
    digest = hashlib.sha256(payload).hexdigest()
    scoped = scope_key(month, table=table)
    snapshot = SourceSnapshot(
        id=uuid5(_NAMESPACE, "snapshot:" + digest),
        source_id=source.id,
        content_hash=digest,
        metadata={
            "source_contract": contract,
            "provider_total_count": page.provider_total_count,
            "row_count": page.sampled_row_count,
            "scope_key": scoped,
            "query": {
                "STATBL_ID": table,
                "CLS_ID": L2_REGION,
                "ITM_ID": "100001",
                "DTACYCLE_CD": "MM",
                "START_WRTTIME": month,
                "END_WRTTIME": month,
                "pIndex": "1",
                "pSize": "1",
            },
            "provider_history": "UNKNOWN",
            "published": False,
        },
        fulltext=None,
    )
    observation = FeederObservation(
        id=uuid5(_NAMESPACE, "observation:" + digest),
        feeder=FEEDER if kind == "housing_volume" else SALE_FEEDER,
        scope_key=scoped,
        provider_record_key=f"{table}:{L2_REGION}:100001:{month}",
        snapshot_id=snapshot.id,
        run_id=run_id,
        provider_observed_at=None,
        semantic_scope=SEMANTIC_SCOPE,
        identity_hints={},
        normalized=normalized,
        content_hash=digest,
    )
    return source, snapshot, observation


def commit_one_month(
    repository: SqlAlchemyRepository,
    *,
    page: RebHousingResearchPage | RebRegionalSalesPage,
    month: str,
    policy: SourcePolicy,
    kind: str = "housing_volume",
) -> dict[str, object]:
    """Commit to existing canonical repository; policy must be registered FIRST."""
    require_reb_market_l2_policy(policy)
    repository.assert_ready()
    stored = repository.policies([policy.id]).get(policy.id)
    if stored is None or not source_policy_semantics_equal(stored, policy):
        raise RebMarketStatError("an exact stored R-ONE policy is required before any import")
    preflight = capture_one_month(
        page,
        month=month,
        policy=policy,
        run_id=uuid5(_NAMESPACE, "preflight"),
        kind=kind,
    )
    scoped = preflight[2].scope_key
    contract = preflight[2].normalized["source_contract"]
    feeder = FEEDER if kind == "housing_volume" else SALE_FEEDER
    run = repository.start_source_run(
        feeder,
        scoped,
        metadata={
            "source_contract": contract,
            "source_kind": kind,
            "publication": "NOT_APPROVED",
        },
    )
    try:
        source, snapshot, observation = capture_one_month(
            page, month=month, policy=policy, run_id=run.id, kind=kind
        )
        committed = repository.commit_source_page(
            run_id=run.id,
            policy=policy,
            source=source,
            snapshot=snapshot,
            observations=[observation],
            cursor=month,
            checkpoint_metadata={
                "source_contract": contract,
                "provider_total_count": page.provider_total_count,
                "region_code": L2_REGION,
                "reported_month": month,
                "publication": "NOT_APPROVED",
            },
            require_stored_policy_match=True,
        )
    except Exception:
        with suppress(ValueError, RuntimeError, SQLAlchemyError):
            repository.finish_source_run(
                run.id,
                SourceRunStatus.FAILED,
                error_code="REB_L2_COMMIT_ERROR",
                error_summary="Single-month R-ONE capture failed; no credentials recorded",
            )
        raise
    # The page is already committed. A status-transition failure must not mark
    # committed evidence as FAILED: leave the run for explicit operator recovery.
    finished = repository.finish_source_run(run.id, SourceRunStatus.SUCCESS)
    return {
        "status": finished.status.value,
        "scope_key": scoped,
        "snapshot_id": str(committed.snapshot_id),
        "observations_created": committed.observations_created,
        "observations_unchanged": committed.observations_unchanged,
        "publication": "NOT_APPROVED",
    }


def read_issued_key_from_env_file(path: Path) -> str:
    """Read a single private RONE_API_KEY assignment; never log file contents."""
    if not path.is_file() or path.stat().st_mode & 0o077:
        raise RebMarketStatError("R-ONE credential file must exist with private permissions")
    import re

    keys: list[str] = []
    for line in path.read_text("utf-8").splitlines():
        hit = re.fullmatch(r"\s*(?:export\s+)?RONE_API_KEY\s*=\s*(.*?)\s*", line)
        if hit:
            key = hit.group(1).strip()
            if len(key) >= 2 and key[0] == key[-1] and key[0] in ('"', "'"):
                key = key[1:-1]
            keys.append(key)
    if len(keys) != 1 or not 8 <= len(keys[0]) <= 512:
        raise RebMarketStatError("exactly one nonempty issued R-ONE credential is required")
    return keys[0]
