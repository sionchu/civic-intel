# Governance Ontology Projection

## Purpose

Civic Intel projects already-public canonical evidence into a typed, read-only graph for
exploration. PostgreSQL remains the canonical source of truth. The ontology is not a second
identity store, a graph database, or a publication bypass.

## Projection boundary

The dependency remains:

```text
Person / Organization
 + current published Claim
 + ClaimEvidence
 + Source / SourcePolicy
 -> Governance Ontology projection
 -> API / Web explorer
```

Every public edge must retain the canonical Claim and Evidence identifiers that support it.
Unsupported or untraceable relations are omitted rather than inferred.

## V0 node kinds

```text
PERSON
ORGANIZATION
EDUCATIONAL_INSTITUTION
COMPANY
COMMITTEE
OFFICE
HEARING
ISSUE
```

Only canonical People and Organizations reuse canonical IDs. A projection-only target such as a
role label is scoped to the supporting Claim and is not a reusable identity record.

## Source-listed role-holder nodes

Organization graphs may project a published ALIO executive disclosure as
`SOURCE_LISTED_ROLE_HOLDER`. This is a Claim-scoped record node, not a canonical Person:

```text
canonical Organization
→ LISTS_EXECUTIVE
→ SOURCE_LISTED_ROLE_HOLDER (Claim-scoped, canonical_id = null)
```

Two rows with the same displayed name remain distinct unless the separate identity-resolution
pipeline establishes a reviewed bridge. The ontology projection itself never links these nodes to
Person profiles.

## V0 relation kinds

```text
HELD_ROLE
WORKED_AT
STUDIED_AT
SERVED_ON
DIRECTOR_OF
APPOINTED_TO
APPEARED_AT
QUESTIONED
AUDITED_BY
```

The executable Person projection maps canonical `HELD_ROLE` to a Claim-scoped `OFFICE`
target and the exact current-roster `ASSEMBLY_COMMITTEES` Claim to a Claim-scoped
`COMMITTEE` target. Committee display text is preserved exactly as the provider-supported Claim;
it is not split, normalized into a shared committee identity, or used for cross-Person paths.

The wider vocabulary is reserved for later source slices and becomes executable only after each
exact predicate and target-identity contract exists.

Appointment, election, nomination and designation events are not rewritten as `HELD_ROLE`.

A nomination or designation event is not rewritten as `HELD_ROLE`. The v0 mapping omits
`NOMINATED_AS` and `DESIGNATED_AS` until an exact event relation is modeled.

## Public edge gate

A v0 public ontology edge is created only from a current `PUBLISHED` Claim whose epistemic
status is `FACT` or attributable `CLAIM`, with non-empty ClaimEvidence and Source provenance.

`UNKNOWN`, `ENTITY_UNRESOLVED`, `INFERENCE` and `HYPOTHESIS` remain visible through their
normal evidence/profile surfaces when eligible, but they do not become public connection edges.

If supporting and refuting ClaimEvidence are both present, the projection retains
`source_conflict=true`; the graph must not hide that disagreement.

## Identity and relationship rules

- Name overlap may reduce a research candidate universe but never creates an ontology identity edge.
- A research-level cross-lane RESOLVED decision does not authorize a canonical Person merge.
- Shared school, employer, committee or other institution means only a source-backed institutional
  overlap. It does not establish friendship, faction, influence or motive.
- Precise residence, apartment/building overlap and private-family discovery are excluded.
- Political or ideological proximity is not a FACT edge.

## Time

Temporal relations preserve canonical valid time where the supporting Claim provides it.
A shared institution in different periods is not rendered as a same-period overlap.

## Public exploration

The public experience should be search-first:

```text
Search
 -> local one-hop graph
 -> relation filter
 -> bounded path
 -> timeline
 -> Evidence / Source
```

The graph is supplemental. Equivalent textual relation lists remain available for accessibility.

The v0 Person route currently uses Claim-scoped noncanonical targets. Therefore cross-Person path
search is deliberately deferred: two Claim-scoped nodes with the same label must not be merged by
string equality. Path search becomes eligible only after the corresponding shared institution or
event has an exact canonical/source-scoped binding contract.

## Storage and query boundary

V0 uses the existing SQLAlchemy repository and FastAPI read path. Do not add Neo4j, Apache AGE,
OpenSearch, a vector database or another persistence layer without measured traversal/search
evidence that the current architecture cannot satisfy.


## Reviewed ALIO Person–Organization roles

The admin-reviewed `ALIO_REVIEWED_PERSON_ROLE` predicate can project `DISCLOSED_ROLE_AT` only after
its Claim is published and passes the existing publication gate. Both endpoints use exact current
canonical IDs. The read query additionally requires the original observation hash and an active
stored PersonObservationLink. Named source-listed role-holder nodes remain noncanonical records;
review candidates, drafts, withheld records and same-name lookalikes do not become these edges.
Generic correction drafts do not silently inherit this source-specific relation predicate.
