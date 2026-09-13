# Organization Claim publication v0

Status: completed — in-place subject contract and bounded ALIO Item 12 publication-path proof on
2026-09-14. Live ALIO organization binding and public MONEY projection remain outside this plan.

## Objective

Extend the canonical Claim/Evidence path to support a public record whose subject is an
Organization, while preserving the existing Person path and the evidence-first source boundary.
The slice proves the smallest reusable contract needed for a future descriptive ALIO Item 12
publication; it does not add a generic financial model or make the bounded worker publish claims.

## Baseline and contract

- Baseline `HEAD` and `origin/master`: `0ad72f6331a82fd0b46be232a5945c12ceba30e5`.
- `Claim` requires exactly one subject: `person_id XOR organization_id`.
- Person publication still requires a current `RESOLVED` Person.
- Organization publication requires an existing current canonical `Organization` row supplied by a
  reviewed binding. An ALIO `apbaId`, name or source row never creates that row.
- `ClaimEvidence` and the existing `SourcePolicy → Source → SourceSnapshot → FeederObservation`
  chain are reused. No `OrganizationClaim` table, raw payload store or generic money schema is
  introduced.

## Implementation

- Added nullable `claims.organization_id`, the exclusive-subject database constraint and
  reversible Alembic migration `0005`.
- Extended the shared publication validator and repository with an atomic, existing-row-only
  organization Claim importer. It applies the same policy, source, snapshot and observation
  checks as the Person path.
- Added a source-specific ALIO Item 12 organization Claim builder. It preserves `apbaId` as
  source-scoped qualifier context, requires exact current Organization-name binding and emits a
  descriptive `DISCLOSED_BUSINESS_EXPENSE` proposition only for the official aggregate row.
- Added read-only `GET /organizations/{organization_id}` and
  `GET /organizations/{organization_id}/claims` routes. There is no organization list route and
  no `/money` bypass.
- Added a fail-closed version gate: multiple immutable observation content hashes for one
  source-specific record key cannot be published as one organization Claim.

## Provenance and semantic boundary

The publication path remains:

```text
Claim → ClaimEvidence → FeederObservation → SourceSnapshot → Source → SourcePolicy
```

The ALIO Item 12 worker remains observation-only. The annual aggregate is a statement of what the
institution disclosed; it is not a Person's spending, an accusation, an evaluation of the
institution or a correction interpretation. Family/member materialization, automatic provider-ID
identity, raw report/attachment storage and generic financial abstractions remain prohibited.

## Verification evidence

The targeted regression after the subject/version changes passed:

```text
pytest -o addopts='' tests/test_alio_item12_money.py tests/test_migrations.py tests/test_api.py -q
32 passed, 4 warnings
```

The source-specific test covers the exclusive subject validator, canonical Organization-row
requirement, exact ClaimEvidence provenance, read-only routes, no provider-ID materialization and
ambiguous immutable-version rejection. Full repository and web verification are recorded when the
milestone is closed:

```text
pytest -o addopts='' -q: 314 passed, 4 warnings
ruff check apps packages workers tests migrations: passed
mypy packages workers apps/api: success for 55 source files
packages.verification.quality: passed; all Golden Set checks true
web lint: passed
web typecheck: passed
web test: 5 passed
web build: passed; /, /_not-found, /admin/review and /people/[id] generated
Markdown relative-link check: 57 files, 70 links, 0 broken
git diff --check: passed
```

The migration test exercised upgrade to `0005`, downgrade through the earlier heads and upgrade
back to `0005`. No live ALIO organization Claim was published.

## Maturity decision and not executed

The contract is implemented, but ALIO Item 12 remains `L2 SINGLE_PULL` for the three-institution
bounded observation proof. This plan does not promote the lane to L3, enumerate all 355 directory
institutions, create an organization registry, bind live ALIO IDs, run scheduled sync, store raw
attachments or publish a public MONEY projection. A derived MONEY result remains blocked until it
consumes published annual organization Claims with their Claim IDs and exact provenance.

## Next concrete action

Build a read-only organization MONEY projection whose only inputs are published annual
organization Claims and their exact ClaimEvidence/observation provenance, with ambiguous
observation versions failing closed.
