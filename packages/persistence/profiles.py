from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from packages.domain.contracts import (
    Claim,
    ClaimEvidence,
    FeederObservation,
    Person,
    Source,
    SourcePolicy,
)
from packages.domain.enums import EpistemicStatus, EvidenceStance, IdentityStatus, PublicationStatus
from packages.persistence.mapping import (
    _claim,
    _evidence,
    _observation,
    _person,
    _policy,
    _source,
    _temporal,
)
from packages.persistence.models import (
    ClaimEvidenceRow,
    ClaimRow,
    FeederObservationRow,
    PersonObservationLinkRow,
    PersonRow,
    SourcePolicyRow,
    SourceRow,
    SourceSnapshotRow,
)
from packages.verification.assembly_base_profile import (
    ASSEMBLY_BASE_PROFILE_FEEDER,
    ASSEMBLY_BASE_PROFILE_SCOPE,
    ASSEMBLY_BASE_PROFILE_SOURCE_CONTRACT,
    AssemblyBaseProfileError,
    is_assembly_base_profile_field,
)
from packages.verification.assembly_legislative_activity import (
    ASSEMBLY_LEGISLATIVE_FEEDER,
    ASSEMBLY_LEGISLATIVE_PARTICIPATION_PREDICATE,
    ASSEMBLY_LEGISLATIVE_SEMANTIC_SCOPE,
    ASSEMBLY_LEGISLATIVE_SOURCE_CONTRACT,
    AssemblyLegislativeActivityError,
)
from packages.verification.claims import validate_claim_publication
from packages.verification.policy import PolicyAction, PolicyDenied, require_policy


