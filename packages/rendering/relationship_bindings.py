"""Exact registry bindings for biography text (organizations, universities, campaigns).

Biography lines name organizations in free text. A line becomes a bindable affiliation only when
one span of it equals exactly one entry of an official registry already held by Civic Intel:

- canonical current Organizations (ALIO institutions, Assembly committees, …);
- OpenDART listed-company master names (``corp_code``) from the executive feeder;
- MOIS standard organization codes, representative institutions only (``org_code``).

A name that maps to more than one registry entity is ambiguous and never binds. Universities bind
on an exact full official name (``…대학교``) or a reviewed short-form alias. Campaigns bind on an
official election (reviewed NEC election table) plus an exact party name. Everything else stays
``SOURCE_TEXT_UNBOUND`` (CANDIDATE). Binding identifies the entity named in the text; it never
upgrades the member-maintained text into a verified fact.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date
from uuid import UUID

ORGANIZATION_NAME_SPAN_MAX_WORDS = 4
MIN_REGISTRY_NAME_LENGTH = 3


# Reviewed same-entity names: 청와대 and 대통령실 are names of the 대통령비서실 (MOIS 1015000).
GOVERNMENT_ALIASES = {"청와대": "대통령비서실", "대통령실": "대통령비서실"}
_LEGAL_FORM = re.compile(r"\((?:주|株|사|재)\)|（주）|㈜|주식회사|재단법인|사단법인")
_ROLE_TAIL = re.compile(
    r"(대표이사|부사장|사장|회장|부회장|이사장|이사|감사|원장|부원장|청장|차장|처장|국장|과장|"
    r"장관|차관|위원장|위원|본부장|센터장|실장|팀장|소장|총장|사무총장|고문|비서관|행정관|수석)$"
)


def name_words(text: str) -> list[str]:
    """Words of a biography line for exact span lookup: legal-form markers and brackets split."""

    return [item for item in re.split(r"[\s,/()\[\]·]+", _LEGAL_FORM.sub(" ", text)) if item]


def registry_key(value: str) -> str:
    text = re.sub(r"\((?:주|株)\)|（주）|㈜|주식회사|\(재\)|재단법인|사단법인|\(사\)", "", value)
    return re.sub(r"[\s·・ㆍ]+", "", text)


@dataclass(frozen=True)
class RegistryEntity:
    key: str  # via key, e.g. organization:{uuid}, opendart_corp:{code}, mois_org:{code}
    kind: str  # PUBLIC_INSTITUTION / COMPANY / GOVERNMENT_BODY / PARLIAMENTARY_COMMITTEE
    label: str
    binding: str  # Binding value
    organization_id: UUID | None = None


@dataclass
class OrganizationRegistry:
    """Exact-name lookup with source precedence (lower priority number wins for one name).

    Precedence: canonical Organization (0) > OpenDART corp master (1) > MOIS code registry (2), so a
    public institution that is also a MOIS entry binds to its canonical Organization. Two different
    entities with the same name at the winning precedence are ambiguous and never bind.
    """

    by_name: dict[str, dict[int, set[RegistryEntity]]] = field(default_factory=dict)

    def add(self, name: str, entity: RegistryEntity, priority: int = 0) -> None:
        key = registry_key(name)
        if len(key) >= MIN_REGISTRY_NAME_LENGTH:
            self.by_name.setdefault(key, {}).setdefault(priority, set()).add(entity)

    def _candidates(self, key: str, kinds: frozenset[str] | None) -> set[RegistryEntity]:
        tiers = self.by_name.get(key, {})
        for priority in sorted(tiers):
            matching = [item for item in tiers[priority] if kinds is None or item.kind in kinds]
            if matching:
                # One entity per via key: the same code listed under two name spellings is one.
                return set({item.key: item for item in sorted(matching, key=lambda e: e.label)}.values())
        return set()

    def lookup(self, name: str, kinds: frozenset[str] | None = None) -> RegistryEntity | None:
        found = self._candidates(registry_key(name), kinds)
        return next(iter(found)) if len(found) == 1 else None

    def bind(self, text: str, kinds: frozenset[str] | None = None) -> RegistryEntity | None:
        """Longest word span of ``text`` that names exactly one registry entity."""

        words = name_words(text)
        for length in range(min(ORGANIZATION_NAME_SPAN_MAX_WORDS, len(words)), 0, -1):
            found: set[RegistryEntity] = set()
            for start in range(len(words) - length + 1):
                span = words[start : start + length]
                keys = {registry_key(" ".join(span))}
                if length == 1:
                    keys.add(registry_key(_ROLE_TAIL.sub("", span[0])))
                for key in keys:
                    found |= self._candidates(GOVERNMENT_ALIASES.get(key, key), kinds)
            unique = {item.key: item for item in found}
            if len(unique) == 1:
                return next(iter(unique.values()))
            if len(unique) > 1:
                return None  # two different entities at the same span length: ambiguous
        return None

    def __len__(self) -> int:
        return len(self.by_name)


# Reviewed short forms whose expansion is unambiguous among Korean universities.
UNIVERSITY_SHORT_FORMS: dict[str, str] = {
    "서울대": "서울대학교", "고려대": "고려대학교", "연세대": "연세대학교", "성균관대": "성균관대학교",
    "한양대": "한양대학교", "경희대": "경희대학교", "중앙대": "중앙대학교", "부산대": "부산대학교",
    "경북대": "경북대학교", "전남대": "전남대학교", "전북대": "전북대학교", "충남대": "충남대학교",
    "동국대": "동국대학교", "건국대": "건국대학교", "국민대": "국민대학교", "영남대": "영남대학교",
    "조선대": "조선대학교", "이화여대": "이화여자대학교", "숙명여대": "숙명여자대학교",
    "한국외대": "한국외국어대학교", "서강대": "서강대학교", "단국대": "단국대학교", "인하대": "인하대학교",
    "아주대": "아주대학교", "원광대": "원광대학교", "계명대": "계명대학교", "동아대": "동아대학교",
    "홍익대": "홍익대학교", "광운대": "광운대학교", "명지대": "명지대학교", "숭실대": "숭실대학교",
    "세종대": "세종대학교", "경상대": "경상대학교", "강원대": "강원대학교", "충북대": "충북대학교",
    "제주대": "제주대학교", "경남대": "경남대학교", "울산대": "울산대학교", "한림대": "한림대학교",
    "서울시립대": "서울시립대학교", "카이스트": "한국과학기술원",
}
_FULL_UNIVERSITY = re.compile(r"^[가-힣]{2,}(대학교|과학기술원)$")


def university_key(name: str, level: str | None, country: str | None) -> str | None:
    """Exact domestic university/graduate institution key, else None (stays CANDIDATE)."""

    if country or level not in {"UNIVERSITY", "GRADUATE_SCHOOL"}:
        return None
    text = registry_key(name)
    text = UNIVERSITY_SHORT_FORMS.get(text, text)
    if text.startswith("국립") and len(text) > 5:
        text = text[2:]
    return text if _FULL_UNIVERSITY.match(text) else None


@dataclass(frozen=True)
class Election:
    code: str  # NEC sgId (election day)
    label: str
    day: date


# Reviewed from the NEC election history (선거통계시스템 역대선거). Ordinal → election.
PRESIDENTIAL = {
    15: Election("19971218", "제15대 대통령선거", date(1997, 12, 18)),
    16: Election("20021219", "제16대 대통령선거", date(2002, 12, 19)),
    17: Election("20071219", "제17대 대통령선거", date(2007, 12, 19)),
    18: Election("20121219", "제18대 대통령선거", date(2012, 12, 19)),
    19: Election("20170509", "제19대 대통령선거", date(2017, 5, 9)),
    20: Election("20220309", "제20대 대통령선거", date(2022, 3, 9)),
    21: Election("20250603", "제21대 대통령선거", date(2025, 6, 3)),
}
GENERAL = {
    18: Election("20080409", "제18대 국회의원선거", date(2008, 4, 9)),
    19: Election("20120411", "제19대 국회의원선거", date(2012, 4, 11)),
    20: Election("20160413", "제20대 국회의원선거", date(2016, 4, 13)),
    21: Election("20200415", "제21대 국회의원선거", date(2020, 4, 15)),
    22: Election("20240410", "제22대 국회의원선거", date(2024, 4, 10)),
}
LOCAL = {
    5: Election("20100602", "제5회 전국동시지방선거", date(2010, 6, 2)),
    6: Election("20140604", "제6회 전국동시지방선거", date(2014, 6, 4)),
    7: Election("20180613", "제7회 전국동시지방선거", date(2018, 6, 13)),
    8: Election("20220601", "제8회 전국동시지방선거", date(2022, 6, 1)),
    9: Election("20260603", "제9회 전국동시지방선거", date(2026, 6, 3)),
}
PARTY_NAMES = (
    "더불어민주당", "국민의힘", "조국혁신당", "개혁신당", "진보당", "기본소득당", "사회민주당", "정의당",
    "미래통합당", "자유한국당", "새누리당", "한나라당", "새정치민주연합", "민주통합당", "국민의당",
    "바른미래당", "바른정당", "열린우리당", "새천년민주당", "통합진보당", "민주평화당", "미래한국당",
    "더불어시민당", "국민의미래", "더불어민주연합",
)
_ORDINAL = re.compile(r"제?\s*(\d{1,2})\s*(대|회)")


def election_of(text: str) -> Election | None:
    compact = re.sub(r"\s+", "", text)
    match = _ORDINAL.search(compact)
    if match is None:
        return None
    ordinal, unit = int(match.group(1)), match.group(2)
    if unit == "회" and "지방선거" in compact:
        return LOCAL.get(ordinal)
    if unit == "대" and re.search(r"대선|대통령선거|대통령후보|대통령선거대책", compact):
        return PRESIDENTIAL.get(ordinal)
    if unit == "대" and re.search(r"총선|국회의원선거", compact):
        return GENERAL.get(ordinal)
    return None


def party_of(text: str) -> str | None:
    compact = re.sub(r"\s+", "", text)
    found = {name for name in PARTY_NAMES if name in compact}
    # "더불어민주당" contains no other listed name; drop names contained in a longer match.
    found = {name for name in found if not any(name != other and name in other for other in found)}
    return next(iter(found)) if len(found) == 1 else None


# Reviewed major presidential candidates (NEC 역대선거 후보자) → nominating party.
PRESIDENTIAL_CANDIDATES: dict[str, dict[str, str]] = {
    "20071219": {"이명박": "한나라당", "정동영": "대통합민주신당"},
    "20121219": {"박근혜": "새누리당", "문재인": "민주통합당"},
    "20170509": {"문재인": "더불어민주당", "홍준표": "자유한국당", "안철수": "국민의당",
                 "유승민": "바른정당", "심상정": "정의당"},
    "20220309": {"이재명": "더불어민주당", "윤석열": "국민의힘", "심상정": "정의당"},
    "20250603": {"이재명": "더불어민주당", "김문수": "국민의힘", "이준석": "개혁신당"},
}
# President-elect name → the election whose transition body it was (ordinal may be absent).
TRANSITION_PRESIDENTS = {"김대중": 15, "노무현": 16, "이명박": 17, "박근혜": 18, "윤석열": 20}
_PRESIDENTIAL_ELECTIONS_BY_CODE = {item.code: item for item in PRESIDENTIAL.values()}


def campaign_key(text: str) -> tuple[str, str, Election] | None:
    election, party = election_of(text), party_of(text)
    if election is not None and party is None and election.code in PRESIDENTIAL_CANDIDATES:
        compact = re.sub(r"\s+", "", text)
        named = {
            nominee_party
            for name, nominee_party in PRESIDENTIAL_CANDIDATES[election.code].items()
            if name in compact
        }
        party = next(iter(named)) if len(named) == 1 else None
    if election is None or party is None:
        return None
    return f"campaign:{election.code}:{party}", f"{election.label} {party} 선거대책기구", election


def registry_from_rows(
    rows: Iterable[tuple[str, RegistryEntity, int]],
) -> OrganizationRegistry:
    registry = OrganizationRegistry()
    for name, entity, priority in rows:
        registry.add(name, entity, priority)
    return registry


def transition_key(text: str) -> tuple[str, str] | None:
    """Presidential transition body of a reviewed presidential election.

    Bound from an explicit ordinal (제N대) or the named president-elect; 문재인 2017's
    국정기획자문위원회 and 이재명 2025's 국정기획위원회 were the transition bodies of their elections.
    Regional (도지사·시장) transition committees never bind.
    """

    compact = re.sub(r"\s+", "", text)
    if re.search(r"도지사|시장|군수|구청장|교육감", compact):
        return None
    election: Election | None = None
    if "국정기획자문위원회" in compact:
        election = PRESIDENTIAL[19]
    elif "국정기획위원회" in compact and "이재명" in compact:
        election = PRESIDENTIAL[21]
    elif "인수위" in compact and "대통령" in compact:
        match = _ORDINAL.search(compact)
        if match and match.group(2) == "대":
            election = PRESIDENTIAL.get(int(match.group(1)))
        else:
            named = {TRANSITION_PRESIDENTS[name] for name in TRANSITION_PRESIDENTS if name in compact}
            election = PRESIDENTIAL.get(next(iter(named))) if len(named) == 1 else None
    if election is None:
        return None
    return f"transition:{election.code}", f"{election.label} 당선인 인수 기구"
