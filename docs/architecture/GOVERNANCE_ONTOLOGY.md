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

The first executable slice projects only relation predicates already supported by canonical
Person Claims. Later source slices may add more of the vocabulary only after their Claim/Evidence
contracts exist.

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

## Storage and query boundary

V0 uses the existing SQLAlchemy repository and FastAPI read path. Do not add Neo4j, Apache AGE,
OpenSearch, a vector database or another persistence layer without measured traversal/search
evidence that the current architecture cannot satisfy.
