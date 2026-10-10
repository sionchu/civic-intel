import json
from datetime import date

import httpx
import pytest

from packages.connectors.open_assembly import AssemblyApiError, national_assembly_member_policy
from packages.connectors.open_assembly_press_releases import OpenAssemblyPressReleaseConnector
from packages.verification.policy import PolicyDenied


def payload(rows=None):
    return {
        OpenAssemblyPressReleaseConnector.API_CODE: [
            {"head": [{"list_total_count": 1}, {"RESULT": {"CODE": "INFO-000"}}]},
            {
                "row": rows
                if rows is not None
                else [
                    {
                        "NUM": "8530",
                        "TITLE": "공식 보도자료",
                        "WRITE_DATE": "2026-10-09",
                        "BBS_TITLE": "국회사무처",
                        "CONTENT": "NEVER RETAIN ARTICLE",
                        "CONTENT_URL": "https://unreviewed.invalid/private?KEY=never-retain",
                        "KEY": "never-retain",
                        "MONA_CD": "unverified-person",
                    }
                ]
            },
        ]
    }


def connector(document=None, **kwargs):
    def serve(request):
        assert request.url.params["KEY"] == "test-only-key"
        return httpx.Response(200, json=document or payload())

    return OpenAssemblyPressReleaseConnector(
        policy=kwargs.pop("policy", national_assembly_member_policy()),
        written_on=date(2026, 10, 9),
        api_key="test-only-key",
        transport=httpx.MockTransport(serve),
        **kwargs,
    )


def test_policy_precedes_discovery_and_network():
    policy = national_assembly_member_policy().model_copy(update={"can_fetch": False})
    with pytest.raises(PolicyDenied):
        connector(policy=policy).discover()
    with pytest.raises(PolicyDenied):
        connector(policy=policy).fetch(OpenAssemblyPressReleaseConnector.BASE_URL)


def test_only_normalized_metadata_crosses_document_boundary():
    reader = connector()
    document = reader.fetch(reader.discover()[0])
    serialized = json.dumps(document.__dict__)
    for forbidden in ("CONTENT", "NEVER RETAIN", "never-retain", "test-only-key", "MONA_CD"):
        assert forbidden not in serialized
    record = json.loads(document.body)[0]
    assert record["record_key"] == "8530"
    assert record["written_date"] == "2026-10-09"
    assert record["source_url"].startswith(reader.BASE_URL + "?")
    assert document.metadata["identity_status"] == "ENTITY_UNRESOLVED"
    assert document.published_at is None  # WRITE_DATE is not a publication timestamp.


@pytest.mark.parametrize("suffix", ["&KEY=secret", "&CONTENT=body", "&pIndex=2", "#fragment"])
def test_arbitrary_request_variants_fail_before_network(suffix):
    reader = connector()
    with pytest.raises(ValueError):
        reader.fetch(reader.discover()[0] + suffix)


@pytest.mark.parametrize(
    "field,value",
    [
        ("NUM", "../1"),
        ("NUM", True),
        ("TITLE", None),
        ("WRITE_DATE", "2026-02-30"),
        ("WRITE_DATE", "2026-10-08"),
        ("BBS_TITLE", ""),
    ],
)
def test_invalid_or_out_of_scope_rows_fail_closed(field, value):
    data = payload()
    data[OpenAssemblyPressReleaseConnector.API_CODE][1]["row"][0][field] = value
    reader = connector(data)
    with pytest.raises(AssemblyApiError):
        reader.fetch(reader.discover()[0])


def test_duplicates_and_provider_error_do_not_become_success():
    data = payload()
    row = data[OpenAssemblyPressReleaseConnector.API_CODE][1]["row"][0]
    data[OpenAssemblyPressReleaseConnector.API_CODE][1]["row"].append(row.copy())
    reader = connector(data)
    with pytest.raises(AssemblyApiError):
        reader.fetch(reader.discover()[0])
    data = payload()
    data[OpenAssemblyPressReleaseConnector.API_CODE][0]["head"][1]["RESULT"] = {
        "CODE": "ERROR-SECRET",
        "MESSAGE": "private credential",
    }
    reader = connector(data)
    with pytest.raises(AssemblyApiError) as error:
        reader.fetch(reader.discover()[0])
    assert "SECRET" not in str(error.value)
    assert "credential" not in str(error.value)


def test_metadata_corrections_change_body_without_person_link_or_new_truth_store():
    first = connector()
    data = payload()
    data[OpenAssemblyPressReleaseConnector.API_CODE][1]["row"][0]["TITLE"] = "정정 제목"
    second = connector(data)
    a, b = first.fetch(first.discover()[0]), second.fetch(second.discover()[0])
    assert a.body != b.body
    assert json.loads(a.body)[0]["record_key"] == json.loads(b.body)[0]["record_key"]
    assert "person" not in b.body


@pytest.mark.parametrize("heads", [None, "invalid", [None]])
def test_malformed_headers_are_sanitized_errors(heads):
    data = payload()
    data[OpenAssemblyPressReleaseConnector.API_CODE][0]["head"] = heads
    reader = connector(data)
    with pytest.raises(AssemblyApiError):
        reader.fetch(reader.discover()[0])
