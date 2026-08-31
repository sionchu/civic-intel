# CleanEye local-public-institution executives L3

Status: blocked — official source-contract gate failed on 2026-08-31; L3 was not implemented.

## Objective

Evaluate and, only if the official source contract permits it, promote the CleanEye local
public-institution executive lane to source-bounded L3 `FULL_ENUMERATION` on the canonical
`SourceRun` / `SourceCheckpoint` / `FeederObservation` foundation.

The intended public-interest universe is the local counterpart to the ALIO central-public-
institution executive lane:

```text
local public enterprises
+
local-government invested / contributed institutions
```

This plan does not add a generic crawler, a shared ALIO/CleanEye disclosure framework,
person-by-person enrichment, fuzzy matching, automatic cross-Person merge, scheduling or new
infrastructure.

## Baseline and actual maturity

Verified on 2026-08-31:

```text
branch: master
local/origin HEAD: 782a3068ca8d9418cb0b8a1ebdff305a8ae29184
tracked tree: clean
Alembic head: 0004
CleanEye connector/contracts/tests: none
actual CleanEye maturity: L0 RESEARCHED while this source gate is evaluated
```

Six existing source-specific L3 feeders remain implemented on the canonical repository:

1. National Assembly members
2. Gwanbo personnel notices
3. NEC local elected-office winners
4. National Assembly bill participation
5. NEC local-election candidates
6. ALIO public-institution executives

Their current persistent-enumerator and ALIO staging regressions pass together. CleanEye has no
existing code to promote; the source contract must therefore be established before any
connector, fixture contract or observation shape is added.

## Official source-contract gate

The following must all be verified from current official sources before implementation:

- [x] official institution-universe surfaces
- [x] available REST dataset catalog
- [x] public executive-disclosure surfaces and exact item routes
- [x] institution identifiers exposed by those surfaces
- [x] executive fields and role coverage
- [x] provider disclosure-date/version behavior
- [x] copyright and public-data reuse policy
- [x] current robots policy
- [x] published request-limit behavior
- [x] policy-minimized metadata boundary
- [ ] machine-readable named-executive contract permitted for automated enumeration

### Current official findings

The official establishment-status pages describe two dated universes:

```text
local public enterprises: 423 at 2026-01-01
local invested/contributed institutions: 890 at 2026-06-30
```

The live institution selectors expose source identifiers and current lists:

```text
local public enterprise: entId + entName + entKind
local invested/contributed institution: insttCode + insttNm + entKind
```

The exact public executive item routes returned by the official item selectors are:

```text
2_2_1 / ownerStatus       -> POST /user/empOwnerStatus.do
20_20  / iptSuOwnerStatus -> POST /user/iptSuOwnerStatus.do
```

Both public pages expose named executive metadata such as position, name, term, major career
and selection procedure. They also expose gender/origin and disclosure-staff contacts that are
outside the permitted storage boundary. Neither inspected page exposes a stable executive-
person identifier or an explicit disclosure number/version/as-of timestamp.

The official public-data catalog currently lists 34 REST datasets. It does not list a named
executive-status dataset. The available `openApiOwnerSal` executive-compensation API is an
institution/role aggregate with year, institution name, role counts and compensation values; it
does not expose executive names or person identifiers and cannot satisfy this feeder.

The official copyright/public-data policy permits free use of site-owned works and public data,
including commercial use, subject to protected third-party rights. That permission does not
establish an automated named-executive endpoint. The current official `robots.txt` is:

```text
User-agent: *
Disallow: /
```

No request limit is published for the executive HTML surfaces. The REST catalog documents its
own API limits, but those limits cannot be transferred to the separate HTML routes.

### Storage boundary if the source gate later passes

Permitted normalized metadata would be limited to:

```text
institution lane / identifier / name / official category
executive position / disclosed name / term text
major-career text with reported-by-CleanEye semantics
selection procedure
official disclosure version/as-of only when the provider supplies it
```

Prohibited persistence includes gender, origin, employee rosters, disclosure-staff identities,
phone numbers, addresses, attachments, raw HTML and provider credentials.

Without a provider executive-person ID, any future observation key would remain a disclosure-
row identity only. It must not authorize `AUTO_CREATE`, `AUTO_LINK` or merge. Every CleanEye
observation must enter `REVIEW_REQUIRED`, and name + position + institution must never become
merge authority.

## Milestone A — Source gate

- [x] reread governing repository, batch, DB, identity and ALIO documents
- [x] verify local/remote HEAD and clean baseline
- [x] verify all six existing L3 implementations with current tests
- [x] inspect current official institution and disclosure surfaces
- [x] inspect current official REST dataset catalog and executive-compensation schema
- [x] verify rights, robots and rate-limit statements without borrowing semantics across routes
- [x] record the smallest permitted metadata boundary
- [ ] establish a permitted machine-readable named-executive universe

