# National Assembly Meeting Graph L3 v0

Status: COMPLETE — every CONF_ID of the 22nd-Assembly meeting universe expanded through the three
official meeting services, keyed, and re-run.

## Objective

Lift the meeting-graph lane from one-`CONF_ID` L2 staging to a full per-age enumeration without
inventing identifiers or joins.

## Pre-implementation probe (keyed, 200 sampled meetings)

- `VCONFDETAIL` one row, date equal to the minutes index, Y/N flags clean;
- agenda and bill rows always carried the detail's `ERACO / SESS / DGR`;
- no duplicate `BLL_NO` inside a meeting; every `BLL_LV` was 1;
- 7 of 200 meetings listed one `BILL_ID` more than once: either identical rows, or the same
  `BILL_ID` with different bill names (different proposers / printed 의안번호).

The full run found one more shape: 4 meetings published as several detail rows that differ only in
the meeting-type flags.

## Decisions

1. Universe = meeting-universe lane, re-fetched and validated every run
   (`AssemblyMeetingUniverseEnumerator.fetch_meetings()`; no cross-lane DB read).
2. One observation per `CONF_ID`; agenda rows stay inside it (no agenda-row provider key exists).
3. Identical repeated bill rows are collapsed with a `provider_row_count`.
4. A `BILL_ID` listed with different rows inside one meeting is a provider conflict: kept
   verbatim, listed in `bill_id_conflicts`, excluded from `exact_bill_ids`. No repair from titles.
5. Multi-row detail is merged only when nothing but the meeting-type flags differ (any-Y), with
   per-row flag sets kept.
6. Resume by sorted position under a universe fingerprint; `--max-meetings` budget.
7. The meeting connectors now accept a top-level `INFO-200` (meeting with no rows) as an empty list.

## Implementation

- `workers/assembly_meeting_graph_enumeration.py` — `AssemblyMeetingGraphEnumerator`,
  `reconcile_meeting_bills()`, `merge_detail_rows()`, CLI `civic-stage-assembly-meeting-graph-age`.
- `workers/assembly_meeting_universe.py` — `fetch_meetings()` (fetch + validate, no persistence).
- `packages/connectors/open_assembly_meetings.py` — `parse_detail_rows()`, `INFO-200` handling.
- `tests/test_assembly_meeting_graph_enumeration.py` — 10 tests.

## Live proof — keyed, disposable SQLite, 2026-10-05

Run 1 (`--enumerate`), 10:23–11:04 UTC:

- SUCCESS; 1,954 / 1,954 meetings; 1,954 observations created
- agenda rows 49,144; bill rows 46,345 → 45,799 distinct entries (546 identical repeats)
- exact meeting→bill edges 45,423 over 18,953 distinct `BILL_ID`s
- `BILL_ID` conflicts: 188 instances / 152 distinct `BILL_ID`s / 51 meetings
- meetings without bill rows 429; multi-row detail meetings 4; subcommittee meetings 711
- snapshots 5,862; Person / Organization / Claim 0 / 0 / 0

An earlier attempt stopped fail-closed at meeting 35 (`053887`, two detail rows); that led to
decision 5 and a fresh run.

Run 2 (`--enumerate`, same database), 11:05–11:47 UTC:

- SUCCESS; 1,954 / 1,954 meetings; universe unchanged
- observations created 0, unchanged 1,954; same 51 conflict meetings

## Verification

Windows, 2026-10-05:

- new tests: 10 passed; with universe + meeting-graph suites: 40 passed
- full pytest: 984 passed, 3 skipped, 1 failed — the known Windows-only
  `test_admin_workflow::test_append_only_audit_and_populated_migration_roundtrip`
  (configparser `%` in the temp path; passes on Linux CI)
- `ruff check apps packages workers tests`: pass; `mypy packages workers apps/api`: pass
- web: NOT_RUN (no `apps/` change)
