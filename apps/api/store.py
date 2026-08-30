from __future__ import annotations

from uuid import UUID

from packages.domain.contracts import Claim, ClaimEvidence, Person, Source, SourcePolicy
from packages.domain.enums import (
    EpistemicStatus,
    EvidenceStance,
    IdentityStatus,
    SourceCollectionMode,
)

PERSON_ID = UUID("00000000-0000-0000-0000-000000000001")
POLICY_ID = UUID("10000000-0000-0000-0000-000000000001")
SOURCE_ID = UUID("20000000-0000-0000-0000-000000000001")
CLAIM_ID = UUID("30000000-0000-0000-0000-000000000001")
EVIDENCE_ID = UUID("40000000-0000-0000-0000-000000000001")

policy = SourcePolicy(
    id=POLICY_ID,
    domain="example.gov",
    source_class="official",
    collection_mode=SourceCollectionMode.API,
    can_fetch=True,
    can_store_metadata=True,
    can_store_fulltext=True,
    can_send_to_ai=False,
    can_show_excerpt=True,
    can_commercialize=True,
    license="Open Government Licence",
)
source = Source(
    id=SOURCE_ID,
    url="https://example.gov/open-data/cabinet/kim-min",
    title="Cabinet appointment notice: Kim Min",
    publisher="Example Government",
    policy_id=POLICY_ID,
)
person = Person(id=PERSON_ID, canonical_name="Kim Min", identity_status=IdentityStatus.RESOLVED)
claim = Claim(
    id=CLAIM_ID,
    person_id=PERSON_ID,
    proposition="Kim Min took office on 2 January 2026.",
    epistemic_status=EpistemicStatus.FACT,
    published=True,
)
evidence = ClaimEvidence(
    id=EVIDENCE_ID,
    claim_id=CLAIM_ID,
    source_id=SOURCE_ID,
    stance=EvidenceStance.SUPPORT,
    excerpt="took office as Minister of Civic Affairs on 2 January 2026",
)

PEOPLE = {person.id: person}
POLICIES = {policy.id: policy}
SOURCES = {source.id: source}
CLAIMS = {claim.id: claim}
EVIDENCE = {evidence.id: evidence}
RELATIONSHIPS: dict[UUID, list] = {PERSON_ID: []}
ASSETS: dict[UUID, list] = {PERSON_ID: []}
