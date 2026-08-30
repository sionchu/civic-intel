from enum import StrEnum

from packages.domain.contracts import SourcePolicy
from packages.domain.enums import SourceCollectionMode


class PolicyAction(StrEnum):
    FETCH = "FETCH"
    STORE_METADATA = "STORE_METADATA"
    STORE_FULLTEXT = "STORE_FULLTEXT"
    SEND_TO_AI = "SEND_TO_AI"
    SHOW_EXCERPT = "SHOW_EXCERPT"
    COMMERCIALIZE = "COMMERCIALIZE"


_FIELDS = {
    PolicyAction.FETCH: "can_fetch",
    PolicyAction.STORE_METADATA: "can_store_metadata",
    PolicyAction.STORE_FULLTEXT: "can_store_fulltext",
    PolicyAction.SEND_TO_AI: "can_send_to_ai",
    PolicyAction.SHOW_EXCERPT: "can_show_excerpt",
    PolicyAction.COMMERCIALIZE: "can_commercialize",
}


class PolicyDenied(PermissionError):
    pass


def require_policy(policy: SourcePolicy | None, action: PolicyAction) -> None:
    if policy is None:
        raise PolicyDenied("No SourcePolicy decision exists")
    if policy.collection_mode == SourceCollectionMode.BLOCKED:
        raise PolicyDenied(f"{policy.domain} is blocked")
    if (
        action == PolicyAction.FETCH
        and policy.collection_mode == SourceCollectionMode.DISCOVERY_ONLY
    ):
        raise PolicyDenied(f"{policy.domain} is discovery-only")
    if not getattr(policy, _FIELDS[action]):
        raise PolicyDenied(f"{action.value} is prohibited for {policy.domain}")
