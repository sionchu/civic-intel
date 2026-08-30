from __future__ import annotations

from datetime import UTC, datetime

import httpx

from packages.domain.contracts import SourcePolicy
from packages.verification.policy import PolicyAction, require_policy

from .base import Connector, ConnectorDocument


class PolicyHttpConnector(Connector):
    """Live-safe HTTP connector; callers must supply the matching policy."""

    def __init__(self, policy: SourcePolicy, user_agent: str, timeout: float = 10.0):
        self.policy = policy
        self.user_agent = user_agent
        self.timeout = timeout

    def discover(self) -> list[str]:
        return []

    def fetch(self, url: str) -> ConnectorDocument:
        require_policy(self.policy, PolicyAction.FETCH)
        response = httpx.get(
            url,
            headers={"User-Agent": self.user_agent},
            timeout=self.timeout,
            follow_redirects=True,
        )
        response.raise_for_status()
        return ConnectorDocument(
            url=str(response.url),
            title="",
            publisher=self.policy.domain,
            published_at=datetime.now(UTC),
            body=response.text,
            metadata={"content_type": response.headers.get("content-type", "")},
        )
