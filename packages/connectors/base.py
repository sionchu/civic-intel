from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class ConnectorDocument:
    url: str
    title: str
    publisher: str
    published_at: datetime | None
    body: str
    metadata: dict[str, str]


class Connector(ABC):
    @abstractmethod
    def discover(self) -> list[str]: ...

    @abstractmethod
    def fetch(self, url: str) -> ConnectorDocument: ...
