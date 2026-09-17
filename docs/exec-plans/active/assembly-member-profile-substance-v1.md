# Assembly Member Profile Substance v1

Status: COMPLETE

## Objective

Turn the published National Assembly Person read model into a useful, evidence-backed
profile without adding a new canonical financial, bill, or profile schema.

Baseline: `c96fc49fd163669d4af288db20dd9af56dab309e` (`origin/master` at start).

## Scope

- Use existing published Assembly Base Profile Claims for deterministic overview and current role.
- Use only explicit dated, reviewed career Claims for the career timeline. A current roster row is
  not treated as a complete career history.
- Publish Assembly bill participation through the existing `Claim` / `ClaimEvidence` path, using
  the existing `FeederObservation` and exact reviewed current-roster `MONA_CD` crosswalk.
- Render representative and co-sponsored bills as descriptive activity, with title, date,
  committee, source-provided result/status, official detail link, and exact provenance.
- Render derived historical role changes only when two eligible dated Claims exist.
- Keep source-level evidence trace and compact coverage limitations visible.
- Apply the Assembly-specific profile contract only to Assembly profiles; preserve the existing
  legacy projection contract for non-Assembly regression fixtures.

## Identity and provenance gates

- `MONA_CD` is a provider identity, never a canonical `Person.id`.
- `BILL_ID` is the immutable provider record key for a bill observation.
- `RST_MONA_CD` maps to `REPRESENTATIVE_PROPOSER`; `PUBL_MONA_CD` maps to `CO_PROPOSER`.
- Only an active, exact, reviewed current-roster observation link to a resolved Person may publish
  a bill participation Claim. Name matching is forbidden.
- Every public activity Claim keeps `ClaimEvidence -> SourceSnapshot -> FeederObservation -> Source
  -> SourcePolicy`; raw normalized observations are never read by the web UI.
- A changed immutable bill observation version conflicts with an existing current logical bill
  Claim; it is not silently overwritten or superseded.

## Explicit exclusions

No new feeder, crawler, search service, schema/migration, LLM summary, ranking, ideology or
influence score, assets/money, voting, news, controversy crawl, stakeholder network, forecast,
hearing-question, portrait, admin, or deployment work.

## Implementation and verification gates

1. Add the source-specific Assembly legislative activity publication seam using existing
   repository and Claim/Evidence persistence.
2. Add the Assembly-specific profile projection and public rendering for overview, current role,
   dated career, legislative activity, conditional recent changes, evidence/source library, and
   limitations. Hide unsupported generic sections.
3. Add deterministic unit/regression coverage for exact identity, provenance, idempotency,
   immutable-version conflicts, role separation, and no raw observation exposure.
4. Run the full Python/Ruff/mypy/quality/web verification available in the repository, plus a
   local production browser smoke with at least three Assembly people, same-name separation,
   390px layout, keyboard focus, and the existing People filters.
5. Re-read the diff, update this plan and `HANDOFF.md` with actual evidence, commit coherently,
   push `master`, and verify `HEAD == origin/master` and a clean worktree in the isolated checkout.

## Current checkpoint

- Portrait Pilot v0 is closed at `c96fc49`.
- No live Assembly acquisition or staging write is part of this milestone.
- Implemented the source-specific Assembly legislative activity publication seam, using the
  existing `FeederObservation`, `SourceRun`, `SourceCheckpoint`, `Claim`, and `ClaimEvidence`
  persistence path. Publication is limited to the latest successful full bill manifest and an
  exact active reviewed current-roster `MONA_CD` crosswalk; name matching is not used.
- Added the Assembly-specific profile projection and rendering path. It exposes deterministic
  overview/current role, explicit dated career Claims, representative/co-sponsored activity,
  conditional recent changes, evidence/source trace, and compact limitations while retaining the
  legacy projection for non-Assembly profiles. Raw normalized observations and contact fields are
  not read by the web UI.
- Added regression coverage for exact identity and role separation, provenance, idempotency,
  immutable-version conflict behavior, missing crosswalks, role-aware sections, and same-name
  facet behavior. Added the missing web icon so the production artifact has no static asset 404.

## Evidence closure — 2026-09-17

- Python regression: `359 passed, 1 skipped, 4 warnings`; focused Assembly/profile tests and
  source-specific publication tests also passed. Ruff, mypy, Golden quality, web lint,
  typecheck, and web tests passed.
- A standalone production artifact built successfully in a disposable directory. Playwright
  smoke used Chromium at exact `390x844` and desktop `1440x900` against a disposable local API
  fixture with three resolved Assembly People, two same-name `박지원` records, long Korean
  district/committee values, and representative/co-sponsored bills. People filters returned
  `party=2`, `district=1`, `committee=1`, `reelection=1`, and a valid combination `1`; name
  search returned `박지원=2`, and the no-match state returned `0` with `검색 결과가 없습니다.`.
- The browser run found no horizontal overflow, console warning/error, page error, or
  hydration/framework overlay. It confirmed skip-link keyboard focus, distinct same-name
  canonical links, evidence/source trace, no raw normalized/contact fields, and separate
  unknown-Person/no-match states. Screenshots were captured for Home, People, and a representative
  profile in the private disposable QA directory.
- No staging/Railway/API/PostgreSQL/schema or live Assembly acquisition operation was performed.

## Closure

Implementation, tests, browser evidence, diff review, and documentation are complete. The next
bounded action is to expand the existing reviewed Assembly historical-career packet to one
additional Person while keeping the L1 reviewed-Claim path and its coverage limits unchanged.
