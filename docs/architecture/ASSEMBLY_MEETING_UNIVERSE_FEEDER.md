# National Assembly Meeting Universe Feeder

## Purpose

Acquire the bounded, complete set of meeting identifiers (`CONF_ID`) that the official minutes
indexes publish for one Assembly age. This is the universe the meeting-graph lane
([ASSEMBLY_MEETING_GRAPH_FEEDER.md](ASSEMBLY_MEETING_GRAPH_FEEDER.md)) needs before it can expand
`CONF_ID -> VCONFDETAIL / VCONFBLLLIST / VCONFBILLLIST` at L3.

```text
nzbyfwhwaoanttzje (본회의 회의록)  ┐
                                    ├─ DAE_NUM=age, CONF_DATE=YYYY, every page ─> rows (one per agenda item)
ncwgseseafwbuheph (위원회 회의록)  ┘                                              └─ group by CONF_ID ─> meetings
```

Acquisition only: no Person, Organization or Claim is created.

## Official APIs — keyed probes 2026-10-05

Both indexes require `DAE_NUM` and `CONF_DATE` (missing either returns `ERROR-300`).

`CONF_DATE` accepts a `YYYY` prefix and then returns every row of that calendar year. Evidence:
for `DAE_NUM=22` and years 2024/2025/2026 in both indexes, every returned row's `CONF_DATE`
started with the requested year (0 rows outside), and the fetched row count equalled
`list_total_count` for every year. A `YYYY-MM-DD` value returns one day; a day with no plenary
returns `INFO-200`.

Row shape: one row per agenda item (`SUB_NAME`). Meeting-level fields repeat on every row:
`CONF_ID`, `CONFER_NUM`, `DAE_NUM`, `CONF_DATE`, `CLASS_NAME`, `TITLE`, `PDF_LINK_URL`; the
committee index adds `COMM_NAME` and `DEPT_CD`.

## 22nd Assembly live result (keyed, 2026-10-05)

| index | 2024 rows / meetings | 2025 rows / meetings | 2026 rows / meetings |
|---|---|---|---|
| committee `ncwgseseafwbuheph` | 12,822 / 551 | 22,792 / 781 | 13,566 / 489 |
| plenary `nzbyfwhwaoanttzje` | 661 / 35 | 1,080 / 54 | 1,224 / 44 |

- distinct `CONF_ID`: **1,954**; `CONF_ID` and `CONFER_NUM` are 1:1 in every year;
- no `CONF_ID` repeats across indexes or years with different meeting fields;
- 2023 is empty in both indexes for `DAE_NUM=22` (lower bound proven);
- committee `CLASS_NAME` values: 상임위원회, 특별위원회, 예산결산특별위원회; plenary: 국회본회의;
- `CONF_ID` has two provider formats (`0xxxxx` older, `Nxxxxxx` newer); both resolve in
  `VCONFDETAIL` with matching dates (checked on four universe IDs, oldest and newest).

The worker's own keyed run against a disposable database is recorded in the completed exec plan.

### Coverage relative to other lists

- `VCONFSUBCCONFLIST` (소위원회 회의 목록) lists only 30 meetings for 제22대; all 30 are in this
  universe (subcommittee minutes are filed under their standing committee in the committee index).
  It is therefore not used as a universe source.
- `VCONFBILLLIST` without `CONF_ID` returns 205,990 rows across all ages and ignores `ERACO`; it is
  not a bounded per-age source and is not used here.
- National audit (국정감사) and national investigation (국정조사) minutes have separate official
  indexes and are **outside** this universe. A meeting that appears only there is not covered.

## Universe definition and bounds

For one run: `DAE_NUM=age`, both indexes, calendar years `from_year .. to_year`.

- Lower bound: the run first requests `from_year - 1` in both indexes and fails closed unless both
  report zero rows.
- Upper bound: `to_year` defaults to the current year in Asia/Seoul and may not be in the future.
- Every page of every (index, year) is fetched; `list_total_count` must stay constant within a
  (index, year) and each page must carry exactly the expected number of rows.
- Each row must report the requested `DAE_NUM` and a `CONF_DATE` within the requested year.
- The whole universe is fetched and validated before anything is committed.

## Identity and normalization

- `provider_record_key = CONF_ID` (the provider's documented meeting ID).
- All rows sharing a `CONF_ID` must agree on index, `CONFER_NUM`, age, date, class, committee name,
  `DEPT_CD`, title and PDF URL; otherwise the run fails closed.
- One `CONFER_NUM` must map to exactly one `CONF_ID`.
- `PDF_LINK_URL` must equal `https://record.assembly.go.kr/assembly/viewer/minutes/download/pdf.do?id=<CONFER_NUM>`
  exactly; anything else fails closed. The PDF itself is not fetched by this lane.

Normalized observation fields: `meeting_id`, `minutes_number`, `assembly_age`, `meeting_date`,
`minutes_index` (`plenary` | `committee`), `class_name`, `committee_name`, `committee_dept_code`,
`title`, `minutes_pdf_url`, `index_agenda_row_count`, `meeting_semantics`.

Not normalized: `SUB_NAME` agenda titles (kept only in the minimized snapshot; agenda rows belong
to `VCONFBLLLIST`), `VOD_LINK_URL` (plain http), `CONF_LINK_URL`, `PDF_FILE_ID`, `VODCOMM_CODE`.

`identity_hints` is empty. `DEPT_CD` and committee names are provider metadata, not canonical
Organization bindings; a reviewed committee join is still required (see the committee-roster lane).

Each meeting is observed once, attached to the snapshot of the page that carries its first row.

## Run semantics

- Feeder `assembly_meeting_universe`, scope `assembly_age:<age>`.
- A re-run over an unchanged universe creates no new observation versions
  (`uq_feeder_observations_version`), so the lane is idempotent.
- There is no mid-run resume: a run is roughly 60 requests and commits only after full validation.
  A crash during the commit phase leaves a PARTIAL run; the next full run converges.
- Checkpoint metadata records the universe fingerprint, meeting count and page counters.

## SourcePolicy / credentials

Reuses the reviewed `open.assembly.go.kr` official Open API policy (metadata only, no fulltext, no
AI). `ASSEMBLY_API_KEY` is required (no sample mode: sample responses are capped at 5 rows and
cannot prove a universe). The key never enters discovered URLs, snapshots, metadata or errors.

## Maturity

**L3 FULL_ENUMERATION** for the meeting-identifier universe defined above (plenary + committee
minutes indexes, one Assembly age), with the keyed run and idempotent re-run recorded in the exec
plan.

Still open (not claimed):

1. expanding each `CONF_ID` through `VCONFDETAIL / VCONFBLLLIST / VCONFBILLLIST` with persistence
   and version semantics (meeting-graph lane);
2. national audit / investigation minutes indexes;
3. reviewed `DEPT_CD` → canonical committee Organization join;
4. scheduling in `civic-acquire`.
