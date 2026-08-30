from __future__ import annotations

import argparse
import json
from dataclasses import dataclass

from packages.connectors.open_assembly import (
    AssemblyApiError,
    AssemblyMemberRecord,
    OpenAssemblyMemberConnector,
    national_assembly_member_policy,
)
from packages.domain.contracts import SourcePolicy
from packages.verification.identity import IdentityCandidate
from packages.verification.policy import PolicyAction, PolicyDenied, require_policy


def assembly_member_to_identity_candidate(record: AssemblyMemberRecord) -> IdentityCandidate:
    aliases = tuple(
        value for value in (record.name_hanja, record.name_en) if value and value != record.name_ko
    )
    anchors = [f"assembly_member_code:{record.member_code}"]
    for label, value in (
        ("district", record.district),
        ("committees", record.committees),
        ("reelection", record.reelection),
        ("election_type", record.election_type),
    ):
        if value:
            anchors.append(f"{label}:{value}")
    return IdentityCandidate(
        canonical_name=record.name_ko,
        aliases=aliases,
        birth_date=record.birth_date,
        office="국회의원",
        organization=record.party,
        career_anchors=tuple(anchors),
    )


@dataclass(frozen=True)
class StagedAssemblyMember:
    member_code: str
    candidate: IdentityCandidate

    def to_dict(self) -> dict[str, object]:
        return {
            "member_code": self.member_code,
            "canonical_name": self.candidate.canonical_name,
            "aliases": list(self.candidate.aliases),
            "birth_date": (
                self.candidate.birth_date.isoformat() if self.candidate.birth_date else None
            ),
            "office": self.candidate.office,
            "organization": self.candidate.organization,
            "identity_anchors": list(self.candidate.career_anchors),
        }


class AssemblyRosterStager:
    def __init__(
        self,
        connector: OpenAssemblyMemberConnector,
        policy: SourcePolicy | None = None,
    ) -> None:
        self.connector = connector
        self.policy = policy or national_assembly_member_policy()

    def stage(self, url: str | None = None) -> list[StagedAssemblyMember]:
        if self.policy.domain != self.connector.HOST:
            raise PolicyDenied("SourcePolicy domain does not match the National Assembly connector")
        require_policy(self.policy, PolicyAction.FETCH)
        target = url or self.connector.discover()[0]
        document = self.connector.fetch(target)
        return [
            StagedAssemblyMember(record.member_code, assembly_member_to_identity_candidate(record))
            for record in self.connector.parse_members(document)
        ]


def render_staged_json(items: list[StagedAssemblyMember]) -> str:
    return json.dumps(
        [item.to_dict() for item in items],
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Stage National Assembly member rows as identity candidates."
    )
    parser.add_argument("--page-index", type=int, default=1)
    parser.add_argument("--page-size", type=int, default=100)
    parser.add_argument("--name")
    parser.add_argument("--party")
    parser.add_argument("--district")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    connector = OpenAssemblyMemberConnector(
        page_index=args.page_index,
        page_size=args.page_size,
        name=args.name,
        party=args.party,
        district=args.district,
    )
    try:
        staged = AssemblyRosterStager(connector).stage()
    except (AssemblyApiError, PolicyDenied, ValueError) as exc:
        parser.error(str(exc))
    print(render_staged_json(staged))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
