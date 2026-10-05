# National Assembly Meeting Graph Source v0

Status: COMPLETE — aligned official L2 meeting/agenda/bill sample proof and repository-wide verification passed; L3 remains blocked by the documented universe/version gaps.

## Objective

Stage a source-specific L2 graph for one official National Assembly meeting using three Open Assembly
services while preserving their distinct semantics:

CONF_ID meeting detail -> meeting agenda rows
CONF_ID meeting detail -> meeting bill rows

Do not infer an agenda-to-bill edge from title similarity or row position.

## Official contracts — reviewed 2026-10-05

All three services are version 1 dated 2024-03-01 and show provider request-limit value 200000.

Meeting detail:
- service: https://open.assembly.go.kr/portal/data/service/selectAPIServicePage.do/OOWY4R001216HX11520
- API: VCONFDETAIL
- required request: CONF_ID
- stable meeting identifier: CONF_ID
- output includes term/session/degree, meeting date/type, committee/subcommittee names, place,
  start/end/duration, hearing/joint/speech flags, and DOWN_URL.

Meeting agenda list:
- service: https://open.assembly.go.kr/portal/data/service/selectAPIServicePage.do/OOWY4R001216HX11524
- API: VCONFBLLLIST
- required request: CONF_ID
- output: CONF_ID, ERACO, SESS, DGR, BLL_NO, BLL_NM, BLL_LV
- BLL_NO is documented as 안건 번호. It is not BILL_ID and must not be treated as an 의안번호.

Meeting bill list:
- service: https://open.assembly.go.kr/portal/data/service/selectAPIServicePage.do/OOWY4R001216HX11525
- API: VCONFBILLLIST
- provider requests CONF_ID and BILL_ID are both optional; this meeting-graph slice requires CONF_ID
  deliberately to remain meeting-scoped.
- output: CONF_ID, ERACO, SESS, DGR, BILL_ID, BILL_NM, LINK_URL
- BILL_ID is the exact provider bill identifier.

## Verified aligned public sample

A no-key sample pull for CONF_ID 053084 with Type=json and page size 5 returned:
- VCONFDETAIL: total 1
- VCONFBLLLIST: total 73
- VCONFBILLLIST: total 72
- all result codes INFO-000

The unequal 73 agenda rows vs 72 bill rows proves that this source family must not assume a 1:1
agenda-to-bill mapping.

The meeting detail for 053084 reported a 21st-Assembly meeting dated 2023-07-27 and a minutes PDF
download URL. The bill rows expose BILL_ID + exact LINK_URL; agenda rows expose BLL_NO + BLL_LV.

## Graph boundary

Exact edges in this slice:
- meeting CONF_ID -> each agenda row carrying the same CONF_ID
- meeting CONF_ID -> each bill row carrying the same CONF_ID

Not created:
- agenda BLL_NO -> BILL_ID
- title-based joins
- positional joins
- canonical Bill/Organization/Person entities
- Claims or publication records
- persistent FeederObservations

## Identity / row-key boundary

CONF_ID is documented meeting identity.

For future persistence:
- meeting detail can use CONF_ID as its provider key;
- meeting-bill relation has exact provider identifiers CONF_ID + BILL_ID, but persistence semantics
  still require a reviewed L3 design;
- agenda rows have CONF_ID + BLL_NO, but the provider does not document a separate stable agenda-row
  ID or revision contract. Do not promote this composite to a permanent key in this L2 slice.

## Privacy / rights

No person, contact, address, room or staff fields are documented by these three APIs.
Open Assembly normal operation requires an issued API key and source attribution. Credentials stay
out of discovered URLs, bodies, metadata, staged output and errors.

The existing open.assembly.go.kr policy is reused as the L2 network gate. Persistent L3 collection
requires a current policy-note reconciliation covering these meeting services.

## Implementation boundary

Create:
1. three source-specific connectors in one meeting-source module;
2. typed meeting, agenda and bill records;
3. explicit sample mode fixed to page 1 / size 5;
4. a meeting graph stager requiring one CONF_ID;
5. strict date/Y-N parsing and credential-safe link sanitization;
6. deterministic tests and one live aligned sample proof;
7. architecture/coverage documentation and CLI entrypoint.

Do not add a DB migration, L3 enumerator, source checkpoint, synthetic agenda-to-bill join, canonical
entity mutation or public projection.

## Acceptance

- focused Ruff/mypy/pytest pass;
- official sample graph returns 1 detail, 5 agenda rows and 5 bill rows with totals 1/73/72;
- all returned CONF_ID values equal the requested meeting;
- agenda and bill lists remain separate;
- credentials never persist;
- repository-wide verification passes.



## Verification closure — 2026-10-05

Live official proof through the implemented graph stager:

- CONF_ID: 053084
- meeting date: 2023-07-27
- meeting-detail provider total: 1
- staged agenda rows: 5 / provider total 73
- staged bill rows: 5 / provider total 72
- first agenda number: 1
- first bill ID: PRC_W2L3Z0U7S2K7Y1D3G0L4L4H7O6S0A2
- inferred agenda-to-bill edges: 0

Focused verification:

- Ruff: PASS
- mypy: PASS
- new meeting tests: 18 / 18
- bill + meeting regression group: 39 / 39

Repository-wide verification:

- Ruff: PASS
- mypy: PASS over 115 source files
- pytest: 794 passed / 3 skipped
- Golden Set: PASS
- web lint: PASS
- web typecheck: PASS
- web tests: 42 / 42
- Next.js production build: PASS
- standalone runtime asset preparation: PASS
- full verification exit code: 0

No schema/migration, FeederObservation persistence, canonical Bill/Organization/Person mutation,
Claim publication path, or agenda-to-bill title/position join was introduced.

Existing SQLite datetime deprecation and Node module-type warnings remain unchanged.

## Stop condition

Stop at L2 SINGLE_PULL. L3 requires an issued key plus a bounded meeting-universe source and reviewed
row/version semantics.
