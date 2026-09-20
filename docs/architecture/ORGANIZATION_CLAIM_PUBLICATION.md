# Organization-Scoped Claim and Evidence

Status: governing contract and bounded ALIO Item 12 plus item-4 implementation proof, including
the Claim-backed read-only projections, on 2026-09-18.

This document defines the smallest extension needed for a public record whose subject is an
organization rather than a Person. It reuses the existing Claim, ClaimEvidence, Source,
SourcePolicy, SourceSnapshot and FeederObservation path. It does not create an
`OrganizationClaim` table, a generic money schema or a generic organization registry. A
source-specific importer may make a bounded deterministic Organization decision only when its
own reviewed provider identity contract authorizes it.

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

For the separate ALIO item 4 current-executive lane, the reviewed operator command may use a fixed
UUID namespace plus the exact provider `apbaId` as a source-specific Organization key. It may
reuse an existing row only through an exact current published ALIO item-4 Claim carrying the same
`alio_apba_id`; a same-name row without that binding fails closed. This exception is not a
general provider-ID resolver and never materializes an executive name as a Person. The command
reads a successful complete item-4 checkpoint and already committed observations, then publishes
institution classification and named executive disclosure Claims with exact snapshot and
observation Evidence. Masked/vacant, no-current and correction-only outcomes do not create named
Claims.

An annual direct-disclosure proposition may be represented as a `FACT` only when the official
aggregate row, current Organization binding, SourcePolicy, Source, SourceSnapshot and exact
FeederObservation chain all pass the normal publication gate. Example semantics:

```text
기관 → DISCLOSED_BUSINESS_EXPENSE → 2025 회계연도 기관장 업무추진비 12,861천원
```

This states what the institution disclosed. It does not state who spent the money, that the
amount was wasteful or improper, or that the institution performed well or poorly.

## Gukgam reviewed-plan application

The reviewed 2026 National Assembly audit-plan lane reuses this same Organization Claim/Evidence
contract without creating a Gukgam-specific Claim table or Organization crosswalk.

A reviewed operator command may publish one Claim only after the caller supplies an existing
current canonical Organization ID and one exact audited-target occurrence `review_key`. The
source-specific preflight must still resolve that occurrence to exactly one current exact-name
candidate and must recover the exact reviewed plan observation/snapshot/source provenance.

The predicate is:

`LISTED_AS_GUKGAM_AUDIT_TARGET`

The Claim asserts only that the official plan lists the Organization as a target on the printed
audit schedule. It does **not** assert that an audit occurred or completed, nor any wrongdoing,
responsibility, performance judgment or outcome. The plan publication date anchors valid time;
the planned audit date/time/venue are qualifiers.

The operator command is dry-run by default. `--commit` may persist one deterministic
Claim/Evidence pair through `SqlAlchemyRepository.import_organization_claim()`; it never creates
or updates an Organization. The target-level `review_key` is retained as
`qualifiers.provider_record_key`, while the original schedule-row key remains separately recorded.
Exact retries may reuse only semantically identical stored Claim/Evidence. Multiple immutable
observation versions, a changed Organization binding or conflicting stored semantics fail closed.

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
GET /organizations
```

The organization list is a read-only projection of current canonical Organizations with at least
one eligible published Claim; it is not an enumeration or binding command. There is no generic
`/money` bypass. The organization MONEY route is read-only, requires an existing current
Organization and returns only when the requested years can be derived from published annual
organization Claims. The bounded Item 12 worker still creates observations only and the reviewed
Item 12 importer still requires an existing Organization binding. The separate item 4 importer is
the source-specific exception described above; its organization directory and executive Claims
are not an Item 12 binding or an automatic Person path.

The public web may render the read-only `/organizations` directory and an explicit
`/organizations/{organization_id}` record page using these existing reads. The directory is a
projection of already published content, not an organization binding or collection action; the
detail page does not add a slug registry, binding action or new publication path. An unavailable
derived MONEY result remains unavailable in the UI and is never replaced with observation-only
data.

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

- generic or cross-source `apbaId` to Organization identity resolution;
- Person creation for an institution head or any other disclosure staff member;
- a generic `Expense`, `Transaction`, asset or financial framework;
- publication of raw ALIO report HTML, XLS/XLSX bytes or contact fields;
- generic organization enumeration, scheduled synchronization or a full 355-institution annual-row
  Claim run;
- turning a derived amount change into a Claim or an accusation.

The remaining Item 12 product gate is therefore narrow: establish reviewed canonical Organization
bindings and publish annual Claims through the existing importer before the route can return live
ALIO MONEY results. The item 4 operator path does not change that gate, create a generic binding
framework or imply an organization-wide scheduled claim run.
