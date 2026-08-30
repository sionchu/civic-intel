from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from packages.connectors.base import Connector, ConnectorDocument
from packages.domain.contracts import Source, SourcePolicy, SourceSnapshot
from packages.verification.policy import PolicyAction, require_policy


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


@dataclass(frozen=True)
class IngestionResult:
    source: Source
    snapshot: SourceSnapshot
    changed: bool
    publish_attempted: bool = False


class IngestionPipeline:
    def __init__(self, connector: Connector):
        self.connector = connector

    def ingest(
        self, url: str, policy: SourcePolicy, previous_hash: str | None = None
    ) -> IngestionResult:
        require_policy(policy, PolicyAction.FETCH)
        document: ConnectorDocument = self.connector.fetch(url)
        return self.ingest_document(document, policy, previous_hash)

    def ingest_document(
        self,
        document: ConnectorDocument,
        policy: SourcePolicy,
        previous_hash: str | None = None,
    ) -> IngestionResult:
        require_policy(policy, PolicyAction.STORE_METADATA)
        normalized = normalize_text(document.body)
        digest = hashlib.sha256(normalized.encode()).hexdigest()
        fulltext = None
        if policy.can_store_fulltext:
            require_policy(policy, PolicyAction.STORE_FULLTEXT)
            fulltext = normalized
        source = Source(
            url=document.url,
            title=document.title,
            publisher=document.publisher,
            published_at=document.published_at,
            policy_id=policy.id,
        )
        snapshot = SourceSnapshot(
            source_id=source.id,
            content_hash=digest,
            metadata=document.metadata,
            fulltext=fulltext,
        )
        return IngestionResult(source, snapshot, digest != previous_hash)
