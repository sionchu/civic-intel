import pytest

from packages.connectors.official_fixture import OfficialRosterFixtureConnector
from packages.domain.contracts import SourcePolicy
from packages.domain.enums import SourceCollectionMode
from packages.verification.policy import PolicyDenied
from workers.ingest import IngestionPipeline


def make_policy(mode=SourceCollectionMode.API, **updates):
    values = {
        "domain": "example.gov",
        "source_class": "official",
        "collection_mode": mode,
        "can_fetch": True,
        "can_store_metadata": True,
        "can_store_fulltext": True,
        "can_send_to_ai": False,
        "can_show_excerpt": True,
        "can_commercialize": True,
        "license": "Open Government Licence",
    }
    return SourcePolicy(**(values | updates))


def test_fixture_ingestion_end_to_end_and_change_detection() -> None:
    connector = OfficialRosterFixtureConnector()
    pipeline = IngestionPipeline(connector)
    first = pipeline.ingest(connector.discover()[0], make_policy())
    second = pipeline.ingest(connector.discover()[0], make_policy(), first.snapshot.content_hash)
    assert first.changed
    assert not second.changed
    assert first.snapshot.fulltext
    assert first.publish_attempted is False


def test_worker_cannot_fetch_blocked_source() -> None:
    connector = OfficialRosterFixtureConnector()
    with pytest.raises(PolicyDenied):
        IngestionPipeline(connector).ingest(
            connector.URL, make_policy(SourceCollectionMode.BLOCKED)
        )


def test_metadata_only_policy_discards_fulltext() -> None:
    connector = OfficialRosterFixtureConnector()
    result = IngestionPipeline(connector).ingest(
        connector.URL, make_policy(can_store_fulltext=False)
    )
    assert result.snapshot.fulltext is None
