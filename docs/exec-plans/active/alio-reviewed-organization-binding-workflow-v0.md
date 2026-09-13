# ALIO reviewed Organization binding workflow v0

Status: completed on 2026-09-14 — operator-only source-specific Claim import; no public binding
surface.

Date: 2026-09-14

## Objective

Make the approved C0908 Claim-backed Item 12 slice repeatable through one explicit operator
command. The workflow accepts a caller-supplied canonical Organization and an ALIO `apbaId`,
then reuses the existing observation, Claim builder, SourcePolicy and organization Claim importer
to import exactly two selected annual Claims.

This is a reviewed import workflow, not an ALIO identity resolver or an organization registry.

## Baseline and boundaries

- `origin/master` was `12f715b` before this plan's implementation.
- The existing `Organization`, `Claim`, `ClaimEvidence`, `Source`, `SourcePolicy`,
  `SourceSnapshot`, `FeederObservation` and `SqlAlchemyRepository.import_organization_claim()`
  contracts are the only persistence foundation.
- The command reads already committed bounded ALIO Item 12 observations. It does not fetch the
  network, enumerate the directory, download attachments or schedule sync.
- The operator must supply an existing current canonical Organization ID and the exact ALIO
  institution code. The command never creates, resolves or updates an Organization from a name,
  `apbaId` or provider row.
- The command is dry-run by default. A separate explicit commit flag is required to import the
  two Claims. No public API, UI, authentication system or crosswalk table is introduced.

## Contract

The supported input is only:

```text
existing current Organization
 + explicit ALIO institution code
 + one bounded Item 12 scope
 + exactly two distinct fiscal years
 + exactly one immutable observation for each year
 -> existing source-specific Claim builder/importer
```

The workflow fails closed when the Organization is absent/superseded, the institution code or
source name differs, a year is missing/duplicated, an observation version is ambiguous, the
Claim already exists, or any normal SourcePolicy/Claim publication gate fails. It preserves
`Claim → ClaimEvidence → SourceSnapshot → FeederObservation → Source → SourcePolicy` and keeps
the ALIO provider code in source-scoped Claim qualifiers.

## Milestones

### A — Explicit operator command

- [x] Add a source-specific dry-run/commit command under `workers/`.
- [x] Require an existing Organization ID, exact `apbaId`, earlier/later fiscal years and the
  existing bounded scope.
- [x] Preflight both Claims before any write; use the canonical repository importer for each
  committed Claim.
- [x] Emit only bounded result IDs/counts and never credentials, raw report content or contacts.

### B — Regression and local proof

- [x] Prove dry-run does not write.
- [x] Prove missing Organization, binding mismatch and existing Claim
  fail closed before partial import.
- [x] Prove explicit commit preserves the two Claim/Evidence provenance chains and remains
  observation-only with respect to the feeder.
- [x] Re-run the C0908 local route against the imported Claims.

### C — Delivery

- [x] Update the organization Claim and ALIO feeder documentation with the operator boundary.
- [x] Run targeted tests, full constituent verification, diff audit and Markdown link checks.
- [x] Commit and push one coherent milestone with `HEAD == origin/master` and a clean worktree.

## Acceptance criteria

- No Organization row is created by the command.
- Default execution is a no-write dry run.
- Commit mode imports exactly the two requested annual Claims through the shared importer, or
  imports none when preflight fails.
- Both Claims are `PUBLISHED` `FACT` Claims with exact supporting Evidence and immutable
  observation provenance.
- Provider correction/version ambiguity, policy denial and publication failures remain fail-closed.
- No generic financial model, new crosswalk table, raw payload store, network dependency,
  automatic binding, public UI or public organization enumeration is added.

## Implementation

- Added `workers/alio_reviewed_claim_import.py` and the `civic-import-alio-reviewed-claims`
  entry point. It reads the existing bounded Item 12 scope, requires an existing current
  Organization and explicit institution code, builds both Claims before any commit, and uses the
  existing organization Claim importer.
- Default execution is `DRY_RUN`; only `--commit` persists Claims. The command never fetches the
  network and never creates or updates an Organization.
- Added deterministic regression coverage for dry-run no-write behavior, commit provenance,
  missing Organization, source-name binding mismatch and duplicate provider-key rejection.

## Verification evidence

- `tests/test_alio_item12_money.py`: `24 passed, 2 warnings`.
- Full Python suite: `321 passed, 4 warnings`.
- Ruff `apps packages workers tests migrations`: passed.
- mypy `packages workers apps/api`: success for 56 source files.
- Golden quality checks: passed with all checks true.
- Web lint and typecheck passed; web UI tests: `5 passed`; production build passed and generated
  `/`, `/_not-found`, `/admin/review` and `/people/[id]`.
- Markdown check: 60 Markdown files, 74 relative links, 0 broken links. `git diff --check`
  passed.
- Actual local runtime dry run returned `DRY_RUN` for C0908/2021–2022 and left the database at
  one Organization, two Claims, two ClaimEvidence rows and 15 observations. The previously
  imported C0908 2024–2025 route returned `200` / `AVAILABLE` with `-2,162,000 KRW` and `-14.39%`.
- GNU Make is unavailable on this Windows host, so `make verify` was not runnable; every
  constituent verification command was executed directly.

## Maturity decision

The workflow does not change the feeder maturity: ALIO Item 12 remains `L2 SINGLE_PULL`. It is a
repeatable human-approved import lane for already committed observations, not automatic binding,
full-directory Claim publication, scheduled sync or L3 evidence.

## Not in scope

Full ALIO annual-row enumeration, additional institutions without a separate review, scheduled
sync, automatic `apbaId` binding, Organization list/public page, admin approval API, authentication
or claims for assets, votes, contributions or people.

## Next concrete action

Keep the operator command limited to reviewed existing Organization bindings and create a new
execution plan before adding further institution Claims or a public organization page.
