from __future__ import annotations

import argparse
import html
import json
import re
import time
from collections.abc import Iterable
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx


class PublicBetaPreflightError(RuntimeError):
    pass


@dataclass(frozen=True)
class PreflightCheck:
    name: str
    path: str
    http_status: int
    elapsed_ms: int

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "path": self.path,
            "http_status": self.http_status,
            "elapsed_ms": self.elapsed_ms,
        }


def _validate_base_url(value: str) -> str:
    text = value.strip()
    parsed = urlparse(text)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise PublicBetaPreflightError("web base URL must be an absolute http(s) URL")
    if parsed.username or parsed.password:
        raise PublicBetaPreflightError("web base URL must not contain credentials")
    if parsed.query or parsed.fragment:
        raise PublicBetaPreflightError("web base URL must not contain query or fragment")
    return text.rstrip("/")


def _visible_text(value: str) -> str:
    without_tags = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", html.unescape(without_tags)).strip()


def _require_text(body: str, required: Iterable[str], *, label: str) -> None:
    visible = _visible_text(body)
    missing = [item for item in required if item not in visible]
    if missing:
        raise PublicBetaPreflightError(
            f"{label} lacks required visible text: {', '.join(missing)}"
        )


def _reject_tokens(body: str, forbidden: Iterable[str], *, label: str) -> None:
    found = [item for item in forbidden if item in body]
    if found:
        raise PublicBetaPreflightError(
            f"{label} exposes forbidden token(s): {', '.join(found)}"
        )


def _get(
    client: httpx.Client,
    *,
    path: str,
    name: str,
) -> tuple[PreflightCheck, str]:
    started = time.perf_counter()
    try:
        response = client.get(path)
    except httpx.HTTPError as exc:
        raise PublicBetaPreflightError(f"{name} request failed") from exc
    elapsed_ms = int((time.perf_counter() - started) * 1000)
    if response.status_code != 200:
        raise PublicBetaPreflightError(
            f"{name} returned HTTP {response.status_code}"
        )
    return (
        PreflightCheck(
            name=name,
            path=path,
            http_status=response.status_code,
            elapsed_ms=elapsed_ms,
        ),
        response.text,
    )


def run_public_beta_preflight(
    *,
    web_base_url: str,
    expect_indexing: bool,
    person_id: str | None = None,
    organization_id: str | None = None,
    timeout_seconds: float = 20.0,
    transport: httpx.BaseTransport | None = None,
) -> dict[str, object]:
    base_url = _validate_base_url(web_base_url)
    if timeout_seconds <= 0:
        raise PublicBetaPreflightError("timeout must be positive")

    checks: list[PreflightCheck] = []
    forbidden_tokens = (
        "TEL_NO",
        "E_MAIL",
        "normalized_payload",
        "raw_payload",
        "private-ish@example.invalid",
    )

    with httpx.Client(
        base_url=base_url,
        timeout=timeout_seconds,
        follow_redirects=True,
        transport=transport,
        headers={"User-Agent": "CivicIntel-PublicBetaPreflight/0.1"},
    ) as client:
        check, home = _get(client, path="/", name="home")
        checks.append(check)
        _require_text(home, ("Civic Intel", "국감 2026"), label="home")
        _reject_tokens(home, forbidden_tokens, label="home")

        check, gukgam = _get(client, path="/gukgam/2026", name="gukgam_2026")
        checks.append(check)
        _require_text(
            gukgam,
            ("국감", "2026", "검증된 만큼만", "공식 기록상 연결만"),
            label="gukgam_2026",
        )
        _reject_tokens(gukgam, forbidden_tokens, label="gukgam_2026")

        check, robots = _get(client, path="/robots.txt", name="robots")
        checks.append(check)
        check, sitemap = _get(client, path="/sitemap.xml", name="sitemap")
        checks.append(check)

        home_lower = home.casefold()
        if expect_indexing:
            if "noindex" in home_lower:
                raise PublicBetaPreflightError(
                    "indexing-enabled home still contains noindex"
                )
            if "rel=\"canonical\"" not in home_lower:
                raise PublicBetaPreflightError(
                    "indexing-enabled home lacks canonical link"
                )
            if "Allow: /" not in robots or "Disallow: /admin/" not in robots:
                raise PublicBetaPreflightError(
                    "indexing-enabled robots contract is incomplete"
                )
            if "Sitemap:" not in robots:
                raise PublicBetaPreflightError(
                    "indexing-enabled robots lacks sitemap"
                )
            if "/gukgam/2026" not in sitemap:
                raise PublicBetaPreflightError(
                    "indexing-enabled sitemap lacks Gukgam route"
                )
        else:
            if "noindex" not in home_lower:
                raise PublicBetaPreflightError(
                    "indexing-disabled home lacks noindex"
                )
            if "Disallow: /" not in robots:
                raise PublicBetaPreflightError(
                    "indexing-disabled robots must disallow all"
                )
            if "<url>" in sitemap:
                raise PublicBetaPreflightError(
                    "indexing-disabled sitemap must be empty"
                )

        if person_id:
            check, person = _get(
                client,
                path=f"/people/{person_id}",
                name="person_detail",
            )
            checks.append(check)
            _require_text(
                person,
                ("공식 기록상 연결", "Evidence"),
                label="person_detail",
            )
            _reject_tokens(person, forbidden_tokens, label="person_detail")

        if organization_id:
            check, organization = _get(
                client,
                path=f"/organizations/{organization_id}",
                name="organization_detail",
            )
            checks.append(check)
            _require_text(
                organization,
                ("공식 기록상 연결", "Evidence"),
                label="organization_detail",
            )
            _reject_tokens(
                organization,
                forbidden_tokens,
                label="organization_detail",
            )

    return {
        "status": "PASS",
        "web_base_url": base_url,
        "expect_indexing": expect_indexing,
        "checks": [check.to_dict() for check in checks],
        "semantics": (
            "READ_ONLY_HTTP_PREFLIGHT; this command does not mutate application data, "
            "Railway configuration, indexing settings, or canonical evidence"
        ),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run read-only Civic Intel public-beta HTTP acceptance checks."
    )
    parser.add_argument("--web-base-url", required=True)
    parser.add_argument(
        "--expect-indexing",
        choices=("enabled", "disabled"),
        required=True,
    )
    parser.add_argument("--person-id")
    parser.add_argument("--organization-id")
    parser.add_argument("--timeout-seconds", type=float, default=20.0)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        report = run_public_beta_preflight(
            web_base_url=args.web_base_url,
            expect_indexing=args.expect_indexing == "enabled",
            person_id=args.person_id,
            organization_id=args.organization_id,
            timeout_seconds=args.timeout_seconds,
        )
    except PublicBetaPreflightError as exc:
        print(
            json.dumps(
                {"status": "FAIL", "error": str(exc)},
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return 2

    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
