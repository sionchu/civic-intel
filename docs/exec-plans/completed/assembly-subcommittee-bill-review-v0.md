# National Assembly Subcommittee Bill Review Source v0

Status: COMPLETE — official L2 sample proof and repository-wide verification passed; L3 remains blocked by the documented key/row-identity/join gaps.

## Objective

Add a source-specific, privacy-safe L2 connector and staging path for the Open Assembly
TVBPMCONFINFO subcommittee bill-review API without creating persistent FeederObservations,
Claims, committee Organizations, or inferred review-event identities.

## Official contract — reviewed 2026-10-05

- service detail:
  https://open.assembly.go.kr/portal/data/service/selectAPIServicePage.do/OOWY4R001216HX11542
- API code: TVBPMCONFINFO
- endpoint: https://open.assembly.go.kr/portal/openapi/TVBPMCONFINFO
- provider version: 1, published 2026-07-07
- provider request-limit value shown: 200000
- required service argument: AGE
- optional filters: BILL_NO, BILL_ID, ENROLL_TYPE

Output fields:

AGE, BILL_NO, BILL_ID, COMMITTEE_ID, COMMITTEE_NAME, SUB_COMMITTEE_NAME,
PRESENT_SESSION, PRESENT_CHA, PROC_SESSION, PROC_CHA, SUBMIT_DT, PRESENT_DT,
PROC_DT, PROC_RESULT_CD, ENROLL_TYPE, CONF_BIGO.

No person, contact, address or staff fields are documented.

## Public sample proof

The official no-key sample URL for AGE=22 returned INFO-000 and list_total_count 18324.
Five sample rows were returned. Some rows have no subcommittee/table/decision values yet; one
sample row reports a completed result such as 대안반영폐기.

The provider does not document a stable subcommittee-review row ID. BILL_ID is a bill identity,
not proven to be a unique review-row identity. This slice therefore does not define a persistent
FeederObservation provider_record_key.

## Semantic boundary

- SUBMIT_DT is committee referral date.
- PRESENT_DT is subcommittee table date.
- PROC_DT is subcommittee processing/decision date.
- PRESENT_SESSION/PRESENT_CHA and PROC_SESSION/PROC_CHA retain provider session/meeting values.
- PROC_RESULT_CD is retained as provider review-result text despite its field name ending in _CD.
- ENROLL_TYPE is the documented direct-subcommittee-referral indicator.
- CONF_BIGO is source-provided subcommittee referral/review information; do not infer extra meaning.

Missing values remain null. Do not invent dates, results, subcommittee names, or review events.

## Implementation boundary

Create:

1. a TVBPMCONFINFO connector reusing the existing Open Assembly domain policy;
2. typed source records and strict date/Y-N parsing;
3. explicit official sample mode fixed to AGE + page 1 / size 5;
4. one-page staging CLI with optional BILL_NO/BILL_ID/ENROLL_TYPE filters;
5. focused tests for contract, credentials, sample bounds, parsing and no-data/error handling;
6. a live official no-key sample proof through the connector;
7. architecture/coverage documentation.

Do not add:

- L3 enumerator/checkpoint;
- FeederObservation persistence;
- a synthetic review-event ID;
- bill/committee canonical binding;
- Claim/ClaimEvidence;
- schema or migration changes.

## L3 blockers

Before L3:

1. obtain/use an issued ASSEMBLY_API_KEY through the existing credential path;
2. fully enumerate AGE=22 and prove total/page stability;
3. measure duplicate BILL_ID frequency and determine whether one bill can have multiple rows;
4. approve a stable provider-derived row key only from proven source semantics;
5. verify correction/change behavior across repeated pulls;
6. reconcile COMMITTEE_ID to the existing reviewed committee/organization boundary;
7. reconcile the shared open.assembly.go.kr SourcePolicy review note for this 2026 endpoint.

## Acceptance

- focused Ruff/mypy/pytest pass;
- official no-key sample through new connector returns five rows and provider total 18324;
- no credential enters URL/body/metadata/errors;
- normal mode fails closed without ASSEMBLY_API_KEY;
- sample mode cannot request other page/size;
- no persistent DB or publication path is added;
- repository-wide verification passes.



## Verification closure — 2026-10-05

Live official proof through the implemented connector:

- sample mode: true
- AGE: 22
- records: 5
- provider list_total_count: 18324
- first BILL_ID: PRC_R2I4R0J5J3T0L1S0T1F7I2T5J6G9L8
- first COMMITTEE_ID: 9700407
- first ENROLL_TYPE: N, parsed as direct_referral=false

Focused verification:

- Ruff: PASS
- mypy: PASS
- new subcommittee tests: 12 / 12
- bill + subcommittee regression group: 33 / 33

Repository-wide verification:

- Ruff: PASS
- mypy: PASS over 115 source files
- pytest: 788 passed / 3 skipped
- Golden Set: PASS
- web lint: PASS
- web typecheck: PASS
- web tests: 42 / 42
- Next.js production build: PASS
- standalone runtime asset preparation: PASS
- full verification exit code: 0

No migration, persistent observation writer, Person/Organization/Claim mutation, or synthetic
review-event key was introduced.

The isolated worktree required npm ci before web verification. It restored lockfile-declared
dependencies only; no dependency or lockfile change is part of this slice. Existing npm audit
findings and pre-existing SQLite/Node warnings were not modified.

## Stop condition

Stop at evidence-backed L2 SINGLE_PULL. Do not promote to L3 or invent a provider row key.
