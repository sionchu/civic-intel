from datetime import UTC, datetime

from .base import Connector, ConnectorDocument


class OfficialRosterFixtureConnector(Connector):
    """Deterministic stand-in for an official public roster API."""

    URL = "https://example.gov/open-data/cabinet/kim-min"

    def discover(self) -> list[str]:
        return [self.URL]

    def fetch(self, url: str) -> ConnectorDocument:
        if url != self.URL:
            raise KeyError(url)
        return ConnectorDocument(
            url=url,
            title="Cabinet appointment notice: Kim Min",
            publisher="Example Government",
            published_at=datetime(2026, 1, 2, tzinfo=UTC),
            body="Kim Min took office as Minister of Civic Affairs on 2 January 2026.",
            metadata={"license": "Open Government Licence", "fixture": "true"},
        )
