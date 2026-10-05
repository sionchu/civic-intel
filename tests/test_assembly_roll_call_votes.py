from __future__ import annotations

from pathlib import Path

import httpx
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import select

from packages.connectors.open_assembly import AssemblyApiError, MissingAssemblyApiKey
from packages.connectors.open_assembly_votes import (
    AssemblyRollCallContractError,
    OpenAssemblyBillVoteSummaryConnector,
    OpenAssemblyMemberVoteConnector,
    RollCallVoteValue,
    national_assembly_roll_call_vote_policy,
)
from packages.domain.db import PersonRow, SourceRow, SourceSnapshotRow
from packages.domain.enums import SourceCollectionMode, SourceRunStatus
from packages.persistence import SqlAlchemyRepository
from packages.verification.policy import PolicyDenied
from workers.assembly_roll_call_votes import (
    AssemblyRollCallCoverageError,
    AssemblyRollCallVoteEnumerator,
    main,
)

SECRET = "assembly-vote-secret-must-not-persist"
SCOPE = "assembly_age:22"
FEEDER = AssemblyRollCallVoteEnumerator.FEEDER
SUMMARY_CODE = OpenAssemblyBillVoteSummaryConnector.API_CODE
MEMBER_CODE = OpenAssemblyMemberVoteConnector.API_CODE

# Shapes below mirror keyless sample responses captured from open.assembly.go.kr on 2026-10-04
# (ncocpgfiaoituanbr AGE=22; nojepdqqaweusdfbi AGE=22&BILL_ID=...). Personal display fields are
# replaced with sentinel values so tests can prove they are never persisted.


def summary_row(bill_id: str, votes: dict[str, str], **overrides: object) -> dict[str, object]:
    yes = sum(value == "찬성" for value in votes.values())
    no = sum(value == "반대" for value in votes.values())
    blank = sum(value == "기권" for value in votes.values())
    row: dict[str, object] = {
        "BILL_ID": bill_id,
        "PROC_DT": "2026-10-01",
        "BILL_NO": f"22{bill_id[-1]}1665",
        "BILL_NAME": f"테스트법 일부개정법률안(대안)({bill_id})",
        "CURR_COMMITTEE": "농림축산식품해양수산위원회",
        "CURR_COMMITTEE_ID": "9700408",
        "PROC_RESULT_CD": "원안가결",
        "BILL_KIND_CD": "법률안",
        "AGE": "22",
        "MEMBER_TCNT": len(votes),
        "VOTE_TCNT": yes + no + blank,
        "YES_TCNT": yes,
        "NO_TCNT": no,
        "BLANK_TCNT": blank,
        "LINK_URL": f"https://likms.assembly.go.kr/bill/billDetail.do?billId={bill_id}",
    }
    row.update(overrides)
    return row


def member_row(bill_id: str, mona_cd: str, vote: str, **overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "HG_NM": "비저장의원",
        "HJ_NM": "非貯藏",
        "POLY_NM": "비저장정당",
        "ORIG_NM": "비저장선거구",
        "MEMBER_NO": "2200000000999",
        "POLY_CD": "101182",
        "ORIG_CD": "080184",
        "VOTE_DATE": "20261001 145522",
        "BILL_NO": f"22{bill_id[-1]}1665",
        "BILL_NAME": f"테스트법 일부개정법률안(대안)({bill_id})",
        "BILL_ID": bill_id,
        "LAW_TITLE": "테스트법",
        "CURR_COMMITTEE": "농림축산식품해양수산위원회",
        "RESULT_VOTE_MOD": vote,
        "DEPT_CD": "9771408",
        "CURR_COMMITTEE_ID": "9700408",
        "DISP_ORDER": 0,
        "BILL_URL": (
            f"http://likms.assembly.go.kr/bill/billDetail.do?billId={bill_id}&KEY={SECRET}"
        ),
        "BILL_NAME_URL": f"http://likms.assembly.go.kr/bill/billDetail.do?billId={bill_id}",
        "SESSION_CD": 439,
        "CURRENTS_CD": 10,
        "AGE": 22,
        "MONA_CD": mona_cd,
        "KEY": SECRET,
    }
    row.update(overrides)
    return row


