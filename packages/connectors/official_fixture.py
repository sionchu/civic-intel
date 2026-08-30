from datetime import UTC, datetime

from .base import Connector, ConnectorDocument


class OfficialRosterFixtureConnector(Connector):
    """Offline excerpt from the reviewed Golden Set 001 presidential briefing."""

    URL = "https://www.president.go.kr/briefings/qGTHgnQ8"

    def discover(self) -> list[str]:
        return [self.URL]

    def fetch(self, url: str) -> ConnectorDocument:
        if url != self.URL:
            raise KeyError(url)
        return ConnectorDocument(
            url=url,
            title="인사 발표 관련 강훈식 비서실장 브리핑",
            publisher="대한민국 청와대",
            published_at=datetime(2026, 8, 30, 3, 0, tzinfo=UTC),
            body="이재명 대통령은 오늘 장관 후보자 총 6명을 지명했습니다.",
            metadata={"capture": "manual_review", "fixture": "golden_set_001"},
        )
