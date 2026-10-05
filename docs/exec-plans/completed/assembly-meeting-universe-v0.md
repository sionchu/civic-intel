# National Assembly Meeting Universe Source v0

Status: COMPLETE — keyed 22nd-Assembly CONF_ID universe acquired and re-run idempotently against a
disposable database; per-meeting graph expansion remains a separate slice.

## Objective

Close the meeting-graph L3 blocker "bounded complete CONF_ID universe" (see
[ASSEMBLY_MEETING_GRAPH_FEEDER.md](../../architecture/ASSEMBLY_MEETING_GRAPH_FEEDER.md)) using only
official, provider-backed identifiers. No inferred joins, no Person/Organization/Claim creation.

## Decisions

1. Universe sources: plenary (`nzbyfwhwaoanttzje`) and committee (`ncwgseseafwbuheph`) minutes
   indexes. `VCONFSUBCCONFLIST` is a strict subset for 제22대 (30/30 inside the universe) and
   `VCONFBILLLIST` is not age-bounded, so neither defines the universe.
2. Year enumeration via `CONF_DATE=YYYY`, verified live to return exactly that calendar year.
3. Lower bound proven by an empty prior year in both indexes; upper bound is the current Seoul year.
4. `provider_record_key = CONF_ID`; rows grouped by `CONF_ID` must agree on every meeting field and
   `CONFER_NUM` must be 1:1 with `CONF_ID`, otherwise fail closed.
5. Fetch and validate everything before the first commit; no mid-run resume (≈60 requests).
6. Agenda titles stay out of normalized observations; agenda rows belong to `VCONFBLLLIST`.
7. National audit / investigation minutes indexes are explicitly out of scope for v0.

## Implementation

- `packages/connectors/open_assembly_meetings.py`: `OpenAssemblyMinutesIndexConnector`,
  `AssemblyMinutesIndexRow`, `minutes_pdf_url()` (exact official PDF URL or fail closed).
- `workers/assembly_meeting_universe.py`: `AssemblyMeetingUniverseEnumerator`,
  `aggregate_meetings()`, CLI `civic-stage-assembly-meeting-universe`.
- `tests/test_assembly_meeting_universe.py`: 12 tests (cross-index/year/page aggregation, idempotent
  re-run, lower bound, per-CONF_ID disagreement, cross-index CONF_ID, CONFER_NUM→CONF_ID
  uniqueness, out-of-year row, non-official PDF URL, total drift, incomplete page, year-range
  validation, key handling and embedded-credential rejection).

## Live proof — keyed, disposable SQLite, 2026-10-05

Command: `civic-stage-assembly-meeting-universe --age 22 --from-year 2024` (run twice).

Run 1:
- status SUCCESS, years 2024–2026
- index rows 52,145; meetings 1,954 (committee 1,821, plenary 133)
- observations created 1,954
- universe fingerprint `128863f4707ab926b725563e7044a0a91e1373c741dbe69e4003e770ab8006ef`

Run 2 (same database, immediately after):
- status SUCCESS, same fingerprint
- observations created 0, unchanged 1,954

Database check after both runs:
- 1,954 observations / 1,954 distinct `CONF_ID`; committee 1,821, plenary 133
- meeting dates 2024-06-05 .. 2026-10-02; summed agenda rows 52,145
- 59 snapshots (page captures; run 2 reused unchanged content)
- 36 distinct committee `DEPT_CD` values (provider metadata only)
- people 0, organizations 0, claims 0
- credential string present in observations/snapshots/sources/runs/checkpoints: no
- `SUB_NAME` present in normalized observations: 0

Earlier keyed probes (same day) cross-checked four universe IDs (`053846`, `053847`, `N054544`,
`N054579`) against `VCONFDETAIL`: each returned exactly one row with the same meeting date.

## Verification

Windows, Python venv, 2026-10-05:
- `tests/test_assembly_meeting_universe.py`: 12 passed
- with `tests/test_open_assembly_meetings.py`: 30 passed
- full pytest: 805 passed, 3 skipped, 1 failed — the failure is
  `test_admin_workflow.py::test_append_only_audit_and_populated_migration_roundtrip`, which fails
  identically on the base branch on Windows (configparser rejects the `%` in the URL-encoded
  temp path); it is unrelated to this change
- `ruff check apps packages workers tests`: pass
- `mypy packages workers apps/api`: pass
- web tests / production build: NOT_RUN (no web change)

## Follow-ups

1. Meeting-graph L3: for each universe `CONF_ID`, page `VCONFBLLLIST` / `VCONFBILLLIST`, persist
   with `CONF_ID:BILL_ID` relation locators after version-semantics review.
2. Join `TVBPMCONFINFO` subcommittee review rows only through provider identifiers.
3. Add national audit / investigation minutes indexes as separate universe sources.
4. Schedule this lane in `civic-acquire` once the scheduled-acquisition PR is merged.