def envelope(api_code: str, rows: list[dict], total: int | None = None) -> dict:
    count = len(rows) if total is None else total
    if count == 0 and not rows:
        return {"RESULT": {"CODE": "INFO-200", "MESSAGE": "해당하는 데이터가 없습니다."}}
    return {
        api_code: [
            {
                "head": [
                    {"list_total_count": count},
                    {"RESULT": {"CODE": "INFO-000", "MESSAGE": "정상 처리되었습니다."}},
                ]
            },
            {"row": rows},
        ]
    }


DEFAULT_VOTES = {
    "B1": {"M001": "찬성", "M002": "반대", "M003": "기권", "M004": "불참"},
    "B2": {"M001": "찬성", "M002": "찬성", "M003": "불참", "M004": "불참"},
    "B3": {"M001": "반대", "M002": "찬성", "M003": "찬성", "M004": "찬성"},
}


class VoteApi:
    def __init__(self, votes: dict[str, dict[str, str]] | None = None) -> None:
        self.votes = {bill: dict(rows) for bill, rows in (votes or DEFAULT_VOTES).items()}
        self.summary_overrides: dict[str, dict[str, object]] = {}
        self.member_rows_override: dict[str, list[dict]] = {}
        self.summary_totals: dict[int, int] = {}
        self.fail_bills: set[str] = set()
        self.summary_calls: list[int] = []
        self.member_calls: list[str] = []

    def summaries(self) -> list[dict]:
        # Provider order is newest-first; the enumerator must not depend on it.
        return [
            summary_row(bill, rows, **self.summary_overrides.get(bill, {}))
            for bill, rows in sorted(self.votes.items(), reverse=True)
        ]

    def handle(self, request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.params["KEY"] == SECRET
        assert request.url.params["AGE"] == "22"
        page = int(request.url.params["pIndex"])
        size = int(request.url.params["pSize"])
        if request.url.path.endswith(SUMMARY_CODE):
            assert "BILL_ID" not in request.url.params
            self.summary_calls.append(page)
            rows = self.summaries()
            chunk = rows[(page - 1) * size : page * size]
            total = self.summary_totals.get(page, len(rows))
            return httpx.Response(200, json=envelope(SUMMARY_CODE, chunk, total))
        assert request.url.path.endswith(MEMBER_CODE)
        bill_id = request.url.params["BILL_ID"]
        self.member_calls.append(bill_id)
        if bill_id in self.fail_bills:
            return httpx.Response(503, text=f"provider failure {SECRET}")
        rows = self.member_rows_override.get(bill_id) or [
            member_row(bill_id, code, vote) for code, vote in self.votes.get(bill_id, {}).items()
        ]
        return httpx.Response(200, json=envelope(MEMBER_CODE, rows[:size]))

    def connector(self, *, page_size: int = 2) -> OpenAssemblyBillVoteSummaryConnector:
        return OpenAssemblyBillVoteSummaryConnector(
            assembly_age=22,
            api_key=SECRET,
            page_size=page_size,
            transport=httpx.MockTransport(self.handle),
        )


def migrated_repository(database: Path) -> SqlAlchemyRepository:
    database_url = f"sqlite:///{database.as_posix()}"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(config, "head")
    return SqlAlchemyRepository(database_url)


def enumerator(
    api: VoteApi, repository: SqlAlchemyRepository, **kwargs
) -> AssemblyRollCallVoteEnumerator:
    return AssemblyRollCallVoteEnumerator(api.connector(), repository, **kwargs)


# -- connector -----------------------------------------------------------------------------


def test_member_vote_discovery_requires_age_and_bill_and_keeps_key_out() -> None:
    connector = OpenAssemblyMemberVoteConnector(assembly_age=22, bill_id="B1", api_key=SECRET)
    url = httpx.URL(connector.discover()[0])
    assert url.params["AGE"] == "22"
    assert url.params["BILL_ID"] == "B1"
    assert "KEY" not in url.params
    assert SECRET not in str(url)
    with pytest.raises(ValueError, match="BILL_ID is required"):
        connector.fetch(f"{connector.base_url()}?Type=json&AGE=22")
    with pytest.raises(ValueError, match="credentials"):
        connector.fetch(f"{connector.base_url()}?Type=json&AGE=22&BILL_ID=B1&KEY=x")
    with pytest.raises(ValueError, match="query parameter"):
        connector.fetch(f"{connector.base_url()}?Type=json&AGE=22&BILL_ID=B1&HG_NM=x")


def test_missing_key_blocks_fetch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ASSEMBLY_API_KEY", raising=False)
    connector = OpenAssemblyBillVoteSummaryConnector(
        assembly_age=22,
        transport=httpx.MockTransport(lambda request: pytest.fail(f"unexpected fetch {request}")),
    )
    with pytest.raises(MissingAssemblyApiKey):
        connector.fetch(connector.discover()[0])


def test_member_vote_parser_keeps_verbatim_value_and_closed_enum() -> None:
    api = VoteApi()
    connector = api.connector().member_votes("B1", page_size=1000)
    document = connector.fetch(connector.discover()[0])
    records = connector.parse_votes(document)

    assert '"KEY":' not in document.body and SECRET not in document.url
    assert document.metadata["BILL_ID"] == "B1"
    by_code = {item.member_code: item for item in records}
    assert by_code["M001"].vote_value_published == "찬성"
    assert by_code["M001"].vote_value == RollCallVoteValue.YES
    assert by_code["M002"].vote_value == RollCallVoteValue.NO
    assert by_code["M003"].vote_value == RollCallVoteValue.ABSTAIN
    assert by_code["M004"].vote_value_published == "불참"
    assert by_code["M004"].vote_value == RollCallVoteValue.NOT_PARTICIPATING
    assert by_code["M004"].vote_value != RollCallVoteValue.NO
    assert by_code["M001"].provider_record_key == "B1:M001"
    assert by_code["M001"].vote_datetime.isoformat() == "2026-10-01T14:55:22+09:00"
    assert by_code["M001"].session_code == "439"
    assert by_code["M001"].sitting_number == "10"


@pytest.mark.parametrize(
    ("override", "message"),
    [
        ({"RESULT_VOTE_MOD": "출석"}, "unknown RESULT_VOTE_MOD"),
        ({"RESULT_VOTE_MOD": None}, "unknown RESULT_VOTE_MOD"),
        ({"MONA_CD": ""}, "identity fields"),
        ({"MONA_CD": "M0 01"}, "malformed MONA_CD"),
        ({"VOTE_DATE": "2026-10-01"}, "malformed VOTE_DATE"),
    ],
)
def test_member_vote_parser_fails_closed(override: dict, message: str) -> None:
    api = VoteApi()
    api.member_rows_override["B1"] = [member_row("B1", "M001", "찬성", **override)]
    connector = api.connector().member_votes("B1", page_size=1000)
    document = connector.fetch(connector.discover()[0])
    with pytest.raises(AssemblyRollCallContractError, match=message):
        connector.parse_votes(document)


def test_top_level_result_envelopes() -> None:
    assert OpenAssemblyMemberVoteConnector.response_parts(
        {"RESULT": {"CODE": "INFO-200", "MESSAGE": "해당하는 데이터가 없습니다."}}
    ) == ([], 0, "INFO-200")
    with pytest.raises(AssemblyApiError, match="ERROR-300"):
        OpenAssemblyMemberVoteConnector.response_parts(
            {"RESULT": {"CODE": "ERROR-300", "MESSAGE": "필수 값이 누락되어 있습니다."}}
        )


def test_summary_parser_requires_integer_tallies() -> None:
    api = VoteApi()
    api.summary_overrides["B1"] = {"VOTE_TCNT": None}
    connector = api.connector(page_size=10)
    document = connector.fetch(connector.discover()[0])
    with pytest.raises(AssemblyRollCallContractError, match="VOTE_TCNT"):
        connector.parse_summaries(document)


# -- enumeration ---------------------------------------------------------------------------


def test_full_term_enumeration_is_complete_and_minimized(tmp_path: Path) -> None:
    repository = migrated_repository(tmp_path / "votes.db")
    api = VoteApi()

    result = enumerator(api, repository).enumerate()

    assert result.run.status == SourceRunStatus.SUCCESS
    assert result.complete
    assert result.universe_bill_count == 3
    assert result.bills_committed_total == 3
    assert result.run.observations_created == 12
    assert api.summary_calls == [1, 2]
    assert api.member_calls == ["B1", "B2", "B3"]  # canonical BILL_ID order
    checkpoint = repository.source_checkpoint(FEEDER, SCOPE)
    assert checkpoint is not None and checkpoint.cursor == "3"
    assert checkpoint.metadata["universe_bill_count"] == 3
    assert checkpoint.metadata["bills_committed"] == 3

    observations = repository.feeder_observations(FEEDER, SCOPE)
    keys = sorted(item.provider_record_key for item in observations)
    assert keys[:4] == ["B1:M001", "B1:M002", "B1:M003", "B1:M004"]
    absent = next(item for item in observations if item.provider_record_key == "B1:M004")
    assert absent.normalized["vote_value_published"] == "불참"
    assert absent.normalized["vote_value"] == "NOT_PARTICIPATING"
    assert absent.normalized["bill_url"] == (
        "http://likms.assembly.go.kr/bill/billDetail.do?billId=B1"
    )
    assert absent.identity_hints == {
        "record_kind": "single_person_roll_call_vote",
        "participants": [
            {"external_id_namespace": "assembly_mona_cd", "external_id": "M004", "role": "VOTER"}
        ],
    }
    assert absent.provider_observed_at is not None
    persisted = repr([item.model_dump(mode="json") for item in observations])
    for forbidden in ("비저장의원", "非貯藏", "비저장정당", "비저장선거구", "2200000000999", SECRET):
        assert forbidden not in persisted

    with repository.sessions() as session:
        sources = list(session.scalars(select(SourceRow)))
        snapshots = list(session.scalars(select(SourceSnapshotRow)))
        persons = list(session.scalars(select(PersonRow)))
    assert len(sources) == 5  # 2 summary pages + 3 bills
    assert all("KEY=" not in item.url and SECRET not in item.url for item in sources)
    assert all(item.fulltext is None for item in snapshots)
    assert SECRET not in repr([item.metadata_json for item in snapshots])
    assert persons == []


def test_unchanged_rerun_is_noop_and_changed_vote_creates_version(tmp_path: Path) -> None:
    repository = migrated_repository(tmp_path / "votes-rerun.db")
    api = VoteApi()

    first = enumerator(api, repository).enumerate()
    second = enumerator(api, repository).enumerate()
    # A provider correction that keeps tallies consistent.
    api.votes["B2"]["M003"] = "찬성"
    api.votes["B2"]["M004"] = "찬성"
    api.votes["B2"]["M001"] = "불참"
    api.votes["B2"]["M002"] = "불참"
    changed = enumerator(api, repository).enumerate()

    assert first.run.observations_created == 12
    assert second.run.observations_created == 0
    assert second.run.observations_unchanged == 12
    assert changed.run.observations_created == 4
    assert changed.run.observations_unchanged == 8
    versions = repository.feeder_observations(FEEDER, SCOPE, "B2:M001")
    assert {item.normalized["vote_value_published"] for item in versions} == {"찬성", "불참"}


def test_max_bills_budget_then_resume_completes(tmp_path: Path) -> None:
    repository = migrated_repository(tmp_path / "votes-budget.db")
    api = VoteApi()

    bounded = enumerator(api, repository, max_bills=1).enumerate()
    assert bounded.run.status == SourceRunStatus.PARTIAL
    assert bounded.run.error_code == "MaxBillsReached"
    assert not bounded.complete
    assert bounded.bills_committed_total == 1
    assert repository.source_checkpoint(FEEDER, SCOPE).cursor == "1"

    resumed = enumerator(api, repository, max_bills=1).enumerate(resume=True)
    assert resumed.bills_committed_total == 2
    finished = enumerator(api, repository).enumerate(resume=True)
    assert finished.run.status == SourceRunStatus.SUCCESS
    assert finished.complete
    assert finished.bills_committed_this_run == 1
    assert api.member_calls == ["B1", "B2", "B3"]
    assert len(repository.feeder_observations(FEEDER, SCOPE)) == 12

    with pytest.raises(AssemblyRollCallCoverageError, match="already covers"):
        enumerator(api, repository).enumerate(resume=True)


def test_partial_failure_retains_checkpoint_and_resume_completes(tmp_path: Path) -> None:
    repository = migrated_repository(tmp_path / "votes-resume.db")
    api = VoteApi()
    api.fail_bills.add("B2")

    with pytest.raises(AssemblyApiError):
        enumerator(api, repository).enumerate()

    partial = repository.source_runs(FEEDER, SCOPE)[-1]
    assert partial.status == SourceRunStatus.PARTIAL
    assert partial.checkpoint_after == "1"
    assert partial.error_summary == "Assembly roll-call vote enumeration did not complete"
    assert SECRET not in repr(partial.model_dump(mode="json"))

    api.fail_bills.clear()
    resumed = enumerator(api, repository).enumerate(resume=True)
    assert resumed.run.status == SourceRunStatus.SUCCESS
    assert resumed.bills_committed_this_run == 2
    assert api.member_calls[-2:] == ["B2", "B3"]


def test_resume_fails_closed_when_universe_changed(tmp_path: Path) -> None:
    repository = migrated_repository(tmp_path / "votes-universe.db")
    api = VoteApi()
    enumerator(api, repository, max_bills=1).enumerate()

    api.votes["B4"] = {"M001": "찬성"}
    with pytest.raises(AssemblyRollCallCoverageError, match="universe changed"):
        enumerator(api, repository).enumerate(resume=True)
    assert repository.source_checkpoint(FEEDER, SCOPE).cursor == "1"


def test_checkpoint_does_not_advance_when_commit_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = migrated_repository(tmp_path / "votes-atomic.db")
    api = VoteApi()
    original = repository.commit_source_page
    calls = 0

    def fail_fourth_commit(**kwargs):
        nonlocal calls
        calls += 1
        if calls == 4:  # 2 universe pages, B1, then B2 fails
            raise RuntimeError("synthetic vote persistence failure")
        return original(**kwargs)

    monkeypatch.setattr(repository, "commit_source_page", fail_fourth_commit)
    with pytest.raises(RuntimeError, match="synthetic vote"):
        enumerator(api, repository).enumerate()

    assert repository.source_checkpoint(FEEDER, SCOPE).cursor == "1"
    assert len(repository.feeder_observations(FEEDER, SCOPE)) == 4


@pytest.mark.parametrize(
    ("rows", "message"),
    [
        (
            [member_row("B1", "M001", "찬성"), member_row("B1", "M001", "찬성")],
            "duplicate MONA_CD",
        ),
        (
            [member_row("B1", "M001", "찬성"), member_row("B1", "M001", "반대")],
            "conflicting MONA_CD",
        ),
        ([member_row("B9", "M001", "찬성")], "BILL_ID is inconsistent"),
        ([member_row("B1", "M001", "찬성", AGE=21)], "Assembly age is inconsistent"),
    ],
)
def test_member_row_duplicates_and_conflicts_fail_closed(
    tmp_path: Path, rows: list[dict], message: str
) -> None:
    repository = migrated_repository(tmp_path / f"votes-dup-{message[:5]}.db")
    api = VoteApi({"B1": {"M001": "찬성", "M002": "반대"}})
    api.member_rows_override["B1"] = rows

    with pytest.raises(AssemblyRollCallCoverageError, match=message):
        enumerator(api, repository).enumerate()
    assert repository.feeder_observations(FEEDER, SCOPE) == []
    assert repository.source_checkpoint(FEEDER, SCOPE).cursor == "0"


def test_unknown_vote_value_fails_before_any_vote_commit(tmp_path: Path) -> None:
    repository = migrated_repository(tmp_path / "votes-unknown.db")
    api = VoteApi({"B1": {"M001": "찬성"}})
    api.member_rows_override["B1"] = [member_row("B1", "M001", "무효")]

    with pytest.raises(AssemblyRollCallContractError, match="unknown RESULT_VOTE_MOD"):
        enumerator(api, repository).enumerate()
    assert repository.feeder_observations(FEEDER, SCOPE) == []
    assert repository.source_runs(FEEDER, SCOPE)[-1].status == SourceRunStatus.PARTIAL


@pytest.mark.parametrize(
    ("override", "status"),
    [
        ({"YES_TCNT": 0, "VOTE_TCNT": 2}, "SOURCE_CONFLICT"),
        ({"MEMBER_TCNT": 5}, "MEMBER_ROWS_INCOMPLETE"),
    ],
)
def test_tally_disagreement_is_recorded_not_corrected(
    tmp_path: Path, override: dict, status: str
) -> None:
    repository = migrated_repository(tmp_path / "votes-tally.db")
    api = VoteApi()
    api.summary_overrides["B1"] = override

    result = enumerator(api, repository).enumerate()
    assert result.complete is True
    assert result.tally_exceptions == {"B1": status}
    observations = repository.feeder_observations(FEEDER, SCOPE)
    flagged = [o for o in observations if o.normalized["bill_id"] == "B1"]
    others = [o for o in observations if o.normalized["bill_id"] != "B1"]
    assert flagged and all(o.normalized["bill_tally_reconciliation"] == status for o in flagged)
    assert all("published_bill_tallies" in o.normalized for o in flagged)
    assert all("member_row_tallies" in o.normalized for o in flagged)
    assert all(o.normalized["bill_tally_reconciliation"] == "MATCHED" for o in others)
    assert all("published_bill_tallies" not in o.normalized for o in others)
    checkpoint = repository.source_checkpoint(FEEDER, SCOPE)
    assert checkpoint.metadata["tally_exceptions"] == {"B1": status}
    # No vote value is rewritten to make the totals agree.
    assert {o.normalized["vote_value_published"] for o in flagged} <= {"찬성", "반대", "기권", "불참"}


def test_bill_without_member_rows_is_recorded_as_incomplete(tmp_path: Path) -> None:
    repository = migrated_repository(tmp_path / "votes-empty-bill.db")
    api = VoteApi()
    api.member_rows_override["B1"] = []
    api.votes["B1"] = {}
    api.summary_overrides["B1"] = {
        "MEMBER_TCNT": 4,
        "VOTE_TCNT": 3,
        "YES_TCNT": 1,
        "NO_TCNT": 1,
        "BLANK_TCNT": 1,
    }

    result = enumerator(api, repository).enumerate()
    assert result.tally_exceptions == {"B1": "MEMBER_ROWS_INCOMPLETE"}
    assert not [
        o for o in repository.feeder_observations(FEEDER, SCOPE) if o.normalized["bill_id"] == "B1"
    ]


def test_tally_exceptions_survive_resume(tmp_path: Path) -> None:
    repository = migrated_repository(tmp_path / "votes-tally-resume.db")
    api = VoteApi()
    api.summary_overrides["B1"] = {"YES_TCNT": 0, "VOTE_TCNT": 2}
    first = enumerator(api, repository, max_bills=1).enumerate()
    assert first.complete is False
    second = enumerator(api, repository).enumerate(resume=True)
    assert second.complete is True
    assert second.tally_exceptions == {"B1": "SOURCE_CONFLICT"}


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda api: api.summary_totals.update({1: 3, 2: 4}), "total count changed"),
        (
            lambda api: api.summary_overrides.update({"B1": {"BILL_ID": "B2"}}),
            "BILL_ID in vote summary",
        ),
        (lambda api: api.summary_overrides.update({"B1": {"AGE": "21"}}), "row Assembly age"),
        (lambda api: api.summary_overrides.update({"B1": {"VOTE_TCNT": 9}}), "do not add up"),
    ],
)
def test_universe_anomalies_fail_before_any_commit(tmp_path: Path, mutate, message: str) -> None:
    repository = migrated_repository(tmp_path / f"votes-universe-{message[:5]}.db")
    api = VoteApi()
    mutate(api)

    with pytest.raises(AssemblyRollCallCoverageError, match=message):
        enumerator(api, repository).enumerate()
    assert repository.source_runs(FEEDER, SCOPE)[-1].status == SourceRunStatus.FAILED
    assert repository.source_checkpoint(FEEDER, SCOPE) is None
    assert api.member_calls == []


