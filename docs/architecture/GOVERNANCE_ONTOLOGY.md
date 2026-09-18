# Governance Ontology read model

## Purpose

Civic Intel needs a user-facing way to explore evidence-backed public-governance connections
without turning co-occurrence, name overlap or private-life data into a relationship claim.

The Governance Ontology is therefore a **read-only projection**, not a second canonical store.

```text
PostgreSQL canonical records
→ Claim / ClaimEvidence / Source / SourcePolicy gate
→ Governance Ontology projection
→ search / local graph / bounded path / timeline
```

PostgreSQL remains the SSOT. This milestone does not add a graph database, schema migration,
parallel identity store or generic relationship table.

## V0 node vocabulary

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

A public `PERSON` node requires a canonical resolved Person. A public `ORGANIZATION` node
requires a canonical Organization. A source-scoped witness row never becomes a Person node by
name alone.

## V0 relation vocabulary

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

These labels describe observable public-record relationships. They do not imply friendship,
faction, influence, motive or private affiliation.

Precise residence, apartment/building overlap and family residence are intentionally absent from
the ontology relation vocabulary.

## Public edge gate

Every public ontology edge must be:

- backed by at least one canonical Claim;
- backed by at least one ClaimEvidence;
- traceable to at least one Source;
- `PublicationStatus.PUBLISHED`;
- `EpistemicStatus.FACT` or an explicitly attributable `CLAIM`;
- bounded by the source-supported valid time when available.

`UNKNOWN`, `ENTITY_UNRESOLVED`, `INFERENCE` and `HYPOTHESIS` do not become V0 public
connection edges.

An ontology edge does not grant permission to merge identities.

## Path semantics

The V0 path query answers:

> 공식 기록상 두 대상 사이 어떤 연결 경로가 있는가?

It does not answer:

> 두 사람이 실제로 친한가?
> 누가 누구에게 영향력을 행사했는가?
> 왜 특정 국감 질문을 했는가?

The path algorithm is deterministic bounded BFS:

- maximum 3 hops;
- maximum 5 shortest paths;
- only eligible published edges;
- optional relation-type filtering;
- bidirectional exploration while preserving each stored edge's semantic direction.

Bidirectional exploration is necessary for paths such as:

```text
Person A → STUDIED_AT → School X ← STUDIED_AT ← Person B
```

The UI must expose each edge's provenance and time range.

## Time semantics

Where both intervals are known, a later projection may distinguish:

- same-period institutional overlap;
- different-period institutional connection;
- unknown overlap.

The existence of the same institution at different times does not prove the people met.

## Graph UX

The public product should remain search-first:

```text
Search
→ center Person / Organization
→ 1-hop local graph
→ relation filter
→ second node
→ bounded shortest path
→ timeline
→ Evidence
```

Do not render the entire canonical universe as an initial graph.

The visual graph must have an equivalent textual relation list for accessibility and auditability.

## Deferred

V0 does not add:

- Neo4j or Apache AGE;
- Elasticsearch/OpenSearch;
- graph centrality as a public ranking;
- community detection as a political/faction label;
- friendship/influence inference;
- residence-based connection inference;
- question-tone or ideology classification.

Those require separate evidence and product contracts.
