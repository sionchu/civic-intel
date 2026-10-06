from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID, uuid5

from packages.connectors.gukgam_witness_packet import (
    GukgamWitnessPacketError,
    ReviewedGukgamWitnessPacket,
    parse_reviewed_gukgam_witness_packet,
)
from packages.domain.contracts import Claim, ClaimEvidence, FeederObservation, Organization
from packages.persistence import OrganizationClaimImportError, SqlAlchemyRepository
from packages.rendering.gukgam_witness_claim import (
    SUBJECT_SCOPE_COMMITTEE,
    GukgamWitnessClaimError,
    build_gukgam_witness_claim,
)
from packages.verification.gukgam_witness_import import (
    GUKGAM_WITNESS_FEEDER,
    committee_organization,
)

GUKGAM_WITNESS_CLAIM_COMMIT_SEMANTICS = "REVIEWED_GUKGAM_WITNESS_CLAIM_COMMIT_V1"
# Deterministic IDs for the 국회 committee Organizations this lane may create on request.
GUKGAM_COMMITTEE_ORGANIZATION_NAMESPACE = UUID("8a4f0f3e-6c2b-4d55-9a61-2f7e3c9b1d04")


class GukgamWitnessClaimCommitError(ValueError):
    pass


@dataclass(frozen=True)
class PreparedWitnessPacket:
    packet: ReviewedGukgamWitnessPacket
    organization: Organization
    organization_action: str  # "REUSE" | "CREATE"
    items: tuple[tuple[Claim, ClaimEvidence], ...]


@dataclass(frozen=True)
class WitnessClaimPlan:
    packets: tuple[PreparedWitnessPacket, ...]

    def sha256(self) -> str:
        lines = sorted(
            f"{prepared.organization.id}\t{prepared.organization.name}\t"
            f"{prepared.organization_action}\t{claim.id}\t{evidence.id}"
            for prepared in self.packets
            for claim, evidence in prepared.items
        )
        return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()


def committee_organization_for(committee_name: str) -> Organization:
    name = f"국회 {committee_name}"
    return Organization(id=uuid5(GUKGAM_COMMITTEE_ORGANIZATION_NAMESPACE, name), name=name)


def _observations_for(
    repository: SqlAlchemyRepository, packet: ReviewedGukgamWitnessPacket
) -> list[FeederObservation]:
    observations = repository.feeder_observations(GUKGAM_WITNESS_FEEDER, packet.scope_key)
    expected = {packet.record_key(row) for row in packet.rows}
    actual = {item.provider_record_key for item in observations}
    if actual != expected or len(observations) != len(expected):
        raise GukgamWitnessClaimCommitError(
            f"imported observations for {packet.scope_key} do not match the reviewed packet "
            f"(expected {len(expected)}, found {len(observations)}); run gukgam_witness_import first"
        )
    return sorted(observations, key=lambda item: item.provider_record_key)


def prepare_witness_claim_plan(
    repository: SqlAlchemyRepository,
    packets: Sequence[ReviewedGukgamWitnessPacket],
    *,
    create_committee_organizations: bool,
) -> WitnessClaimPlan:
    """Committee-scope Claims for every reviewed, imported row. Never touches Person rows."""

    if not packets:
        raise GukgamWitnessClaimCommitError("at least one reviewed packet is required")
    scopes = [packet.scope_key for packet in packets]
    if len(set(scopes)) != len(scopes):
        raise GukgamWitnessClaimCommitError("the same reviewed packet was given twice")
    current = repository.organizations(current_only=True)
    prepared: list[PreparedWitnessPacket] = []
    for packet in packets:
        if not packet.is_human_reviewed:
            raise GukgamWitnessClaimCommitError(
                f"{packet.scope_key} is not HUMAN_REVIEWED; witness Claims require owner review"
            )
        committee_name = packet.source.committee_name
        organization = committee_organization(current, committee_name)
        action = "REUSE"
        if organization is None:
            if not create_committee_organizations:
                raise GukgamWitnessClaimCommitError(
                    f"no current Organization for {committee_name}; pass "
                    "--create-committee-organizations to create it"
                )
            organization = committee_organization_for(committee_name)
            action = "CREATE"
        items: list[tuple[Claim, ClaimEvidence]] = []
        for observation in _observations_for(repository, packet):
            snapshot = repository.source_snapshot(observation.snapshot_id)
            if snapshot is None:
                raise GukgamWitnessClaimCommitError("witness observation snapshot is missing")
            source = repository.sources([snapshot.source_id]).get(snapshot.source_id)
            if source is None:
                raise GukgamWitnessClaimCommitError("witness observation source is missing")
            policy = repository.policies([source.policy_id]).get(source.policy_id)
            if policy is None:
                raise GukgamWitnessClaimCommitError("witness observation policy is missing")
            items.append(
                build_gukgam_witness_claim(
                    organization,
                    observation=observation,
                    snapshot=snapshot,
                    source=source,
                    policy=policy,
                    subject_scope=SUBJECT_SCOPE_COMMITTEE,
                )
            )
        prepared.append(
            PreparedWitnessPacket(
                packet=packet,
                organization=organization,
                organization_action=action,
                items=tuple(items),
            )
        )
    return WitnessClaimPlan(packets=tuple(prepared))


