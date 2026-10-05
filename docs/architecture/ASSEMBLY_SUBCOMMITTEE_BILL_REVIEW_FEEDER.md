# National Assembly Subcommittee Bill Review Feeder

## Purpose

Acquire the official National Assembly `TVBPMCONFINFO` subcommittee bill-review universe as
immutable, bill-scoped source observations.

This lane records provider-declared review context for a bill: committee/subcommittee routing,
referral, table and processing coordinates, result text, direct-referral flag and provider note.

It is an **acquisition-only enrichment lane**. It does not identify speakers or individual
legislators and does not create canonical People, Organizations, Bills, Claims or public output.

For the 22nd Assembly the lane is **L3 FULL_ENUMERATION**.

## Official source — reviewed 2026-10-05

Service detail:

https://open.assembly.go.kr/portal/data/service/selectAPIServicePage.do/OOWY4R001216HX11542

API:

- code: `TVBPMCONFINFO`
- endpoint: https://open.assembly.go.kr/portal/openapi/TVBPMCONFINFO
- official page version: 1
- official page date: 2026-07-07
- provider-displayed request-limit value: `200000`

### Request contract

Standard Open Assembly arguments:

- `KEY` — required for normal keyed use
- `Type` — xml/json
- `pIndex` — page index
- `pSize` — page size

Service-specific arguments:

- `AGE` — required Assembly term
- `BILL_NO` — optional bill number
- `BILL_ID` — optional bill ID
- `ENROLL_TYPE` — optional direct-subcommittee-referral flag

L3 enumeration requires an **unfiltered AGE scope**. A connector with BILL_NO, BILL_ID or
ENROLL_TYPE filters is rejected by the enumerator.

The connector supports `pSize <= 1000`. The 22nd-Assembly L3 run used `pSize=1000`.

## Output contract

The provider documents 16 fields:

- `AGE` — 대수
- `BILL_NO` — 의안번호
- `BILL_ID` — 의안ID
- `COMMITTEE_ID` — 위원회ID
- `COMMITTEE_NAME` — 소관위명
- `SUB_COMMITTEE_NAME` — 소위원회명
- `PRESENT_SESSION` — 상정회기
- `PRESENT_CHA` — 상정차수
- `PROC_SESSION` — 의결회기
- `PROC_CHA` — 의결차수
- `SUBMIT_DT` — 회부일
- `PRESENT_DT` — 상정일
- `PROC_DT` — 처리일
- `PROC_RESULT_CD` — 의안심의결과
- `ENROLL_TYPE` — 소위직접회부여부
- `CONF_BIGO` — 소위회부정보

No person, contact, address, room or staff fields are documented.

Missing provider values remain null. Non-empty dates must parse as ISO `YYYY-MM-DD`.
`ENROLL_TYPE` must be Y or N when present.

`PROC_RESULT_CD` is retained as provider result text. Civic Intel does not reinterpret it as an
internal code because the live values are human-readable result labels.

## Why the L3 observation key is BILL_ID

The API does **not** publish a stable review-row/event ID.

A keyed 22nd-Assembly audit enumerated all **18,324 provider rows** over **19 pages** and measured
the complete multiplicity before any persistent row-key decision.

### Complete multiplicity audit

- provider rows: **18,324**
- unique `BILL_ID`: **17,727**
- BILL_ID values with more than one provider row: **471**
- maximum provider rows for one BILL_ID: **5**
- BILL_ID values mapping to more than one BILL_NO: **0**
- exact distinct normalized provider rows: **18,319**
- exact duplicate surplus rows: **5**
- BILL_ID + COMMITTEE_ID duplicate keys: **305**
- BILL_ID + COMMITTEE_ID + SUB_COMMITTEE_NAME duplicate keys: **63**
- even the full semantic row tuple has five duplicate keys because the provider emits five exact
  repeated rows

Missingness in the same complete universe:

