from __future__ import annotations

import argparse
import json
from dataclasses import dataclass

from packages.connectors.nec_local_elections import (
    LOCAL_ELECTION_TYPES,
    NecApiError,
    NecCandidateConnector,
    NecCandidateRecord,
    NecWinnerConnector,
    nec_local_election_policy,
)
from packages.domain.contracts import SourcePolicy
from packages.verification.identity import IdentityCandidate
from packages.verification.policy import PolicyAction, PolicyDenied, require_policy


@dataclass(frozen=True)
class StagedLocalElectionCandidate:
    candidate: IdentityCandidate
    candidate_id: str
    election_id: str
    election_type: int
    election_type_name: str
    district_name: str
    province_name: str
    municipality_name: str | None
    party: str | None
    candidate_number: str | None
    candidate_sub_number: str | None
    registration_status: str | None
    public_job: str | None
    submitted_education: str | None
    submitted_careers: tuple[str, ...]
    outcome: str
    votes: int | None = None
    vote_rate: float | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "candidate_id": self.candidate_id,
            "canonical_name": self.candidate.canonical_name,
            "aliases": list(self.candidate.aliases),
            "birth_date": self.candidate.birth_date.isoformat() if self.candidate.birth_date else None,
            "election": {
                "election_id": self.election_id,
                "type_code": self.election_type,
                "type_name": self.election_type_name,
                "province": self.province_name,
                "municipality": self.municipality_name,
                "district": self.district_name,
                "party": self.party,
                "candidate_number": self.candidate_number,
                "candidate_sub_number": self.candidate_sub_number,
                "registration_status": self.registration_status,
                "outcome": self.outcome,
                "votes": self.votes,
                "vote_rate": self.vote_rate,
            },
            "candidate_submitted": {
                "public_job": self.public_job,
                "education": self.submitted_education,
                "careers": list(self.submitted_careers),
                "semantics": (
                    "후보자가 선거관리위원회에 제출해 공개된 정보이며, 독립 검증된 경력과는 구분한다."
                ),
            },
            "identity_anchors": list(self.candidate.career_anchors),
        }


def candidate_to_identity(record: NecCandidateRecord) -> IdentityCandidate:
    aliases = (record.name_hanja,) if record.name_hanja and record.name_hanja != record.name_ko else ()
    jurisdiction = "/".join(
        value for value in (record.province_name, record.municipality_name, record.district_name) if value
    )
    anchors = (
        f"nec_candidate_id:{record.candidate_id}",
        f"election_id:{record.election_id}",
        f"election_type:{record.election_type}",
        f"election_jurisdiction:{jurisdiction}",
    )
    return IdentityCandidate(
        canonical_name=record.name_ko,
        aliases=aliases,
        birth_date=record.birth_date,
        office=f"{LOCAL_ELECTION_TYPES[record.election_type]} 후보",
        organization=record.party,
        career_anchors=anchors,
    )


def _coverage_complete(metadata: dict[str, str]) -> bool:
    total_text = metadata.get("total_count")
    if not total_text:
        return False
    try:
        total = int(total_text)
        page_no = int(metadata.get("page_no", "1"))
        page_size = int(metadata.get("page_size", "100"))
    except ValueError:
        return False
    return page_no == 1 and total <= page_size


class LocalElectionStager:
    def __init__(
        self,
        candidate_connector: NecCandidateConnector,
        winner_connector: NecWinnerConnector,
        policy: SourcePolicy | None = None,
    ) -> None:
        if (
            candidate_connector.election_id != winner_connector.election_id
            or candidate_connector.election_type != winner_connector.election_type
        ):
            raise ValueError("candidate and winner connectors must target the same election")
        self.candidate_connector = candidate_connector
        self.winner_connector = winner_connector
        self.policy = policy or nec_local_election_policy()

    def stage(self) -> list[StagedLocalElectionCandidate]:
        if self.policy.domain != self.candidate_connector.HOST:
            raise PolicyDenied("SourcePolicy domain does not match NEC connectors")
        require_policy(self.policy, PolicyAction.FETCH)

        candidate_document = self.candidate_connector.fetch(self.candidate_connector.discover()[0])
        winner_document = self.winner_connector.fetch(self.winner_connector.discover()[0])
        candidates = self.candidate_connector.parse_candidates(candidate_document)
        winners = {
            record.candidate_id: record for record in self.winner_connector.parse_winners(winner_document)
        }
        winner_coverage_complete = _coverage_complete(winner_document.metadata)

        staged: list[StagedLocalElectionCandidate] = []
        for record in candidates:
            winner = winners.get(record.candidate_id)
            outcome = "WINNER" if winner else "NOT_WINNER" if winner_coverage_complete else "UNKNOWN"
            staged.append(
                StagedLocalElectionCandidate(
                    candidate=candidate_to_identity(record),
                    candidate_id=record.candidate_id,
                    election_id=record.election_id,
                    election_type=record.election_type,
                    election_type_name=LOCAL_ELECTION_TYPES[record.election_type],
                    district_name=record.district_name,
                    province_name=record.province_name,
                    municipality_name=record.municipality_name,
                    party=record.party,
                    candidate_number=record.candidate_number,
                    candidate_sub_number=record.candidate_sub_number,
                    registration_status=record.registration_status,
                    public_job=record.public_job,
                    submitted_education=record.submitted_education,
                    submitted_careers=record.submitted_careers,
                    outcome=outcome,
                    votes=winner.votes if winner else None,
                    vote_rate=winner.vote_rate if winner else None,
                )
            )
        return staged


def render_local_election_json(items: list[StagedLocalElectionCandidate]) -> str:
    return json.dumps([item.to_dict() for item in items], ensure_ascii=False, indent=2, sort_keys=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Stage NEC local-election candidates for review.")
    parser.add_argument("--election-id", required=True)
    parser.add_argument("--type", required=True, type=int, choices=sorted(LOCAL_ELECTION_TYPES))
    parser.add_argument("--province")
    parser.add_argument("--district")
    parser.add_argument("--party")
    parser.add_argument("--page-no", type=int, default=1)
    parser.add_argument("--page-size", type=int, default=100)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    candidate_connector = NecCandidateConnector(
        election_id=args.election_id,
        election_type=args.type,
        page_no=args.page_no,
        page_size=args.page_size,
        district_name=args.district,
        province_name=args.province,
        party=args.party,
    )
    winner_connector = NecWinnerConnector(
        election_id=args.election_id,
        election_type=args.type,
        page_no=args.page_no,
        page_size=args.page_size,
        district_name=args.district,
        province_name=args.province,
    )
    try:
        staged = LocalElectionStager(candidate_connector, winner_connector).stage()
    except (NecApiError, PolicyDenied, ValueError) as exc:
        raise SystemExit(str(exc)) from None
    print(render_local_election_json(staged))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
