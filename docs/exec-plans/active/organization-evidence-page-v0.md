# Organization Evidence page v0

Status: completed — bounded direct-ID public read surface for reviewed organization Claims.

Date: 2026-09-14

## Objective

Render one public, read-only organization record from the existing organization Claim/Evidence
API. The page is the product surface for the reviewed C0908 ALIO Item 12 runtime slice, but it
does not ship the ignored local database or claim that all ALIO institutions are covered.

This plan adds a narrow organization page, not an organization directory, identity resolver or
new financial data model.

## Baseline and boundaries

- `origin/master` and the active worktree start at `a23871fd5011ad40ee003bfb1c23e49ddda4afd1`.
- The API already exposes `GET /organizations/{organization_id}`,
  `GET /organizations/{organization_id}/claims` and the Claim-gated
  `GET /organizations/{organization_id}/money` projection.
- The page accepts an explicit organization UUID route parameter. There is no organization list,
  search endpoint, slug registry, public binding control or automatic `apbaId` resolution.
- The page renders only the current Organization row, current published organization Claims and
  the optional derived MONEY result returned by the existing API. Missing money is an explicit
  `UNKNOWN`/unavailable state, not a fallback to observation-only data.
- Claim cards retain Claim → ClaimEvidence → Source → SourcePolicy context. SourceSnapshot and
  FeederObservation identifiers remain behind audit disclosure, consistent with the person page.
- The local C0908 Organization/Claim rows are runtime proof only. No local database, raw ALIO
  payload, attachment, provider secret or fixture is added to the web bundle.

## Contract

```text
explicit organization UUID
  -> current Organization API read
  -> published organization Claims and exact Evidence
  -> existing source/policy reads
  -> optional Claim-backed derived MONEY view
```

The organization page must not:

- create or bind an Organization;
- enumerate institutions or expose a public organization registry;
- infer a Person, institution head, spending actor, waste, misconduct or performance;
- turn a derived MONEY comparison into a Claim or FACT;
- bypass SourcePolicy, publication validation or existing API routes;
- introduce a schema, migration, generic financial framework, or new raw-payload store.

## Product surface

- Route: `/organizations/[id]`, reachable only when an explicit canonical organization ID is
  supplied.
- Header: organization name, read-only/canonical record context and a clear evidence posture.
- Claims section: annual published organization Claims with FACT/PUBLISHED status, fiscal-year
  context and source-linked Evidence trace.
- Derived section: optional `DERIVED · MONEY` card showing the two compared annual disclosed values,
  arithmetic delta, method version and the existing limitations/correction semantics.
- Source library: source title, publisher, policy summary and audit identifiers from the existing
  source endpoint. Fulltext and attachments are not copied into the page.
- No global navigation link or list is added; the existing public navigation remains person
  directory-only.

## Milestones

### A — Contract and implementation

- [x] record this plan and the explicit-ID/no-enumeration boundary;
- [x] add typed web reads for an organization and its optional MONEY projection;
- [x] implement the organization page with existing components, tokens and read-only semantics;
- [x] render explicit empty/unavailable states without implying a negative fact;
- [x] add deterministic UI regressions for route/data/provenance boundaries.

### B — Verification and delivery

- [x] run web lint, typecheck, UI tests and production build;
- [x] run the full Python and quality verification because the page consumes canonical API
  contracts;
- [x] inspect desktop and narrow responsive page states against `DESIGN.md`;
- [x] run Markdown/link and diff checks;
- [x] update `HANDOFF.md`, commit one coherent slice, push and verify remote equality/clean state.

## Implementation evidence

- Added `apps/web/app/organizations/[id]/page.tsx` as a direct-ID, read-only App Router page.
  It reads the existing organization endpoint, published organization Claims, exact Evidence and
  source-policy details, plus the existing Claim-gated MONEY projection when available.
- Added typed reads and contracts in `apps/web/app/data.ts` and `apps/web/app/types.ts`, and kept
  the UI within the existing warm-surface/status-token system in `apps/web/app/styles.css`.
- Added deterministic UI regressions in `apps/web/tests/ui.test.mjs` for the direct-ID route,
  evidence/provenance rendering and the absence of organization binding or enumeration controls.
- Updated the organization publication contract and documentation index. No API route, database
  table, migration, feeder, provider fetch, raw-payload store or public organization directory was
  added.
- The reviewed local C0908 runtime sample rendered the existing organization
  `정보통신기획평가원`, two published annual Claims, and the Claim-backed derived comparison. The
  page treats missing MONEY as an explicit unavailable state and does not fall back to observations.

## Verification evidence

- Web verification passed: lint, TypeScript typecheck, 7 UI tests and production build. The build
  includes the dynamic route `/organizations/[id]` alongside the existing person and review routes.
- Repository verification passed: full Python suite `321 passed, 4 warnings`; Ruff passed for
  `apps packages workers tests migrations`; mypy passed for 56 source files; Golden quality
  verification returned `passed: true`.
- The local API check returned `200` / `AVAILABLE` for C0908 with two Claims, two Evidence rows,
  a derived delta of `-2,162,000 KRW` and `-14.39%`. This is local runtime evidence, not a
  deployment or coverage claim.
- Direct browser inspection covered desktop and 390px responsive states. The rendered page showed
  the organization, Claim/Evidence/source trace and derived MONEY card; browser error/warning logs
  were empty and the narrow viewport reported no horizontal overflow.
- Markdown relative-link and `git diff --check` verification passed. Next-generated files were
  removed or restored when they were unrelated to the change; the local ignored database and
  provider credentials remain outside the commit.

## Acceptance criteria

1. An explicit organization ID renders current organization claims from the existing API only.
2. Every rendered claim retains its Evidence and source-policy trace; no UI code makes a
   publication decision.
3. The derived MONEY card is visibly distinct from FACT claims and states that it is not a new
   claim about a person, spending propriety or performance.
4. A missing MONEY result renders an explicit unavailable state and never falls back to raw
   observations.
5. No organization list, search, binding action, new API endpoint, migration, provider fetch,
   raw payload or generic financial abstraction is introduced.
6. The page remains keyboard-visible, responsive and consistent with the existing design system;
   internal review navigation remains unadvertised.

## Maturity decision

This page changes no feeder maturity. ALIO Item 12 remains `L2 SINGLE_PULL`; the reviewed C0908
Claim-backed result remains a bounded local runtime slice and not a deployment-wide coverage
claim. The page is a read-only consumer of already published canonical records.

## Next concrete action

Perform a product/deployment review of the direct-ID Organization page against the deployment
database before adding further Organization coverage or identity-binding behavior.
