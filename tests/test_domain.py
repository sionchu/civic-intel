from datetime import UTC, datetime

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine, inspect

from packages.domain.contracts import Hypothesis, Person
from packages.domain.db import Base
from packages.domain.enums import EpistemicStatus, IdentityStatus


def test_canonical_enums_and_temporal_ordering() -> None:
    assert EpistemicStatus.UNKNOWN.value == "UNKNOWN"
    with pytest.raises(ValidationError):
        Person(
            canonical_name="Example",
            identity_status=IdentityStatus.RESOLVED,
            valid_from=datetime(2026, 2, 1, tzinfo=UTC),
            valid_to=datetime(2026, 1, 1, tzinfo=UTC),
        )


def test_hypothesis_requires_h0_and_falsifier() -> None:
    with pytest.raises(ValidationError):
        Hypothesis(
            person_id="00000000-0000-0000-0000-000000000001",
            statement="Influence",
            ordinary_explanation="",
            falsifier="",
        )


def test_schema_contains_canonical_tables() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    names = set(inspect(engine).get_table_names())
    assert {
        "people",
        "person_aliases",
        "organizations",
        "offices",
        "appointments",
        "sources",
        "source_snapshots",
        "source_policies",
        "source_origin_clusters",
        "claims",
        "claim_evidence",
        "asset_disclosures",
        "asset_items",
        "events",
        "event_documents",
        "decision_episodes",
        "relationships",
        "hypotheses",
        "hypothesis_evidence",
        "profile_snapshots",
    } <= names


def test_prohibited_private_location_fields_are_rejected() -> None:
    with pytest.raises(ValidationError):
        Person.model_validate(
            {
                "canonical_name": "Example",
                "identity_status": "RESOLVED",
                "precise_residential_address": "Never store this",
            }
        )