- SUB_COMMITTEE_NAME null: **10,120**
- PRESENT_DT null: **10,130**
- PROC_DT null: **12,821**
- PROC_RESULT_CD null: **12,821**
- CONF_BIGO null: **16,030**

The audit required zero retries and kept `list_total_count=18324` on every page.

Audit-statistics digest:

`f62e7d09eb887ab0ed88c5d8c9686c874348367ac83d284d8787949abb054d44`

### Identity decision

`BILL_ID` is not a source-row ID, so Civic Intel does **not** create one observation per provider
row.

Instead, L3 uses one observation packet per `BILL_ID`:

`provider_record_key = BILL_ID`

This is justified because the complete AGE=22 universe proved that each BILL_ID maps to exactly one
BILL_NO while legitimately carrying several review rows.

The packet preserves those rows as a deterministic sorted `reviews` collection.

Exact repeated provider rows collapse to one review variant with:

`provider_row_count`

Packet-level fields preserve the original multiplicity:

- `provider_row_total`
- `distinct_review_rows`
- `duplicate_provider_rows`

The packet also records its source-page locators:

- `source_pages`
- `source_page_count`

These page values are acquisition provenance, not a provider Bill or review-event identifier.

## Provider ordering and page boundaries

A second full layout audit found:

- 17,727 BILL_ID groups in provider order
- 17,727 contiguous BILL_ID runs
- **0 non-contiguous BILL_ID groups**
- only **1 BILL_ID** spans a page boundary
- that one packet spans pages 16 and 17
- maximum rows per BILL_ID remains 5
- BILL_ID -> BILL_NO conflicts remain 0

Provider-order digest:

`83a4665b15d140df0f14aa8038daeba6d0ba652546e74ea552d5d31c147fb00d`

A packet is therefore committed only when its final source page has been reached. All fetched
pages are persisted as Source/Snapshot evidence; the packet observation anchors to its last source
page following the existing meeting-graph L3 pattern.

The cross-page live packet correctly records `source_pages=[16,17]` and anchors to the page-17
snapshot.

## L3 enumeration contract

Feeder:

`assembly_subcommittee_bill_reviews`

Scope:

`assembly_age:<AGE>`

22nd-Assembly scope:

`assembly_age:22`

Source contract:

`assembly_age_subcommittee_review_packets_by_bill_id`

The enumerator:

1. rejects sample mode and filtered connectors;
2. fetches every page for the declared AGE;
3. requires stable `list_total_count`;
4. validates expected rows on every page;
5. rejects AGE drift;
6. groups the full source universe by BILL_ID;
7. rejects any BILL_ID -> multiple BILL_NO mapping;
8. canonicalizes review variants and exact duplicate counts;
9. computes a deterministic universe fingerprint over packet hashes;
10. persists every fetched page as an immutable SourceSnapshot;
11. commits BILL_ID packet observations at their anchor page;
12. stores page/packet counts, duplicate surplus and universe fingerprint in the checkpoint;
13. on resume, re-fetches/revalidates the complete universe before continuing after the last
    committed page;
14. refuses resume if the universe fingerprint, counts, contract, AGE or page size changed.

No identity hints are emitted.

## Live L3 proof — 22nd Assembly

Final-code / final-policy disposable run:

- provider rows: **18,324**
- source pages: **19 / 19**
- BILL_ID packet observations: **17,727**
- exact duplicate surplus rows: **5**
- created: **17,727**
- unchanged: 0
- status: **SUCCESS**
- checkpoint: **19**

Immediate fresh rerun on the same DB:

- provider rows: **18,324**
- packets: **17,727**
- created: **0**
- unchanged: **17,727**
- status: **SUCCESS**
- checkpoint: **19**
- same universe fingerprint

### Partial / resume proof

A separate final-policy disposable DB intentionally stopped after three pages:

- status: **PARTIAL**
- pages committed: **3 / 19**
- observations created: **2,813**

Normal `--resume` re-fetched and revalidated the complete source universe, then continued after
page 3:

- pages committed this run: **16**
- pages committed total: **19**
- observations created: **14,914**
- final status: **SUCCESS**

Fixture tests also cover:

- unchanged rerun;
- changed packet -> one immutable new version;
- max-page checkpoint/resume;
- synthetic persistence failure with last successful checkpoint retained;
- changed-universe resume rejection;
- total drift;
- incomplete page;
- BILL_ID -> multiple BILL_NO rejection;
- sample/filtered scope rejection;
- policy denial before network;
- provider failure before persistence with secret-safe error handling.

## SourceSnapshot representation drift

The final live DB contains 19 Source URLs and 21 immutable SourceSnapshots.

Between the first and second full pulls, page 1 and page 3 produced a different sanitized page-body
hash while **all 17,727 BILL_ID packet observations remained unchanged**.

The provider did not expose a correction/version marker explaining that page-level difference.
Civic Intel therefore does not label it a correction.

The page-level change is preserved as new SourceSnapshots. Packet observations version only when
their deterministic normalized review packet changes.

Immediately repeated keyed probes of pages 1 and 3 then produced stable body, provider-order and
sorted semantic-row hashes across three rounds.

This is why raw page representation and semantic BILL_ID packet versioning remain separate.

## Cross-source corroboration

BILL_ID remains a provider namespace. L3 does not require another lane to authorize the source row.

A read-only comparison against the existing 22nd-Assembly meeting-graph L3 database found:

- subcommittee BILL_ID packets: **17,727**
- meeting-graph distinct bill IDs observed in any row: **18,956**
- subcommittee BILL_ID found in meeting graph: **17,016**
- subcommittee BILL_ID not found in meeting graph: **711**
- subcommittee BILL_ID found in meeting-graph exact-bill set: **17,013**
- subcommittee BILL_ID appearing in meeting-graph conflict set: **149**

The 711 subcommittee-only IDs remain valid TVBPMCONFINFO source truth. Their absence from the
meeting-graph lane is not a deletion or correction rule.

The subcommittee universe contains **25 distinct COMMITTEE_ID values** and no observed
COMMITTEE_ID -> multiple COMMITTEE_NAME conflict in the complete audit.

COMMITTEE_ID is not automatically materialized as a canonical Organization.

## SourcePolicy and credentials

This source uses the shared `open.assembly.go.kr` policy identity with a source-specific reviewed
policy contract dated 2026-10-05.

The review records:

- official TVBPMCONFINFO service page;
- Open Assembly Open API terms;
- attribution requirement to 열린국회정보;
- `이용허락범위 제한 없음`;
- provider-displayed request-limit value `200000`;
- normal keyed use;
- public no-key sample mode limited to page 1 / 5 rows.

Civic Intel stores structured metadata only:

- fulltext storage: disabled
- AI transmission: disabled
- excerpt publication: disabled

`ASSEMBLY_API_KEY` is appended only to the outgoing HTTP request. It is not included in
discovered URLs, normalized documents, snapshots, observations, checkpoints or error messages.

A final fresh disposable DB verified:

- SourcePolicy review contains TVBPMCONFINFO;
- terms_checked_at = 2026-10-05;
- rate-limit note contains 200000;
- credential/fulltext leakage checks = 0.

## Canonical identity / publication boundary

This L3 lane creates no:

- Person;
- PersonAlias;
- Organization / InstitutionalBody;
- canonical Bill;
- CommitteeMembershipEpisode;
- Claim / ClaimEvidence;
- public projection;
- ideology/partisanship/behavioral score.

The final live proof contained:

- People: **0**
- Organizations: **0**
- Claims: **0**

BILL_ID and COMMITTEE_ID can support future reviewed exact joins, but acquisition success does not
authorize materialization or publication.

## Maturity

**L3 FULL_ENUMERATION** for the 22nd Assembly.

L4 scheduling/freshness is not part of this milestone.
