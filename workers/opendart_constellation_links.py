"""Link OpenDART executive rows to People by the three-anchor constellation rule.

Default is a dry run. ``--publish`` writes the linked role CLAIMs and the review-queue items; run
it only after the owner approved the rule (see ``packages.verification.opendart_constellation_links``).
"""

from __future__ import annotations

import argparse
import json

from packages.persistence import SqlAlchemyRepository
from packages.verification.opendart_constellation_links import OpendartConstellationLinker


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--publish", action="store_true")
    parser.add_argument("--database-url")
    args = parser.parse_args(argv)
    result = OpendartConstellationLinker(SqlAlchemyRepository(args.database_url)).publish(
        dry_run=not args.publish
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
