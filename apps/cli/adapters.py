"""Effect-specific composition; collection and parsing remain in source workers."""

from __future__ import annotations

import argparse
import importlib
import json
from pathlib import Path
from typing import Any

from apps.cli.main import ROUTES


def worker(name: str) -> Any:
    return importlib.import_module("workers." + name)


def repository(args: argparse.Namespace) -> Any:
    from packages.bootstrap import application

    return application(args.database_url)


def _read_only_monitor_url(value: str) -> str:
    from sqlalchemy.engine import make_url

    url = make_url(value)
    if url.get_backend_name() == "sqlite":
        if not url.database or url.database == ":memory:" or url.database.startswith("file:"):
            raise ValueError("collection monitor requires an existing file SQLite URL")
        path = Path(url.database).resolve()
        if not path.is_file():
            raise ValueError("collection monitor database does not exist")
        url = url.set(database="file:" + path.as_posix(), query={"mode": "ro", "uri": "true"})
    elif url.get_backend_name() != "postgresql":
        raise ValueError("collection monitor requires SQLite or PostgreSQL")
    return url.render_as_string(hide_password=False)


def materialize_assembly(repo: Any) -> Any:
    return worker("assembly_roster").materialize_latest_successful(repo)


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def observe(a: argparse.Namespace) -> Any:
    if a.lane == "gukgam-schedule-probe":
        w = worker("gukgam_schedule_probe")
        connector = w.OpenAssemblyScheduleConnector(
            schedule_date=a.date, committee=a.committee.strip(), page_size=a.page_size
        )
        return w.build_probe_report(connector=connector)
    if a.lane in ("assembly", "assembly-page"):
        w = worker("assembly_roster")
        request_kwargs = {}
        if a.lane == "assembly" and a.max_requests is not None:
            from packages.connectors.open_assembly import AssemblyRequestLimits

            request_kwargs["request_limits"] = AssemblyRequestLimits(
                max_requests=a.max_requests,
                min_interval_seconds=a.min_request_interval,
                deadline_seconds=a.fetch_deadline_seconds,
            )
        c = w.OpenAssemblyMemberConnector(
            page_index=getattr(a, "page_index", 1),
            page_size=a.page_size,
            name=getattr(a, "name", None),
            party=getattr(a, "party", None),
            district=getattr(a, "district", None),
            **request_kwargs,
        )
        if a.lane == "assembly-page":
            return w.AssemblyRosterStager(c).stage()
        return w.AssemblyRosterEnumerator(c, repository(a)).enumerate(resume=a.resume)
    if a.lane in ("legislative", "legislative-person"):
        w = worker("legislative_activity")
        c = w.OpenAssemblyBillConnector(assembly_age=a.age, page_index=1, page_size=a.page_size)
        if a.lane == "legislative-person":
            candidate = w.IdentityCandidate(
                canonical_name=a.name,
                office="국회의원",
                career_anchors=(f"assembly_member_code:{a.member_code}",),
            )
            return w.LegislativeActivityStager(candidate, c, max_pages=a.max_pages).stage()
        return w.AssemblyBillParticipationEnumerator(
            c, repository(a), max_pages=a.max_pages
        ).enumerate(resume=a.resume)
    if a.lane.startswith("nec-"):
        w = worker("local_elections")
        kwargs = {
            "election_id": a.election_id,
            "election_type": a.type,
            "page_no": a.page_no,
            "page_size": a.page_size,
        }
        if a.lane == "nec-page":
            c = w.NecCandidateConnector(
                **kwargs, district_name=a.district, province_name=a.province, party=a.party
            )
            winner = w.NecWinnerConnector(
                **kwargs, district_name=a.district, province_name=a.province
            )
            return w.LocalElectionStager(c, winner).stage()
        if a.lane == "nec-candidates":
            return w.LocalElectionCandidateEnumerator(
                w.NecCandidateConnector(**kwargs), repository(a)
            ).enumerate(resume=a.resume)
        return w.LocalElectionWinnerEnumerator(
            w.NecWinnerConnector(**kwargs), repository(a)
        ).enumerate(resume=a.resume)
    if a.lane == "gwanbo":
        w = worker("gwanbo_personnel")
        c = w.GwanboPersonnelConnector(
            date_from=a.from_date, date_to=a.to_date, page_size=a.page_size
        )
        return w.GwanboPersonnelEnumerator(c, repository(a)).enumerate(resume=a.resume)
    if a.lane == "policy-research":
        w = worker("policy_research")
        c = w.NkisResearchReportConnector(
            page_no=a.page_no,
            row_count=a.row_count,
            title=a.title,
            publisher=a.publisher,
            publisher_code=a.publisher_code,
            year_begin=a.year_begin,
            year_end=a.year_end,
        )
        return w.PolicyResearchStager(c).stage()
    if a.lane.startswith("dart"):
        w = worker("corporate_talent")
        if a.lane == "dart-executives":
            return w.OpenDartExecutiveEnumerator(
                w.OpenDartCorpCodeConnector(),
                repository(a),
                business_year=a.business_year,
                report_code=a.report_code,
                listed_only=a.listed_only,
            ).enumerate(resume=a.resume)
        c = w.OpenDartCorporateConnector(
            dataset=w.DartCorporateDataset(a.dataset),
            corp_code=a.corp_code,
            business_year=a.business_year,
            report_code=a.report_code,
        )
        return w.OpenDartCorporateStager(c).stage()
    if a.lane == "mois-organization-lookup":
        w = worker("mois_organization_codes")
        c = w.MoisOrganizationCodeConnector(
            page_no=1, page_size=a.page_size, full_name=a.full_name, org_code=a.org_code
        )
        return w.MoisOrganizationLookup(
            c, repository(a), expected_full_name=a.expected_full_name
        ).capture()
    if a.lane == "mois-organizations":
        w = worker("mois_organization_codes")
        c = w.MoisOrganizationCodeConnector(page_no=1, page_size=a.page_size)
        return w.MoisOrganizationEnumerator(c, repository(a), max_pages=a.max_pages).enumerate(
            resume=a.resume
        )
    if a.lane == "alio-item4":
        w = worker("public_institutions")
        return w.AlioExecutiveEnumerator(
            w.AlioExecutiveDisclosureConnector(), repository(a)
        ).enumerate(resume=a.resume)
    if a.lane == "alio-item12":
        w = worker("alio_business_expense")
        return w.AlioBusinessExpenseEnumerator(
            w.AlioInstitutionHeadBusinessExpenseConnector(),
            repository(a),
            institution_codes=tuple(a.institution_codes or w.KNOWN_POSITIVE_INSTITUTION_CODES),
        ).enumerate(resume=a.resume)
    raise ValueError("unsupported source lane")


