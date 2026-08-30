from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from packages.domain.contracts import Person


@dataclass(frozen=True)
class QualityReport:
    people_count: int
    scenario_count: int
    failures: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return not self.failures


def evaluate_golden(root: Path | None = None) -> QualityReport:
    fixture_root = root or Path("tests/golden/fixtures")
    people_data = json.loads((fixture_root / "people.json").read_text(encoding="utf-8"))
    scenarios = json.loads((fixture_root / "scenarios.json").read_text(encoding="utf-8"))
    failures: list[str] = []
    people = [Person.model_validate(item) for item in people_data]
    if len(people) != 10:
        failures.append("golden harness must support exactly ten representative people")
    required = {
        "resolved_identity",
        "same_name_false_match",
        "source_reprint_collapse",
        "official_assertion_remains_claim",
        "support_and_refute",
        "unknown_first_class",
        "one_episode_not_pattern",
        "two_independent_episodes_candidate",
        "weak_comention",
        "blocked_source_policy",
        "discovery_only_source_policy",
    }
    names = {scenario["name"] for scenario in scenarios}
    failures.extend(f"missing scenario: {name}" for name in sorted(required - names))
    return QualityReport(len(people), len(scenarios), tuple(failures))


def main() -> int:
    report = evaluate_golden()
    print(json.dumps(asdict(report) | {"passed": report.passed}, indent=2))
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
