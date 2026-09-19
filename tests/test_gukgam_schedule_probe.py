import json
from datetime import date

from packages.connectors.base import ConnectorDocument
from packages.connectors.open_assembly_schedule import OpenAssemblyScheduleConnector
from workers.gukgam_schedule_probe import build_probe_report, main

SECRET = "probe-test-secret"


def _document() -> ConnectorDocument:
    payload = {
        OpenAssemblyScheduleConnector.API_CODE: [
            {
                "head": [
                    {"list_total_count": 2},
                    {"RESULT": {"CODE": "INFO-000", "MESSAGE": "정상"}},
                ]
            },
            {
                "row": [
                    {
                        "SCH_KIND": "위원회",
                        "SCH_DT": "20261006",
                        "SCH_TM": "10:00",
                        "CMIT_NM": "과학기술정보방송통신위원회",
                        "SCH_CN": "2026년도 국정감사",
                        "EV_PLC": "국회",
                        "CONF_SESS": "439",
                        "CONF_DGR": "1",
                    },
                    {
                        "SCH_KIND": "위원회",
                        "SCH_DT": "20261006",
                        "SCH_TM": "14:00",
                        "CMIT_NM": "과학기술정보방송통신위원회",
                        "SCH_CN": "법률안 상정",
                        "EV_PLC": "국회",
                        "CONF_SESS": "439",
                        "CONF_DGR": "2",
                    },
                ]
            },
        ]
    }
    return ConnectorDocument(
        url=(
            "https://open.assembly.go.kr/portal/openapi/ALLSCHEDULE?"
            "Type=json&pIndex=1&pSize=10&SCH_DT=20261006&"
            "CMIT_NM=%EA%B3%BC%ED%95%99%EA%B8%B0%EC%88%A0%EC%A0%95%EB%B3%B4"
            "%EB%B0%A9%EC%86%A1%ED%86%B5%EC%8B%A0%EC%9C%84%EC%9B%90%ED%9A%8C"
        ),
        title="국회 국회사무처_국회일정 통합 API",
        publisher="국회 국회사무처",
        published_at=None,
        body=json.dumps(payload, ensure_ascii=False),
        metadata={
            "api_code": "ALLSCHEDULE",
            "source_contract": "national_assembly_schedule_v1",
            "page_index": "1",
            "page_size": "10",
            "row_count": "2",
            "list_total_count": "2",
            "result_code": "INFO-000",
            "SCH_DT": "20261006",
            "CMIT_NM": "과학기술정보방송통신위원회",
        },
    )


def test_probe_report_is_read_only_and_only_returns_gukgam_candidates(
    monkeypatch,
) -> None:
    connector = OpenAssemblyScheduleConnector(
        api_key=SECRET,
        schedule_date=date(2026, 10, 6),
        committee="과학기술정보방송통신위원회",
        page_size=10,
    )
    monkeypatch.setattr(connector, "fetch", lambda url: _document())

    report = build_probe_report(connector=connector)

    assert report["status"] == "READ_ONLY_PROBE"
    assert report["api_code"] == "ALLSCHEDULE"
    assert report["provider"] == {
        "result_code": "INFO-000",
        "list_total_count": "2",
        "row_count": "2",
    }
    assert report["gukgam_candidate_count"] == 1
    assert report["gukgam_candidates"] == [
        {
            "schedule_date": "2026-10-06",
            "schedule_kind": "위원회",
            "schedule_time": "10:00",
            "committee_name": "과학기술정보방송통신위원회",
            "content": "2026년도 국정감사",
            "place": "국회",
            "session": "439",
            "degree": "1",
        }
    ]
    assert SECRET not in json.dumps(report, ensure_ascii=False)
    assert "audited_organizations" not in json.dumps(report)
    assert "witnesses" not in json.dumps(report)


def test_probe_cli_requires_a_bounded_date_and_committee() -> None:
    try:
        main(["--date", "2026-10-06", "--committee", ""])
    except SystemExit as exc:
        assert exc.code == 2
    else:
        raise AssertionError("empty committee must fail")


def test_probe_cli_rejects_large_page_size() -> None:
    try:
        main(
            [
                "--date",
                "2026-10-06",
                "--committee",
                "과학기술정보방송통신위원회",
                "--page-size",
                "101",
            ]
        )
    except SystemExit as exc:
        assert exc.code == 2
    else:
        raise AssertionError("unbounded page size must fail")
