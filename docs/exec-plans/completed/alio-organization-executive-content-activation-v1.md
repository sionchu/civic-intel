# ALIO Organization & Executive Content Activation v1

Status: complete — implementation and verification closed on 2026-09-18.

## Objective

Make the existing ALIO item-4 current executive disclosure lane discoverable as
evidence-backed Organization content. Reuse the canonical
`SourcePolicy → Source → SourceSnapshot → FeederObservation → Organization → Claim/Evidence`
path. This plan does not create Persons from ALIO executive names, add a new feeder, change the
Assembly lane, or introduce a generic organization identity framework.

## Baseline

- `origin/master`: `fabe85d6bd87c60a47ef506b4bd968ade48f8c12`.
- Existing item-4 L3 contract: unfiltered provider directory, one provider-ranked current
  disclosure per `apbaId`, explicit no-current and correction-only outcomes, minimized
  immutable observations.
- Existing local contract evidence: 355 institutions, 347 current disclosures, 8 no-current
  outcomes, 3,624 named rows, 173 masked/vacant rows and a correction-only observation.
- Existing `Organization` has only canonical `id` and `name`; no provider binding column or
  migration is justified.
- Existing organization Claim import requires a current caller-supplied Organization. Existing
  C0908 Item-12 reviewed binding and Claim-backed MONEY behavior remain unchanged.
- Existing API exposes direct organization detail/claims/money routes; no public organization
  list route or ALIO executive content projection exists.
- Baseline targeted regression: `68 passed, 2 warnings` for ALIO item-4, ALIO Item-12 and API
  tests.
- Staging activation, live acquisition, Railway changes and database writes are outside this
  implementation milestone.

## Contract decisions

### Organization identity

`apbaId` is an ALIO provider identity. A fixed UUID namespace plus exact `apbaId` may provide a
source-specific deterministic Organization id without changing the schema. An existing exact
ALIO binding is reusable only when a current published organization Claim carries the exact
`alio_apba_id`; a same-name row without that proof fails closed. Names never authorize reuse.
Masked/vacant and correction-only observations never create a named Person or a named executive
Claim.

### Executive content

Named item-4 observations produce organization-scoped published Claims that state what ALIO
disclosed about the institution's executive seat. They do not assert an independent Person fact.
Qualifiers retain the source contract, scope, semantic scope, `alio_apba_id`, provider row key,
immutable observation hash, disclosure number, role/title, dates and as-of date as strings.
Every ClaimEvidence points to the exact observation and snapshot, with `SUPPORT` and no excerpt.
Classification, if published, is one institution-level Claim per organization, not an executive
attribute. Masked/vacant, no-current and correction-only outcomes remain explicit non-content
coverage states.

The same `(organization, predicate, source contract, provider record key)` cannot silently move
to a different immutable observation version. A changed version is a preflight conflict until a
separate replacement decision exists; two simultaneous current Claims for one logical source row
are never published.

### Operator path

Add a source-specific `workers/alio_current_executive_claim_import.py` command. It reads only a
latest successful complete item-4 checkpoint/run and already committed observations; it never
fetches ALIO. Dry-run is the default and `--commit` is explicit. Global validation completes
before one atomic repository transaction. The receipt is bounded and contains no raw payload,
HTML, contacts or secrets. Person count must remain unchanged.

### Public read path

Add the smallest canonical `GET /organizations` list over current canonical Organizations with
published ALIO content, deterministic ordering and no observation payload. Extend the existing
organization page to show current executive Claims, source/evidence trace, classification where
published, existing Claim-backed Item-12 MONEY where available, and compact coverage states.
Add a directory link without creating a parallel organization model or page abstraction.

## Milestones

- [x] A — Define source-specific ALIO organization binding and executive Claim builders; validate
  observation/snapshot/source/policy provenance and immutable-version preconditions.
- [x] B — Add one atomic repository batch seam that can create/reuse exact Organizations and
  import/recover exact organization Claim/Evidence rows; preserve existing Item-12 behavior.
- [x] C — Implement dry-run/default and explicit-commit operator import with bounded receipts and
  complete-checkpoint preflight.
- [x] D — Add public organization list/detail executive projection and minimal navigation/UI.
- [x] E — Add deterministic, privacy, policy, provenance, idempotency/version, rollback and
  Assembly/Item-12 regression coverage.
- [x] F — Run full Python/Ruff/mypy/quality/web verification, inspect the final diff, update
  governing docs/HANDOFF, commit and push. No staging activation in this plan.

## Required regression matrix

- exact `apbaId` deterministic id, exact existing binding reuse, same-name rejection and malformed
  or conflicting identity fail-closed behavior;
- named row to one Organization Claim/Evidence with exact source/snapshot/observation path;
- masked/vacant, no-current and correction-only rows produce no named Claim or Person;
- exact rerun is idempotent, changed observation version is not silently overwritten, and the
  complete operation is atomic;
- source-policy/provenance mismatch, fulltext/contact/raw HTML leakage and invalid checkpoint
  fail closed;
- public list/detail return only canonical current published content, show executive grouping and
  never expose `FeederObservation.normalized`;
- existing C0908 Item-12 MONEY, Assembly identity/same-name and all existing regressions remain
  green; no ranking, score, influence or political label is introduced.

## Evidence log

- Baseline: isolated worktree started at `fabe85d6bd87c60a47ef506b4bd968ade48f8c12`, which
  matched `origin/master`; the root checkout and other worktrees were not modified.
- Added source-specific builders and an operator command. The command is dry-run by default,
  reads only a successful complete committed item-4 checkpoint, stores no raw report/fulltext or
  contacts, and uses a single repository transaction for Organization plus Claim/Evidence writes.
  `--commit` is the only write mode; no live ALIO request was made.
- The exact fixture-backed activation regression passed: `8 passed`. It covered dry-run/commit,
  five claims across two organizations, exact ALIO binding reuse, same-name rejection, masked and
  no-current rows, correction-only exclusion, immutable-version conflict, atomic rollback and
  policy denial. No Person was created and public detail omitted normalized payload/contact data.
- Existing ALIO item-4, Item-12 MONEY and API regressions passed after the route assertion update;
  the full Python suite exited `0` with the existing PostgreSQL-only skip. Ruff passed for
  `apps packages workers tests`; mypy passed for `packages workers apps/api` with 63 source files;
  Golden quality checks passed.
- Web lint, typecheck, UI tests (`11 passed`), production `next build` and standalone contract
  check passed. The build included `/organizations` and `/organizations/[id]`; no schema,
  dependency or Railway/staging operation was performed.
- Governing source/organization documents, INDEX and HANDOFF were updated minimally. `git
  diff --check` passed. Commit `2a34791bebb2c76830bb197d61315792d6f820bf` is on `master`;
  GitHub Actions Verify run `35245137821` passed.

The closure records a source-specific, operator-run Organization content lane. The next action is
one reviewed cross-lane Person-linking path using exact non-name identity evidence; do not infer
that link from an ALIO executive name.
