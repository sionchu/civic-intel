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
    RebHousingResearchPage,
    RebMarketStatError,
    parse_reb_housing_l2_month,
    require_reb_housing_l2_policy,
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

FEEDER = "reb_reporting_date_housing_volume"
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


def scope_key(month: str) -> str:
    return f"{HOUSING_TABLE}:CLS:{L2_REGION}:ITM:100001:MM:{_month(month)}"


class _NoProviderRedirect(HTTPRedirectHandler):
    """R-ONE authenticated requests must never follow cross-host redirects."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def fetch_one_month(
    *,
    month: str,
    policy: SourcePolicy,
    key: str,
    opener: Callable[[Request], Any] | None = None,
) -> RebHousingResearchPage:
    """One bounded official HTTPS request with no HTTPX request-URL INFO logging.

    The supplied opener is for deterministic offline tests only. The real
    client uses a fresh stdlib HTTPS handler with debug logging disabled.
    Failures are translated into fixed messages without a KEY-bearing URL.
    """
    require_reb_housing_l2_policy(policy)
    _month(month)
    if not isinstance(key, str) or not 8 <= len(key) <= 512 or any(c.isspace() for c in key):
        raise RebMarketStatError("R-ONE issued key is missing or malformed")
    query = {
        "KEY": key,
        "STATBL_ID": HOUSING_TABLE,
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
            # New per-call opener, not the process-wide urllib opener. No
            # debug-level request URL tracing or transport logs are enabled.
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
    return parse_reb_housing_l2_month(result, month=month, region_code=L2_REGION, policy=policy)


def capture_one_month(
    page: RebHousingResearchPage,
    *,
    month: str,
    policy: SourcePolicy,
    run_id: UUID,
) -> tuple[Source, SourceSnapshot, FeederObservation]:
    """Prepare only minimized Source/Snapshot/Observation, never provider fulltext."""
    require_reb_housing_l2_policy(policy)
    _month(month)
    if page.publishable or page.provider_total_count != 1 or len(page.rows) != 1:
        raise RebMarketStatError("single month capture requires exactly one unpublishable row")
    record = page.rows[0]
    if record.month != month or record.region_code != L2_REGION:
        raise RebMarketStatError("R-ONE capture scope differs from the requested month")
    source = Source(
        id=uuid5(_NAMESPACE, "reb-housing-official-api"),
        url=HOUSING_ENDPOINT,  # NEVER place the KEY or other request params in Source URLs
        title="한국부동산원 부동산거래현황 — 전국 월별 주택거래량",
        publisher="한국부동산원",
        published_at=None,  # A reporting month is not a source publication date.
        policy_id=policy.id,
    )
    normalized: dict[str, Any] = {
        "source_contract": L2_SOURCE_CONTRACT,
        "provider_table": HOUSING_TABLE,
        "item_id": "100001",
        "unit": "동(호)수",
        "reported_month": month,
        "region_namespace": "RONE_CLS_ID_NOT_MOLIT_LAWD_CD",
        "region_code": L2_REGION,
        "region_label": record.region_label,
        "reported_housing_units": record.reported_housing_units,
        "statistical_basis": "RONE_REPORTED_DATE",
        "coverage": "ONE_NATIONAL_MONTH_ONLY",
        "publication": "NOT_APPROVED",
        "person_linkage": "NONE",
    }
    payload = json.dumps(
        normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode()
    digest = hashlib.sha256(payload).hexdigest()
    snapshot = SourceSnapshot(
        id=uuid5(_NAMESPACE, "snapshot:" + digest),
        source_id=source.id,
        content_hash=digest,
        metadata={
            "source_contract": L2_SOURCE_CONTRACT,
            "provider_total_count": page.provider_total_count,
            "row_count": page.sampled_row_count,
            "scope_key": scope_key(month),
            "query": {
                "STATBL_ID": HOUSING_TABLE,
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
        feeder=FEEDER,
        scope_key=scope_key(month),
        provider_record_key=f"{HOUSING_TABLE}:{L2_REGION}:100001:{month}",
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
    page: RebHousingResearchPage,
    month: str,
    policy: SourcePolicy,
) -> dict[str, object]:
    """Commit to existing canonical repository; policy must be registered FIRST."""
    require_reb_housing_l2_policy(policy)
    repository.assert_ready()
    stored = repository.policies([policy.id]).get(policy.id)
    if stored is None or not source_policy_semantics_equal(stored, policy):
        raise RebMarketStatError("an exact stored R-ONE policy is required before any import")
    scoped = scope_key(month)
    # Validate input before starting a persistent run.
    capture_one_month(page, month=month, policy=policy, run_id=uuid5(_NAMESPACE, "preflight"))
    run = repository.start_source_run(
        FEEDER,
        scoped,
        metadata={
            "source_contract": L2_SOURCE_CONTRACT,
            "source_kind": "RONE_REPORTED_DATE_ALL_HOUSING_TRADES",
            "publication": "NOT_APPROVED",
        },
    )
    try:
        source, snapshot, observation = capture_one_month(
            page, month=month, policy=policy, run_id=run.id
        )
        committed = repository.commit_source_page(
            run_id=run.id,
            policy=policy,
            source=source,
            snapshot=snapshot,
            observations=[observation],
            cursor=month,
            checkpoint_metadata={
                "source_contract": L2_SOURCE_CONTRACT,
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
