# Person profile linkage v0 (witness / OpenDART → existing Person)

**Status: `CANONICAL_LINKS_APPLIED_DEPLOY_PENDING`.** Code, tests and documents are on branch
`feat/person-profile-linkage` (base `origin/master` `0a448eb`). The canonical Mac DB, the public
API and the Sites snapshot are unchanged. Applying any link to the canonical DB needs the owner's
explicit approval (see "STOP boundary").

## Goal

Close, for at least one real source lane, the path that already-collected source rows lacked:
official row → SourceSnapshot → FeederObservation → reviewed identity link → canonical Person →
Claim → ClaimEvidence → public API → person page → clickable Source. Ambiguous identities must
stay unlinked. No new truth store, table or migration.

## Measured state (2026-10-06, canonical DB, read-only)

Alembic `0008`; People 9,120 (RESOLVED 299, all Assembly roster; REVIEW 2,688 ALIO + 6,133 NEC);
Claims 16,169; FeederObservations 772,768 at the audit start (774,482 when the rehearsal copy was
taken; daily acquisition keeps running).

| Lane | Collected | Normalized | Identity | Person | Claim | Published | API | Frontend |
|---|---|---|---|---|---|---|---|---|
| Assembly roster (`MONA_CD`) | 314 obs | yes | AUTO_CREATE 298 + reviewed 1 | 299 RESOLVED | 1,494 | 1,494 | yes | yes |
| Assembly bills / votes / meetings | 20,067 / 568,649 / 3,908 | yes | none | – | 0 | 0 | – | pending lane |
| Gukgam witness | 1,965 obs | yes | none (policy) | – | 1,731 Organization-subject | 1,731 | list only | list only, no Person |
| ALIO item 4 | 3,799 obs | yes | 2,688 deterministic source-context | 2,688 REVIEW | 2,688 DRAFT role + 3,624 org | org only | – | org page text |
| OpenDART `exctvSttus` | 35,022 obs | yes | none | 0 | 0 | 0 | – | – |
| NEC candidates | 6,756 obs | yes | 6,133 deterministic source-context | 6,133 REVIEW | 6,133 DRAFT | 0 | – | – |
| Gwanbo personnel | 0 obs | – | – | – | – | – | – | – |

Root cause: not missing collection and not missing API/frontend support. The break is at
identity (no path from no-Person-ID rows to an existing Person) and at publication (ALIO/NEC
source-context People and Claims never left DRAFT/REVIEW).

## Implemented (this branch)

- `packages/verification/person_record_links.py`: anchor rules (listed name without Hanja,
  birth year/month conflict, witness institution anchor) and the two Person Claim builders
  `LISTED_AS_GUKGAM_WITNESS` and `OPENDART_DISCLOSED_EXECUTIVE_ROLE` (DRAFT, `CLAIM`, not asserted).
- `packages/persistence/admin_workflow.py`: `LINK_PERSON` accepts witness and OpenDART rows onto an
  existing RESOLVED Person (no REGISTER); bridge Evidence must belong to the target's own current
  Claims; PUBLISH revalidates link/hash/source list Claim; WITHDRAW of a committee witness Claim
  withholds dependent Person Claims. The ALIO link path now shares the same link/Claim writer.
- `packages/rendering/profile_projection.py`: `2026 국정감사`, `공공기관 임원 공시`, `기업 임원 공시`
  sections, emitted only when published entries exist.
- `packages/rendering/gukgam_witness_claim.py`, `apps/api/main.py`: `/gukgam/2026/witnesses` adds
  `linked_person` only for a row restated by a published Person Claim of a public Person.
- `workers/person_link_candidates.py` (`civic-preflight-person-link-candidates`): read-only review
  packet with evidence bundles; name overlap alone is never a candidate.
- Web: person page 국정감사 block for witness listings, labelled key facts, EvidencePanel labels;
  witness list links a row to the Person only through `linked_person`.
- Docs: `IDENTITY_RESOLUTION.md`, `GUKGAM_2026_WITNESS_SOURCE_CONTRACT.md`,
  `CORPORATE_TALENT_FEEDER.md`, `ADMIN_OPERATIONS.md`.

## Verification evidence

- `make verify` on the Mac worktree at `96ead59`: ruff clean, mypy 136 files, pytest 1012 passed /
  3 skipped, Golden quality `passed: true`, web lint/typecheck, web tests 47/47, production build.
  Later commits changed only particles/scope note; targeted Python tests and web lint/typecheck/tests
  were rerun locally.
