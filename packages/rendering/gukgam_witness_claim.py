from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from uuid import UUID, uuid5

from packages.connectors.gukgam_witness_packet import (
    ACQUISITION_CHANNELS,
    CHANNEL_OFFICIAL_MINUTES,
    CHANNEL_OWNER_SUPPLIED_COPY,
    OWNER_COPY_LABEL,
    WITNESS_CATEGORIES,
    witness_source_tag,
)
from packages.domain.contracts import (
    Claim,
    ClaimEvidence,
    FeederObservation,
    Organization,
    Source,
    SourcePolicy,
    SourceSnapshot,
)
from packages.domain.enums import EpistemicStatus, EvidenceStance, PublicationStatus
from packages.verification.claims import validate_claim_publication
from packages.verification.gukgam_witness_import import (
    GUKGAM_WITNESS_FEEDER,
    GUKGAM_WITNESS_SEMANTIC_SCOPE,
    GUKGAM_WITNESS_SOURCE_CONTRACT,
    OWNER_COPY_SOURCE_CLASS,
)

OFFICIAL_SOURCE_CLASS = "official_reviewed_committee_attachment"
MINUTES_SOURCE_CLASS = "official_national_assembly_minutes"


def expected_source_class(channel: str) -> str:
    """The only SourcePolicy class each acquisition channel may be backed by."""

    if channel == CHANNEL_OWNER_SUPPLIED_COPY:
        return OWNER_COPY_SOURCE_CLASS
    if channel == CHANNEL_OFFICIAL_MINUTES:
        return MINUTES_SOURCE_CLASS
    return OFFICIAL_SOURCE_CLASS
GUKGAM_WITNESS_PREDICATE = "LISTED_AS_GUKGAM_WITNESS_SOURCE_TEXT"
GUKGAM_WITNESS_CLAIM_NAMESPACE = UUID("3c1f2f55-0b0e-4b7e-9a25-6f4c1d8e7a10")
GUKGAM_WITNESS_EVENT_SEMANTICS = "OFFICIAL_ATTENDANCE_REQUEST_LISTING_NOT_WRONGDOING"
GUKGAM_WITNESS_IDENTITY_SEMANTICS = "SOURCE_LISTED_TEXT_NO_PERSON_LINK"
SUBJECT_SCOPE_COMMITTEE = "COMMITTEE"
SUBJECT_SCOPE_TARGET_INSTITUTION = "TARGET_INSTITUTION"

GUKGAM_PUBLIC_WITNESS_PROJECTION_SEMANTICS = "PUBLIC_CLAIM_BACKED_GUKGAM_WITNESS_LISTS_V1"
GUKGAM_PUBLIC_WITNESS_COVERAGE = "BOUNDED_INCOMPLETE_PUBLISHED_CLAIMS_ONLY"


class GukgamWitnessClaimError(ValueError):
    pass


def _obs_text(observation: FeederObservation, key: str) -> str | None:
    value = observation.normalized.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise GukgamWitnessClaimError(f"witness observation field is invalid: {key}")
    return value.strip()


def _obs_required(observation: FeederObservation, key: str) -> str:
    value = _obs_text(observation, key)
    if value is None:
        raise GukgamWitnessClaimError(f"witness observation lacks {key}")
    return value


