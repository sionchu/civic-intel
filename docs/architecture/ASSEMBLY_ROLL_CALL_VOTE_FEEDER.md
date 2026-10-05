# National Assembly plenary roll-call vote feeder

## Purpose

This feeder acquires the official member-level plenary roll-call record (국회 본회의 표결 기록)
for one National Assembly term: for each plenary-voted bill, every seated member's published
result keyed by the provider member code `MONA_CD`.

It is an **acquisition-only** lane. It creates no Person, links no identity, publishes no Claim
and renders nothing. The 22nd-Assembly lane is `L3 FULL_ENUMERATION` (see "Maturity" below).

## Out of scope

Explicitly out of scope for this lane and for any consumer of its observations without a
separately approved plan:

- political-orientation, ideology or "progressive/conservative" scoring;
- vote alignment, agreement or similarity between members;
- party-line, party-deviation, cohesion or rebellion metrics;
- attendance or diligence scores derived from `불참`;
- inferring a reason (absence, boycott, walk-out, leave, conflict of interest) for `불참`.

Party, district and display-name fields are deliberately not retained, partly to keep these
derivations impossible from this lane's observations.

## Official contract (verified 2026-10-04)

Verification used the official Open Assembly service page and keyless sample requests from
open.assembly.go.kr. No authentication key was available, so no keyed request was made.

```text
service page: https://open.assembly.go.kr/portal/data/service/selectServicePage.do/OPR1MQ000998LC12535
catalog:      https://www.data.go.kr/data/15125948/openapi.do
member votes: https://open.assembly.go.kr/portal/openapi/nojepdqqaweusdfbi   (국회의원 본회의 표결정보)
bill tallies: https://open.assembly.go.kr/portal/openapi/ncocpgfiaoituanbr   (의안별 표결현황)
```

Service-page metadata: provider 국회사무처, origin system 의안정보시스템 표결정보, table
view covers the 22nd Assembly, file/API covers the 20th Assembly onward, published
2019-11-05, irregular update cycle. The page lists the common parameters `KEY`, `Type`,
`pIndex`, `pSize` (default 100) and states that the sample key is fixed to `pIndex=1`,
`pSize=5`. Its request-parameter and output tables did not render server-side, so parameter
requirements below come from observed provider behavior.

Observed behavior:

| Request | Result |
|---|---|
| `nojepdqqaweusdfbi?AGE=22` | `ERROR-300` (required value missing) |
| `nojepdqqaweusdfbi?BILL_ID=…` | `ERROR-300` |
| `nojepdqqaweusdfbi?AGE=22&BILL_ID=<voted bill>` | `INFO-000`, `list_total_count` 299 |
| `nojepdqqaweusdfbi?AGE=22&BILL_ID=<unknown>` | top-level `INFO-200` (no data) |
| `ncocpgfiaoituanbr` without `AGE` | `ERROR-300` |
| `ncocpgfiaoituanbr?AGE=22` / `21` / `20` / `19` | 1,911 / 3,272 / 3,492 / `INFO-200` |

Member-vote row fields observed: `BILL_ID`, `BILL_NO`, `BILL_NAME`, `LAW_TITLE`, `AGE`
(integer), `MONA_CD`, `MEMBER_NO`, `HG_NM`, `HJ_NM`, `POLY_NM`, `POLY_CD`, `ORIG_NM`,
`ORIG_CD`, `RESULT_VOTE_MOD`, `VOTE_DATE` (`YYYYMMDD HHMMSS`), `SESSION_CD`, `CURRENTS_CD`,
`CURR_COMMITTEE`, `CURR_COMMITTEE_ID`, `DEPT_CD`, `DISP_ORDER`, `BILL_URL`, `BILL_NAME_URL`.

Bill-tally row fields observed: `BILL_ID`, `BILL_NO`, `BILL_NAME`, `AGE` (string), `PROC_DT`,
`PROC_RESULT_CD`, `BILL_KIND_CD` (법률안, 중요동의, …), `CURR_COMMITTEE`,
`CURR_COMMITTEE_ID`, `MEMBER_TCNT`, `VOTE_TCNT`, `YES_TCNT`, `NO_TCNT`, `BLANK_TCNT`,
`LINK_URL`.

Observed `RESULT_VOTE_MOD` values: `찬성`, `반대`, `기권`, `불참`. For one sampled bill
(22nd term, 2026-10-01) per-value filtered totals were 찬성 219, 반대 3, 기권 5, 불참 72; the
bill row published `YES_TCNT` 219, `NO_TCNT` 3, `BLANK_TCNT` 5, `VOTE_TCNT` 227 and
`MEMBER_TCNT` 299. That exact reconciliation is the coverage check this lane enforces.