def test_policy_denial_happens_before_network_or_run(tmp_path: Path) -> None:
    repository = migrated_repository(tmp_path / "votes-blocked.db")
    api = VoteApi()
    policy = national_assembly_roll_call_vote_policy().model_copy(
        update={"collection_mode": SourceCollectionMode.BLOCKED, "can_fetch": False}
    )
    with pytest.raises(PolicyDenied):
        AssemblyRollCallVoteEnumerator(api.connector(), repository, policy).enumerate()
    assert api.summary_calls == []
    assert repository.source_runs() == []

    page_two = OpenAssemblyBillVoteSummaryConnector(
        assembly_age=22, api_key=SECRET, page_index=2, transport=httpx.MockTransport(api.handle)
    )
    with pytest.raises(AssemblyRollCallCoverageError, match="start at page 1"):
        AssemblyRollCallVoteEnumerator(page_two, repository).enumerate()
    assert repository.source_runs() == []


def test_policy_matches_shared_assembly_host_policy() -> None:
    from packages.connectors.open_assembly_bills import national_assembly_bill_policy

    policy = national_assembly_roll_call_vote_policy()
    bill_policy = national_assembly_bill_policy()
    assert policy.id == bill_policy.id
    assert policy.domain == bill_policy.domain
    assert not policy.can_store_fulltext
    assert not policy.can_send_to_ai


def test_cli_requires_mode_and_age() -> None:
    with pytest.raises(SystemExit):
        main(["--age", "22"])
    with pytest.raises(SystemExit):
        main(["--enumerate"])
    with pytest.raises(SystemExit):
        main(["--age", "22", "--enumerate", "--resume"])
