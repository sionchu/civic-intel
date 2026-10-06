# Evidence Graph status — 2026-10-07

Measured with `workers/relationship_coverage.py` (read-only) and the rehearsal API. BEFORE = canonical
`civic_intel` (Mac, rev 0008, 558,801 Claims, read-only). AFTER = disposable copy
`civic_intel_graph_rehearsal` restored from a fresh `pg_dump` of canonical, then:

| Step (rehearsal only) | Result |
|---|---|
| `assembly_committees --publish-memberships` | 477 / 477 rows → 477 FACT Claims, 0 unresolved `MONA_CD` |
| `legislative_activity --publish-claims` (existing lane, first full run) | 19,807 bills → 240,490 participation FACT Claims; 22 codes of former members not on the current roster reported, never name-matched |
| `assembly_member_biographies --enumerate` (live API) | 299 / 299 members, 1 page, SUCCESS; contact/staff fields not stored |
| `assembly_member_biographies --publish` | 294 members with entries → 561 education + 4,292 career CLAIMs |

Canonical DB, public Site and the Mac API were not changed. Rehearsal DB 2.9 GB vs canonical 2.6 GB.

## Coverage matrix (504 public People: 299 current Assembly members + 205 ALIO-linked)

`AVAILABLE` = asserted FACT, `PARTIAL` = source-attributed CLAIM only, `UNKNOWN` = no published Claim
(a collection gap, not a negative finding). No dimension is `CONFLICTING`.

| Dimension | BEFORE | AFTER |
|---|---|---|
| identity / source_provenance | 100% | 100% |
| birth · external_identifiers (MONA_CD) · vote · party · elected_office · term | 59.3% | 59.3% |
| committee / special_committee | 59.1% / 22.2% | 59.1% / 22.2% (now also code-keyed) |
| aliases · birthplace | 0% | 0% (aliases exist in roster observations but no `PersonAlias` rows) |
| education | 0% | 42.1% (70.9% of members) |
| high_school / university / graduate_school / department | 0% | 20.6% / 35.7% / 28.0% / 25.0% |
| education_dates | 0% | 3.0% |
| employment | 40.7% | 77.6% |
| campaign / campaign_role | 0% | 10.7% / 10.5% |
| transition_committee / government_committee | 0% | 4.2% / 4.2% |
| government_role / presidential_office / ministry | 0% | 36.1% / 15.7% / 26.0% |
| advisory_committee | 0% | 8.1% |
| association / foundation / think_tank / professional_association | 0% | 11.3% / 5.4% / 9.1% / 3.2% |
| military_service | 0% | 7.1% |
| corporate_role (OpenDART) / outside_director / audit_role | 6.9% / 6.0% / 5.4% | unchanged |
| board_membership (OpenDART + ALIO 이사) | 22.6% | 22.6% |
| bill_sponsorship / cosponsorship | 0% | 59.1% / 59.3% |
| ownership · major_shareholder · family · religion · asset/real-estate/securities/tax · executive_compensation | 0% | 0% (no published source lane) |

All biography-derived dimensions are `PARTIAL`: member-maintained profile text, never verified FACT.

## Relations (unique pairs; one pair can have several types)

| Relation | Status | BEFORE | AFTER |
|---|---|---|---|
| SAME_PARTY | DERIVED | 18,869 | 18,869 |
| SAME_PARLIAMENTARY_COMMITTEE | DERIVED | 0 | 3,714 |
| SAME_SPECIAL_COMMITTEE | DERIVED | 0 | 1,799 |
| COMMITTEE_WITNESS_REQUEST (member ↔ witness of that committee) | DERIVED | 0 | 3,976 |
| PUBLIC_INSTITUTION_OVERLAP | DERIVED | 200 | 200 |
| BOARD_INTERLOCK | DERIVED | 12 | 12 |
| BILL_COSPONSORSHIP (≥1 bill) / of which REPEATED (≥10) | DERIVED | 0 | 38,168 / 21,070 |
| **DERIVED total (excl. party)** | | **212** | **47,869** |
| SAME_SCHOOL / SAME_DEPARTMENT | CANDIDATE | 0 | 4,752 / 102 |
| SAME_EMPLOYER / SAME_CAMPAIGN / SAME_TRANSITION_COMMITTEE / SAME_GOVERNMENT_COMMITTEE | CANDIDATE | 0 | 449 / 4 / 5 / 7 |

