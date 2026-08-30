from fastapi.testclient import TestClient

from apps.api.main import app
from apps.api.store import PERSON_ID, SOURCE_ID

client = TestClient(app)


def test_health_and_people() -> None:
    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/people").json()[0]["identity_status"] == "RESOLVED"


def test_published_fact_is_traceable_through_source_policy() -> None:
    claims = client.get(f"/people/{PERSON_ID}/claims").json()
    assert claims[0]["epistemic_status"] == "FACT"
    assert claims[0]["evidence"][0]["stance"] == "SUPPORT"
    source_id = claims[0]["source_ids"][0]
    source = client.get(f"/sources/{source_id}").json()
    assert source["id"] == str(SOURCE_ID)
    assert source["policy"]["can_store_metadata"] is True
    assert source["policy"]["can_show_excerpt"] is True


def test_profile_sections_and_not_found() -> None:
    profile = client.get(f"/people/{PERSON_ID}").json()
    assert profile["claims"][0]["evidence"]
    assert client.get(f"/people/{PERSON_ID}/relationships").json() == []
    assert client.get(f"/people/{PERSON_ID}/assets").json() == []
    assert client.get("/people/00000000-0000-0000-0000-999999999999").status_code == 404
