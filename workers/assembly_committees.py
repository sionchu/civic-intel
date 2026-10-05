from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass

from packages.connectors.open_assembly_committees import (
    AssemblyCommitteeMemberRecord,
    AssemblyCommitteeStatusRecord,
    OpenAssemblyCommitteeMemberConnector,
    OpenAssemblyCommitteeStatusConnector,
    national_assembly_committee_policy,
)
from packages.domain.contracts import SourcePolicy
from packages.verification.policy import PolicyAction, PolicyDenied, require_policy


def committee_status_provider_key(record: AssemblyCommitteeStatusRecord) -> str:
    return record.committee_code


def committee_membership_provider_key(record: AssemblyCommitteeMemberRecord) -> str:
    return f"{record.committee_code}:{record.member_code}"


@dataclass(frozen=True)
class StagedAssemblyCommitteeRoster:
    statuses: tuple[AssemblyCommitteeStatusRecord, ...]
    memberships: tuple[AssemblyCommitteeMemberRecord, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "statuses": [
                {
                    "provider_record_key": committee_status_provider_key(item),
                    **asdict(item),
                }
                for item in self.statuses
            ],
            "memberships": [
                {
                    "provider_record_key": committee_membership_provider_key(item),
                    **asdict(item),
                }
                for item in self.memberships
            ],
        }


class AssemblyCommitteeRosterStager:
    def __init__(
        self,
        status_connector: OpenAssemblyCommitteeStatusConnector,
        member_connector: OpenAssemblyCommitteeMemberConnector,
        policy: SourcePolicy | None = None,
    ) -> None:
        self.status_connector = status_connector
        self.member_connector = member_connector
        self.policy = policy or national_assembly_committee_policy()

    def _authorize(self) -> None:
        if (
            self.policy.domain != self.status_connector.HOST
            or self.policy.domain != self.member_connector.HOST
        ):
            raise PolicyDenied(
                "SourcePolicy domain does not match the National Assembly committee connectors"
            )
        require_policy(self.policy, PolicyAction.FETCH)

    def stage(self) -> StagedAssemblyCommitteeRoster:
        self._authorize()
        status_document = self.status_connector.fetch(
            self.status_connector.discover()[0]
        )
        member_document = self.member_connector.fetch(
            self.member_connector.discover()[0]
        )
        return StagedAssemblyCommitteeRoster(
            statuses=self.status_connector.parse_statuses(status_document),
            memberships=self.member_connector.parse_memberships(member_document),
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Stage one privacy-minimized page from the official Assembly committee APIs."
    )
    parser.add_argument(
        "--sample",
        action="store_true",
        help="Use the official no-key sample mode (page 1, 5 rows).",
    )
    parser.add_argument("--page-index", type=int, default=1)
    parser.add_argument("--page-size", type=int, default=100)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    page_index = 1 if args.sample else args.page_index
    page_size = 5 if args.sample else args.page_size
    try:
        staged = AssemblyCommitteeRosterStager(
            OpenAssemblyCommitteeStatusConnector(
                page_index=page_index,
                page_size=page_size,
                sample_mode=args.sample,
            ),
            OpenAssemblyCommitteeMemberConnector(
                page_index=page_index,
                page_size=page_size,
                sample_mode=args.sample,
            ),
        ).stage()
    except (PolicyDenied, ValueError, RuntimeError) as exc:
        parser.error(str(exc))
    print(
        json.dumps(
            staged.to_dict(),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
