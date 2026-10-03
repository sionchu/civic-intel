"""Offline command-boundary regressions: no operational worker/DB invocation."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from apps.cli import adapters
from apps.cli.main import ROUTES, CommandEffect, main, parse_command


@pytest.mark.parametrize("flags", [
    [], ["--org-code", "A123456", "--resume"],
    ["--org-code", "A123456", "--max-pages", "2"],
    ["--org-code", "A123456", "--full-name", "synthetic"],
    ["--org-code", "bad"], ["--full-name", " "],
    ["--full-name", "different"], ["--org-code", "A123456", "--page-size", "101"],
])
def test_lookup_invalid_scope_rejected_before_worker_or_database(monkeypatch, flags):
    def forbidden(_):
        pytest.fail("invalid lookup was dispatched")

    monkeypatch.setattr(adapters, "dispatch", forbidden)
    with pytest.raises(SystemExit) as exc:
        main(["observe", "mois-organization-lookup", "--allow-effect", "SOURCE_INGESTION",
              "--expected-full-name", "synthetic", *flags])
    assert exc.value.code == 2


def test_lookup_dispatch_uses_only_bounded_capture(monkeypatch, capsys):
    calls = []

    class Lookup:
        def __init__(self, connector, repo, *, expected_full_name):
            calls.append((connector, repo, expected_full_name))

        def capture(self):
            calls.append("one-page capture")
            return {"coverage": "FIRST_FILTERED_PAGE_ONLY_NOT_L3"}

    w = SimpleNamespace(MoisOrganizationCodeConnector=lambda **kw: kw,
                        MoisOrganizationLookup=Lookup)
    monkeypatch.setattr(adapters, "worker", lambda name: w)
    monkeypatch.setattr(adapters, "repository", lambda args: "fake isolated DB")
    assert main(["observe", "mois-organization-lookup", "--allow-effect", "SOURCE_INGESTION",
                 "--org-code", "A123456", "--expected-full-name", "synthetic",
                 "--page-size", "10"]) == 0
    assert calls == [({"page_no": 1, "page_size": 10, "org_code": "A123456", "full_name": None},
                      "fake isolated DB", "synthetic"), "one-page capture"]
    assert json.loads(capsys.readouterr().out)["effect"] == "SOURCE_INGESTION"


@pytest.mark.parametrize(
    "verb,lane,effect",
    [(verb, lane, effect) for verb, (effect, lanes) in ROUTES.items() for lane in lanes],
)
def test_effect_registry_has_explicit_single_effect(verb, lane, effect):
    assert isinstance(effect, CommandEffect)
    assert "sync" not in lane


@pytest.mark.parametrize(
    "argv",
    [
        ["observe", "assembly"],
        ["observe", "assembly", "--allow-effect", "READ_ONLY"],
        ["observe", "assembly", "--allow-effect", "CLAIM_PUBLICATION"],
        ["observe", "assembly", "--allow-effect", "SOURCE_INGESTION", "--materialize"],
        ["observe", "assembly", "--allow-effect", "SOURCE_INGESTION", "--publish-base-profile"],
        ["materialize", "assembly", "--allow-effect", "SOURCE_INGESTION"],
        ["publish", "assembly-profile", "--allow-effect", "SOURCE_INGESTION"],
        ["inspect", "commands", "--commit"],
        ["sync", "assembly-roster"],
        ["observe", "nec-winners", "--election-id", "20260603", "--type", "3", "--party", "x"],
        [
            "materialize",
            "alio-safe-people",
            "--allow-effect",
            "IDENTITY_MATERIALIZATION",
            "--expected-receipt-sha256",
            "wrong",
        ],
        ["observe", "assembly", "--allow-effect", "SOURCE_INGESTION", "--page-size", "0"],
    ],
)
def test_rejection_precedes_all_dispatch(monkeypatch, argv):
    def forbidden(_):
        pytest.fail("worker dispatch occurred before rejection")

    monkeypatch.setattr(adapters, "dispatch", forbidden)
    with pytest.raises(SystemExit) as exc:
        main(argv)
    assert exc.value.code == 2


def test_assembly_observation_calls_only_enumeration(monkeypatch, capsys):
    calls = []

    class Enumerator:
        def __init__(self, connector, repo):
            calls.append((connector, repo))

        def enumerate(self, *, resume):
            calls.append(resume)
            return {"status": "SUCCESS"}

        def enumerate_and_materialize(self, **kwargs):
            pytest.fail("mixed runner called")

    w = SimpleNamespace(
        OpenAssemblyMemberConnector=lambda **kw: kw, AssemblyRosterEnumerator=Enumerator
    )
    monkeypatch.setattr(adapters, "worker", lambda name: w)
    monkeypatch.setattr(adapters, "repository", lambda args: "isolated fake repo")
    assert main(["observe", "assembly", "--resume", "--allow-effect", "SOURCE_INGESTION"]) == 0
    assert calls[1] is True
    assert json.loads(capsys.readouterr().out)["effect"] == "SOURCE_INGESTION"


@pytest.mark.parametrize(
    "limits",
    [
        ["--max-requests", "2"],
        ["--max-requests", "0", "--min-request-interval", "1", "--fetch-deadline-seconds", "120"],
        ["--max-requests", "2", "--min-request-interval", "nan", "--fetch-deadline-seconds", "120"],
        ["--max-requests", "2", "--min-request-interval", "-1", "--fetch-deadline-seconds", "120"],
        ["--max-requests", "2", "--min-request-interval", "1", "--fetch-deadline-seconds", "inf"],
        ["--max-requests", "2", "--min-request-interval", "1", "--fetch-deadline-seconds", "0"],
    ],
)
def test_invalid_assembly_request_limits_precede_dispatch(monkeypatch, limits):
    def forbidden(_):
        pytest.fail("worker or DB dispatched for invalid Assembly request limits")

    monkeypatch.setattr(adapters, "dispatch", forbidden)
    with pytest.raises(SystemExit) as exc:
        main(["observe", "assembly", "--allow-effect", "SOURCE_INGESTION", *limits])
    assert exc.value.code == 2


def test_assembly_request_limits_reach_canonical_enumerator(monkeypatch, capsys):
    calls = []

    class Enumerator:
        def __init__(self, connector, repo):
            calls.append((connector, repo))

        def enumerate(self, *, resume):
            assert resume is False
            return {"status": "SUCCESS"}

    w = SimpleNamespace(
        OpenAssemblyMemberConnector=lambda **kw: kw, AssemblyRosterEnumerator=Enumerator
    )
    monkeypatch.setattr(adapters, "worker", lambda name: w)
    monkeypatch.setattr(adapters, "repository", lambda args: "isolated fake repo")
    assert main([
        "observe", "assembly", "--allow-effect", "SOURCE_INGESTION", "--max-requests", "8",
        "--min-request-interval", "1", "--fetch-deadline-seconds", "120",
    ]) == 0
    limits = calls[0][0]["request_limits"]
    assert (limits.max_requests, limits.min_interval_seconds, limits.deadline_seconds) == (8, 1, 120)
    assert json.loads(capsys.readouterr().out)["effect"] == "SOURCE_INGESTION"


def test_materialization_does_not_fetch(monkeypatch):
    called = []
    monkeypatch.setattr(adapters, "repository", lambda args: "fake")
    monkeypatch.setattr(adapters, "materialize_assembly", lambda repo: called.append(repo))
    assert main(["materialize", "assembly", "--allow-effect", "IDENTITY_MATERIALIZATION"]) == 0
    assert called == ["fake"]


def test_inspect_has_no_repository_or_workers(monkeypatch, capsys):
    monkeypatch.setattr(adapters, "repository", lambda args: pytest.fail("DB opened"))
    monkeypatch.setattr(adapters, "worker", lambda name: pytest.fail("worker loaded"))
    assert main(["inspect", "commands"]) == 0
    receipt = json.loads(capsys.readouterr().out)
    assert receipt["effect"] == "READ_ONLY"
    assert len(receipt["result"]) == sum(len(lanes) for _, lanes in ROUTES.values())


def test_safe_people_preflight_and_commit_are_separate(monkeypatch):
    calls = []
    r = SimpleNamespace(
        prepare_alio_person_materialization=lambda: SimpleNamespace(
            to_dict=lambda: calls.append("read")
        ),
        commit_alio_person_materialization=lambda **kw: calls.append(("write", kw)),
    )
    monkeypatch.setattr(adapters, "repository", lambda args: SimpleNamespace(administration=r))
    assert main(["inspect", "alio-safe-people"]) == 0
    digest = "a" * 64
    assert (
        main(
            [
                "materialize",
                "alio-safe-people",
                "--allow-effect",
                "IDENTITY_MATERIALIZATION",
                "--expected-receipt-sha256",
                digest,
            ]
        )
        == 0
    )
    assert calls == ["read", ("write", {"expected_receipt_sha256": digest})]


def test_cli_failure_suppresses_operational_details(monkeypatch, capsys):
    def fail(args):
        raise RuntimeError("postgres://private-password@host/database")

    monkeypatch.setattr(adapters, "dispatch", fail)
    assert main(["inspect", "commands"]) == 1
    output = capsys.readouterr().out
    assert "private-password" not in output
    assert json.loads(output)["error_code"] == "COMMAND_FAILED"


def test_readonly_preflight_rejects_mutation_digest():
    with pytest.raises(SystemExit):
        parse_command(["inspect", "alio-safe-people", "--expected-receipt-sha256", "a" * 64])


def test_review_effect_includes_actual_role_claim_publication():
    args = parse_command(
        [
            "review",
            "assembly-distinct-person",
            "--review-item-id",
            "10000000-0000-0000-0000-000000000001",
            "--resolution-note",
            "reviewed distinct person",
            "--allow-effect",
            "CLAIM_PUBLICATION",
        ]
    )
    assert args.effect == CommandEffect.CLAIM_PUBLICATION
