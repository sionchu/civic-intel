from __future__ import annotations

from datetime import date
from uuid import uuid4

from packages.domain.contracts import Person
from packages.domain.enums import IdentityStatus
from packages.verification.opendart_constellation_links import (
    RULE_ALIO,
    RULE_MEMBER,
    KnownPerson,
    classify,
)


def person(name: str = "서갑원") -> Person:
    return Person(id=uuid4(), canonical_name=name, identity_status=IdentityStatus.RESOLVED)


def row(**extra: str) -> dict[str, str]:
    return {"canonical_name": "서갑원", "birth_year_month": "1962년 06월", "corp_name": "미래아이앤지",
            "reported_main_career": "前 제17, 18대 국회의원", **extra}


def test_member_link_needs_name_birth_month_and_stated_assembly_career() -> None:
    former = KnownPerson(person(), date(1962, 6, 24), "FORMER")
    assert classify(row(), [former])[:2] == (RULE_MEMBER, former)
    # Name + birth month only: review queue, not a link.
    rule, known, review = classify(row(reported_main_career="미래아이앤지 상무"), [former])
    assert rule is None and known is former and review
    # Birth month conflict: a different person, never linked or queued.
    assert classify(row(birth_year_month="1970년 01월"), [former]) == (None, None, False)


def test_two_qualifying_people_is_ambiguous() -> None:
    first = KnownPerson(person(), date(1962, 6, 1), "FORMER")
    second = KnownPerson(person(), date(1962, 6, 2), "MEMBER")
    assert classify(row(), [first, second]) == (None, None, False)


def test_public_institution_executive_needs_own_institution() -> None:
    alio = KnownPerson(person("김동철"), None, "ALIO", ("한국전력공사",))
    linked = classify(row(canonical_name="김동철", corp_name="한국전력공사", birth_year_month="1955년 06월",
                          reported_main_career="서울대 법학"), [alio])
    assert linked[:2] == (RULE_ALIO, alio)
    other = classify(row(canonical_name="김동철", corp_name="다른회사", reported_main_career="경력 없음"), [alio])
    assert other == (None, None, False)
