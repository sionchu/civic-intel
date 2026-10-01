from dataclasses import dataclass
from uuid import UUID

from packages.domain.contracts import Claim


@dataclass(frozen=True)
class BatchPageCommitResult:
    snapshot_id: UUID
    observation_ids: tuple[UUID, ...]
    observations_created: int
    observations_unchanged: int


@dataclass(frozen=True)
class OrganizationClaimBatchResult:
    claims: tuple[Claim, ...]
    organizations_created: int
    organizations_reused: int
    claims_created: int
    claims_reused: int


@dataclass(frozen=True)
class OrganizationBatchResult:
    organizations_created: int
    organizations_reused: int