def build_gukgam_witness_claim(
    organization: Organization,
    *,
    observation: FeederObservation,
    snapshot: SourceSnapshot,
    source: Source,
    policy: SourcePolicy,
    subject_scope: str,
) -> tuple[Claim, ClaimEvidence]:
    """One reviewed Organization Claim for one exact witness-list row.

    The listed person name stays source-listed text. No Person is created or linked.
    """

    if (
        observation.feeder != GUKGAM_WITNESS_FEEDER
        or observation.semantic_scope != GUKGAM_WITNESS_SEMANTIC_SCOPE
        or observation.identity_hints
        or observation.snapshot_id != snapshot.id
        or snapshot.source_id != source.id
        or source.policy_id != policy.id
    ):
        raise GukgamWitnessClaimError("witness observation provenance is inconsistent")
    if organization.superseded_at is not None:
        raise GukgamWitnessClaimError("witness Claim requires a current Organization")

    committee_name = _obs_required(observation, "committee_name")
    category = _obs_required(observation, "category")
    if category not in WITNESS_CATEGORIES:
        raise GukgamWitnessClaimError("witness observation category is unsupported")
    name = _obs_required(observation, "name")
    target_institution = _obs_text(observation, "target_institution")
    if subject_scope == SUBJECT_SCOPE_COMMITTEE:
        if organization.name not in (committee_name, f"국회 {committee_name}"):
            raise GukgamWitnessClaimError(
                "committee-scope witness Claim requires the exact committee Organization"
            )
    elif subject_scope == SUBJECT_SCOPE_TARGET_INSTITUTION:
        if target_institution is None or target_institution != organization.name:
            raise GukgamWitnessClaimError(
                "target-scope witness Claim requires the list to state the exact institution"
            )
    else:
        raise GukgamWitnessClaimError("witness Claim subject scope is unsupported")

    adoption_date = _obs_text(observation, "adoption_date")
    list_title = _obs_required(observation, "list_title")
    list_version = _obs_required(observation, "list_version")
    list_year = observation.normalized.get("list_year")
    if isinstance(list_year, bool) or not isinstance(list_year, int):
        raise GukgamWitnessClaimError("witness observation list_year is invalid")
    channel = _obs_required(observation, "acquisition_channel")
    if channel not in ACQUISITION_CHANNELS:
        raise GukgamWitnessClaimError("witness observation acquisition channel is invalid")
    if policy.source_class != expected_source_class(channel):
        raise GukgamWitnessClaimError("witness acquisition channel contradicts the source policy")
    locator = observation.normalized.get("locator")
    if (
        not isinstance(locator, Mapping)
        or not isinstance(locator.get("table_index"), int)
        or not isinstance(locator.get("table_row"), int)
        or not (
            locator.get("page_number") is None or isinstance(locator.get("page_number"), int)
        )
    ):
        raise GukgamWitnessClaimError("witness observation locator is invalid")
    row_number = observation.normalized.get("row_number")
    if not isinstance(row_number, int) or row_number < 1:
        raise GukgamWitnessClaimError("witness observation row_number is invalid")

    qualifiers: dict[str, str] = {
        "source_contract": GUKGAM_WITNESS_SOURCE_CONTRACT,
        "source_scope": observation.scope_key,
        "semantic_scope": observation.semantic_scope,
        "provider_record_key": observation.provider_record_key,
        "immutable_observation_hash": observation.content_hash,
        "committee_name": committee_name,
        "list_title": list_title,
        "list_version": list_version,
        "list_year": str(list_year),
        "acquisition_channel": channel,
        "source_tag": witness_source_tag(channel, _obs_text(observation, "artifact_format")),
        "category": category,
        "witness_name": name,
        "row_number": str(row_number),
        "table_index": str(locator["table_index"]),
        "table_row": str(locator["table_row"]),
        "subject_scope": subject_scope,
        "event_semantics": GUKGAM_WITNESS_EVENT_SEMANTICS,
        "identity_semantics": GUKGAM_WITNESS_IDENTITY_SEMANTICS,
    }
    # request_reason_text is deliberately never copied: the policy denies excerpts.
    if locator.get("page_number") is not None:
        qualifiers["page_number"] = str(locator["page_number"])
    for key in (
        "adoption_date",
        "affiliation_title",
        "list_section",
        "attendance_date_text",
        "attendance_date",
        "assumed_year_basis",
    ):
        value = _obs_text(observation, key)
        if value is not None:
            qualifiers[key] = value
    if channel == CHANNEL_OWNER_SUPPLIED_COPY:
        qualifiers["provenance_label"] = OWNER_COPY_LABEL
        received_via = _obs_required(observation, "received_via")
        received_at = _obs_required(observation, "received_at")
        qualifiers["received_via"] = received_via
        qualifiers["received_at"] = received_at
    valid_from_text = adoption_date or _obs_required(observation, "received_at")
    if adoption_date is None:
        qualifiers["valid_from_basis"] = "RECEIVED_AT"

    claim_id = uuid5(
        GUKGAM_WITNESS_CLAIM_NAMESPACE,
        "|".join(
            (
                str(organization.id),
                GUKGAM_WITNESS_PREDICATE,
                observation.provider_record_key,
                observation.content_hash,
            )
        ),
    )
    claim = Claim(
        id=claim_id,
        organization_id=organization.id,
        proposition=(
            f"{committee_name} {list_year}년도 국정감사 {list_title}({list_version})에 "
            f"{name}이(가) {category}으로 기재되어 있다."
        ),
        subject=organization.name,
        predicate=GUKGAM_WITNESS_PREDICATE,
        object_text=f"{category}: {name}",
        qualifiers=qualifiers,
        epistemic_status=EpistemicStatus.FACT,
        publication_status=PublicationStatus.PUBLISHED,
        asserted_as_true=True,
        valid_from=datetime.combine(
            date.fromisoformat(valid_from_text), time.min, tzinfo=UTC
        ),
        recorded_at=observation.recorded_at,
    )
    evidence = ClaimEvidence(
        id=uuid5(
            claim.id,
            "|".join(
                (
                    str(source.id),
                    str(observation.snapshot_id),
                    str(observation.id),
                    EvidenceStance.SUPPORT.value,
                )
            ),
        ),
        claim_id=claim.id,
        source_id=source.id,
        snapshot_id=snapshot.id,
        feeder_observation_id=observation.id,
        stance=EvidenceStance.SUPPORT,
        excerpt=None,
    )
    gate = validate_claim_publication(
        claim, organization, [evidence], {source.id: source}, {policy.id: policy}
    )
    if not gate.publishable:
        raise GukgamWitnessClaimError(f"witness Claim failed publication gate: {gate.failures}")
    return claim, evidence


