from __future__ import annotations

import argparse
import re

_SHA256 = re.compile("^[0-9a-f]{64}$")


def _types(value: str) -> tuple[int, ...]:
    try:
        parsed = tuple(sorted({int(item.strip()) for item in value.split(",") if item.strip()}))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("types must be comma-separated integers") from exc
    if not parsed:
        raise argparse.ArgumentTypeError("at least one election type is required")
    return parsed
