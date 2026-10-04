"""Reviewed list of the 2026 국정감사 standing committees, used for presentation scope only.

Semantics: ``PRESENTATION_SCOPE_COMMITTEE_LIST_NOT_A_CLAIM``. This constant decides which
committee rosters the Gukgam page may show. It is not a Claim, carries no Evidence and is
never published as a fact about any person or institution.

Source: docs/research/gukgam_2026_assembly_comprehensive_schedule_2026-10-01.json (the
``committee_full_name`` of each of its 17 ``committees``), itself a discovery inventory
(``DISCOVERY_SCHEDULE_INVENTORY_NOT_CLAIMS``) extracted from the owner-supplied copy of the
Assembly 의사국 2026 국정감사 종합 일정표 (as of 2026-10-01), source sha256
3bf5274964d7d34ffc7b5fb3ae6632e94b81658cec6bb3dd2073cbfc02dbc730.

Confirmation status: every name below is CONFIRMED against the inventory's
``committee_full_name``. The inventory was not compared with live Assembly roster strings
(the database was offline when this list was written); a name that differs from the roster
string simply lists no members, and former names (for example 기획재정위원회) are never merged.
"""

from __future__ import annotations

GUKGAM_2026_COMMITTEES_SEMANTICS = "PRESENTATION_SCOPE_COMMITTEE_LIST_NOT_A_CLAIM"
GUKGAM_2026_COMMITTEES_SOURCE_SHA256 = (
    "3bf5274964d7d34ffc7b5fb3ae6632e94b81658cec6bb3dd2073cbfc02dbc730"
)
GUKGAM_2026_COMMITTEES_INVENTORY = (
    "docs/research/gukgam_2026_assembly_comprehensive_schedule_2026-10-01.json"
)

# Names that could not be confirmed from the inventory. Empty: all 17 are confirmed.
GUKGAM_2026_UNCONFIRMED_COMMITTEE_NAMES: frozenset[str] = frozenset()

# Inventory order (short name -> full name); the three FOOTNOTE-region committees are last.
GUKGAM_2026_COMMITTEE_NAMES: tuple[str, ...] = (
    "법제사법위원회",
    "정무위원회",
    "재정경제기획위원회",
    "교육위원회",
    "과학기술정보방송통신위원회",
    "외교통일위원회",
    "국방위원회",
    "행정안전위원회",
    "문화체육관광위원회",
    "농림축산식품해양수산위원회",
    "산업통상자원중소벤처기업위원회",
    "보건복지위원회",
    "기후에너지환경노동위원회",
    "국토교통위원회",
    "국회운영위원회",
    "정보위원회",
    "성평등가족위원회",
)
