from datetime import UTC, datetime
from uuid import UUID

from packages.domain.contracts import SourcePolicy
from packages.domain.enums import SourceCollectionMode

POLICY_ID = UUID("12000000-0000-0000-0000-000000000001")


def data_go_kr_policy() -> SourcePolicy:
    return SourcePolicy(
        id=POLICY_ID,
        domain="apis.data.go.kr",
        source_class="official_open_api",
        collection_mode=SourceCollectionMode.API,
        can_fetch=True,
        can_store_metadata=True,
        can_store_fulltext=False,
        can_send_to_ai=False,
        can_show_excerpt=False,
        can_commercialize=True,
        terms_checked_at=datetime(2026, 9, 22, tzinfo=UTC),
        license="이용허락범위 제한 없음",
        rate_limit=(
            "Dataset/account-specific public-data-portal quotas apply. The reviewed NEC "
            "development account documents 10,000 requests; MOIS development/operation access "
            "is automatic. Source-specific workers must remain within the approved dataset scope."
        ),
        policy_note=(
            "Host-level policy reviewed for exactly these Civic Intel lanes: NEC candidate "
            "dataset 15000908, NEC winner dataset 15000864, and MOIS Standard Organization "
            "Code dataset 15077870. This shared host policy does not authorize unrelated "
            "apis.data.go.kr endpoints. Source-specific connectors enforce endpoint, field, "
            "pagination and minimization contracts; credentials and raw fulltext are not persisted."
        ),
    )
