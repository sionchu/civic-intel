from __future__ import annotations

from uuid import UUID

from packages.connectors.open_assembly_historical import (
    HISTORICAL_REVIEWED_INPUT_SCOPE,
    NORMALIZATION_REVISION,
    SOURCE_RECORD_IDENTITY_UNAVAILABLE,
    AssemblyHistoricalCareerRecord,
)
from packages.domain.contracts import Claim
from packages.domain.enums import EpistemicStatus, PublicationStatus


def build_reviewed_assembly_career_claim(
    record: AssemblyHistoricalCareerRecord,
    *,
    person_id: UUID,
) -> Claim:
    """Build one reviewed Claim from one already parsed, source-specific observation."""

    return Claim(
        person_id=person_id,
        proposition=(
            f"{record.name_ko}는 {record.profile_unit_name} 국회 이력에서 "
            f"{record.profile_sj}(으)로 기록되어 있다."
        ),
        subject=record.name_ko,
        predicate="HELD_ROLE",
        object_text=record.profile_sj,
        qualifiers={
            "date": record.valid_from.isoformat(),
            "source_field": "PROFILE_SJ",
            "source_semantics": "COMPOSITE_DISPLAY_TEXT",
            "mona_cd": record.member_code,
            "profile_unit_cd": record.profile_unit_code,
            "profile_unit_nm": record.profile_unit_name,
            "frto_date": record.frto_date,
            "provider_record_group_key": record.provider_record_key,
            "provider_record_identity": SOURCE_RECORD_IDENTITY_UNAVAILABLE,
            "source_record_fingerprint": record.content_hash,
            "change_input_scope": HISTORICAL_REVIEWED_INPUT_SCOPE,
            "normalization_revision": NORMALIZATION_REVISION,
        },
        epistemic_status=EpistemicStatus.FACT,
        publication_status=PublicationStatus.PUBLISHED,
        asserted_as_true=True,
    )
