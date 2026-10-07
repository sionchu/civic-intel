"""National Assembly candidate submissions (NEC 후보자 정보) as attributed education/career CLAIMs.

The NEC candidate service publishes, per candidate, the education (``edu``), two careers
(``career1``/``career2``) and occupation (``job``) the candidate submitted to the election
authority, with birth date, party and district. Following the Career Facets provenance rule these
become non-asserted CLAIMs ("후보자가 선관위에 제출한 …"), never verified biography FACTs.

Identity (deterministic, no new Person, no merge):

- current members: candidate in the 22nd general election whose name *and* exact birth date equal
  the current-roster Person (the roster publishes the birth date);
- former members: candidate in the election of a published ``ASSEMBLY_HISTORICAL_TERM`` whose
  name and party equal that term's member name and party.

Exactly one candidate row must match; zero or several matches publish nothing.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, time
from typing import TYPE_CHECKING
from uuid import UUID, uuid5

from packages.domain.contracts import Claim, ClaimEvidence, FeederObservation, Person
from packages.domain.enums import (
    EpistemicStatus,
    EvidenceStance,
    IdentityStatus,
    PublicationStatus,
    SourceRunStatus,
)
from packages.verification.assembly_member_biography import (
    biography_lines,
    parse_career,
    parse_education,
    split_marker,
)
from packages.verification.claims import validate_claim_publication
from packages.verification.policy import PolicyAction, require_policy

if TYPE_CHECKING:
    from packages.persistence.repository import SqlAlchemyRepository

NEC_ASSEMBLY_FEEDER = "nec_national_assembly_candidates"
NEC_ASSEMBLY_SEMANTIC_SCOPE = "national_assembly_candidacy_submission"
NEC_ASSEMBLY_SOURCE_CONTRACT = "nec_assembly_candidate_submission"
NEC_EDUCATION_PREDICATE = "NEC_CANDIDATE_EDUCATION"
NEC_CAREER_PREDICATE = "NEC_CANDIDATE_CAREER"
NEC_SEMANTICS = "candidate_submitted_to_election_authority_not_independently_verified"
CURRENT_TERM_ELECTION = "20240410"
# NEC general-election sgId → Assembly 의원이력 PROFILE_UNIT_CD of the term it elected.
ELECTION_TERMS = {
    "20040415": "100017",
    "20080409": "100018",
    "20120411": "100019",
    "20160413": "100020",
    "20200415": "100021",
    "20240410": "100022",
}
ELECTION_TYPES = (2, 7)
_CLAIM_NAMESPACE = UUID("c3a8e5f1-7b2d-4e96-a4c0-1d9f6b2e8a57")


class NecAssemblyCandidateError(ValueError):
    pass


def scope_key(election_id: str, election_type: int) -> str:
    return f"{election_id}:{election_type}"


def normalized_candidate(record) -> dict[str, object]:
    return {
        "candidate_id": record.candidate_id,
        "election_id": record.election_id,
        "election_type": record.election_type,
        "canonical_name": record.name_ko,
        "hanja_name": record.name_hanja,
        "birth_date": record.birth_date.isoformat() if record.birth_date else None,
        "party": record.party,
        "province": record.province_name,
        "district": record.district_name,
        "education_text": record.submitted_education,
        "careers": [item for item in record.submitted_careers if item and item != "미기재"],
        "job": record.public_job,
        "registration_status": record.registration_status,
        "submission_semantics": NEC_SEMANTICS,
    }


def _entries(observation: FeederObservation) -> list[tuple[str, str, str]]:
    """(kind, line text, entry key) for the education, careers and occupation fields."""

    n = observation.normalized
    entries: list[tuple[str, str, str]] = []
    education = n.get("education_text")
    if isinstance(education, str) and education.strip() and education.strip() != "미기재":
        entries.append(("EDUCATION", education.strip(), "edu"))
    for index, text in enumerate(n.get("careers") or []):
        if isinstance(text, str) and text.strip():
            entries.append(("CAREER", text.strip(), f"career{index + 1}"))
    job = n.get("job")
    if isinstance(job, str) and job.strip() and job.strip() not in {"미기재", "정당인", "국회의원"}:
        entries.append(("CAREER", job.strip(), "job"))
    return entries


def build_candidate_claims(
    person: Person,
    observation: FeederObservation,
    source,
    policy,
    *,
    identity_basis: str,
) -> list[tuple[Claim, ClaimEvidence]]:
    require_policy(policy, PolicyAction.STORE_METADATA)
    if person.identity_status != IdentityStatus.RESOLVED:
        raise NecAssemblyCandidateError("candidate Claims require a resolved Person")
    n = observation.normalized
    election_day = datetime.strptime(str(n["election_id"]), "%Y%m%d").replace(tzinfo=UTC)
    out: list[tuple[Claim, ClaimEvidence]] = []
    for kind, raw_text, field_key in _entries(observation):
        (text,) = biography_lines(raw_text) or ("",)
        if not text:
            continue
        marker, body = split_marker(text)
        base = {
            "source_contract": NEC_ASSEMBLY_SOURCE_CONTRACT,
            "source_scope": observation.scope_key,
            "semantic_scope": observation.semantic_scope,
            "provider_record_key": observation.provider_record_key,
            "immutable_observation_hash": observation.content_hash,
            "provider_identity_namespace": "nec_huboid",
            "candidate_id": str(n["candidate_id"]),
            "election_id": str(n["election_id"]),
            "entry_key": field_key,
            "line_text": text,
            "current_marker": marker,
            "identity_basis": identity_basis,
            "submission_semantics": NEC_SEMANTICS,
            "binding": "SOURCE_TEXT_UNBOUND",
        }
        items: list[tuple[str, dict[str, str]]] = []
        if kind == "EDUCATION":
            for position, entry in enumerate(parse_education(body, in_education_section=True)):
                q = base | {
                    "entry_key": f"edu:{position}",
                    "institution_name": entry.institution_name,
                    "institution_key": entry.institution_key,
                    "institution_level": entry.institution_level,
                }
                for key, value in (
                    ("department_text", entry.department_text),
                    ("graduate_unit_text", entry.graduate_unit_text),
                    ("degree_text", entry.degree_text),
                    ("country_text", entry.country_text),
                ):
                    if value:
                        q[key] = value
                items.append((NEC_EDUCATION_PREDICATE, q))
        else:
            career = parse_career(body)
            if career is None:
                continue
            q = base | {"career_category": career.category, "organization_text": career.organization_text}
            if career.role_text:
                q["role_text"] = career.role_text
            if marker == "CURRENT":
                q["period_ongoing"] = "true"
            items.append((NEC_CAREER_PREDICATE, q))
        for predicate, qualifiers in items:
            claim = Claim(
                id=uuid5(_CLAIM_NAMESPACE, "|".join((
                    str(person.id), observation.provider_record_key, observation.content_hash,
                    predicate, qualifiers["entry_key"],
                ))),
                person_id=person.id,
                proposition=(
                    f"{person.canonical_name}가 중앙선거관리위원회에 제출한 후보자 정보"
                    f"({n['election_id']})에 「{text}」이 기재되어 있다."
                ),
                subject=person.canonical_name,
                predicate=predicate,
                object_text=text,
                qualifiers=qualifiers,
                epistemic_status=EpistemicStatus.CLAIM,
                publication_status=PublicationStatus.PUBLISHED,
                asserted_as_true=False,
                valid_from=datetime.combine(election_day.date(), time(), UTC),
                recorded_at=observation.recorded_at,
            )
            evidence = ClaimEvidence(
                id=uuid5(claim.id, f"{source.id}|{observation.snapshot_id}|{observation.id}|SUPPORT"),
                claim_id=claim.id,
                source_id=source.id,
                snapshot_id=observation.snapshot_id,
                feeder_observation_id=observation.id,
                stance=EvidenceStance.SUPPORT,
            )
            gate = validate_claim_publication(
                claim, person, [evidence], {source.id: source}, {policy.id: policy}
            )
            if not gate.publishable:
                raise NecAssemblyCandidateError(f"candidate Claim failed gate: {gate.failures}")
            out.append((claim, evidence))
    return out


@dataclass(frozen=True)
class NecAssemblyResult:
    candidates: int
    current_matched: int
    former_matched: int
    ambiguous: int
    claims: int


class NecAssemblyCandidatePublisher:
    def __init__(self, repository: SqlAlchemyRepository) -> None:
        self.repository = repository

    def _observations(self) -> list[FeederObservation]:
        found: list[FeederObservation] = []
        for election_id in ELECTION_TERMS:
            for election_type in ELECTION_TYPES:
                scope = scope_key(election_id, election_type)
                checkpoint = self.repository.source_checkpoint(NEC_ASSEMBLY_FEEDER, scope)
                if checkpoint is None or checkpoint.last_run_id is None:
                    continue
                run = self.repository.source_run(checkpoint.last_run_id)
                hashes = checkpoint.metadata.get("seen_provider_hashes")
                if run is None or run.status != SourceRunStatus.SUCCESS or not isinstance(hashes, dict):
                    continue
                for item in self.repository.feeder_observations(NEC_ASSEMBLY_FEEDER, scope):
                    if hashes.get(item.provider_record_key) == item.content_hash:
                        found.append(item)
        return found

    def publish(self, *, dry_run: bool = False) -> NecAssemblyResult:
        observations = self._observations()
        by_election_name: dict[tuple[str, str], list[FeederObservation]] = {}
        for item in observations:
            key = (str(item.normalized["election_id"]), str(item.normalized["canonical_name"]))
            by_election_name.setdefault(key, []).append(item)
        contexts = self.repository.assembly_legislative_source_contexts([item.id for item in observations])
        pending: list[tuple[Claim, ClaimEvidence]] = []
        current = ambiguous = former = 0

        for person in self.repository.current_roster_people():
            rows = [
                item
                for item in by_election_name.get((CURRENT_TERM_ELECTION, person.canonical_name), [])
                if person.birth_date and item.normalized.get("birth_date") == person.birth_date.isoformat()
            ]
            if len(rows) > 1:
                ambiguous += 1
            if len(rows) != 1:
                continue
            current += 1
            pending += build_candidate_claims(
                person, rows[0], *contexts[rows[0].id], identity_basis="EXACT_NAME_AND_BIRTH_DATE_22ND_ELECTION"
            )

        term_to_election = {unit: election for election, unit in ELECTION_TERMS.items()}
        for person, term in self.repository.published_historical_terms():
            election = term_to_election.get(str(term.qualifiers.get("profile_unit_code")))
            party = term.qualifiers.get("party")
            if election is None or not party:
                continue
            rows = [
                item
                for item in by_election_name.get((election, person.canonical_name), [])
                if item.normalized.get("party") == party
            ]
            if len(rows) > 1:
                ambiguous += 1
            if len(rows) != 1:
                continue
            former += 1
            pending += build_candidate_claims(
                person, rows[0], *contexts[rows[0].id], identity_basis="EXACT_NAME_PARTY_AND_ELECTION_OF_TERM"
            )
        if not dry_run:
            self.repository.insert_attributed_person_claims(pending)
        return NecAssemblyResult(
            candidates=len(observations), current_matched=current, former_matched=former,
            ambiguous=ambiguous, claims=len(pending),
        )
