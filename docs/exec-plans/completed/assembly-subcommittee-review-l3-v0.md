# National Assembly Subcommittee Bill Review L3 v0

Status: COMPLETE — 22nd-Assembly TVBPMCONFINFO lane reached L3 after full keyed multiplicity audit, BILL_ID packet identity proof, persistent full enumeration, live resume/idempotency evidence and repository-wide verification.

## Objective

Promote the 22nd-Assembly TVBPMCONFINFO subcommittee bill-review lane from L2 staging to L3
FULL_ENUMERATION only after live source multiplicity proves a stable observation identity/version
contract.

No Person, Organization, canonical Bill, Claim, publication or UI materialization is in scope.

## Baseline

- official API: TVBPMCONFINFO
- required scope: AGE
- 22nd-Assembly provider total observed in sample: 18,324 rows
- L2 connector/parser exists and is credential-safe
- no provider review-row ID is documented
- BILL_ID is bill identity only and is not pre-approved as a row key

## Phase 1 — live multiplicity audit — COMPLETE

The keyed AGE=22 audit enumerated all **18,324 provider rows** over **19 pages** at `pSize=1000`.

Coverage was stable on every page and required **zero retries**.

Observed multiplicity:

- unique `BILL_ID`: **17,727**
- BILL_ID keys with more than one provider row: **471**
- maximum rows for one BILL_ID: **5**
- BILL_ID with more than one BILL_NO: **0**
- exact distinct normalized provider rows: **18,319**
- exact duplicate surplus rows: **5** (five exact rows repeated once)
- unique BILL_ID + COMMITTEE_ID: **17,978**; 305 repeated keys
- unique BILL_ID + COMMITTEE_ID + SUB_COMMITTEE_NAME: **18,257**; 63 repeated keys
- even the full semantic row tuple has five duplicate keys because those five provider rows are
  exact repeats.

Missingness is source semantics, not parse failure:

- SUB_COMMITTEE_NAME null: 10,120
- PRESENT_DT null: 10,130
- PROC_DT / PROC_RESULT_CD null: 12,821
- CONF_BIGO null: 16,030

The audit also proved that one BILL_ID may contain genuinely distinct rows across committees,
subcommittees and review stages. Therefore BILL_ID cannot be a provider-row key. A full-row
composite would confuse provider state changes with provider identity; BILL_ID is instead used as
the bill-scoped packet key described below.

Audit digest over the reported statistics:

`f62e7d09eb887ab0ed88c5d8c9686c874348367ac83d284d8787949abb054d44`

## Phase 2 — approved source-backed observation model — COMPLETE

Choose **B: one observation per BILL_ID**, because:

- BILL_ID is the provider's stable bill namespace;
- every BILL_ID maps to exactly one BILL_NO in the complete AGE=22 universe;
- multi-row records are legitimate review-state/history context, not identity collisions;
- corrections/additional review rows can become a new immutable version under the same BILL_ID key.

The normalized observation keeps a deterministic sorted collection of distinct review rows.
Exact repeated provider rows collapse to one review variant with `provider_row_count`; packet-level
`provider_row_total`, `distinct_review_rows` and `duplicate_provider_rows` preserve source
multiplicity.

All source pages are persisted as SourceSnapshots. A packet is committed when the last source page
containing that BILL_ID has been reached, following the existing meeting-graph L3 page-anchor
pattern. No committee/bill canonical entity link is created by this lane.

A second keyed layout audit confirmed this commit boundary against the live provider order:

- all 17,727 BILL_ID groups are contiguous in provider order;
- provider bill runs: exactly 17,727;
- non-contiguous BILL_ID groups: 0;
- bills spanning more than one 1,000-row page: **1**;
- that single bill spans pages 16→17;
- maximum provider rows per BILL_ID: 5;
- direct-referral distribution: 2,294 true / 16,030 false;
- SUBMIT_DT null rows: 334.

Provider-order audit digest:

`83a4665b15d140df0f14aa8038daeba6d0ba652546e74ea552d5d31c147fb00d`

## Phase 3 — L3 implementation — COMPLETE

Implemented:

- `OpenAssemblySubcommitteeReviewConnector.for_page()`;
- source-specific `AssemblySubcommitteeReviewEnumerator`;
- one `BILL_ID` packet observation with deterministic nested review variants;
- exact duplicate multiplicity preservation;
- page-level Source/SourceSnapshot persistence;
- full-universe fingerprinting;
- checkpoint/resume;
- budgeted partial runs;
- changed-packet immutable versions;
- persistence-failure checkpoint test;
- universe-drift and page-total fail-closed tests;
- blocked policy before network;
- source-specific reviewed SourcePolicy;
- credentials excluded from URLs/snapshots/checkpoints/errors;
- no canonical entity or publication mutation.