def _report(plan: WitnessClaimPlan) -> dict[str, object]:
    return {
        "semantics": GUKGAM_WITNESS_CLAIM_COMMIT_SEMANTICS,
        "plan_sha256": plan.sha256(),
        "subject_scope": SUBJECT_SCOPE_COMMITTEE,
        "packets": [
            {
                "scope_key": prepared.packet.scope_key,
                "committee_name": prepared.packet.source.committee_name,
                "acquisition_channel": prepared.packet.source.acquisition_channel,
                "organization_name": prepared.organization.name,
                "organization_action": prepared.organization_action,
                "witness_claims": sum(
                    1 for claim, _ in prepared.items if claim.qualifiers["category"] == "증인"
                ),
                "reference_person_claims": sum(
                    1 for claim, _ in prepared.items if claim.qualifiers["category"] == "참고인"
                ),
            }
            for prepared in plan.packets
        ],
        "claim_count": sum(len(prepared.items) for prepared in plan.packets),
        "person_materialization": False,
        "identity_links": False,
        "request_reason_copied": False,
    }


def commit_witness_claim_plan(
    repository: SqlAlchemyRepository, plan: WitnessClaimPlan
) -> dict[str, object]:
    organizations = {prepared.organization.id: prepared.organization for prepared in plan.packets}
    result = repository.import_organization_claim_batch(
        list(organizations.values()),
        [
            (prepared.organization, claim, [evidence])
            for prepared in plan.packets
            for claim, evidence in prepared.items
        ],
    )
    return {
        "status": "COMMITTED" if result.claims_created or result.organizations_created else "REUSED",
        "organizations_created": result.organizations_created,
        "organizations_reused": result.organizations_reused,
        "claims_created": result.claims_created,
        "claims_reused": result.claims_reused,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Dry-run (default) or commit committee-scope published witness-list Claims for "
            "HUMAN_REVIEWED packets whose rows were already imported by gukgam_witness_import. "
            "Names stay source-listed text: no Person is created or linked."
        )
    )
    parser.add_argument("--packet", type=Path, action="append", required=True)
    parser.add_argument("--database-url", required=True)
    parser.add_argument(
        "--create-committee-organizations",
        action="store_true",
        help="Create a missing '국회 <위원회>' Organization (owner-approved) instead of failing.",
    )
    parser.add_argument("--commit", action="store_true")
    parser.add_argument(
        "--expected-plan-sha256",
        help="plan_sha256 printed by the dry run; required with --commit.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        packets = [
            parse_reviewed_gukgam_witness_packet(json.loads(path.read_text(encoding="utf-8")))
            for path in args.packet
        ]
        repository = SqlAlchemyRepository(args.database_url)
        plan = prepare_witness_claim_plan(
            repository,
            packets,
            create_committee_organizations=args.create_committee_organizations,
        )
    except (
        GukgamWitnessPacketError,
        GukgamWitnessClaimCommitError,
        GukgamWitnessClaimError,
        OSError,
        json.JSONDecodeError,
    ) as exc:
        parser.error(str(exc))

    report = _report(plan)
    if not args.commit:
        print(json.dumps({"status": "DRY_RUN"} | report, ensure_ascii=False, indent=2))
        return 0
    expected = (args.expected_plan_sha256 or "").strip().casefold()
    if expected != plan.sha256():
        parser.error("--expected-plan-sha256 must equal the dry-run plan_sha256")
    try:
        result = commit_witness_claim_plan(repository, plan)
    except OrganizationClaimImportError as exc:
        parser.error(str(exc))
    print(json.dumps(result | report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
