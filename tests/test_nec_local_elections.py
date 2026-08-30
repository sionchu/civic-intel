import json

import httpx
import pytest

from packages.connectors.nec_local_elections import (
    LOCAL_ELECTION_TYPES,
    MissingNecApiKey,
    NecCandidateConnector,
    NecWinnerConnector,
    nec_local_election_policy,
)
from packages.domain.enums import SourceCollectionMode
from packages.verification.policy import PolicyDenied
from workers.local_elections import LocalElectionStager, render_local_election_json

SECRET = "nec-secret-must-not-persist"


def response_payload(rows: list[dict], *, total: int | None = None) -> dict:
    return {
        "response": {
            "header": {"resultCode": "00", "resultMsg": "NORMAL SERVICE"},
            "body": {
                "pageNo": 1,
                "numOfRows": 100,
                "totalCount": len(rows) if total is None else total,
                "items": {"item": rows},
            },
        }
    }


def candidate_rows(election_type: int = 4) -> list[dict]:
    return [
        {
            "sgId": "20260603",
            "sgTypecode": str(election_type),
            "huboid": "C-001",
            "sggName": "테스트시",
            "sdName": "경기도",
            "wiwName": "테스트시",
            "giho": "1",
            "gihoSangse": "",
            "jdName": "테스트당",
            "name": "홍길동",
            "hanjaName": "洪吉童",
            "gender": "남",
            "birthday": "19700102",
            "age": "56",
            "addr": "경기도 테스트시 공개동",
            "jobId": "75",
            "job": "정당인",
            "eduId": "68",
            "edu": "테스트대학교 졸업",
            "career1": "(전) 테스트시의원",
            "career2": "(전) 테스트협회장",
            "status": "등록",
        },
        {
            "sgId": "20260603",
            "sgTypecode": str(election_type),
            "huboid": "C-002",
            "sggName": "테스트시",
            "sdName": "경기도",
            "wiwName": "테스트시",
            "giho": "2",
            "jdName": "다른당",
            "name": "홍길동",
            "hanjaName": "洪二童",
            "birthday": "19800102",
            "addr": "경기도 다른시 비공개동",
            "job": "회사원",
            "edu": "다른대학교 졸업",
            "career1": "-",
            "career2": "",
            "status": "등록",
        },
    ]


def winner_rows() -> list[dict]:
    return [
        {
            "sgId": "20260603",
            "sgTypecode": "4",
            "huboid": "C-001",
            "sggName": "테스트시",
            "sdName": "경기도",
            "jdName": "테스트당",
            "name": "홍길동",
            "birthday": "19700102",
            "addr": "경기도 테스트시 공개동",
            "dugsu": "12,345",
            "dugyul": "52.10",
        }
    ]


def transport_for(payload: dict) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["serviceKey"] == SECRET
        return httpx.Response(200, json=payload)

    return httpx.MockTransport(handler)


def connector_pair(*, winner_total: int = 1, election_type: int = 4):
    common = {
        "election_id": "20260603",
        "election_type": election_type,
        "api_key": SECRET,
        "province_name": "경기도",
        "district_name": "테스트시",
    }
    candidates = NecCandidateConnector(
        **common, transport=transport_for(response_payload(candidate_rows(election_type)))
    )
    winners_payload = response_payload(winner_rows() if election_type == 4 else [], total=winner_total)
    winners = NecWinnerConnector(**common, transport=transport_for(winners_payload))
    return candidates, winners


def test_supported_local_election_codes_are_explicit() -> None:
    assert LOCAL_ELECTION_TYPES == {
        3: "시·도지사",
        4: "구·시·군의 장",
        5: "시·도의회의원",
        6: "구·시·군의회의원",
        10: "교육의원",
        11: "교육감",
    }


def test_discovery_url_contains_no_api_key() -> None:
    connector = NecCandidateConnector(
        election_id="20260603",
        election_type=4,
        api_key=SECRET,
        province_name="경기도",
        district_name="테스트시",
    )
    url = httpx.URL(connector.discover()[0])
    assert url.scheme == "https"
    assert url.host == "apis.data.go.kr"
    assert url.params["sgId"] == "20260603"
    assert url.params["sgTypecode"] == "4"
    assert "serviceKey" not in url.params
    assert SECRET not in str(url)


def test_missing_key_blocks_live_fetch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NEC_API_KEY", raising=False)
    connector = NecCandidateConnector(
        election_id="20260603",
        election_type=4,
        transport=httpx.MockTransport(lambda request: pytest.fail(f"unexpected fetch: {request}")),
    )
    with pytest.raises(MissingNecApiKey):
        connector.fetch(connector.discover()[0])


def test_candidate_parser_discards_address_and_preserves_submission_semantics() -> None:
    candidates, _ = connector_pair()
    document = candidates.fetch(candidates.discover()[0])
    records = candidates.parse_candidates(document)

    assert len(records) == 2
    assert records[0].candidate_id == "C-001"
    assert records[0].submitted_education == "테스트대학교 졸업"
    assert records[0].submitted_careers == ("(전) 테스트시의원", "(전) 테스트협회장")
    assert not hasattr(records[0], "address")
    assert SECRET not in document.url
    assert SECRET not in document.body


def test_stager_joins_complete_winner_data_without_merging_same_names() -> None:
    candidates, winners = connector_pair()
    staged = LocalElectionStager(candidates, winners).stage()

    assert len(staged) == 2
    first, second = staged
    assert first.candidate.canonical_name == second.candidate.canonical_name == "홍길동"
    assert first.candidate.birth_date != second.candidate.birth_date
    assert first.candidate_id != second.candidate_id
    assert first.outcome == "WINNER"
    assert first.votes == 12345
    assert first.vote_rate == 52.10
    assert second.outcome == "NOT_WINNER"

    rendered = render_local_election_json(staged)
    data = json.loads(rendered)
    assert data[0]["candidate_submitted"]["semantics"]
    assert "addr" not in rendered.casefold()
    assert "address" not in rendered.casefold()
    assert "공개동" not in rendered
    assert SECRET not in rendered


def test_incomplete_winner_coverage_leaves_nonmatch_unknown() -> None:
    candidates, winners = connector_pair(winner_total=200)
    staged = LocalElectionStager(candidates, winners).stage()
    assert staged[0].outcome == "WINNER"
    assert staged[1].outcome == "UNKNOWN"


def test_source_policy_denial_happens_before_fetch() -> None:
    def forbidden(request: httpx.Request) -> httpx.Response:
        pytest.fail(f"network should not be reached: {request}")

    candidate = NecCandidateConnector(
        election_id="20260603",
        election_type=4,
        api_key=SECRET,
        transport=httpx.MockTransport(forbidden),
    )
    winner = NecWinnerConnector(
        election_id="20260603",
        election_type=4,
        api_key=SECRET,
        transport=httpx.MockTransport(forbidden),
    )
    policy = nec_local_election_policy().model_copy(
        update={"collection_mode": SourceCollectionMode.BLOCKED, "can_fetch": False}
    )
    with pytest.raises(PolicyDenied):
        LocalElectionStager(candidate, winner, policy).stage()


def test_non_winner_candidacy_remains_a_valid_staged_episode() -> None:
    candidates, winners = connector_pair()
    staged = LocalElectionStager(candidates, winners).stage()
    non_winner = next(item for item in staged if item.outcome == "NOT_WINNER")
    assert non_winner.registration_status == "등록"
    assert "nec_candidate_id:C-002" in non_winner.candidate.career_anchors