The `ncocpgfiaoituanbr` service name 의안별 표결현황 is corroborated by the observed response
shape and a secondary developer reference; its own official service page was not located in
this review.

### Keyed behavior observed 2026-10-05

- keyed pagination is operational: the 1,911-row bill universe was fetched completely with
  `pSize=1000` over two summary pages, and every member-vote request used `pSize=1000`.
  The provider therefore accepts 1000 for these services; a higher ceiling was not probed.
- not every bill reconciles: one 22nd-term bill publishes tallies 195/0/2 while its 296 complete
  member rows count 196/0/1. It is recorded as `SOURCE_CONFLICT`, not dropped or corrected.
- the complete 22nd-term run found no repeated `MONA_CD` inside one `BILL_ID`; any future
  repeated member still fails closed because the provider does not publish an independent
  vote-event identifier.
- the service page displays request-limit value `200000`. A keyed HTTP probe returned 200 and
  exposed no response headers containing rate/limit/retry/remaining/quota. A second keyed
  member-vote probe after a transient full-run request failure also returned HTTP 200,
  `INFO-000`, 300 rows and no such headers. The reset period is not documented or inferred.
- correction/republication timing remains unpublished. Immutable observation versioning preserves
  any later provider change instead of overwriting it.

## Bounded universe

```text
scope_key: assembly_age:{AGE}
universe:  every BILL_ID returned by ncocpgfiaoituanbr?AGE={AGE}
           x every member row of nojepdqqaweusdfbi?AGE={AGE}&BILL_ID={BILL_ID}
```

The scope key follows the bill-participation lane (`assembly_age:`) rather than a bare
`age:` prefix so both Assembly term lanes share one scope vocabulary.

## Coverage contract (fails closed)

Universe phase (before any bill is fetched):

- page 1 start, stable `list_total_count`, expected page count within `--max-universe-pages`;
- exact expected row count on every summary page;
- every summary row has `BILL_ID`, matching `AGE` and integer tallies;
- `YES_TCNT + NO_TCNT + BLANK_TCNT == VOTE_TCNT <= MEMBER_TCNT`;
- unique `BILL_ID` (duplicate or conflicting rows fail);
- `MEMBER_TCNT` fits one member-vote page (default `pSize` 1000).

Per bill:

- the response echoes the requested contract, term, bill and page;
- `list_total_count` equals the parsed row count and fits one page;
- every row has the requested `BILL_ID` and `AGE`, a whitespace-free `MONA_CD` and a parseable
  `VOTE_DATE`;
- `RESULT_VOTE_MOD` is one of the four published values; anything else (including empty) fails;
- `MONA_CD` is unique within the bill; a repeated member fails as duplicate (identical) or
  conflicting (different);
- member rows are reconciled against the bill's published tallies. The outcome is stored on
  every observation of that bill as `bill_tally_reconciliation`:
  - `MATCHED`: row counts reproduce `YES_TCNT`, `NO_TCNT`, `BLANK_TCNT` and `MEMBER_TCNT`;
  - `SOURCE_CONFLICT`: member rows are complete but their YES/NO/ABSTAIN counts differ from the
    published tallies — the two official datasets disagree;
  - `MEMBER_ROWS_INCOMPLETE`: the row count differs from `MEMBER_TCNT` (including zero rows).
  Non-`MATCHED` observations also carry `published_bill_tallies` and `member_row_tallies`.
  Neither side is corrected or chosen; the bill IDs are listed in the checkpoint metadata and
  the run receipt (`tally_exceptions`). Any later Claim or derived use must exclude or flag
  these bills.

Bills are processed in ascending `BILL_ID` order because the provider lists newest-first and
its order shifts as votes are added.

## Persistent observation

```text
feeder: assembly_plenary_roll_call_votes
scope_key: assembly_age:{AGE}
provider_record_key: {BILL_ID}:{MONA_CD}
semantic_scope: legislative_plenary_roll_call_vote
identity_hints: single_person_roll_call_vote, participant {assembly_mona_cd, MONA_CD, VOTER}
```

The normalized record retains only vote facts:

- bill ID, number and title; Assembly term;
- `member_code` (`MONA_CD`);
- `vote_value_published` exactly as published (`찬성`/`반대`/`기권`/`불참`) and the closed
  enum `vote_value` (`YES`/`NO`/`ABSTAIN`/`NOT_PARTICIPATING`);
- `vote_datetime_published` and its KST ISO form; session code and sitting number;
- committee name/code and a credential-scrubbed bill link;
- `vote_semantics: official_member_plenary_roll_call_record`.

`불참` maps to `NOT_PARTICIPATING`. It is never `NO`, and no reason is inferred.