## Milestone B — Conditional L3 implementation

This milestone may start only after Milestone A's final source gate passes.

- [ ] add one source-specific CleanEye connector
- [ ] preserve separate public-enterprise and invested/contributed contracts where they differ
- [ ] validate complete institution coverage and exact identifiers
- [ ] validate source-provided pagination/cursor, or exact unpaginated coverage when official
- [ ] persist SourceRun/SourceCheckpoint/FeederObservation atomically
- [ ] support partial failure, resume, unchanged rerun and immutable changed observations
- [ ] reject private/contact/raw fields
- [ ] route every identity to REVIEW_REQUIRED with zero automatic Persons
- [ ] avoid a generic crawler or ALIO/CleanEye framework

## Milestone C — Conditional verification and closure

- [ ] targeted connector/enumerator/materialization tests
- [ ] full pytest, Ruff, mypy, quality and web verification
- [ ] Alembic upgrade/downgrade/re-upgrade roundtrip
- [ ] limited live probe only within the official permitted contract
- [ ] clean-v0 audit
- [ ] coherent commit and push
- [ ] update feeder maturity to L3 only when all L3 conditions pass

## Blocked closure evidence

Official finite probes on 2026-08-31 confirmed:

```text
establishment status pages: HTTP 200
local-public-enterprise dated total: 423 at 2026-01-01
invested/contributed dated total: 890 at 2026-06-30

current institution selectors: HTTP 200
public-enterprise selector: 441 unique entId rows
  - 414 rows with a published entKind
  - 27 rows without entKind
invested/contributed selector: 903 unique insttCode rows

item selectors: HTTP 200
2_2_1 -> ownerStatus -> /user/empOwnerStatus.do
20_20 -> iptSuOwnerStatus -> /user/iptSuOwnerStatus.do
one finite executive-page probe per lane: HTTP 200 with named executive rows

REST dataset catalog: 34 datasets; no named-executive-status dataset
openApiOwnerSal: aggregate institution/role compensation only
robots.txt: User-agent: * / Disallow: /
named-executive HTML rate limit: not published
```

The selector totals are not silently equated to the differently dated establishment totals.
The review found no official version/as-of field on the named executive pages and no stable
executive-person identifier. No full live enumeration or persistence run was performed.

Observed local verification after the documentation/maturity change:

```text
six L3 targeted persistent-enumerator regressions plus ALIO staging: 76 passed
full pytest: 257 passed, 4 warnings in 81.35s
ruff check: All checks passed
mypy: Success, 51 source files
packages.verification.quality: passed=true
apps/web lint: PASS
apps/web typecheck: PASS
apps/web tests: 2 passed
apps/web build: PASS
```

`make verify` itself remains runner-unavailable because GNU Make is not installed. Every
underlying Makefile verification command was executed directly. Repository-wide Ruff format
check remains non-passing on 43 pre-existing Python files; this change touches documentation
only.

Migration verification used a new temporary SQLite database:

```text
Alembic heads: 0004 (head)
fresh upgrade -> 0004
downgrade 0004 -> 0003 -> 0002 -> 0001 -> base
re-upgrade -> 0004
tests/test_migrations.py: 1 passed
```

The first migration-test invocation shared the explicit roundtrip `DATABASE_URL`; that runner
environment overrode the test's own temporary URL and caused a `NoSuchTableError`. Removing the
environment override and rerunning independently passed. The earlier full suite had already
passed the same migration test. This was runner contamination, not a schema defect.

Clean-v0 audit:

```text
changed scope: documentation only
new connector/contracts/tests: 0
schema/migration changes: 0
dependency changes: 0
SqlAlchemyRepository class definitions: 1
parallel raw observation/payload stores: 0
generic crawler/framework additions: 0
Person/materialization/publication changes: 0
git diff --check: PASS
```

The conditional implementation and CleanEye-specific targeted tests remain `NOT_RUN` because
the source gate failed. This plan closes as blocked and does not claim L1, L2 or L3.

## Stop condition

L3 may be claimed only when an official permitted named-executive contract supplies a complete
bounded institution universe, exact institution identifiers, executive rows, coverage semantics
and a usable disclosure-time/version contract, and the implementation proves atomic persistence,
resume, idempotency and REVIEW_REQUIRED identity isolation.

If the official catalog still lacks that contract and the only named-executive surfaces remain
disallowed for automated access, close this plan as `BLOCKED` without connector code, without a
guessed endpoint/field and without promoting the maturity beyond L0.

That blocked branch is the observed result. The stop condition is satisfied as a safe source-
contract stop, not as L3 completion.

## Next Best Action

Obtain a published CleanEye named-executive API contract or written provider permission that
defines the complete institution universe, exact executive fields, disclosure version,
pagination/coverage, request limit and storage terms before resuming this feeder.
