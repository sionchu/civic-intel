from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import timedelta
from difflib import SequenceMatcher
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from packages.domain.contracts import Source


def normalize_url(url: str) -> str:
    parts = urlsplit(url)
    query = urlencode(
        sorted((k, v) for k, v in parse_qsl(parts.query) if not k.lower().startswith("utm_"))
    )
    return urlunsplit(
        (
            parts.scheme.lower(),
            parts.netloc.lower().removeprefix("www."),
            parts.path.rstrip("/"),
            query,
            "",
        )
    )


def text_fingerprint(text: str, shingle_size: int = 4) -> str:
    words = re.findall(r"\w+", text.casefold())
    shingles = sorted(
        " ".join(words[i : i + shingle_size]) for i in range(max(1, len(words) - shingle_size + 1))
    )
    return hashlib.sha256("\n".join(shingles).encode()).hexdigest()


@dataclass(frozen=True)
class OriginDecision:
    same_origin: bool
    score: float
    reasons: tuple[str, ...]


def compare_sources(
    a: Source, b: Source, text_a: str = "", text_b: str = "", attribution_hint: bool = False
) -> OriginDecision:
    reasons: list[str] = []
    score = 0.0
    if normalize_url(str(a.url)) == normalize_url(str(b.url)):
        score += 1.0
        reasons.append("normalized_url")
    title_score = SequenceMatcher(None, a.title.casefold(), b.title.casefold()).ratio()
    if title_score >= 0.88:
        score += 0.4
        reasons.append("title")
    if text_a and text_b and text_fingerprint(text_a) == text_fingerprint(text_b):
        score += 0.6
        reasons.append("fingerprint")
    if (
        a.published_at
        and b.published_at
        and abs(a.published_at - b.published_at) <= timedelta(hours=48)
    ):
        score += 0.1
        reasons.append("time")
    if attribution_hint:
        score += 0.5
        reasons.append("attribution")
    return OriginDecision(score >= 0.7, round(score, 2), tuple(reasons))


def source_counts(sources: list[Source]) -> dict[str, int]:
    return {
        "raw_url_count": len(sources),
        "independent_origin_count": len({s.origin_cluster_id or s.id for s in sources}),
    }
