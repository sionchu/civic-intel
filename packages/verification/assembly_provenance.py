"""Pure, policy-first validation of stored member-roster identity provenance."""

from packages.domain.contracts import FeederObservation, Source, SourcePolicy, SourceSnapshot
from packages.domain.source_contracts import (
    ASSEMBLY_MEMBER_API_CODE,
    ASSEMBLY_MEMBER_HOST,
    ASSEMBLY_MEMBER_POLICY_ID,
    assembly_member_query,
)
from packages.verification.assembly_base_profile import (
    ASSEMBLY_BASE_PROFILE_FEEDER,
    ASSEMBLY_BASE_PROFILE_SCOPE,
    ASSEMBLY_BASE_PROFILE_SEMANTIC_SCOPE,
)
from packages.verification.materialization import MaterializationError
from packages.verification.policy import PolicyAction, PolicyDenied, require_policy


def validate_assembly_member_provenance(
    observation: FeederObservation, snapshot: SourceSnapshot, source: Source, policy: SourcePolicy
) -> None:
    try:
        require_policy(policy, PolicyAction.STORE_METADATA)
    except PolicyDenied:
        raise MaterializationError(
            "Assembly SourcePolicy does not permit metadata storage"
        ) from None
    if (
        observation.snapshot_id != snapshot.id
        or snapshot.source_id != source.id
        or source.policy_id != policy.id
    ):
        raise MaterializationError("Assembly observation source provenance does not match")
    if (
        policy.id != ASSEMBLY_MEMBER_POLICY_ID
        or policy.domain != ASSEMBLY_MEMBER_HOST
        or policy.source_class != "official_open_api"
        or policy.collection_mode.value != "API"
    ):
        raise MaterializationError(
            "Assembly identity requires the official member API SourcePolicy"
        )
    try:
        query = assembly_member_query(str(source.url))
    except ValueError:
        raise MaterializationError(
            "Assembly Source URL is outside the member API contract"
        ) from None
    if any(key in query for key in ("HG_NM", "POLY_NM", "ORIG_NM")):
        raise MaterializationError("Assembly automatic identity requires an unfiltered roster")
    if (
        snapshot.metadata.get("api_code") != ASSEMBLY_MEMBER_API_CODE
        or snapshot.fulltext is not None
    ):
        raise MaterializationError("Assembly snapshot is outside the member API contract")
    external_ids = observation.identity_hints.get("external_ids")
    if (
        observation.feeder != ASSEMBLY_BASE_PROFILE_FEEDER
        or observation.scope_key != ASSEMBLY_BASE_PROFILE_SCOPE
        or observation.semantic_scope != ASSEMBLY_BASE_PROFILE_SEMANTIC_SCOPE
        or observation.normalized.get("member_code") != observation.provider_record_key
        or not isinstance(external_ids, dict)
        or external_ids.get("assembly_mona_cd") != observation.provider_record_key
    ):
        raise MaterializationError(
            "Assembly observation provider identity is outside the current-roster contract"
        )
