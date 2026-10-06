from __future__ import annotations

from datetime import date

from packages.verification.assembly_member_biography import (
    biography_lines,
    parse_biography,
    parse_career,
    parse_education,
    split_period,
)


def _education(line: str, *, section: bool = False):
    return parse_education(line, in_education_section=section)


def test_lines_are_verbatim_and_drop_contact_like_lines() -> None:
    text = "[학력]\r\n서울대학교 법과대학 졸업&middot;수료\r\n\r\n연락처 02-788-0000\r\nmember@assembly.go.kr\r\n"
    assert biography_lines(text) == ("[학력]", "서울대학교 법과대학 졸업·수료")


def test_university_department_and_degree_are_copied_exactly() -> None:
    (entry,) = _education("서울대학교 법과대학 졸업")
    assert (entry.institution_name, entry.institution_level, entry.department_text) == (
        "서울대학교", "UNIVERSITY", "법과대학",
    )
    assert entry.degree_text == "졸업"


def test_university_and_graduate_school_are_distinct_levels() -> None:
    (graduate,) = _education("영남대학교 경영대학원 경영학 석사")
    assert graduate.institution_name == "영남대학교"
    assert graduate.institution_level == "GRADUATE_SCHOOL"
    assert graduate.graduate_unit_text == "경영대학원"
    (undergraduate,) = _education("고려대학교 경영학과 학사")
    assert undergraduate.institution_level == "UNIVERSITY"


def test_affiliated_high_school_is_not_its_university() -> None:
    (entry,) = _education("경북대학교 사범대학 부속고등학교", section=True)
    assert entry.institution_level == "HIGH_SCHOOL"
    assert entry.institution_name == "경북대학교 사범대학 부속고등학교"


def test_short_forms_keep_source_text_and_compare_on_expanded_key() -> None:
    high, university = _education("춘천고, 서울대 철학과 졸업")
    assert (high.institution_name, high.institution_key, high.degree_text) == ("춘천고", "춘천고등학교", "졸업")
    assert (university.institution_name, university.institution_key) == ("서울대", "서울대학교")
    assert university.department_text == "철학과"


def test_same_graduate_school_reference_reuses_previous_institution() -> None:
    first, second = _education("서울대학교 법학과 및 동 대학원 졸업(법학석사)")
    assert first.institution_level == "UNIVERSITY"
    assert (second.institution_name, second.institution_level) == ("서울대학교", "GRADUATE_SCHOOL")


def test_teaching_positions_and_honorary_degrees_are_not_education() -> None:
    assert _education("(전) 배재대학교 행정학과 겸임교수") == ()
    assert _education("원광대학교 중등특수교육과 교수") == ()
    assert _education("한국대학교 명예 정치학박사") == ()
    # Outside an explicit education section a school name alone is not an education entry.
    assert _education("송정초등학교") == ()
    assert _education("송정초등학교", section=True)[0].institution_level == "ELEMENTARY_SCHOOL"


def test_periods_record_only_stated_precision() -> None:
    period, rest = split_period("2020.7 ~ 2024.5 국회 교육위원회 위원")
    assert (period.start.value, period.start.precision) == (date(2020, 7, 1), "MONTH")
    assert (period.end.value, period.end.precision) == (date(2024, 5, 1), "MONTH")
    assert rest == "국회 교육위원회 위원"
    ongoing, rest = split_period("2026. 9.  ~ 현재      더불어민주당 민주연구원 원장")
    assert ongoing.ongoing and ongoing.end is None and rest.startswith("더불어민주당")
    point, rest = split_period("1991 서울대 법학과 졸업")
    assert point.point.value == date(1991, 1, 1) and point.point.precision == "YEAR"
    assert point.start is None and point.end is None
    none, rest = split_period("제22대 국회의원")
    assert none.start is None and none.point is None and rest == "제22대 국회의원"


def test_career_categories_are_deterministic_keywords_without_causal_labels() -> None:
    assert parse_career("제8회전국동시지방선거 국민의힘 중앙선대위 조직본부장").category == "CAMPAIGN"
    assert parse_career("제20대 대통령직 인수위원회 자문위원").category == "TRANSITION_COMMITTEE"
    entry = parse_career("대통령직속 국가균형발전위원회 위원")
    assert (entry.category, entry.organization_text, entry.role_text) == (
        "GOVERNMENT_COMMITTEE", "대통령직속 국가균형발전위원회", "위원",
    )
    assert parse_career("경기도의회 의장").category == "LOCAL_GOVERNMENT"


def test_sections_route_lines_and_skip_other_sections() -> None:
    lines = (
        "[학력]",
        "송정초등학교",
        "영남대학교 대학원 경영학 박사",
        "[경력]",
        "현) 제22대 국회 국토교통위원회 위원",
        "전) 국민의힘 최고위원",
        "□ 저서",
        "『어느 책』(2020)",
    )
    entries = parse_biography(lines)
    education = [item for item in entries if item.education]
    career = [item for item in entries if item.career]
    assert [item.education.institution_name for item in education] == ["송정초등학교", "영남대학교"]
    assert [item.marker for item in career] == ["CURRENT", "FORMER"]
    assert all("책" not in item.line_text for item in entries)


def test_generic_university_head_keeps_its_preceding_name_words() -> None:
    (entry,) = _education("버지니아 폴리테크닉 주립대학교(행정학 박사)")
    assert entry.institution_name == "버지니아 폴리테크닉 주립대학교"


def test_admissions_office_or_course_words_are_not_degrees_or_departments() -> None:
    assert _education("원광대학교 입학사정관실장") == ()
    (entry,) = _education("명지대학교 정치학 박사과정 수료")
    assert entry.department_text is None and entry.degree_text == "박사과정 수료"


def test_spaced_headers_trailing_markers_and_party_names() -> None:
    entries = parse_biography((
        "□ 경 력",
        "과학기술정보방송통신위원회 간사(前)",
        "국민의힘 원내부대표",
        "국회 정부 및 공공기관 등의 해외자원개발 진상규명을 위한 국정조사특별위원회 위원",
        "저서/ 섬진강(2005)",
    ))
    assert [(item.marker, item.career.category) for item in entries] == [
        ("FORMER", "OTHER"),
        ("NONE", "PARTY"),
        ("NONE", "LEGISLATURE"),
    ]