@dataclass(frozen=True)
class GukgamWitnessProjectionItem:
    committee_name: str
    category: str
    name: str
    affiliation_title: str | None
    list_section: str | None
    attendance_date_text: str | None
    attendance_date: str | None
    attendance_year_basis: str | None
    list_title: str
    list_version: str
    adoption_date: str | None
    row_number: int
    page_number: int | None
    table_index: int
    table_row: int
    subject_scope: str
    organization_id: UUID
    organization_name: str
    acquisition_channel: str
    source_tag: str
    provenance_label: str | None
    source_url: str | None
    claim_id: UUID
    evidence_ids: tuple[UUID, ...]
    source_ids: tuple[UUID, ...]
    snapshot_ids: tuple[UUID, ...]
    observation_ids: tuple[UUID, ...]
    linked_person: tuple[UUID, str] | None = None

    def to_dict(self) -> dict[str, object]:
        linked = (
            {}
            if self.linked_person is None
            else {
                "linked_person": {
                    "id": str(self.linked_person[0]),
                    "name": self.linked_person[1],
                }
            }
        )
        return {
            "committee_name": self.committee_name,
            "category": self.category,
            "name": self.name,
            "affiliation_title": self.affiliation_title,
            "list_section": self.list_section,
            "attendance_date_text": self.attendance_date_text,
            "attendance_date": self.attendance_date,
            "attendance_year_basis": self.attendance_year_basis,
            "list_title": self.list_title,
            "list_version": self.list_version,
            "adoption_date": self.adoption_date,
            "row_number": self.row_number,
            "page_number": self.page_number,
            "table_index": self.table_index,
            "table_row": self.table_row,
            "acquisition_channel": self.acquisition_channel,
            "source_tag": self.source_tag,
            "provenance_label": self.provenance_label,
            "subject_scope": self.subject_scope,
            "organization": {"id": str(self.organization_id), "name": self.organization_name},
            "source_url": self.source_url,
            "claim_id": str(self.claim_id),
            "evidence_ids": [str(i) for i in self.evidence_ids],
            "source_ids": [str(i) for i in self.source_ids],
            "snapshot_ids": [str(i) for i in self.snapshot_ids],
            "observation_ids": [str(i) for i in self.observation_ids],
            **linked,
        }