class ProfilesRepository:
    def __init__(self, session: Session):
        self._session = session

    def assembly_base_profile_contexts(
        self, observation_ids: Sequence[UUID]
    ) -> dict[UUID, tuple[Person, Source, SourcePolicy]]:
        """Load resolved Assembly profile targets and provenance in one read session."""
        if not observation_ids:
            return {}
        statement = (
            select(
                PersonObservationLinkRow,
                PersonRow,
                FeederObservationRow,
                SourceSnapshotRow,
                SourceRow,
                SourcePolicyRow,
            )
            .join(PersonRow, PersonRow.id == PersonObservationLinkRow.person_id)
            .join(
                FeederObservationRow,
                FeederObservationRow.id == PersonObservationLinkRow.observation_id,
            )
            .join(SourceSnapshotRow, SourceSnapshotRow.id == FeederObservationRow.snapshot_id)
            .join(SourceRow, SourceRow.id == SourceSnapshotRow.source_id)
            .join(SourcePolicyRow, SourcePolicyRow.id == SourceRow.policy_id)
            .where(
                PersonObservationLinkRow.observation_id.in_(
                    [str(item) for item in observation_ids]
                ),
                PersonObservationLinkRow.superseded_at.is_(None),
            )
        )
        contexts: dict[UUID, tuple[Person, Source, SourcePolicy]] = {}
        session = self._session
        for (
            link,
            person_row,
            observation_row,
            snapshot_row,
            source_row,
            policy_row,
        ) in session.execute(statement):
            observation_id = UUID(observation_row.id)
            if observation_id in contexts:
                raise AssemblyBaseProfileError(
                    "Assembly observation has multiple active Person links"
                )
            if snapshot_row.source_id != source_row.id:
                raise AssemblyBaseProfileError(
                    "Assembly observation snapshot does not match Source"
                )
            if source_row.policy_id != policy_row.id:
                raise AssemblyBaseProfileError("Assembly Source does not match SourcePolicy")
            contexts[observation_id] = (
                _person(person_row),
                _source(source_row),
                _policy(policy_row),
            )
        return contexts

    def assembly_legislative_source_contexts(
        self, observation_ids: Sequence[UUID]
    ) -> dict[UUID, tuple[Source, SourcePolicy]]:
        """Load exact bill-observation Source and SourcePolicy provenance."""
        if not observation_ids:
            return {}
        statement = (
            select(FeederObservationRow, SourceSnapshotRow, SourceRow, SourcePolicyRow)
            .join(SourceSnapshotRow, SourceSnapshotRow.id == FeederObservationRow.snapshot_id)
            .join(SourceRow, SourceRow.id == SourceSnapshotRow.source_id)
            .join(SourcePolicyRow, SourcePolicyRow.id == SourceRow.policy_id)
            .where(FeederObservationRow.id.in_([str(item) for item in observation_ids]))
        )
        contexts: dict[UUID, tuple[Source, SourcePolicy]] = {}
        session = self._session
        for observation_row, snapshot_row, source_row, policy_row in session.execute(statement):
            observation_id = UUID(observation_row.id)
            if observation_id in contexts:
                raise AssemblyLegislativeActivityError(
                    "Assembly bill observation has multiple provenance contexts"
                )
            if snapshot_row.source_id != source_row.id:
                raise AssemblyLegislativeActivityError(
                    "Assembly bill observation snapshot does not match Source"
                )
            if source_row.policy_id != policy_row.id:
                raise AssemblyLegislativeActivityError(
                    "Assembly bill Source does not match SourcePolicy"
                )
            contexts[observation_id] = (_source(source_row), _policy(policy_row))
        return contexts

    def assembly_current_person_contexts(self, member_codes: Sequence[str]) -> dict[str, Person]:
        """Resolve exact current-roster MONA_CD links without a name fallback."""
        if not member_codes:
            return {}
        statement = (
            select(FeederObservationRow, PersonObservationLinkRow, PersonRow)
            .join(
                PersonObservationLinkRow,
                PersonObservationLinkRow.observation_id == FeederObservationRow.id,
            )
            .join(PersonRow, PersonRow.id == PersonObservationLinkRow.person_id)
            .where(
                FeederObservationRow.feeder == ASSEMBLY_BASE_PROFILE_FEEDER,
                FeederObservationRow.scope_key == ASSEMBLY_BASE_PROFILE_SCOPE,
                FeederObservationRow.provider_record_key.in_(list(member_codes)),
                PersonObservationLinkRow.superseded_at.is_(None),
                PersonRow.identity_status == IdentityStatus.RESOLVED.value,
                PersonRow.superseded_at.is_(None),
            )
        )
        contexts: dict[str, Person] = {}
        session = self._session
        for observation_row, _link_row, person_row in session.execute(statement):
            normalized = observation_row.normalized_json
            if (
                not isinstance(normalized, dict)
                or normalized.get("member_code") != observation_row.provider_record_key
            ):
                raise AssemblyLegislativeActivityError(
                    "Assembly current-roster identity contract is invalid"
                )
            member_code = observation_row.provider_record_key
            if member_code in contexts:
                existing = contexts[member_code]
                if existing.id != UUID(person_row.id):
                    raise AssemblyLegislativeActivityError(
                        "Assembly MONA_CD resolves to multiple active canonical People"
                    )
                continue
            contexts[member_code] = _person(person_row)
        return contexts

    def _import_assembly_base_profile_claims_in_session(
        self,
        session: Session,
        person: Person,
        observation: FeederObservation,
        claims: Sequence[Claim],
        evidence: Sequence[ClaimEvidence],
    ) -> tuple[Claim, ...]:
        observation_row = session.get(FeederObservationRow, str(observation.id))
        if observation_row is None:
            raise AssemblyBaseProfileError("Assembly observation does not exist")
        stored_observation = _observation(observation_row)
        if stored_observation != observation:
            raise AssemblyBaseProfileError("Assembly observation has changed since claim build")
        if (
            stored_observation.feeder != ASSEMBLY_BASE_PROFILE_FEEDER
            or stored_observation.scope_key != ASSEMBLY_BASE_PROFILE_SCOPE
        ):
            raise AssemblyBaseProfileError("observation is outside the Assembly base-profile scope")
        person_row = session.get(PersonRow, str(person.id))
        if person_row is None:
            raise AssemblyBaseProfileError("Assembly base profile Person does not exist")
        stored_person = _person(person_row)
        if stored_person != person or stored_person.identity_status != IdentityStatus.RESOLVED:
            raise AssemblyBaseProfileError(
                "Assembly base profile Person is not the current resolved row"
            )
        links = list(
            session.scalars(
                select(PersonObservationLinkRow).where(
                    PersonObservationLinkRow.observation_id == str(observation.id),
                    PersonObservationLinkRow.superseded_at.is_(None),
                )
            )
        )
        if len(links) != 1 or links[0].person_id != str(person.id):
            raise AssemblyBaseProfileError(
                "Assembly base profile requires exactly one active Person observation link"
            )
        snapshot_row = session.get(SourceSnapshotRow, str(observation.snapshot_id))
        if snapshot_row is None:
            raise AssemblyBaseProfileError("Assembly observation snapshot does not exist")
        source_row = session.get(SourceRow, snapshot_row.source_id)
        if source_row is None:
            raise AssemblyBaseProfileError("Assembly observation Source does not exist")
        policy_row = session.get(SourcePolicyRow, source_row.policy_id)
        if policy_row is None:
            raise AssemblyBaseProfileError("Assembly observation SourcePolicy does not exist")
        source = _source(source_row)
        policy = _policy(policy_row)
        if not claims:
            raise AssemblyBaseProfileError(
                "Assembly base profile requires at least one present field"
            )
        if len({claim.id for claim in claims}) != len(claims):
            raise AssemblyBaseProfileError("Assembly base profile contains duplicate Claim IDs")
        if len({item.id for item in evidence}) != len(evidence):
            raise AssemblyBaseProfileError("Assembly base profile contains duplicate Evidence IDs")
        evidence_by_claim: dict[UUID, list[ClaimEvidence]] = {}
        for item in evidence:
            evidence_by_claim.setdefault(item.claim_id, []).append(item)
        requested_fields: set[str] = set()
        for claim in claims:
            field_name = claim.qualifiers.get("field_name")
            if field_name is None or not is_assembly_base_profile_field(field_name):
                raise AssemblyBaseProfileError(
                    "Assembly base profile Claim has an unsupported field"
                )
            if field_name in requested_fields:
                raise AssemblyBaseProfileError("Assembly base profile contains duplicate fields")
            requested_fields.add(field_name)
            if (
                claim.person_id != person.id
                or claim.organization_id is not None
                or claim.publication_status != PublicationStatus.PUBLISHED
                or (
                    claim.qualifiers.get("source_contract") != ASSEMBLY_BASE_PROFILE_SOURCE_CONTRACT
                )
                or (claim.qualifiers.get("source_scope") != observation.scope_key)
                or (claim.qualifiers.get("semantic_scope") != observation.semantic_scope)
                or (claim.qualifiers.get("provider_record_key") != observation.provider_record_key)
                or (claim.qualifiers.get("immutable_observation_hash") != observation.content_hash)
            ):
                raise AssemblyBaseProfileError(
                    "Assembly base profile Claim provenance does not match observation"
                )
            claim_evidence = evidence_by_claim.get(claim.id, [])
            if len(claim_evidence) != 1:
                raise AssemblyBaseProfileError(
                    "Assembly base profile Claim requires exactly one Evidence row"
                )
            item = claim_evidence[0]
            if (
                item.source_id != source.id
                or item.snapshot_id != observation.snapshot_id
                or item.feeder_observation_id != observation.id
                or (item.stance != EvidenceStance.SUPPORT)
                or (item.excerpt is not None)
            ):
                raise AssemblyBaseProfileError(
                    "Assembly base profile Evidence provenance does not match observation"
                )
            gate = validate_claim_publication(
                claim, stored_person, claim_evidence, {source.id: source}, {policy.id: policy}
            )
            if not gate.publishable:
                raise AssemblyBaseProfileError(
                    f"Assembly base profile Claim failed publication gate: {gate.failures}"
                )
        current_claim_rows = list(
            session.scalars(
                select(ClaimRow).where(
                    ClaimRow.person_id == str(person.id), ClaimRow.superseded_at.is_(None)
                )
            )
        )
        existing_by_field: dict[str, ClaimRow] = {}
        for row in current_claim_rows:
            field_name = row.qualifiers.get("field_name")
            if row.qualifiers.get(
                "source_contract"
            ) != ASSEMBLY_BASE_PROFILE_SOURCE_CONTRACT or not is_assembly_base_profile_field(
                field_name or ""
            ):
                continue
            assert field_name is not None
            if field_name in existing_by_field:
                raise AssemblyBaseProfileError(
                    "Assembly base profile has duplicate current field Claims"
                )
            existing_by_field[field_name] = row
        results: list[Claim] = []
        for claim in claims:
            field_name = claim.qualifiers["field_name"]
            existing_row = existing_by_field.get(field_name)
            if existing_row is not None and existing_row.id != str(claim.id):
                raise AssemblyBaseProfileError(
                    "Assembly base profile field conflicts with another immutable observation version"
                )
            if existing_row is not None:
                stored_claim = _claim(existing_row)
                stored_evidence = [
                    _evidence(row)
                    for row in session.scalars(
                        select(ClaimEvidenceRow).where(ClaimEvidenceRow.claim_id == existing_row.id)
                    )
                ]
                if _person_claim_import_semantics(stored_claim) != _person_claim_import_semantics(
                    claim
                ) or _evidence_import_semantics(stored_evidence) != _evidence_import_semantics(
                    evidence_by_claim[claim.id]
                ):
                    raise AssemblyBaseProfileError(
                        "Assembly base profile Claim ID has conflicting stored semantics"
                    )
                results.append(stored_claim)
                continue
            if session.get(ClaimRow, str(claim.id)) is not None:
                raise AssemblyBaseProfileError("Assembly base profile Claim ID is already in use")
            session.add(
                ClaimRow(
                    id=str(claim.id),
                    person_id=str(claim.person_id),
                    organization_id=None,
                    proposition=claim.proposition,
                    subject=claim.subject,
                    predicate=claim.predicate,
                    object_text=claim.object_text,
                    qualifiers=claim.qualifiers,
                    epistemic_status=claim.epistemic_status.value,
                    publication_status=claim.publication_status.value,
                    asserted_as_true=claim.asserted_as_true,
                    resolution_note=claim.resolution_note,
                    **_temporal(claim),
                )
            )
            session.flush()
            item = evidence_by_claim[claim.id][0]
            session.add(
                ClaimEvidenceRow(
                    id=str(item.id),
                    claim_id=str(item.claim_id),
                    source_id=str(item.source_id),
                    snapshot_id=str(item.snapshot_id) if item.snapshot_id else None,
                    feeder_observation_id=str(item.feeder_observation_id)
                    if item.feeder_observation_id
                    else None,
                    stance=item.stance.value,
                    excerpt=item.excerpt,
                )
            )
            results.append(claim)
        return tuple(results)

    def import_assembly_base_profile_claims(
        self,
        person: Person,
        observation: FeederObservation,
        claims: Sequence[Claim],
        evidence: Sequence[ClaimEvidence],
    ) -> tuple[Claim, ...]:
        """Atomically import one exact Assembly observation's base-profile Claims.

        An existing field Claim from another immutable observation version is a conflict. The
        importer never supersedes or overwrites it because the provider does not declare a
        correction or replacement contract for current-roster rows.
        """
        session = self._session
        results = self._import_assembly_base_profile_claims_in_session(
            session, person, observation, claims, evidence
        )
        session.flush()
        return tuple(results)

    def import_assembly_base_profile_claims_batch(
        self,
        items: Sequence[tuple[Person, FeederObservation, Sequence[Claim], Sequence[ClaimEvidence]]],
    ) -> tuple[Claim, ...]:
        """Atomically import exact Assembly base-profile bundles in one database session."""
        session = self._session
        results: list[Claim] = []
        for person, observation, claims, evidence in items:
            results.extend(
                self._import_assembly_base_profile_claims_in_session(
                    session, person, observation, claims, evidence
                )
            )
        session.flush()
        return tuple(results)

    def _import_assembly_legislative_claims_in_session(
        self,
        session: Session,
        items: Sequence[tuple[Person, FeederObservation, Sequence[Claim], Sequence[ClaimEvidence]]],
    ) -> tuple[Claim, ...]:
        if not items:
            return ()
        prepared: list[
            tuple[Person, FeederObservation, Claim, ClaimEvidence, Source, SourcePolicy]
        ] = []
        requested_claim_ids: set[UUID] = set()
        requested_evidence_ids: set[UUID] = set()
        requested_keys: set[tuple[str, str, str]] = set()
        for person, observation, claims, evidence in items:
            if len(claims) != 1 or len(evidence) != 1:
                raise AssemblyLegislativeActivityError(
                    "Assembly legislative activity requires one Claim and one Evidence per participant"
                )
            claim = claims[0]
            item = evidence[0]
            if claim.id in requested_claim_ids or item.id in requested_evidence_ids:
                raise AssemblyLegislativeActivityError(
                    "Assembly legislative activity contains duplicate deterministic IDs"
                )
            requested_claim_ids.add(claim.id)
            requested_evidence_ids.add(item.id)
            observation_row = session.get(FeederObservationRow, str(observation.id))
            if observation_row is None or _observation(observation_row) != observation:
                raise AssemblyLegislativeActivityError(
                    "Assembly bill observation changed since Claim build"
                )
            if (
                observation.feeder != ASSEMBLY_LEGISLATIVE_FEEDER
                or observation.semantic_scope != ASSEMBLY_LEGISLATIVE_SEMANTIC_SCOPE
            ):
                raise AssemblyLegislativeActivityError(
                    "observation is outside the Assembly legislative-activity scope"
                )
            person_row = session.get(PersonRow, str(person.id))
            if person_row is None:
                raise AssemblyLegislativeActivityError(
                    "Assembly legislative activity Person does not exist"
                )
            stored_person = _person(person_row)
            if (
                stored_person != person
                or stored_person.identity_status != IdentityStatus.RESOLVED
                or stored_person.superseded_at is not None
            ):
                raise AssemblyLegislativeActivityError(
                    "Assembly legislative activity Person is not the current resolved row"
                )
            snapshot_row = session.get(SourceSnapshotRow, str(observation.snapshot_id))
            if snapshot_row is None:
                raise AssemblyLegislativeActivityError(
                    "Assembly bill observation snapshot does not exist"
                )
            source_row = session.get(SourceRow, snapshot_row.source_id)
            if source_row is None:
                raise AssemblyLegislativeActivityError(
                    "Assembly bill observation Source does not exist"
                )
            policy_row = session.get(SourcePolicyRow, source_row.policy_id)
            if policy_row is None:
                raise AssemblyLegislativeActivityError(
                    "Assembly bill observation SourcePolicy does not exist"
                )
            source = _source(source_row)
            policy = _policy(policy_row)
            if snapshot_row.source_id != source_row.id or source.policy_id != policy.id:
                raise AssemblyLegislativeActivityError(
                    "Assembly bill observation provenance chain is inconsistent"
                )
            try:
                require_policy(policy, PolicyAction.STORE_METADATA)
            except PolicyDenied as exc:
                raise AssemblyLegislativeActivityError(
                    "Assembly bill SourcePolicy forbids metadata publication"
                ) from exc
            if (
                claim.person_id != person.id
                or claim.organization_id is not None
                or claim.predicate != ASSEMBLY_LEGISLATIVE_PARTICIPATION_PREDICATE
                or (claim.publication_status != PublicationStatus.PUBLISHED)
                or (claim.epistemic_status != EpistemicStatus.FACT)
                or (not claim.asserted_as_true)
                or (claim.qualifiers.get("source_contract") != ASSEMBLY_LEGISLATIVE_SOURCE_CONTRACT)
                or (claim.qualifiers.get("source_scope") != observation.scope_key)
                or (claim.qualifiers.get("semantic_scope") != observation.semantic_scope)
                or (claim.qualifiers.get("provider_record_key") != observation.provider_record_key)
                or (claim.qualifiers.get("immutable_observation_hash") != observation.content_hash)
                or (claim.qualifiers.get("bill_id") != observation.provider_record_key)
                or (claim.qualifiers.get("provider_identity_namespace") != "assembly_mona_cd")
                or (not claim.qualifiers.get("provider_person_key"))
                or (
                    claim.qualifiers.get("participation_role")
                    not in {"REPRESENTATIVE_PROPOSER", "CO_PROPOSER"}
                )
                or (claim.object_text != observation.normalized.get("bill_name"))
            ):
                raise AssemblyLegislativeActivityError(
                    "Assembly legislative activity Claim provenance is invalid"
                )
            if (
                item.claim_id != claim.id
                or item.source_id != source.id
                or item.snapshot_id != observation.snapshot_id
                or (item.feeder_observation_id != observation.id)
                or (item.stance != EvidenceStance.SUPPORT)
                or (item.excerpt is not None)
            ):
                raise AssemblyLegislativeActivityError(
                    "Assembly legislative activity Evidence provenance is invalid"
                )
            provider_person_key = claim.qualifiers["provider_person_key"]
            identity_rows = list(
                session.execute(
                    select(PersonObservationLinkRow, FeederObservationRow, PersonRow)
                    .join(
                        FeederObservationRow,
                        FeederObservationRow.id == PersonObservationLinkRow.observation_id,
                    )
                    .join(PersonRow, PersonRow.id == PersonObservationLinkRow.person_id)
                    .where(
                        FeederObservationRow.feeder == ASSEMBLY_BASE_PROFILE_FEEDER,
                        FeederObservationRow.scope_key == ASSEMBLY_BASE_PROFILE_SCOPE,
                        FeederObservationRow.provider_record_key == provider_person_key,
                        PersonObservationLinkRow.superseded_at.is_(None),
                        PersonRow.identity_status == IdentityStatus.RESOLVED.value,
                        PersonRow.superseded_at.is_(None),
                    )
                )
            )
            identity_person_ids: set[str] = set()
            for _link_row, roster_row, linked_person_row in identity_rows:
                if (
                    not isinstance(roster_row.normalized_json, dict)
                    or roster_row.normalized_json.get("member_code")
                    != roster_row.provider_record_key
                ):
                    raise AssemblyLegislativeActivityError(
                        "Assembly current-roster identity contract is invalid"
                    )
                identity_person_ids.add(linked_person_row.id)
            if identity_person_ids != {str(person.id)}:
                raise AssemblyLegislativeActivityError(
                    "Assembly legislative activity requires an exact current-roster MONA_CD link"
                )
            gate = validate_claim_publication(
                claim, stored_person, [item], {source.id: source}, {policy.id: policy}
            )
            if not gate.publishable:
                raise AssemblyLegislativeActivityError(
                    f"Assembly legislative activity Claim failed publication gate: {gate.failures}"
                )
            logical_key = (
                str(person.id),
                claim.qualifiers["bill_id"],
                claim.qualifiers["participation_role"],
            )
            if logical_key in requested_keys:
                raise AssemblyLegislativeActivityError(
                    "Assembly legislative activity contains duplicate current logical keys"
                )
            requested_keys.add(logical_key)
            prepared.append((person, observation, claim, item, source, policy))
        current_rows = list(
            session.scalars(
                select(ClaimRow).where(
                    ClaimRow.person_id.in_([str(person.id) for person, *_ in prepared]),
                    ClaimRow.superseded_at.is_(None),
                )
            )
        )
        existing_by_key: dict[tuple[str, str, str], list[ClaimRow]] = {}
        for row in current_rows:
            if (
                row.predicate != ASSEMBLY_LEGISLATIVE_PARTICIPATION_PREDICATE
                or row.qualifiers.get("source_contract") != ASSEMBLY_LEGISLATIVE_SOURCE_CONTRACT
            ):
                continue
            bill_id = row.qualifiers.get("bill_id")
            role = row.qualifiers.get("participation_role")
            if not isinstance(bill_id, str) or not isinstance(role, str):
                continue
            existing_by_key.setdefault((str(row.person_id), bill_id, role), []).append(row)
        results: list[Claim] = []
        for person, observation, claim, item, source, policy in prepared:
            key = (
                str(person.id),
                claim.qualifiers["bill_id"],
                claim.qualifiers["participation_role"],
            )
            matching = existing_by_key.get(key, [])
            if len(matching) > 1:
                raise AssemblyLegislativeActivityError(
                    "Assembly legislative activity has duplicate current logical Claims"
                )
            if matching:
                existing_row = matching[0]
                if existing_row.id != str(claim.id):
                    raise AssemblyLegislativeActivityError(
                        "Assembly legislative activity conflicts with another immutable observation version"
                    )
                stored_claim = _claim(existing_row)
                stored_evidence = [
                    _evidence(row)
                    for row in session.scalars(
                        select(ClaimEvidenceRow).where(ClaimEvidenceRow.claim_id == existing_row.id)
                    )
                ]
                if _person_claim_import_semantics(stored_claim) != _person_claim_import_semantics(
                    claim
                ) or _evidence_import_semantics(stored_evidence) != _evidence_import_semantics(
                    [item]
                ):
                    raise AssemblyLegislativeActivityError(
                        "Assembly legislative activity Claim ID has conflicting stored semantics"
                    )
                results.append(stored_claim)
                continue
            if session.get(ClaimRow, str(claim.id)) is not None:
                raise AssemblyLegislativeActivityError(
                    "Assembly legislative activity Claim ID is already in use"
                )
            if session.get(ClaimEvidenceRow, str(item.id)) is not None:
                raise AssemblyLegislativeActivityError(
                    "Assembly legislative activity Evidence ID is already in use"
                )
            session.add(
                ClaimRow(
                    id=str(claim.id),
                    person_id=str(claim.person_id),
                    organization_id=None,
                    proposition=claim.proposition,
                    subject=claim.subject,
                    predicate=claim.predicate,
                    object_text=claim.object_text,
                    qualifiers=claim.qualifiers,
                    epistemic_status=claim.epistemic_status.value,
                    publication_status=claim.publication_status.value,
                    asserted_as_true=claim.asserted_as_true,
                    resolution_note=claim.resolution_note,
                    **_temporal(claim),
                )
            )
            session.flush()
            session.add(
                ClaimEvidenceRow(
                    id=str(item.id),
                    claim_id=str(item.claim_id),
                    source_id=str(item.source_id),
                    snapshot_id=str(item.snapshot_id) if item.snapshot_id else None,
                    feeder_observation_id=str(item.feeder_observation_id)
                    if item.feeder_observation_id
                    else None,
                    stance=item.stance.value,
                    excerpt=item.excerpt,
                )
            )
            results.append(claim)
        return tuple(results)

    def import_assembly_legislative_claims_batch(
        self,
        items: Sequence[tuple[Person, FeederObservation, Sequence[Claim], Sequence[ClaimEvidence]]],
    ) -> tuple[Claim, ...]:
        """Atomically publish exact bill participation Claims or recover an identical import."""
        session = self._session
        results = self._import_assembly_legislative_claims_in_session(session, items)
        session.flush()
        return results


from packages.verification.import_semantics import (
    _evidence_import_semantics,
    _person_claim_import_semantics,
)
