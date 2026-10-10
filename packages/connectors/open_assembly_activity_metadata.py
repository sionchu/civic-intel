"""Supplied metadata adapters for four reviewed schemas; no unverified API requests.

Schema review is not proof of a live query, stable record locator or Person identity.
Only deterministic code processes the operator-local provider rows. Bodies, venue,
unknown fields, credentials and unreviewed query-bearing links are discarded.
"""
from __future__ import annotations

import re
from datetime import date
from urllib.parse import urlsplit

from packages.connectors.open_assembly import POLICY_ID
from packages.domain.contracts import SourcePolicy
from packages.domain.enums import SourceCollectionMode
from packages.verification.policy import PolicyAction, PolicyDenied, require_policy

ACTIVITY_APIS = ("SPGRPPRESS", "NAMEMBEREVENT", "nkulntiravezskrjd", "npeslxqbanwkimebr")
ACTIVITY_CONTRACT = "national_assembly_activity_metadata_staged_v1"
LOCATOR_UNVERIFIED = "UNVERIFIED_PROVIDER_RECORD_LOCATOR"


def require_activity_policy(policy: SourcePolicy) -> None:
    require_policy(policy, PolicyAction.STORE_METADATA)
    if (policy.id != POLICY_ID or policy.domain != "open.assembly.go.kr"
            or policy.source_class != "official_open_api"
            or policy.collection_mode != SourceCollectionMode.API):
        raise PolicyDenied("official activity metadata requires the existing Assembly API policy")


def normalize_activity_row(api_code: str, raw: object, *, policy: SourcePolicy) -> dict[str, object]:
    require_activity_policy(policy)
    if api_code not in ACTIVITY_APIS or not isinstance(raw, dict):
        raise ValueError("ACTIVITY_SCHEMA_INVALID")
    if api_code == "SPGRPPRESS":
        title_key, date_key, name_key, link_key = "ARTC_TTL", "WRT_DT", None, "LINK_URL"
    elif api_code == "NAMEMBEREVENT":
        title_key, date_key, name_key, link_key = "EV_TTL", "EV_DTM", "NAAS_NM", "LINK_URL"
    elif api_code == "nkulntiravezskrjd":
        title_key, date_key, name_key, link_key = "V_TITLE", "DATE_RELEASED", None, "URL_LINK"
    else:
        title_key, date_key, name_key, link_key = "TITLE", "TAKING_DATE", "ESSENTIAL_PERSON", "LINK_URL"
    title = raw.get(title_key)
    if not isinstance(title, str) or not title.strip() or len(title) > 1000:
        raise ValueError("ACTIVITY_TITLE_INVALID")
    printed_name = raw.get(name_key) if name_key else None
    if printed_name is not None and (not isinstance(printed_name, str) or not printed_name.strip()
            or len(printed_name) > 100):
        raise ValueError("ACTIVITY_PRINTED_LABEL_INVALID")
    value = raw.get(date_key)
    written_date = None
    if isinstance(value, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        try:
            written_date = date.fromisoformat(value).isoformat()
        except ValueError:
            pass
    # No publication/record identity is inferred from a link. Unknown query semantics
    # (including possible secret query fields) are never retained or followed.
    link = raw.get(link_key)
    safe_link = None
    if isinstance(link, str) and len(link) <= 1000:
        try:
            parsed = urlsplit(link)
            port = parsed.port
        except ValueError:
            raise ValueError("ACTIVITY_LINK_INVALID") from None
        if (parsed.scheme == "https" and parsed.hostname in {
                "www.na.go.kr", "na.go.kr", "www.naon.go.kr", "naon.go.kr",
                "assembly.webcast.go.kr", "w3.assembly.go.kr", "open.assembly.go.kr"}
                and not parsed.username and not parsed.password and not parsed.query
                and not parsed.fragment and port in {None, 443}):
            safe_link = link
    return {"api_code": api_code, "title": title.strip(), "written_date": written_date,
        "date_status": "SOURCE_ISO_CALENDAR_DATE" if written_date else "UNKNOWN",
        "printed_person_label": printed_name.strip() if isinstance(printed_name, str) else None,
        "source_link": safe_link, "record_identity_status": LOCATOR_UNVERIFIED,
        "person_identity_status": "REVIEW_REQUIRED_NO_AUTO_LINK"}
