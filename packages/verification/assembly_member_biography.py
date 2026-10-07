"""Education and career entries from the Assembly member profile biography (``MEM_TITLE``).

The National Assembly member-information Open API returns each current member's profile
biography as free text maintained for the member's official profile. Lines are kept verbatim
(HTML entities decoded, whitespace trimmed); contact-like lines are dropped before persistence.

Each recognized line becomes one source-attributed ``CLAIM`` (never a verified biography FACT):
"the official member profile biography lists …". Parsing is deterministic and fails closed:

- a period is recorded only when the line itself states it, with its stated precision;
- an education entry needs a school token, and outside an explicit 학력 section also a degree
  word; honorary degrees and teaching/positions at a school are not education;
- school and organization names are copied exactly; ``institution_key`` is a whitespace-free
  comparison key only and never binds a canonical entity. Relations through it stay CANDIDATE.
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass, field
from datetime import date
from typing import TYPE_CHECKING
from uuid import UUID, uuid5

from packages.domain.contracts import (
    Claim,
    ClaimEvidence,
    FeederObservation,
    Person,
    Source,
    SourcePolicy,
)
from packages.domain.enums import (
    EpistemicStatus,
    EvidenceStance,
    IdentityStatus,
    PublicationStatus,
    SourceRunStatus,
)
from packages.verification.assembly_member_claims import AssemblyMemberClaimLane
from packages.verification.claims import validate_claim_publication
from packages.verification.policy import PolicyAction, require_policy

if TYPE_CHECKING:
    from packages.persistence.repository import SqlAlchemyRepository

ASSEMBLY_BIOGRAPHY_FEEDER = "national_assembly_member_biographies"
ASSEMBLY_BIOGRAPHY_SCOPE = "current_member_profile_biography"
ASSEMBLY_BIOGRAPHY_SEMANTIC_SCOPE = "legislative_member_profile_biography"
ASSEMBLY_BIOGRAPHY_SOURCE_CONTRACT = "assembly_member_profile_biography"
ASSEMBLY_BIOGRAPHY_SEMANTICS = "official_member_profile_biography_member_maintained"
ASSEMBLY_BIOGRAPHY_EDUCATION_PREDICATE = "ASSEMBLY_BIOGRAPHY_EDUCATION"
ASSEMBLY_BIOGRAPHY_CAREER_PREDICATE = "ASSEMBLY_BIOGRAPHY_CAREER"
PARSER_VERSION = "assembly_biography_parser_v1"
_BIOGRAPHY_CLAIM_NAMESPACE = UUID("3c7e9a14-2b6d-4e58-8f31-6a0d9c2b7e45")
MAX_LINE_LENGTH = 300


class AssemblyBiographyError(ValueError):
    pass


# --------------------------------------------------------------------------------------------
# Line normalization

_CONTACT = re.compile(
    r"@|https?://|www\.|\b0\d{1,2}[-) ]\d{3,4}-\d{4}\b|전화|팩스|fax|e-?mail|이메일|주소\s*:",
    re.IGNORECASE,
)


def biography_lines(text: str | None) -> tuple[str, ...]:
    """Verbatim non-empty lines; contact/URL lines and over-long lines are dropped."""

    if not text:
        return ()
    lines = []
    for raw in html.unescape(text).replace(" ", " ").splitlines():
        line = re.sub(r"\s+", " ", raw).strip()
        if not line or _CONTACT.search(line) or len(line) > MAX_LINE_LENGTH:
            continue
        lines.append(line)
    return tuple(lines)


_BULLET = re.compile(r"^[\-－·•▶▷▣○●■□◎◇◆◈▲△▼▽*ㆍ※►▸•\s]+")
_MARKER = re.compile(r"^(?:\(?\s*(現|現職|현|현재|前|전|전직)\s*\)|\[\s*(現|현|前|전)\s*\]|(現|前)\s)\s*")
_HEADER = re.compile(r"^[\[<【(]*(?:주요)?(학력|경력|약력|저서|수상|상훈|기타|활동|현직|전직)(?:사항)?[\]>】)]*$")
_TRAILING_MARKER = re.compile(r"\s*[(\[]\s*(現|現職|현|현직|前|전|전직)\s*[)\]]\s*$")
_SKIP_PREFIX = re.compile(r"^(저서|수상|상훈|논문)\s*[/:：]")
_DATE = r"(\d{4})(?:\s*[.\-/년]\s*(\d{1,2}))?(?:\s*[.\-/월]\s*(\d{1,2}))?\s*[.일년]?"


def _strip_bullets(line: str) -> str:
    return _BULLET.sub("", line).strip()


def section_of(line: str) -> str | None:
    match = _HEADER.match(re.sub(r"\s+", "", _strip_bullets(line)))
    if not match:
        return None
    word = match.group(1)
    if word == "학력":
        return "EDUCATION"
    if word in {"경력", "약력", "활동", "현직", "전직"}:
        return "CAREER"
    return "OTHER"


@dataclass(frozen=True)
class StatedDate:
    value: date
    precision: str  # YEAR / MONTH / DAY


def _stated(year: str | None, month: str | None, day: str | None) -> StatedDate | None:
    if not year:
        return None
    y = int(year)
    if not 1930 <= y <= 2035:
        return None
    try:
        if month and day:
            return StatedDate(date(y, int(month), int(day)), "DAY")
        if month:
            return StatedDate(date(y, int(month), 1), "MONTH")
    except ValueError:
        return None
    return StatedDate(date(y, 1, 1), "YEAR")


_DATE_TOKEN = re.compile(rf"^{_DATE}")
_DASH = re.compile(r"^\s*[~～\-–]\s*")
_NOW = re.compile(r"^(현재|現在|\(現\)|現|현)\s*")


@dataclass(frozen=True)
class LinePeriod:
    start: StatedDate | None = None
    end: StatedDate | None = None
    point: StatedDate | None = None  # a single stated date without a range
    ongoing: bool = False


def split_period(text: str) -> tuple[LinePeriod, str]:
    """Parse one leading stated period (``2020.5 ~ 2024.5``, ``2024.5~``, ``~2012.3``, ``1991``)."""

    rest = text.lstrip("'(")
    first = _DATE_TOKEN.match(rest)
    if first is None and not _DASH.match(rest):
        return LinePeriod(), text
    start = None
    if first is not None:
        start = _stated(*first.groups())
        if start is None:
            return LinePeriod(), text
        rest = rest[first.end():]
    dash = _DASH.match(rest)
    if dash is None:
        if start is None:
            return LinePeriod(), text
        return LinePeriod(point=start), rest.lstrip(")' ").strip()
    rest = rest[dash.end():]
    end, ongoing = None, False
    second = _DATE_TOKEN.match(rest)
    if second is not None:
        end = _stated(*second.groups())
        rest = rest[second.end():]
    else:
        now = _NOW.match(rest)
        if now is not None:
            ongoing = True
            rest = rest[now.end():]
        elif start is not None:
            ongoing = True  # "2024.5 ~ 기관명": open-ended as listed
    if start is None and end is None:
        return LinePeriod(), text
    if start and end and end.value < start.value:
        return LinePeriod(), text
    return LinePeriod(start=start, end=end, ongoing=ongoing), rest.lstrip(")' ").strip()


def split_marker(text: str) -> tuple[str, str]:
    match = _MARKER.match(text)
    if not match:
        return "NONE", text
    word = next(group for group in match.groups() if group)
    marker = "CURRENT" if word in {"現", "現職", "현", "현재"} else "FORMER"
    return marker, text[match.end():].strip()


# --------------------------------------------------------------------------------------------
# Education


_DEGREE_WORDS = re.compile(r"졸업|수료|(?<!입)학사|석사|박사|중퇴|재학|학위")
_HONORARY = re.compile(r"명예\s*[가-힣]*\s*(?:박사|학위)")
_TEACHING = re.compile(r"교수|강사|겸임|초빙|총장|학장|처장|실장|사정관|이사장|원장|연구원|연구위원|위원|동문회장|회장|감사|직원")
_SCHOOL_SUFFIX = ("고등학교", "중학교", "초등학교", "국민학교")
_SHORT_SCHOOL = re.compile(r"^([가-힣]{2,8})(여고|고|여중|중|초)$")
_SHORT_SCHOOL_FORMS = {
    "여고": ("HIGH_SCHOOL", "여자고등학교"),
    "고": ("HIGH_SCHOOL", "고등학교"),
    "여중": ("MIDDLE_SCHOOL", "여자중학교"),
    "중": ("MIDDLE_SCHOOL", "중학교"),
    "초": ("ELEMENTARY_SCHOOL", "초등학교"),
}
_SHORT_UNIV = re.compile(r"^([가-힣]{1,8})대$")
_DEPARTMENT = re.compile(r"(학과|학부|전공|대학)$")
_COUNTRY = re.compile(r"^(미국|영국|일본|중국|독일|프랑스|캐나다|호주|러시아|스위스|네덜란드|스웨덴|대만|싱가포르|뉴질랜드)\s+")


@dataclass(frozen=True)
class EducationEntry:
    institution_name: str
    institution_key: str
    institution_level: str  # HIGH_SCHOOL / MIDDLE_SCHOOL / ELEMENTARY_SCHOOL / UNIVERSITY / GRADUATE_SCHOOL
    department_text: str | None
    graduate_unit_text: str | None
    degree_text: str | None
    country_text: str | None


def institution_key(name: str) -> str:
    return re.sub(r"\s+", "", name)


def _degree(text: str) -> str | None:
    for pattern, label in (
        (r"박사\s*과정\s*수료|박사\s*수료", "박사과정 수료"),
        (r"석사\s*과정\s*수료|석사\s*수료", "석사과정 수료"),
        (r"박사", "박사"),
        (r"석사", "석사"),
        (r"(?<!입)학사", "학사"),
        (r"중퇴", "중퇴"),
        (r"수료", "수료"),
        (r"재학", "재학"),
        (r"졸업", "졸업"),
    ):
        if re.search(pattern, text):
            return label
    return None


def _education_part(
    part: str, previous: EducationEntry | None, *, line_has_degree: bool
) -> EducationEntry | None:
    text = part.strip(" ,·")
    country = None
    country_match = _COUNTRY.match(text)
    if country_match:
        country, text = country_match.group(1), text[country_match.end():]
    words = text.split()
    if not words:
        return None
    degree = _degree(text)
    if words[0] == "동" and len(words) > 1 and words[1].startswith("대학원") and previous:
        return EducationEntry(
            previous.institution_name, previous.institution_key, "GRADUATE_SCHOOL",
            None, None, degree, previous.country_text,
        )
    for index, word in enumerate(words):
        for suffix, level in zip(
            _SCHOOL_SUFFIX,
            ("HIGH_SCHOOL", "MIDDLE_SCHOOL", "ELEMENTARY_SCHOOL", "ELEMENTARY_SCHOOL"),
            strict=True,
        ):
            if suffix in word:
                name = " ".join(words[: index + 1])
                name = name[: name.index(suffix) + len(suffix)]
                return EducationEntry(name, institution_key(name), level, None, None, degree, country)
    for index, word in enumerate(words):
        if "대학교" in word:
            name = word[: word.index("대학교") + 3]
            if len(name) <= 5 and index > 0:
                # A generic head ("주립대학교", "국립대학교") belongs to the preceding words.
                name = " ".join([*words[:index], name])
            rest = words[index + 1 :]
            graduate = next((item for item in rest if item.endswith("대학원")), None)
            if word.endswith("대학원") and word != name:
                graduate = word[len(name):] or graduate
            department = next(
                (item for item in rest if _DEPARTMENT.search(item) and not item.endswith("대학원")),
                None,
            )
            level = "GRADUATE_SCHOOL" if graduate or (degree in {"석사", "박사", "석사과정 수료", "박사과정 수료"}) else "UNIVERSITY"
            return EducationEntry(
                name, institution_key(name), level, department,
                graduate if graduate and graduate != "대학원" else None, degree, country,
            )
    for index, word in enumerate(words):
        if word.endswith("대학원") and len(word) > 3:
            return EducationEntry(word, institution_key(word), "GRADUATE_SCHOOL", None, None, degree, country)
        short = _SHORT_UNIV.match(word)
        if short and (index + 1 < len(words) or degree):
            rest = words[index + 1 :]
            department = next((item for item in rest if _DEPARTMENT.search(item)), None)
            if department is None and degree is None:
                continue
            graduate = next((item for item in rest if item.endswith("대학원")), None)
            return EducationEntry(
                word, institution_key(f"{short.group(1)}대학교"),
                "GRADUATE_SCHOOL" if graduate else "UNIVERSITY", department,
                graduate if graduate and graduate != "대학원" else None, degree, country,
            )
        school = _SHORT_SCHOOL.match(word.rstrip(","))
        if school and (degree or line_has_degree):
            level, suffix = _SHORT_SCHOOL_FORMS[school.group(2)]
            full = school.group(1) + suffix
            return EducationEntry(
                word.rstrip(","), institution_key(full), level, None, None, degree, country
            )
    return None


def parse_education(text: str, *, in_education_section: bool) -> tuple[EducationEntry, ...]:
    """Education entries of one line body (period/marker already removed)."""

    if _HONORARY.search(text):
        return ()
    has_degree = bool(_DEGREE_WORDS.search(text))
    if not in_education_section and not has_degree:
        return ()
    if _TEACHING.search(text) and not has_degree:
        return ()
    entries: list[EducationEntry] = []
    previous: EducationEntry | None = None
    for part in re.split(r"\s*[,，]\s*|\s+및\s+", text):
        entry = _education_part(part, previous, line_has_degree=has_degree)
        if entry is None:
            continue
        if entry.degree_text is None:
            # A shared trailing degree word ("춘천고, 서울대 철학과 졸업") applies to each part.
            entry = EducationEntry(**{**entry.__dict__, "degree_text": _degree(text)})
        entries.append(entry)
        previous = entry
    return tuple(dict.fromkeys(entries))


# --------------------------------------------------------------------------------------------
# Career

CAREER_CATEGORIES: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("TRANSITION_COMMITTEE", re.compile(r"인수위원회|인수위")),
    ("CAMPAIGN", re.compile(r"선거대책|선대위|선대본|선거캠프|캠프|경선|선거운동본부|후보\s*(?:비서실|특보|대변인)")),
    ("PRESIDENTIAL_OFFICE", re.compile(r"대통령\s*비서실|대통령실|청와대|국가안보실")),
    ("LEGISLATURE", re.compile(r"국회|입법조사처|의원\s*보좌관|보좌관|비서관")),
    ("GOVERNMENT_COMMITTEE", re.compile(r"(대통령\s*직속|국무총리\s*(?:소속|직속)?)\s*[가-힣·\s]*위원")),
    ("PARTY", re.compile(
        r"국민의힘|더불어민주당|민주당|조국혁신당|개혁신당|진보당|기본소득당|사회민주당|정의당|새누리당|"
        r"한나라당|자유한국당|미래통합당|새정치민주연합|열린우리당|국민의당|바른미래당|바른정당|민주통합당|"
        r"통합진보당|새천년민주당|당\s*대표|최고위원|원내대표|원내부대표|대변인|당원협의회|지역위원장|시당|도당|중앙당"
    )),
    ("LOCAL_GOVERNMENT", re.compile(r"도의회|시의회|구의회|군의회|도지사|시장|구청장|군수|부지사|부시장|교육감")),
    ("PUBLIC_SERVICE", re.compile(r"장관|차관|청장|처장|국장|과장|사무관|서기관|이사관|공무원|외교부|대사|총영사|검사|판사|검찰|법원|경찰|감사원|[가-힣]+부\s")),
    ("MILITARY", re.compile(r"육군|해군|공군|해병|합참|사단|전역|예비역|중장|소장|준장|대령|중령")),
    ("ACADEMIA", re.compile(r"교수|강사|대학교|대학원|학장|총장|연구교수")),
    ("LEGAL_PRACTICE", re.compile(r"변호사|법무법인|로펌")),
    ("CIVIC", re.compile(r"협회|재단|연구원|연구소|포럼|연합회|협의회|노동조합|노조|시민|운동본부|단체|학회")),
    ("BUSINESS", re.compile(r"주식회사|\(주\)|㈜|대표이사|사장|회장|그룹|은행|증권|전자|산업")),
)
_ROLE_SUFFIX = re.compile(
    r"(위원장|부위원장|위원|본부장|부본부장|특보|특별보좌역|고문|대변인|단장|부단장|공동대표|대표|원장|부원장|"
    r"회장|부회장|이사장|이사|감사|사장|부사장|비서관|행정관|수석|장관|차관|청장|국장|교수|의원|부의장|의장|"
    r"간사|소장|총장|팀장|실장|과장|사무총장|최고위원|지사|시장|국회의원|변호사|연구위원|자문위원|상임고문)$"
)


@dataclass(frozen=True)
class CareerEntry:
    category: str
    organization_text: str
    role_text: str | None


def parse_career(text: str) -> CareerEntry | None:
    body = re.sub(r"\s*\([^)]*\)\s*$", "", text).strip()
    if len(body) < 2:
        return None
    category = next((name for name, pattern in CAREER_CATEGORIES if pattern.search(body + " ")), "OTHER")
    words = body.split()
    role = None
    if len(words) > 1 and _ROLE_SUFFIX.search(words[-1]):
        role = words[-1]
        organization = " ".join(words[:-1])
    else:
        organization = body
    return CareerEntry(category, organization, role)


# --------------------------------------------------------------------------------------------
# Entries


@dataclass(frozen=True)
class BiographyEntry:
    line_index: int
    entry_index: int
    section: str | None
    line_text: str
    marker: str
    period: LinePeriod
    education: EducationEntry | None = None
    career: CareerEntry | None = None

    @property
    def entry_key(self) -> str:
        return f"{self.line_index}:{self.entry_index}"


def parse_biography(lines: tuple[str, ...]) -> tuple[BiographyEntry, ...]:
    entries: list[BiographyEntry] = []
    section: str | None = None
    for index, line in enumerate(lines):
        header = section_of(line)
        if header is not None:
            section = header
            continue
        if section == "OTHER":
            continue
        body = _strip_bullets(line)
        if _SKIP_PREFIX.match(body):
            continue
        trailing = _TRAILING_MARKER.search(body)
        marker, body = split_marker(body)
        if trailing and marker == "NONE":
            marker = "CURRENT" if trailing.group(1) in {"現", "現職", "현", "현직"} else "FORMER"
            body = body[: trailing.start()].strip()
        period, body = split_period(body)
        if marker == "NONE":
            marker, body = split_marker(body)
        if period.ongoing and marker == "NONE":
            marker = "CURRENT"
        body = _strip_bullets(body)
        if not body:
            continue
        education = parse_education(body, in_education_section=section == "EDUCATION")
        if education:
            entries.extend(
                BiographyEntry(index, position, section, line, marker, period, education=item)
                for position, item in enumerate(education)
            )
            continue
        if section == "EDUCATION":
            continue
        career = parse_career(body)
        if career is not None:
            entries.append(BiographyEntry(index, 0, section, line, marker, period, career=career))
    return tuple(entries)


# --------------------------------------------------------------------------------------------
# Claims


def _period_qualifiers(period: LinePeriod) -> dict[str, str]:
    values: dict[str, str] = {}
    if period.start:
        values["period_start"] = period.start.value.isoformat()
        values["period_start_precision"] = period.start.precision
    if period.end:
        values["period_end"] = period.end.value.isoformat()
        values["period_end_precision"] = period.end.precision
    if period.point:
        values["period_point"] = period.point.value.isoformat()
        values["period_point_precision"] = period.point.precision
    if period.ongoing:
        values["period_ongoing"] = "true"
    return values


def _biography_claim_matches_observation(claim: Claim, observation: FeederObservation) -> bool:
    lines = observation.normalized.get("biography_lines")
    try:
        index = int(claim.qualifiers.get("line_index", "-1"))
    except ValueError:
        return False
    return (
        isinstance(lines, list)
        and 0 <= index < len(lines)
        and lines[index] == claim.qualifiers.get("line_text")
        and claim.object_text == claim.qualifiers.get("line_text")
        and claim.qualifiers.get("provider_record_key") == observation.provider_record_key
    )


def _lane(predicate: str) -> AssemblyMemberClaimLane:
    return AssemblyMemberClaimLane(
        feeder=ASSEMBLY_BIOGRAPHY_FEEDER,
        semantic_scope=ASSEMBLY_BIOGRAPHY_SEMANTIC_SCOPE,
        predicate=predicate,
        source_contract=ASSEMBLY_BIOGRAPHY_SOURCE_CONTRACT,
        logical_key_qualifiers=("entry_key",),
        claim_matches_observation=_biography_claim_matches_observation,
        error=AssemblyBiographyError,
        label="Assembly member biography",
        epistemic_status=EpistemicStatus.CLAIM,
    )


ASSEMBLY_BIOGRAPHY_EDUCATION_LANE = _lane(ASSEMBLY_BIOGRAPHY_EDUCATION_PREDICATE)
ASSEMBLY_BIOGRAPHY_CAREER_LANE = _lane(ASSEMBLY_BIOGRAPHY_CAREER_PREDICATE)


@dataclass(frozen=True)
class BiographyClaimBundle:
    education: tuple[tuple[Claim, ClaimEvidence], ...] = ()
    career: tuple[tuple[Claim, ClaimEvidence], ...] = ()


def build_biography_claims(
    person: Person,
    observation: FeederObservation,
    *,
    source: Source,
    policy: SourcePolicy,
) -> BiographyClaimBundle:
    if person.identity_status != IdentityStatus.RESOLVED:
        raise AssemblyBiographyError("biography Claims require a resolved Person")
    if (
        observation.feeder != ASSEMBLY_BIOGRAPHY_FEEDER
        or observation.scope_key != ASSEMBLY_BIOGRAPHY_SCOPE
        or observation.semantic_scope != ASSEMBLY_BIOGRAPHY_SEMANTIC_SCOPE
        or observation.normalized.get("biography_semantics") != ASSEMBLY_BIOGRAPHY_SEMANTICS
    ):
        raise AssemblyBiographyError("observation is outside the biography scope")
    if source.policy_id != policy.id:
        raise AssemblyBiographyError("biography SourcePolicy does not match Source")
    require_policy(policy, PolicyAction.STORE_METADATA)
    member_code = observation.normalized.get("member_code")
    lines = observation.normalized.get("biography_lines")
    if member_code != observation.provider_record_key or not isinstance(lines, list):
        raise AssemblyBiographyError("biography observation is malformed")

    education: list[tuple[Claim, ClaimEvidence]] = []
    career: list[tuple[Claim, ClaimEvidence]] = []
    for entry in parse_biography(tuple(lines)):
        qualifiers: dict[str, str] = {
            "source_contract": ASSEMBLY_BIOGRAPHY_SOURCE_CONTRACT,
            "source_scope": observation.scope_key,
            "semantic_scope": observation.semantic_scope,
            "provider_record_key": observation.provider_record_key,
            "immutable_observation_hash": observation.content_hash,
            "provider_identity_namespace": "assembly_mona_cd",
            "provider_person_key": str(member_code),
            "entry_key": entry.entry_key,
            "line_index": str(entry.line_index),
            "line_text": entry.line_text,
            "section": entry.section or "UNSPECIFIED",
            "current_marker": entry.marker,
            "parser_version": PARSER_VERSION,
            "biography_semantics": ASSEMBLY_BIOGRAPHY_SEMANTICS,
            **_period_qualifiers(entry.period),
        }
        if entry.education is not None:
            item = entry.education
            predicate = ASSEMBLY_BIOGRAPHY_EDUCATION_PREDICATE
            qualifiers |= {
                "institution_name": item.institution_name,
                "institution_key": item.institution_key,
                "institution_level": item.institution_level,
                "binding": "SOURCE_TEXT_UNBOUND",
            }
            for key, value in (
                ("department_text", item.department_text),
                ("graduate_unit_text", item.graduate_unit_text),
                ("degree_text", item.degree_text),
                ("country_text", item.country_text),
            ):
                if value:
                    qualifiers[key] = value
            target = education
        else:
            assert entry.career is not None
            predicate = ASSEMBLY_BIOGRAPHY_CAREER_PREDICATE
            qualifiers |= {
                "career_category": entry.career.category,
                "organization_text": entry.career.organization_text,
                "binding": "SOURCE_TEXT_UNBOUND",
            }
            if entry.career.role_text:
                qualifiers["role_text"] = entry.career.role_text
            target = career
        claim = Claim(
            id=uuid5(
                _BIOGRAPHY_CLAIM_NAMESPACE,
                "|".join(
                    (str(person.id), observation.provider_record_key, observation.content_hash,
                     predicate, entry.entry_key)
                ),
            ),
            person_id=person.id,
            proposition=(
                f"국회 의원 인적사항의 {person.canonical_name} 약력에 "
                f"「{entry.line_text}」 항목이 기재되어 있다."
            ),
            subject=person.canonical_name,
            predicate=predicate,
            object_text=entry.line_text,
            qualifiers=qualifiers,
            epistemic_status=EpistemicStatus.CLAIM,
            publication_status=PublicationStatus.PUBLISHED,
            asserted_as_true=False,
            valid_from=observation.recorded_at,
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
            raise AssemblyBiographyError(f"biography Claim failed publication gate: {gate.failures}")
        target.append((claim, evidence))
    return BiographyClaimBundle(tuple(education), tuple(career))


@dataclass(frozen=True)
class AssemblyBiographyPublicationResult:
    run_id: UUID
    observations_considered: int
    members_with_entries: int
    education_claims: int
    career_claims: int
    unchanged_claims: int
    unresolved_member_codes: tuple[str, ...] = ()
    category_counts: dict[str, int] = field(default_factory=dict)


class AssemblyBiographyPublisher:
    """Publish biography Claims only from the latest successful full enumeration."""

    def __init__(self, repository: SqlAlchemyRepository) -> None:
        self.repository = repository

    def _latest_successful_observations(self) -> tuple[UUID, tuple[FeederObservation, ...]]:
        checkpoint = self.repository.source_checkpoint(ASSEMBLY_BIOGRAPHY_FEEDER, ASSEMBLY_BIOGRAPHY_SCOPE)
        if checkpoint is None or checkpoint.last_run_id is None:
            raise AssemblyBiographyError("biography success checkpoint is unavailable")
        run = self.repository.source_run(checkpoint.last_run_id)
        if run is None or run.status != SourceRunStatus.SUCCESS:
            raise AssemblyBiographyError("biography Claims require the latest successful enumeration")
        hashes = checkpoint.metadata.get("seen_provider_hashes")
        try:
            expected_total = int(checkpoint.metadata["list_total_count"])
        except (KeyError, TypeError, ValueError):
            raise AssemblyBiographyError("biography checkpoint coverage metadata is invalid") from None
        if not isinstance(hashes, dict) or len(hashes) != expected_total:
            raise AssemblyBiographyError("biography checkpoint coverage is incomplete")
        by_key: dict[str, FeederObservation] = {}
        for observation in self.repository.feeder_observations(ASSEMBLY_BIOGRAPHY_FEEDER, ASSEMBLY_BIOGRAPHY_SCOPE):
            if hashes.get(observation.provider_record_key) == observation.content_hash:
                by_key[observation.provider_record_key] = observation
        if set(by_key) != set(hashes):
            raise AssemblyBiographyError("biography manifest lacks committed observations")
        return run.id, tuple(by_key[key] for key in sorted(by_key))

    def publish_latest_successful(self, *, dry_run: bool = False) -> AssemblyBiographyPublicationResult:
        run_id, observations = self._latest_successful_observations()
        contexts = self.repository.assembly_legislative_source_contexts([item.id for item in observations])
        people = self.repository.assembly_current_person_contexts([item.provider_record_key for item in observations])
        education_items, career_items = [], []
        members = 0
        categories: dict[str, int] = {}
        for observation in observations:
            person = people.get(observation.provider_record_key)
            context = contexts.get(observation.id)
            if person is None:
                continue
            if context is None:
                raise AssemblyBiographyError("biography observation provenance is incomplete")
            source, policy = context
            bundle = build_biography_claims(person, observation, source=source, policy=policy)
            if bundle.education or bundle.career:
                members += 1
            education_items += [(person, observation, (c,), (e,)) for c, e in bundle.education]
            career_items += [(person, observation, (c,), (e,)) for c, e in bundle.career]
            for claim, _ in bundle.career:
                name = claim.qualifiers["career_category"]
                categories[name] = categories.get(name, 0) + 1
        requested = {claims[0].id for *_, claims, _ in (*education_items, *career_items)}
        existing = {
            claim.id
            for claim in self.repository.claims(published_only=True, current_only=True)
            if claim.predicate in {ASSEMBLY_BIOGRAPHY_EDUCATION_PREDICATE, ASSEMBLY_BIOGRAPHY_CAREER_PREDICATE}
        }
        if not dry_run:
            self.repository.import_assembly_member_claims_batch(education_items, ASSEMBLY_BIOGRAPHY_EDUCATION_LANE)
            self.repository.import_assembly_member_claims_batch(career_items, ASSEMBLY_BIOGRAPHY_CAREER_LANE)
        unchanged = len(existing & requested)
        return AssemblyBiographyPublicationResult(
            run_id=run_id,
            observations_considered=len(observations),
            members_with_entries=members,
            education_claims=len(education_items),
            career_claims=len(career_items),
            unchanged_claims=unchanged,
            unresolved_member_codes=tuple(
                sorted({item.provider_record_key for item in observations} - set(people))
            ),
            category_counts=dict(sorted(categories.items())),
        )