The sole cross-page packet carries `source_pages=[16,17]` and anchors to the page-17 snapshot.

## Live L3 proof

### Final-policy fresh full run

A new disposable SQLite DB was migrated to head and acquired under the final
TVBPMCONFINFO-specific SourcePolicy.

First full run:

- provider rows: **18,324**
- BILL_ID packets: **17,727**
- pages committed: **19 / 19**
- exact duplicate surplus rows: **5**
- observations created: **17,727**
- unchanged: 0
- status: **SUCCESS**
- checkpoint: **19**

Immediate fresh rerun on the same DB:

- provider rows: **18,324**
- packets: **17,727**
- pages committed: **19 / 19**
- observations created: **0**
- observations unchanged: **17,727**
- status: **SUCCESS**
- same universe fingerprint and duplicate-surplus count

Final DB evidence:

- Source URLs: **19**
- SourceSnapshots: **21**
- feeder observations: **17,727**
- Person: **0**
- Organization: **0**
- Claim: **0**
- distinct COMMITTEE_ID values: **25**
- persisted SourcePolicy review date: **2026-10-05**
- persisted policy note explicitly names `TVBPMCONFINFO`
- credential/fulltext leakage checks: **0**
- the sole cross-page packet records `source_pages=[16,17]`, `source_page_count=2`,
  and anchors to the page-17 snapshot

The 21 snapshots across 19 source URLs are intentional immutable representation history.
Pages 1 and 3 produced a different sanitized body hash between the first and second full pulls while
all 17,727 semantic BILL_ID packets stayed unchanged. Three immediate follow-up keyed probes of
those pages then produced stable body/order/semantic hashes. The provider exposes no correction
marker, so this is recorded as page-level representation drift, not labeled as a correction.

### Final-policy partial / resume proof

A separate new disposable DB intentionally stopped after three pages:

- provider universe: 18,324 rows / 17,727 packets / 19 pages
- page budget: 3
- status: **PARTIAL**
- observations created: **2,813**
- checkpoint: page 3

Normal `--resume` re-fetched and revalidated the complete universe, then continued after page 3:

- pages committed this run: **16**
- observations created: **14,914**
- status: **SUCCESS**
- checkpoint: page 19

Combined partial+resume coverage:

- provider rows: **18,324 / 18,324**
- packet observations: **17,727 / 17,727**

## Cross-source corroboration

Against the existing 22nd-Assembly meeting-graph disposable universe:

- subcommittee BILL_ID: 17,727
- meeting-graph raw bill IDs: 18,956
- overlap: 17,016
- subcommittee-only: 711
- subcommittee IDs intersecting meeting-graph conflict IDs: 149

Cross-source digest:

`8031cc4eba3b6f4366a32eeec1744a821755da3f72c8b466ca688a7688cbafad`

This is corroboration only. The 711 subcommittee-only IDs remain valid TVBPMCONFINFO source truth.

## Request-limit observation

The official service page displays request-limit value `200000`.

A keyed one-row TVBPMCONFINFO probe returned HTTP 200 / INFO-000 / provider total 18,324 and no
response headers containing rate, limit, retry, remaining or quota. The reset period is not
documented or inferred.

## Acceptance status

- keyed full AGE=22 audit with exact counts: PASS
- evidence-backed packet identity decision: PASS
- complete persistent L3 enumeration: PASS
- live partial/resume: PASS
- live unchanged rerun: PASS
- source-specific policy review: PASS
- no generic framework: PASS
- repository-wide verification: PASS

## Verification closure

Latest-master milestone verification:

- Ruff: PASS
- mypy: PASS over **133 source files**
- focused subcommittee tests: **23 / 23**
- full pytest: **998 passed / 3 skipped**
- Golden Set 001: PASS
- web lint: PASS
- web typecheck: PASS
- web tests: **42 / 42**
- Next.js production build: PASS
- standalone runtime asset preparation: PASS
- full verification exit code: **0**

Existing SQLite datetime deprecation and Node module-type warnings remain unchanged.

No migration, canonical entity materialization, Claim publication, scoring or scheduler change is
introduced by this milestone.

## Stop condition

Stop at acquisition L3. Do not schedule this lane, materialize canonical entities, publish Claims,
or derive scoring in this milestone.
