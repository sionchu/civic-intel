from urllib.parse import parse_qs, urlparse
from uuid import UUID

ALIO_ITEM12_SOURCE_CONTRACT = "alio_item_12_current_institution_head_business_expense"
ASSEMBLY_MEMBER_POLICY_ID = UUID("11000000-0000-0000-0000-000000000001")
ASSEMBLY_MEMBER_HOST = "open.assembly.go.kr"
ASSEMBLY_MEMBER_API_CODE = "nwvrqwxyaytdsfvhu"
ASSEMBLY_MEMBER_PATH = f"/portal/openapi/{ASSEMBLY_MEMBER_API_CODE}"
ASSEMBLY_MEMBER_QUERY_FIELDS = frozenset({"Type", "pIndex", "pSize", "HG_NM", "POLY_NM", "ORIG_NM"})


def assembly_member_query(url: str) -> dict[str, str]:
    """One pure URL contract shared by acquisition and stored-provenance validation."""
    parsed = urlparse(url)
    if (
        parsed.scheme != "https"
        or parsed.netloc != ASSEMBLY_MEMBER_HOST
        or parsed.path != ASSEMBLY_MEMBER_PATH
    ):
        raise ValueError("unsupported National Assembly API URL")
    raw = parse_qs(parsed.query, keep_blank_values=True)
    if "KEY" in raw or "authKey" in raw:
        raise ValueError("credentials must not be embedded in connector URLs")
    if set(raw) - ASSEMBLY_MEMBER_QUERY_FIELDS:
        raise ValueError("unsupported National Assembly API query parameter")
    query = {key: values[-1] for key, values in raw.items()}
    if query.get("Type", "json").lower() != "json":
        raise ValueError("connector requires JSON responses")
    return query