@dataclass(frozen=True)
class GukgamWitnessProjection:
    year: int
    items: tuple[GukgamWitnessProjectionItem, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "semantics": GUKGAM_PUBLIC_WITNESS_PROJECTION_SEMANTICS,
            "coverage": GUKGAM_PUBLIC_WITNESS_COVERAGE,
            "identity_semantics": GUKGAM_WITNESS_IDENTITY_SEMANTICS,
            "year": self.year,
            "witness_count": sum(1 for i in self.items if i.category == "증인"),
            "reference_person_count": sum(1 for i in self.items if i.category == "참고인"),
            "committee_count": len({i.committee_name for i in self.items}),
            "items": [i.to_dict() for i in self.items],
            "limitations": [
                "Only current published reviewed witness-list Claims are included.",
                (
                    "Lists are versioned (adoption, additions, 종합감사 changes); a row may be "
                    "superseded by a later list version."
                ),
                (
                    "Coverage is bounded and incomplete; absence is not evidence that a "
                    "person was not requested to appear."
                ),
                (
                    "A listed 증인/참고인 is an attendance request, not a finding of "
                    "wrongdoing and not evidence of attendance or testimony."
                ),
                (
                    "Names are source-listed text. A row links to a canonical Person only after "
                    "a human-reviewed identity link and a separately published Person Claim."
                ),
                "News reports are never used as a source for these rows.",
                (
                    f"'{OWNER_COPY_LABEL}' rows come from a copy supplied to the operator; "
                    "the official posting location has not been confirmed."
                ),
                (
                    "Dates printed without a year are shown as printed; a derived date uses "
                    "the year the reviewed packet declares, with its stated basis."
                ),
            ],
        }


def _qualifier(claim: Claim, key: str) -> str:
    value = claim.qualifiers.get(key)
    if not isinstance(value, str) or not value.strip():
        raise GukgamWitnessClaimError(f"witness projection Claim qualifier is invalid: {key}")
    return value.strip()


