from __future__ import annotations

import argparse
import json

from packages.application.identity_candidates import (
    AlioCandidatePipelineError,
    generate_alio_cross_lane_candidates,
)
from packages.bootstrap import application
from packages.persistence import DatabaseNotReady


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate read-only ALIO-to-Person cross-lane review candidates."
    )
    parser.add_argument("--database-url")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    repository = application(args.database_url)
    try:
        report = generate_alio_cross_lane_candidates(repository.uows)
    except (AlioCandidatePipelineError, DatabaseNotReady, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

COMMAND_EFFECT = "READ_ONLY"
