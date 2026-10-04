"""Synthetic latency benchmark for the public Gukgam read routes.

Seeds a throwaway SQLite database (never a real one) with public People carrying
ASSEMBLY_COMMITTEES / ASSEMBLY_PARTY claims plus unrelated published claims, and
Organizations carrying Gukgam audit-target claims, then times the routes through
FastAPI's TestClient.  The first reviewed Gukgam claim is produced by the real
import worker so that Source/Policy/Snapshot/Observation provenance is genuine;
every other row is a clone of it with a new subject.

    python scripts/bench_gukgam_read.py --db bench.db --people 300 --targets 150
    python scripts/bench_gukgam_read.py --db bench.db --dump after.json

--dump writes the canonical JSON bodies of the routes so that two runs on the same
database file (before/after a change) can be compared byte for byte.
"""

from __future__ import annotations

import argparse
import json
import random
import statistics
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from fastapi.testclient import TestClient
from sqlalchemy import select

from apps.api.main import create_app
from packages.domain.db import (
    ClaimEvidenceRow,
    ClaimRow,
    OrganizationRow,
    PersonRow,
)
from packages.persistence import SqlAlchemyRepository

COMMITTEE_COUNT = 17
ROUTES = ("/gukgam/2026/targets", "/gukgam/2026/committees", "/people", "/organizations")


def seed(db: Path, people: int, targets: int, noise_claims: int) -> None:
    import test_gukgam_reviewed_claim_import as helpers

    from workers.gukgam_reviewed_claim_import import main as import_main

    repository, url = helpers.migrated_repository(db)
    raw = helpers.packet_payload()
    review_key = helpers.commit_packet(repository, raw)
    first_target = raw["schedule"][0]["audited_targets"][0]
    first_org = helpers.insert_organization(repository, first_target)
    assert (
        import_main(
            [
                "--database-url", url,
                "--organization-id", str(first_org),
                "--review-key", review_key,
                "--commit",
            ]
        )
        == 0
    )
    rng = random.Random(7)
    now = datetime.now(UTC)
    with repository.sessions() as session:
        template = session.scalars(
            select(ClaimRow).where(ClaimRow.organization_id == str(first_org))
        ).one()
        template_evidence = session.scalars(
            select(ClaimEvidenceRow).where(ClaimEvidenceRow.claim_id == template.id)
        ).one()
        committees = [template.qualifiers["committee_name"]] + [
            f"테스트{i}위원회" for i in range(1, COMMITTEE_COUNT)
        ]

        def clone_claim(subject_kw: dict, predicate: str, object_text: str, qualifiers: dict,
                        proposition: str, subject: str) -> ClaimRow:
            return ClaimRow(
                id=str(uuid4()),
                proposition=proposition,
                subject=subject,
                predicate=predicate,
                object_text=object_text,
                qualifiers=qualifiers,
                epistemic_status=template.epistemic_status,
                publication_status=template.publication_status,
                asserted_as_true=True,
                resolution_note=None,
                valid_from=template.valid_from,
                valid_to=None,
                recorded_at=now,
                superseded_at=None,
                **subject_kw,
            )

        def evidence_for(claim: ClaimRow) -> ClaimEvidenceRow:
            return ClaimEvidenceRow(
                id=str(uuid4()),
                claim_id=claim.id,
                source_id=template_evidence.source_id,
                snapshot_id=template_evidence.snapshot_id,
                feeder_observation_id=template_evidence.feeder_observation_id,
                stance=template_evidence.stance,
                excerpt=None,
            )

        for index in range(targets - 1):
            org_id = str(uuid4())
            name = f"합성피감기관{index:03d}"
            session.add(
                OrganizationRow(
                    id=org_id, name=name, valid_from=now, valid_to=None,
                    recorded_at=now, superseded_at=None,
                )
            )
            session.flush()
            qualifiers = dict(template.qualifiers)
            qualifiers["audited_target"] = name
            qualifiers["committee_name"] = committees[index % COMMITTEE_COUNT]
            qualifiers["provider_record_key"] = f"{qualifiers['provider_record_key']}#{index}"
            claim = clone_claim(
                {"person_id": None, "organization_id": org_id},
                template.predicate, template.object_text, qualifiers,
                f"{name}는 합성 국정감사계획서에 피감대상으로 기재되어 있다.", name,
            )
            session.add(claim)
            session.flush()
            session.add(evidence_for(claim))
            # unrelated published org claims, as real Organizations carry ALIO claims
            for k in range(noise_claims):
                noise = clone_claim(
                    {"person_id": None, "organization_id": org_id},
                    "ALIO_NOISE", f"값{k}", {"k": str(k)}, f"{name} 속성 {k}입니다.", name,
                )
                session.add(noise)
                session.flush()
                session.add(evidence_for(noise))

        for index in range(people):
            person_id = str(uuid4())
            name = f"합성의원{index:03d}"
            session.add(
                PersonRow(
                    id=person_id, canonical_name=name, birth_date=None,
                    identity_status="RESOLVED", valid_from=now, valid_to=None,
                    recorded_at=now, superseded_at=None,
                )
            )
            session.flush()
            picked = rng.sample(committees, 2)
            for predicate, field, text in (
                ("ASSEMBLY_COMMITTEES", "committees", ", ".join(picked)),
                ("ASSEMBLY_PARTY", "party", f"합성정당{index % 5}"),
            ):
                claim = clone_claim(
                    {"person_id": person_id, "organization_id": None},
                    predicate, text,
                    {"source_contract": "assembly_member_roster", "field_name": field},
                    f"{name} {field} {text}", name,
                )
                session.add(claim)
                session.flush()
                session.add(evidence_for(claim))
            for k in range(noise_claims):
                noise = clone_claim(
                    {"person_id": person_id, "organization_id": None},
                    "PERSON_NOISE", f"값{k}", {"k": str(k)}, f"{name} 속성 {k}입니다.", name,
                )
                session.add(noise)
                session.flush()
                session.add(evidence_for(noise))
        session.commit()


def timed(client: TestClient, route: str, runs: int) -> tuple[float, list[float], bytes]:
    t0 = time.perf_counter()
    first = client.get(route)
    cold = time.perf_counter() - t0
    assert first.status_code == 200, (route, first.status_code, first.text[:300])
    warm = []
    for _ in range(runs):
        t0 = time.perf_counter()
        client.get(route)
        warm.append(time.perf_counter() - t0)
    return cold, warm, first.content


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--people", type=int, default=300)
    parser.add_argument("--targets", type=int, default=150)
    parser.add_argument("--noise-claims", type=int, default=6)
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument("--dump", type=Path)
    args = parser.parse_args()
    if not args.db.exists():
        seed(args.db, args.people, args.targets, args.noise_claims)
    repository = SqlAlchemyRepository(f"sqlite:///{args.db.resolve().as_posix()}")
    bodies = {}
    with TestClient(create_app(repository)) as client:
        for route in ROUTES:
            cold, warm, body = timed(client, route, args.runs)
            bodies[route] = json.loads(body)
            print(
                f"{route:28s} cold={cold * 1000:8.0f} ms  "
                f"warm_median={statistics.median(warm) * 1000:8.0f} ms  bytes={len(body)}"
            )
    if args.dump:
        args.dump.write_text(
            json.dumps(bodies, ensure_ascii=False, sort_keys=True, indent=1), encoding="utf-8"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