Not retained: `HG_NM`, `HJ_NM`, `POLY_NM`, `POLY_CD`, `ORIG_NM`, `ORIG_CD`, `MEMBER_NO`,
`DEPT_CD`, `LAW_TITLE`, `DISP_ORDER`, `BILL_NAME_URL`. The provider publishes no contact
fields in this service. SourceSnapshot stays metadata-only (`can_store_fulltext=False`).

## SourcePolicy

All Open Assembly lanes share the host-level SourcePolicy row
(`11000000-0000-0000-0000-000000000001`, one policy per domain).
`national_assembly_roll_call_vote_policy()` carries the same rights as the bill lane: official
open API, fetch and metadata storage allowed, no fulltext, no AI transfer, no excerpt,
commercial use allowed under `이용허락범위 제한 없음`. `ASSEMBLY_API_KEY` is read from the
environment only; it never enters Source URLs, snapshot metadata, observations, checkpoints or
run errors.

## Run, budget and resume

A fresh `--enumerate` run fetches and validates the whole summary universe, commits each
summary page as its own Source/SourceSnapshot with checkpoint cursor `0`, then commits one
transaction per bill (Source, SourceSnapshot, member observations, cursor = bills completed).
Persistence failure leaves the checkpoint at the last committed bill.

`--max-bills N` stops after N bills in this invocation; the run ends `PARTIAL`
(`MaxBillsReached`) with the checkpoint retained. `--resume` re-fetches the universe and
continues only if its fingerprint (bill IDs and published tallies), term, page sizes and source
contract equal the checkpoint's; otherwise it fails closed and a fresh `--enumerate` is
required. Only a run that reaches the last bill is `SUCCESS`.

```text
same {BILL_ID}:{MONA_CD} + same normalized hash    -> unchanged
same {BILL_ID}:{MONA_CD} + changed normalized hash -> new immutable observation
```

```bash
civic-stage-assembly-votes --age 22 --enumerate --database-url sqlite:///civic-intel.db
civic-stage-assembly-votes --age 22 --resume --max-bills 200 --database-url sqlite:///civic-intel.db
```

## Identity and publication boundary

Identity stays the provider `MONA_CD`, as in the bill-participation lane. The feeder does not
AUTO_CREATE or link Persons, match by name, or publish Claims. A later publication step would
need its own approved plan, an accepted `MONA_CD` crosswalk and the normal
Claim/ClaimEvidence/Source/SourcePolicy gate.

## Maturity

**L3 FULL_ENUMERATION** for the 22nd Assembly.

### Full-term proof

The keyed disposable run covered all **1,911 / 1,911** bill-summary rows and **568,649**
member-vote records. It completed with one explicit tally exception:

`PRC_G2Z5L1L1C2F1O1S6A0I6O4J4T5B8G3 = SOURCE_CONFLICT`.

The conflict is retained on its observations; neither official dataset is silently preferred.

### Final-contract convergence and idempotency proof

The original full-term acquisition crossed the tally-reconciliation contract change at checkpoint
590: observations before that point did not yet contain `bill_tally_reconciliation`, while later
observations did. A fresh 2026-10-05 run on the same disposable database therefore converged the
historical prefix by creating immutable new versions instead of rewriting old observations.

Across the convergence run and its checkpoint-safe resumes:

- records seen: **568,649**
- new immutable versions: **175,612**
- unchanged under the final contract: **393,037**
- final status: **SUCCESS**
- universe fingerprint unchanged
- same single `SOURCE_CONFLICT` bill retained

Two transient generic API-request failures occurred at bill checkpoints 410 and 532. The worker
left committed checkpoints intact and `--resume` completed from each checkpoint. A direct keyed
probe of the next bill after the second failure immediately returned HTTP 200 / `INFO-000`,
demonstrating that the failure was not a deterministic row-contract failure.

Immediately after convergence, a second fresh full-term run was started under the same final code
and database. Its process was externally interrupted after checkpoint 1008, with:

- created: **0**
- unchanged: **299,948**

The stale RUNNING receipt was explicitly closed as PARTIAL without moving the checkpoint, and
`--resume` completed the remaining 903 bills:

- created: **0**
- unchanged: **268,701**
- final status: **SUCCESS**

Aggregated idempotency proof for the full universe:

- **observations_created = 0**
- **observations_unchanged = 568,649**
- checkpoint **1911 / 1911**
- same universe and tally-exception semantics

This satisfies the L3 full-enumeration, checkpoint/resume and unchanged-rerun contract. It does
**not** authorize Person materialization, Claim publication, vote-derived ideology/alignment
scoring, or scheduled production sync.
