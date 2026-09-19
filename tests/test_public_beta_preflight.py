import json

import httpx

from workers.public_beta_preflight import (
    PublicBetaPreflightError,
    main,
    run_public_beta_preflight,
)

PERSON_ID = "44745d09-398c-46ce-bc38-81f0f606c1d7"
ORGANIZATION_ID = "3ef4de75-fa3f-5815-81f4-8bc5efdc33f1"


def _transport(*, indexing: bool, leak: bool = False) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        leaked = " TEL_NO private-ish@example.invalid" if leak else ""
        if path == "/":
            robots = (
                '<meta name="robots" content="index, follow">'
                '<link rel="canonical" href="https://example.test/">'
                if indexing
                else '<meta name="robots" content="noindex, nofollow">'
            )
            return httpx.Response(
                200,
                text=f"<html><head>{robots}</head><body>Civic Intel 국감 2026{leaked}</body></html>",
            )
        if path == "/gukgam/2026":
            return httpx.Response(
                200,
                text=(
                    "<html><body><h1>국감 <em>2026</em></h1>"
                    "<strong>공식 기록상 연결만</strong>"
                    "<h2>국감 전용 자료는 <em>검증된 만큼만</em></h2>"
                    "</body></html>"
                ),
            )
        if path == "/robots.txt":
            return httpx.Response(
                200,
                text=(
                    "User-agent: *\nAllow: /\nDisallow: /admin/\n"
                    "Sitemap: https://example.test/sitemap.xml\n"
                    if indexing
                    else "User-agent: *\nDisallow: /\n"
                ),
            )
        if path == "/sitemap.xml":
            return httpx.Response(
                200,
                text=(
                    "<?xml version=\"1.0\"?><urlset><url>"
                    "<loc>https://example.test/gukgam/2026</loc>"
                    "</url></urlset>"
                    if indexing
                    else "<?xml version=\"1.0\"?><urlset></urlset>"
                ),
            )
        if path == f"/people/{PERSON_ID}":
            return httpx.Response(
                200,
                text="<html><body>공식 기록상 연결 Evidence</body></html>",
            )
        if path == f"/organizations/{ORGANIZATION_ID}":
            return httpx.Response(
                200,
                text="<html><body>공식 기록상 연결 Evidence</body></html>",
            )
        return httpx.Response(404)

    return httpx.MockTransport(handler)


def test_staging_preflight_requires_noindex_and_detail_routes() -> None:
    report = run_public_beta_preflight(
        web_base_url="https://example.test",
        expect_indexing=False,
        person_id=PERSON_ID,
        organization_id=ORGANIZATION_ID,
        transport=_transport(indexing=False),
    )

    assert report["status"] == "PASS"
    assert report["expect_indexing"] is False
    assert [item["name"] for item in report["checks"]] == [
        "home",
        "gukgam_2026",
        "robots",
        "sitemap",
        "person_detail",
        "organization_detail",
    ]


def test_public_preflight_requires_canonical_robots_and_sitemap() -> None:
    report = run_public_beta_preflight(
        web_base_url="https://example.test/",
        expect_indexing=True,
        transport=_transport(indexing=True),
    )

    assert report["status"] == "PASS"
    assert report["expect_indexing"] is True


def test_preflight_rejects_public_privacy_leak() -> None:
    try:
        run_public_beta_preflight(
            web_base_url="https://example.test",
            expect_indexing=False,
            transport=_transport(indexing=False, leak=True),
        )
    except PublicBetaPreflightError as exc:
        assert "forbidden token" in str(exc)
        assert "TEL_NO" in str(exc)
    else:
        raise AssertionError("privacy leak must fail preflight")


def test_preflight_rejects_credentialed_base_url() -> None:
    try:
        run_public_beta_preflight(
            web_base_url="https://user:secret@example.test",
            expect_indexing=False,
            transport=_transport(indexing=False),
        )
    except PublicBetaPreflightError as exc:
        assert "credentials" in str(exc)
    else:
        raise AssertionError("credentialed URL must fail preflight")


def test_cli_returns_safe_failure_receipt(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        "workers.public_beta_preflight.run_public_beta_preflight",
        lambda **kwargs: (_ for _ in ()).throw(
            PublicBetaPreflightError("synthetic failure")
        ),
    )

    assert (
        main(
            [
                "--web-base-url",
                "https://example.test",
                "--expect-indexing",
                "disabled",
            ]
        )
        == 2
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload == {"status": "FAIL", "error": "synthetic failure"}
