from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass

from packages.connectors.open_assembly_bills import national_assembly_bill_policy
from packages.connectors.open_assembly_subcommittee import (
    AssemblySubcommitteeReviewRecord,
    OpenAssemblySubcommitteeReviewConnector,
)
from packages.domain.contracts import SourcePolicy
from packages.verification.policy import PolicyAction, PolicyDenied, require_policy


@dataclass(frozen=True)
class StagedAssemblySubcommitteeReview:
    records: tuple[AssemblySubcommitteeReviewRecord, ...]
    list_total_count: int | None
    sample_mode: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "list_total_count": self.list_total_count,
            "sample_mode": self.sample_mode,
            "records": [
                {
                    **asdict(record),
                    "referral_date": (
                        record.referral_date.isoformat()
                        if record.referral_date is not None
                        else None
                    ),
                    "present_date": (
                        record.present_date.isoformat()
                        if record.present_date is not None
                        else None
                    ),
                    "process_date": (
                        record.process_date.isoformat()
                        if record.process_date is not None
                        else None
                    ),
                }
                for record in self.records
            ],
        }


class AssemblySubcommitteeReviewStager:
    def __init__(
        self,
        connector: OpenAssemblySubcommitteeReviewConnector,
        policy: SourcePolicy | None = None,
    ) -> None:
        self.connector = connector
        self.policy = policy or national_assembly_bill_policy()

    def stage(self) -> StagedAssemblySubcommitteeReview:
        if self.policy.domain != self.connector.HOST:
            raise PolicyDenied(
                "SourcePolicy domain does not match the National Assembly subcommittee connector"
            )
        require_policy(self.policy, PolicyAction.FETCH)
        document = self.connector.fetch(self.connector.discover()[0])
        records = self.connector.parse_reviews(document)
        total_text = document.metadata.get("list_total_count", "")
        total = int(total_text) if total_text else None
        return StagedAssemblySubcommitteeReview(
            records=records,
            list_total_count=total,
            sample_mode=self.connector.sample_mode,
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Stage one official National Assembly subcommittee bill-review page."
    )
    parser.add_argument("--assembly-age", type=int, default=22)
    parser.add_argument("--sample", action="store_true")
    parser.add_argument("--page-index", type=int, default=1)
    parser.add_argument("--page-size", type=int, default=100)
    parser.add_argument("--bill-no")
    parser.add_argument("--bill-id")
    parser.add_argument("--direct-referral", choices=("Y", "N"))
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    page_index = 1 if args.sample else args.page_index
    page_size = 5 if args.sample else args.page_size
    try:
        staged = AssemblySubcommitteeReviewStager(
            OpenAssemblySubcommitteeReviewConnector(
                assembly_age=args.assembly_age,
                page_index=page_index,
                page_size=page_size,
                bill_no=args.bill_no,
                bill_id=args.bill_id,
                direct_referral=args.direct_referral,
                sample_mode=args.sample,
            )
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