- `tests/test_person_record_links.py` (9 tests): reviewed witness + OpenDART rows reach one public
  profile with Claim → Evidence (SUPPORT + NEUTRAL bridge) → readable Source; nothing public before
  PUBLISH; homonym without institution anchor refused; name mismatch and birth year/month conflict
  refused; bridge from another Person refused; no REGISTER for no-ID rows; re-run never duplicates;
  withdrawn list row withholds the Person Claim and blocks re-publish; candidate report is
  read-only and deterministic.
- Rehearsal on a disposable copy of the canonical DB (`civic_intel_person_link_rehearsal`, dump
  sha256 prefix `e4ae64b53a926bd3`), branch `a94d344`: 강경성 (KOTRA 상임기관장 ↔ 산자위 기관증인)
  and 강승우 (한국지역난방공사 비상임이사 ↔ OpenDART 지역난방공사 이사) linked and published; the
  branch API served both profiles and one linked witness row; re-link `ALREADY_LINKED`; homonym
  (MP 조정식 vs listed "강사(메가스터디)") `WITNESS_INSTITUTION_ANCHOR_REQUIRED`; MP 김재섭 (1987)
  vs OpenDART 김재섭 (1963-01) `BIRTH_YEAR_MONTH_CONFLICT`. Canonical DB afterwards: admin
  operations 0, links 9,120, new-predicate Claims 0.
- Local browser (SQLite fixture, dev server): person page shows the three sections, correct
  sentences, the 국정감사 block and working in-page Evidence anchors; the witness list links only
  the anchored row. Screenshots were unavailable (pane not drawing), so visual layout and mobile
  geometry are NOT VERIFIED; `scrollWidth` stayed 375 at 375px.

## Review queue (canonical, read-only report sha256 `12dafd72…`)

- Witness: 173 candidates (171 People, 167 `기관증인` rows); all blocked only by
  `PERSON_NOT_RESOLVED` (ALIO source-context People need RESOLVE_PERSON first). 462 rows are
  name-only and not candidates; 234 rows have no published list Claim (excluded duplicate lists).
- OpenDART: 61 candidates (36 company-in-ALIO-career, 25 agreeing birth year/month with NEC
  People); all blocked by `PERSON_NOT_RESOLVED`. 7,313 name pairs refused by birth conflict;
  3,152 name-only pairs are not candidates; 26,641 rows have no same-name Person.

## Canonical apply receipt (2026-10-06, owner approval "어 반영해")

- Backup first: `/Users/lee/Developer/civic-intel-serve/backups/pre-person-link-20261006-155704.dump`
  (95 MB); the rehearsal DB was restored from the same dump.
- Candidate report sha256 `12dafd72…` was identical on the rehearsal copy and on canonical; the
  runner refuses any other sha.
- Applied 209 candidates: all 173 witness candidates and the 36 OpenDART candidates anchored by
  the company in the Person's ALIO source-reported career. The 25 candidates anchored only by an
  agreeing birth year/month with NEC People were not applied (their bridge would be an NEC
  candidacy Claim, which would also open those NEC People publicly).
- Admin receipts: 828 (`RESOLVE_PERSON` 205, `PUBLISH` 414 = 205 ALIO roles + 209 linked Claims,
  `LINK_PERSON` 209), 0 failures. The receipt reason records that this is the owner's bulk
  approval of deterministic anchors, not a row-by-row reading.
- After: RESOLVED People 299 → 504, People 9,120 (no new Person), links 9,120 → 9,329, Claims
  16,169 → 16,378. Branch API against canonical: 504 public People, every page 200; sections
  gukgam 171, public institution 205, corporate 35; witness rows with `linked_person` 173 of 1,731.
- The public Sites snapshot is unchanged until it is rebuilt and published.

## STOP boundary (owner approval required)

1. Done for 209 candidates (receipt above). Remaining 25 NEC-anchored OpenDART candidates need
   their own decision. Per candidate: `RESOLVE_PERSON` (source-context Person) → `PUBLISH`
   the ALIO role Claim → `LINK_PERSON` with the packet's bridge Evidence → `PUBLISH` the linked
   Claim. Each is an audited admin command; take a fresh logical backup first.
2. Deploy: restart the Mac private API from merged master (not the stale always-on process),
   rebuild `build:sites`, preflight, then a new Sites version and visibility as before.

## Next

- Bulk throughput: the admin review UI lists only ALIO rows; 234 candidates × 4 commands needs a
  reviewed-manifest runner (preflight sha → commit) or an admin-review candidate tab.
- Existing ALIO/NEC source-context Claim sentences use fixed particles ("강승우을 …이사으로").
- Assembly bill participation Claims (20,067 observations, 0 Claims) are the largest unused lane.