def build_gukgam_witness_projection(
    organizations: Sequence[Organization],
    contexts: Mapping[UUID, tuple[Sequence[Claim], Mapping[UUID, Sequence[ClaimEvidence]]]],
    *,
    sources: Mapping[UUID, Source],
    policies: Mapping[UUID, SourcePolicy],
    year: int = 2026,
    person_links: Mapping[UUID, tuple[UUID, str]] | None = None,
) -> GukgamWitnessProjection:
    """Project only publishable reviewed witness-list Organization Claims.

    ``person_links`` maps a witness Claim ID to a public Person whose published, reviewed Person
    Claim restates that exact row. Rows without such a link stay source-listed text.
    """

    organization_by_id = {o.id: o for o in organizations if o.superseded_at is None}
    items: list[GukgamWitnessProjectionItem] = []
    for organization_id, (claims, evidence_by_claim) in contexts.items():
        organization = organization_by_id.get(organization_id)
        if organization is None:
            continue
        for claim in claims:
            if claim.predicate != GUKGAM_WITNESS_PREDICATE:
                continue
            if claim.qualifiers.get("source_contract") != GUKGAM_WITNESS_SOURCE_CONTRACT:
                raise GukgamWitnessClaimError("witness projection source contract is invalid")
            if (
                claim.qualifiers.get("event_semantics") != GUKGAM_WITNESS_EVENT_SEMANTICS
                or claim.qualifiers.get("identity_semantics")
                != GUKGAM_WITNESS_IDENTITY_SEMANTICS
            ):
                raise GukgamWitnessClaimError("witness projection semantics changed")
            evidence = list(evidence_by_claim.get(claim.id, ()))
            gate = validate_claim_publication(
                claim, organization, evidence, dict(sources), dict(policies)
            )
            if not gate.publishable or not evidence:
                raise GukgamWitnessClaimError(
                    f"witness projection Claim failed publication gate: {gate.failures}"
                )
            category = _qualifier(claim, "category")
            adoption_date = claim.qualifiers.get("adoption_date")
            channel = _qualifier(claim, "acquisition_channel")
            if channel not in ACQUISITION_CHANNELS:
                raise GukgamWitnessClaimError("witness projection acquisition channel is invalid")
            if category not in WITNESS_CATEGORIES:
                raise GukgamWitnessClaimError("witness projection category is invalid")
            try:
                list_year = int(_qualifier(claim, "list_year"))
                row_number = int(_qualifier(claim, "row_number"))
                table_index = int(_qualifier(claim, "table_index"))
                table_row = int(_qualifier(claim, "table_row"))
                raw_page = claim.qualifiers.get("page_number")
                page_number = int(raw_page) if raw_page is not None else None
            except ValueError as exc:
                raise GukgamWitnessClaimError("witness projection qualifier is invalid") from exc
            if (
                list_year != year
                or row_number < 1
                or table_index < 1
                or table_row < 1
                or (page_number is not None and page_number < 1)
            ):
                raise GukgamWitnessClaimError("witness projection year/locator is invalid")
            subject_scope = _qualifier(claim, "subject_scope")
            if subject_scope not in (SUBJECT_SCOPE_COMMITTEE, SUBJECT_SCOPE_TARGET_INSTITUTION):
                raise GukgamWitnessClaimError("witness projection subject scope is invalid")

            first_source: Source | None = None
            for item in evidence:
                found = sources.get(item.source_id)
                policy = policies.get(found.policy_id) if found else None
                if (
                    found is None
                    or policy is None
                    or policy.source_class != expected_source_class(channel)
                    or item.snapshot_id is None
                    or item.feeder_observation_id is None
                    or item.excerpt is not None
                ):
                    raise GukgamWitnessClaimError("witness projection Evidence is invalid")
                first_source = first_source or found
            assert first_source is not None
            items.append(
                GukgamWitnessProjectionItem(
                    committee_name=_qualifier(claim, "committee_name"),
                    category=category,
                    name=_qualifier(claim, "witness_name"),
                    affiliation_title=claim.qualifiers.get("affiliation_title"),
                    list_section=claim.qualifiers.get("list_section"),
                    attendance_date_text=claim.qualifiers.get("attendance_date_text"),
                    attendance_date=claim.qualifiers.get("attendance_date"),
                    attendance_year_basis=claim.qualifiers.get("assumed_year_basis"),
                    list_title=_qualifier(claim, "list_title"),
                    list_version=_qualifier(claim, "list_version"),
                    adoption_date=adoption_date if isinstance(adoption_date, str) else None,
                    row_number=row_number,
                    page_number=page_number,
                    table_index=table_index,
                    table_row=table_row,
                    subject_scope=subject_scope,
                    organization_id=organization.id,
                    organization_name=organization.name,
                    acquisition_channel=channel,
                    source_tag=claim.qualifiers.get("source_tag")
                    or witness_source_tag(channel, None),
                    provenance_label=(
                        OWNER_COPY_LABEL if channel == CHANNEL_OWNER_SUPPLIED_COPY else None
                    ),
                    # An owner-supplied copy has no official location: never expose the
                    # placeholder URL.
                    source_url=(
                        None
                        if channel == CHANNEL_OWNER_SUPPLIED_COPY
                        else str(first_source.url)
                    ),
                    claim_id=claim.id,
                    evidence_ids=tuple(sorted({e.id for e in evidence}, key=str)),
                    source_ids=tuple(sorted({e.source_id for e in evidence}, key=str)),
                    snapshot_ids=tuple(
                        sorted({e.snapshot_id for e in evidence if e.snapshot_id}, key=str)
                    ),
                    observation_ids=tuple(
                        sorted(
                            {e.feeder_observation_id for e in evidence if e.feeder_observation_id},
                            key=str,
                        )
                    ),
                    linked_person=(person_links or {}).get(claim.id),
                )
            )
    items.sort(
        key=lambda i: (
            i.committee_name,
            i.list_version,
            WITNESS_CATEGORIES.index(i.category),
            i.row_number,
            str(i.claim_id),
        )
    )
    return GukgamWitnessProjection(year=year, items=tuple(items))