Gate rejections: 0. Committee-name crosswalk: 13 of the committee names bind to a canonical
`국회 …위원회` Organization; the rest stay code-keyed.

## Relation-layer coverage by population (share with ≥1 bindable/text affiliation)

| Population | Political | Legislative | Public institution | Business | Oversight | Education (text) | Campaign (text) |
|---|---|---|---|---|---|---|---|
| Assembly members (299) | 100% | 99.7% (was 0) | 0% | 0% | — | 70.9% | 21.7% |
| ALIO executives (205) | — | — | 100% | 17.1% | 83.4% | 0% | 0% |
| OpenDART executives (35) | — | — | 100% | 100% | 2.9% | 0% | 0% |

The weakest layer is **politician ↔ business/public institution: 0%**. Members and executives
connect only through official oversight (committee witness lists) and shared institutions.

## End-to-end samples (rehearsal API, `/relationships/*`)

| Sample | Result |
|---|---|
| 현직 의원 + 캠프 약력 (강대식) | 187 DERIVED relations (committee 29, special committee 49, witness request 1, party), 8 SAME_SCHOOL candidates hidden by default, top co-sponsor 346 bills; 6/6 sampled relations traced Claim → SUPPORT Evidence → Snapshot → public `/sources/{id}` |
| 상임위원장 (김성원) | 206 relations incl. 27 witness requests; 4/4 traced |
| 공공기관장·국감 증인 (강경성) | 24 COMMITTEE_WITNESS_REQUEST + 6 PUBLIC_INSTITUTION_OVERLAP; 4/4 traced |
| 대기업 사내이사 (구자열) | BOARD_INTERLOCK + PUBLIC_INSTITUTION_OVERLAP; 2/2 traced |
| 사외이사 (강승우) | 0 relations — no other collected person on that board (UNKNOWN, not "none") |
| 위원 ↔ 증인 compare | direct COMMITTEE_WITNESS_REQUEST via 정무위원회, overlap UNKNOWN, 2-edge path with Claim ids |
| 의원 → 기업 임원 path | 6 edges: 의원 → 예결특위 → 의원 → 정무위원회 → 증인(기관장) → 한국소비자원 → 임원 |
| 정부 고위관료 · 전직 정치인 | NO_SAMPLE — no published Person lane for these populations yet |

Responses take 0.5–2.2 s per call on the Mac (read-time projection, no cache).

## Source catalog in use (relation coverage)

| Source (tier 0) | Entity key | Relations it fills | State |
|---|---|---|---|
| 열린국회정보 의원 인적사항 `nwvrqwxyaytdsfvhu` | `MONA_CD` | party, biography education/career/campaign (CANDIDATE) | roster canonical; biography rehearsal |
| 열린국회정보 위원 명단 `nktulghcadyhmiqxi` | `DEPT_CD:MONA_CD` | committee, special committee, witness request | observations canonical; membership Claims rehearsal |
| 열린국회정보 의원 발의법률안 `nzmimeepazxkubdpn` | `BILL_ID` + `MONA_CD` | co-sponsorship | observations canonical; Claims rehearsal |
| 국회 국정감사 증인·계획서 (reviewed packets) | witness row → reviewed Person link; committee Organization | witness request, audit-target path | canonical |
| ALIO 임원현황 | `apbaId` → canonical Organization | public-institution overlap | canonical (205 published) |
| OpenDART 임원현황 `exctvSttus` | `corp_code`, `rcept_no` | board co-service / interlock | canonical (36 published reviewed links) |
| NEC 후보자/당선인 | `huboid` | (future) local office, candidacy | 6,133 DRAFT, not published |
| 전자관보·MPM·인사혁신처 | notice / roster row | (future) government appointment, revolving door | observation-only |
| Wikidata / OpenSanctions | QID / NK id | discovery crosswalk only | not ingested |
| News (BigKinds etc.) | — | CANDIDATE discovery only | not ingested |

## Biggest gaps (priority order)

1. Politician ↔ business/public-sector career with canonical binding: 0%. Needs reviewed Person
   links from OpenDART/ALIO/관보 to Assembly members and former officials.
2. Education/campaign/government-committee relations exist only as CANDIDATE: no official school
   or campaign/committee registry binding yet.
3. Government officials, former politicians and campaign staff have no published Person lane
   (MPM, 관보, NEC are observation/DRAFT only).
4. Ownership, family, assets, compensation: 0% — sources gated (rights/route) or not started.
