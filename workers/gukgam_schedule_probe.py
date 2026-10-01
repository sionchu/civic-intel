from __future__ import annotations

from packages.connectors.open_assembly_schedule import (
    AssemblyScheduleRecord,
    OpenAssemblyScheduleConnector,
    national_assembly_schedule_policy,
)
from packages.domain.contracts import SourcePolicy
from packages.verification.policy import PolicyAction, require_policy


def _safe_record(record: AssemblyScheduleRecord) -> dict[str, object]:
    return {
        "schedule_date": record.schedule_date.isoformat(),
        "schedule_kind": record.schedule_kind,
        "schedule_time": record.schedule_time,
        "committee_name": record.committee_name,
        "content": record.content,
        "place": record.place,
        "session": record.session,
        "degree": record.degree,
    }


def build_probe_report(
    *, connector: OpenAssemblyScheduleConnector, policy: SourcePolicy | None = None
) -> dict[str, object]:
    selected = policy or national_assembly_schedule_policy()
    require_policy(selected, PolicyAction.FETCH)
    require_policy(selected, PolicyAction.STORE_METADATA)
    if selected.domain != connector.HOST:
        raise ValueError("schedule probe SourcePolicy domain does not match")
    document = connector.fetch(connector.discover()[0])
    records = connector.parse_schedules(document)
    candidates = connector.gukgam_candidates(records)
    return {
        "status": "SOURCE_PROBE",
        "network_fetch": True,
        "persistence_performed": False,
        "api_code": connector.API_CODE,
        "source_contract": document.metadata.get("source_contract"),
        "query": {
            "schedule_date": connector.schedule_date.isoformat()
            if connector.schedule_date is not None
            else None,
            "committee": connector.committee,
            "page_size": connector.page_size,
        },
        "provider": {
            "result_code": document.metadata.get("result_code"),
            "list_total_count": document.metadata.get("list_total_count"),
            "row_count": document.metadata.get("row_count"),
        },
        "gukgam_candidate_count": len(candidates),
        "gukgam_candidates": [_safe_record(record) for record in candidates],
        "semantics": "DISCOVERY_ONLY; schedule candidates do not publish audited organizations, witnesses, reference persons, or identity links",
    }