def dispatch(a: argparse.Namespace) -> Any:
    if a.lane == "gukgam-witness-claim":
        r = repository(argparse.Namespace(database_url=_read_only_monitor_url(a.database_url)))
        if a.claim_id is not None:
            return r.administration.inspect_gukgam_witness_release(a.claim_id)
        return r.onboarding.prepare_gukgam_witness_claim(
            person_id=a.person_id, observation_id=a.observation_id,
            expected_observation_hash=a.expected_observation_hash,
            expected_packet_hash=a.expected_packet_hash,
        ).to_dict()
    if a.lane == "collection-status":
        from packages.rendering.collection_status import build_collection_status

        r = repository(argparse.Namespace(database_url=_read_only_monitor_url(a.database_url)))
        r.uows.assert_ready()
        revision = r.uows.schema_revision()
        report = build_collection_status(
            r.administration.operator_summary(monitoring=True),
            running_age_minutes=a.running_age_minutes,
        )
        return {"schema_revision": revision, "schema_check_scope": "BEFORE_READ_SNAPSHOT"} | report
    if a.lane == "gukgam-witness":
        w = worker("gukgam_witness_import")
        if a.verb == "inspect":
            return w.inspect_inputs(a)
        capture = w.load_capture(a)
        return w.persist_capture(repository(a), capture)
    if a.lane == "gukgam-plan":
        w = worker("gukgam_reviewed_plan_import")
        capture = w._load_capture(a)
        if a.verb == "inspect":
            return {"status": "DRY_RUN"} | w._safe_report(capture)
        return w.persist_capture(repository(a), capture)
    if a.verb == "observe":
        return observe(a)
    if a.lane == "commands":
        return [
            {"command": f"civic {verb} {lane}", "effect": effect.value}
            for verb, (effect, lanes) in ROUTES.items()
            for lane in lanes
        ]
    r = repository(a)
    write = a.verb != "inspect"
    if a.lane == "claim":
        from packages.application.publication import publish_claim

        return publish_claim(r.uows, a.claim_id)
    if a.lane == "alio-item4":
        w = worker("alio_current_executive_claim_import")
        prepared = w.prepare_import(r)
        result = None
        if write:
            organizations = [item.organization for item in prepared.items]
            claim_items = [
                (item.organization, claim, [evidence])
                for item in prepared.items
                for claim, evidence in item.claims
            ]
            result = r.organizations.import_organization_claim_batch(organizations, claim_items)
        return w._receipt(prepared, status="COMMITTED" if write else "DRY_RUN", result=result)
    if a.lane == "assembly":
        return materialize_assembly(r)
    if a.lane == "assembly-distinct-person":
        result = r.review.resolve_assembly_distinct_person_review(
            a.review_item_id, resolution_note=a.resolution_note
        )
        return {
            "status": "SUCCESS",
            "action": result.decision.action.value,
            "decision_class": result.decision.decision_class.value,
            "person_id": str(result.person_id) if result.person_id else None,
            "claim_id": str(result.claim_id) if result.claim_id else None,
            "review_item_id": str(result.review_item_id) if result.review_item_id else None,
            "created": result.created,
        }
    if a.lane == "assembly-profile":
        from packages.application.assembly_base_profile import AssemblyBaseProfilePublisher

        return AssemblyBaseProfilePublisher(r.uows).publish_latest_successful()
    if a.lane == "legislative":
        from packages.application.assembly_legislative_activity import (
            AssemblyLegislativeActivityPublisher,
        )

        return AssemblyLegislativeActivityPublisher(r.uows).publish_latest_successful()
    if a.lane == "alio-safe-people":
        if write:
            return r.administration.commit_alio_person_materialization(
                expected_receipt_sha256=a.expected_receipt_sha256
            )
        return r.administration.prepare_alio_person_materialization().to_dict()
    if a.lane == "nec-safe-people":
        kwargs = {"election_id": a.election_id, "election_types": a.types}
        if write:
            return r.administration.commit_nec_person_materialization(
                expected_receipt_sha256=a.expected_receipt_sha256, **kwargs
            )
        return r.administration.prepare_nec_person_materialization(**kwargs).to_dict()
    if a.lane == "orggo-organizations":
        w = worker("orggo_reviewed_organization_manifest")
        manifest = w.parse_reviewed_orggo_organization_manifest(_read(a.manifest))
        proposal = _read(a.proposal)
        if not write:
            return w.prepare_reviewed_orggo_organization_manifest(r, manifest, proposal).to_dict()
        commit = worker("orggo_reviewed_organization_commit")
        prepared = commit.prepare_reviewed_orggo_organization_commit(
            r, manifest, proposal, expected_manifest_sha256=a.expected_manifest_sha256
        )
        return commit.commit_reviewed_orggo_organizations(r, prepared)
    if a.lane == "gukgam-batch":
        w = worker("gukgam_reviewed_claim_batch_manifest")
        manifest = w.parse_reviewed_gukgam_claim_batch_manifest(_read(a.manifest))
        if not write:
            return w.prepare_reviewed_gukgam_claim_batch_manifest(r, manifest).to_dict()
        commit = worker("gukgam_reviewed_claim_batch_commit")
        prepared = commit.prepare_reviewed_gukgam_claim_batch_commit(
            r, manifest, expected_manifest_sha256=a.expected_manifest_sha256
        )
        return commit.commit_reviewed_gukgam_claim_batch(r, prepared)
    if a.lane == "alio-item12":
        w = worker("alio_reviewed_claim_import")
        prepared = w.prepare_reviewed_import(
            r,
            organization_id=a.organization_id,
            institution_code=a.institution_code,
            earlier_fiscal_year=a.earlier_fiscal_year,
            later_fiscal_year=a.later_fiscal_year,
        )
        claims = (
            r.organizations.import_organization_claim_pair(
                prepared.organization, [(claim, [evidence]) for claim, evidence in prepared.claims]
            )
            if write
            else tuple((claim for claim, _ in prepared.claims))
        )
        return {
            "status": "COMMITTED" if write else "DRY_RUN",
            "claim_ids": [str(c.id) for c in claims],
            "organization_id": str(prepared.organization.id),
            "network_fetch": False,
        }
    if a.lane == "gukgam-claim":
        w = worker("gukgam_reviewed_claim_import")
        prepared = w.prepare_reviewed_gukgam_claim_import(
            r, organization_id=a.organization_id, review_key=a.review_key
        )
        claim = prepared.existing_claim or prepared.claim
        status = "DRY_RUN"
        if write:
            if prepared.existing_claim is not None:
                status = "REUSED"
            else:
                try:
                    claim = r.organizations.import_organization_claim(
                        prepared.organization, prepared.claim, [prepared.evidence]
                    )
                    status = "COMMITTED"
                except w.OrganizationClaimImportError:
                    stored = w._existing_exact_claim(r, prepared.claim, prepared.evidence)
                    if stored is None:
                        raise
                    claim, status = stored, "REUSED"
        return w._receipt(prepared, status=status, stored_claim=claim)
    raise ValueError("unsupported effect-specific command")
