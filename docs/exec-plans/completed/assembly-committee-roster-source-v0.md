# National Assembly Committee Roster Source v0

Status: COMPLETE — L2 official-sample proof and repository-wide verification passed; L3 remains blocked by the documented source-contract gaps.

## Objective

Stage the official Open Assembly committee roster sources as privacy-minimized, source-specific
connectors without creating canonical committee Organizations, membership episodes, People, or Claims.

This slice targets L2 SINGLE_PULL. L3 full enumeration is explicitly blocked until an
`ASSEMBLY_API_KEY` is available and the current-roster boundary can be proven against the existing
National Assembly current-member feeder.

## Official source contracts — 2026-10-05

Committee status:

- service detail: https://open.assembly.go.kr/portal/data/service/selectAPIServicePage.do/O2Q4ZT001004PV11014
- API: `nxrvzonlafugpqjuh`
- endpoint: https://open.assembly.go.kr/portal/openapi/nxrvzonlafugpqjuh
- provider request limit shown on service page: 200,000
- stable committee code: `HR_DEPT_CD`
- output: committee division/code/name, chair text, secretary text, authorized/current counts,
  negotiation/non-negotiation group counts.

Committee member list:

- service detail: https://open.assembly.go.kr/portal/data/service/selectAPIServicePage.do/OCAJQ4001000LI18751
- data.go.kr catalog: https://www.data.go.kr/data/15126035/openapi.do
- API: `nktulghcadyhmiqxi`
- endpoint: https://open.assembly.go.kr/portal/openapi/nktulghcadyhmiqxi
- provider request limit shown on service page: 200,000
- stable committee code: `DEPT_CD`
- stable member code: `MONA_CD`
- output also includes phone, email, room and staff names; Civic Intel must discard all of those
  before normalized payload creation.

Both services use the standard Open Assembly `KEY`, `Type`, `pIndex`, `pSize` envelope.
Without a KEY the official developer guide uses sample mode, fixing the first page/sample size.

## Verified public sample proof

On 2026-10-05, read-only official sample calls with no KEY returned:

- committee status: `INFO-000`, provider total `359`, five sample rows;
- committee members: `INFO-000`, provider total `477`, five sample rows.

The status total is much larger than the currently active committee set and the status rows expose
no Assembly term or effective date. Therefore **all 359 status records must not be treated as a
current-Assembly committee universe**.

The committee-member service likewise publishes no Assembly term/date field. A future L3 current
scope must be proven by reconciling every membership `MONA_CD` against the existing current-member
L3 roster and using only committee codes actually present in that reconciled membership universe.
Status rows are context for those codes, not independent current-membership authority.

## Privacy boundary

Allowed member fields:

- `DEPT_CD`, `DEPT_NM`, `JOB_RES_NM`
- `MONA_CD`, `HG_NM`, `HJ_NM`
- `ORIG_NM`, `POLY_NM`

Excluded before normalized body, snapshot, observation, logs, or tests:

- `ASSEM_TEL`
- `ASSEM_EMAIL`
- `ROOM_NO`
- `STAFF`
- `SECRETARY`
- `SECRETARY2`

No staff Person discovery is authorized.

## Record identity

For a future membership observation, the justified provider-derived key is:

`<DEPT_CD>:<MONA_CD>`

Role (`JOB_RES_NM`) is content, not identity, so a role change produces a new immutable version
under the same committee/member relationship key.

Committee-status identity is exact `HR_DEPT_CD`.

Neither key is a Civic Intel Organization or Person UUID.

## Rights

Open Assembly requires an issued authentication key for normal use and requires source attribution
under its Open API terms. Credentials must never enter discovered URLs, Source/Snapshot bodies,
metadata, checkpoints, errors, or logs.

The existing Open Assembly SourcePolicy remains the domain-level policy for this L2 staging slice.
Before any persistent L3 run, the stored domain-policy review note must be reconciled to explicitly
cover the committee APIs and the current attribution review.

## Implementation boundary

Create:

1. explicit connectors for the two API codes;
2. safe typed status/member records;
3. official-sample mode constrained to page 1 / size 5;
4. a one-page staging CLI using the existing SourcePolicy gate;
5. deterministic tests for keys, pagination, privacy minimization, credentials and provider errors;
6. a live no-key sample proof through the new connector.

Do not add an L3 enumerator, DB migration, committee Organization materialization, membership Claim,
or Person materialization in this slice.

## Acceptance

- focused Ruff / mypy / pytest pass;
- new connectors reproduce the official sample shape;
- contact/staff fields are absent from normalized connector bodies and staged records;
- no-key normal mode fails closed;
- sample mode cannot request another page/size;
- final diff contains no new generic ingestion abstraction.



## Verification closure — 2026-10-05

Implemented and verified:

- source-specific status/member connectors with allowlisted request filters;
- explicit no-key sample mode fixed to page 1 / size 5;
- privacy minimization before normalized ConnectorDocument creation;
- provider-derived keys HR_DEPT_CD and DEPT_CD:MONA_CD;
- no Person, Organization, Claim, membership episode, or DB schema changes;
- live official sample proof: 5 status rows + 5 membership rows; contact/staff output 0.

Focused verification:

- Ruff: PASS
- mypy: PASS
- Assembly-focused pytest: 28 passed
- new committee tests: 9 passed

Repository-wide verification:

- Ruff: PASS
- mypy: PASS over 115 source files
- pytest: 786 passed / 3 skipped
- Golden Set: PASS
- web lint: PASS
- web typecheck: PASS
- web tests: 42 / 42
- Next.js production build: PASS
- standalone runtime asset preparation: PASS

The full verification command exited 0. The only warnings were the existing SQLite datetime
deprecation warnings and the existing Node module-type warning.

L3 remains intentionally blocked. Do not promote the provider totals 359/477 to current-universe
coverage without an issued API key, complete page enumeration, current-member MONA_CD reconciliation,
and restriction of status rows to member-backed committee codes.

## Stop condition

Stop at L2 SINGLE_PULL and document the L3 blockers. Do not search for, expose, or recover a private
Assembly API key from local files.
