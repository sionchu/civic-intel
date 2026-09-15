# Organization-Scoped Claim and Evidence

Status: governing contract and bounded ALIO Item 12 implementation proof, including the
Claim-backed read-only projection, on 2026-09-14.

This document defines the smallest extension needed for a public record whose subject is an
organization rather than a Person. It reuses the existing Claim, ClaimEvidence, Source,
SourcePolicy, SourceSnapshot and FeederObservation path. It does not create an
`OrganizationClaim` table, a generic money schema or an automatic organization registry.

## Subject contract

`Claim` has exactly one canonical subject:

```text
person_id       XOR organization_id
```

The existing Person path is unchanged. Person claims still require a current `RESOLVED` Person
at publication time. Organization claims require an existing current canonical `Organization`
row. A provider identifier, organization name or source row does not create that canonical row
automatically.

The database enforces the same exclusive-subject rule as the Pydantic contract. The extension is
an in-place change to `claims`; it is not a parallel claim abstraction. `ClaimEvidence` remains
unchanged and retains the same source and optional observation references.

## ALIO Item 12 application

For the ALIO institution-head business-expense lane:

- `apbaId` remains an ALIO provider/crosswalk identifier, not a canonical Organization ID.
- The Item 12 builder accepts a caller-supplied, reviewed canonical `Organization`.
- The builder requires the current Organization name to match the source institution name and
  retains the `apbaId` in Claim qualifiers as source-scoped context.
- The builder never resolves or creates an Organization from `apbaId`, name, or table position.
- The existing bounded worker continues to create observations only; it never publishes Claims.

An annual direct-disclosure proposition may be represented as a `FACT` only when the official
aggregate row, current Organization binding, SourcePolicy, Source, SourceSnapshot and exact
FeederObservation chain all pass the normal publication gate. Example semantics:

```text
기관 → DISCLOSED_BUSINESS_EXPENSE → 2025 회계연도 기관장 업무추진비 12,861천원
```

This states what the institution disclosed. It does not state who spent the money, that the
amount was wasteful or improper, or that the institution performed well or poorly.

## Provenance and policy gate

Every organization ClaimEvidence item follows:

```text
Claim
 → ClaimEvidence
 → FeederObservation
 → SourceSnapshot
 → Source
 → SourcePolicy
```

When a feeder observation is used, its snapshot must match exactly and the snapshot's source must
match the evidence source. The policy must permit metadata storage. Excerpts remain absent when
the policy denies excerpt display; ALIO Item 12 report HTML, attachments and disclosure staff
contacts are not copied into the claim path.

`SqlAlchemyRepository.import_organization_claim()` accepts only a Claim targeting the supplied
Organization and an existing Organization row. It does not upsert an organization or source.
It validates the evidence chain and the normal Claim publication gate in one transaction. The
reviewed two-year ALIO command uses `import_organization_claim_pair()` so both annual Claims share
one transaction. Exact retries return the stored rows, an exact legacy one-row partial may add only
the missing row, and divergent partial state fails closed. Source-specific deterministic Claim and
Evidence primary keys provide the database uniqueness guard for concurrent equivalent operations.

## Version and temporal semantics

The source-specific Item 12 key remains `disclosureNo:fiscal_year`. If the same key has multiple
immutable observation content hashes, organization Claim publication fails closed. The provider
does not publish an annual-row correction chain, so a changed observation is not automatically
called a correction and no earlier Claim is silently overwritten or superseded.

Current public organization reads filter to `PUBLISHED` and non-superseded Claims:

```text
GET /organizations/{organization_id}
GET /organizations/{organization_id}/claims
GET /organizations/{organization_id}/money?earlier_fiscal_year=2024&later_fiscal_year=2025
```

There is no organization list endpoint and no generic `/money` bypass. The organization MONEY
route is read-only, requires an existing current Organization and returns only when the requested
years can be derived from published annual organization Claims. The bounded worker still creates
observations only; it does not bind ALIO institutions or publish annual Claims. The separate
reviewed importer does publish exactly the operator-selected annual pair after an existing
Organization binding; the C0908 staging smoke is proof of that narrow route, not automatic
organization coverage.

The public web may render an explicit `/organizations/{organization_id}` record page using these
existing reads. That page is a direct-ID read surface only: it does not add organization search or
enumeration, a slug registry, a binding action, or a new publication path. An unavailable derived
MONEY result remains unavailable in the UI and is never replaced with observation-only data.

## Derived MONEY boundary

`money.alio-head-expense-yoy.v1` remains a separate descriptive derived result. The read-only
organization route consumes only current published annual organization Claims, their exact
ClaimEvidence and repository-complete immutable observation versions. It retains both input Claim
IDs and the complete selected observation provenance, and rejects ambiguous versions. It is not a
Claim, does not become a FACT through this projection and cannot be used to infer waste,
corruption, personal spending, causation or peer superiority. When no reviewed annual Claims are
available, the route returns no MONEY result rather than falling back to observations.

## Explicit exclusions

This contract does not authorize:

- automatic `apbaId` to Organization identity resolution;
- Person creation for an institution head or any other disclosure staff member;
- a generic `Expense`, `Transaction`, asset or financial framework;
- publication of raw ALIO report HTML, XLS/XLSX bytes or contact fields;
- organization enumeration, scheduled synchronization or a full 355-institution annual-row claim
  run;
- turning a derived amount change into a Claim or an accusation.

The remaining product gate is therefore narrow: establish reviewed canonical Organization
bindings and publish annual Claims through the existing importer before the route can return live
ALIO MONEY results. No automatic ALIO binding or organization-wide claim run is implied.
