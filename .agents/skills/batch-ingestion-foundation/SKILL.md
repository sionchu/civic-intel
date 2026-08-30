# Batch ingestion foundation

Use this skill when moving a reviewed official/public source from single-pull staging toward
persistent full enumeration, adding resumable ingestion, creating record-level observations,
or materializing safe canonical identities from feeder data.

This skill does not override `AGENTS.md`, `ARCHITECTURE.md`, product scope, SourcePolicy, role
documents or workflow gates.

## Goal

Turn a reviewed source lane into this deterministic path:

```text
Source universe
 -> source-specific enumeration
 -> SourcePolicy
 -> Source
 -> SourceSnapshot
 -> FeederObservation
 -> deterministic materialization decision
 -> canonical Person / Claim / ClaimEvidence
 -> existing verification/publication gate
```

The profiler is not part of the mandatory ingestion path.

## Required inputs

Before implementation identify:

- feeder name;
- public-interest person/event scope;
- strongest official source;
- reviewed SourcePolicy;
- source scope key;
- pagination/cursor semantics;
- stable provider record key or a justified deterministic source-derived key;
- policy-permitted normalized fields;
- identity hints;
- semantic destination;
- current feeder maturity L0–L4.

If any item is unknown, research the official source first. Do not guess an API endpoint or
provider field.

## Reuse before adding

Search for and reuse:

- existing connector;
- existing staging record;
- `IngestionPipeline`;
- SourcePolicy;
- Source / SourceSnapshot;
- domain career/event contract;
- existing repository;
- identity evidence types;
- existing tests/fixtures.

Do not create a generic batch framework before two real source lanes demonstrate the same need.

## Source maturity

Use exactly:

```text
L0 RESEARCHED
L1 CONTRACT_STAGED
L2 SINGLE_PULL
L3 FULL_ENUMERATION
L4 PRODUCTION_SYNC
```

L3 requires all of:

- full bounded universe coverage;
- deterministic pagination/cursor;
- coverage validation;
- checkpoint;
- resume;
- idempotent rerun;
- source run receipt;
- offline multi-page regression.

A connector that can call one real page/entity is only L2.

## Source capture rules

`SourceSnapshot` remains the source-level capture.

Never add a second raw payload archive simply for reprocessing.

A `FeederObservation` is record-level and must contain only:

- feeder/scope;
- provider record key;
- SourceSnapshot reference;
- source run reference;
- timestamps required for provenance;
- policy-permitted normalized fields;
- identity hints;
- semantic scope;
- deterministic content hash.

Never persist credentials or provider fields excluded by the source policy/data-minimization
contract.

## Observation identity

Provider identity is not observation version identity.

```text
same provider key + same normalized hash
 -> unchanged / no new observation

same provider key + different normalized hash
 -> new immutable observation
```

Do not update old observations in place.

## Page transaction

For one committed page/scope chunk:

```text
fetch + parse
 -> persist/reuse Source
 -> persist/reuse SourceSnapshot
 -> insert/no-op observations
 -> advance checkpoint
```

The DB write and checkpoint advance must be atomic.

If observation persistence fails, the checkpoint must not move.

## Run receipt

Record:

- run id;
- feeder;
- scope;
- start/finish;
- RUNNING/SUCCESS/PARTIAL/FAILED;
- checkpoint before/after;
- records seen;
- observations created/unchanged;
- redacted error code/summary.

Do not store raw exceptions containing request secrets.

## Identity boundary

Research identity resolution and batch materialization are distinct permissions.

Numeric/fuzzy score is never automatic merge authority.

Materialization actions for this milestone:

```text
AUTO_CREATE
AUTO_LINK
REVIEW_REQUIRED
HARD_CONFLICT
```

Cross-person AUTO_MERGE is not required.

### AUTO_CREATE

Only for a reviewed authoritative public roster when:

- stable unique provider key exists;
- no accepted provider-key link already exists;
- public-interest scope is satisfied;
- no same-name ambiguity or hard conflict requires review.

### AUTO_LINK

A later observation with the exact already-linked provider identity may attach to the same
Person.

### REVIEW_REQUIRED

Use for:

- same name without exact provider link;
- cross-lane identity;
- official career continuity without exact provider identity;
- incomplete identifiers;
- conflicting soft attributes.

### HARD_CONFLICT

Use for exact contradictions such as incompatible exact birth dates or provider identity
invariants.

## Publication boundary

Ingestion/materialization must not directly bypass publication gates.

Preferred flow:

```text
Person
 -> DRAFT FACT
 -> ClaimEvidence with Source/Snapshot/Observation provenance
 -> existing publication validator
 -> PUBLISHED only if gate passes
```

A failed gate rolls back the coherent materialization transaction.

## ReviewedPersonBundle

Keep it for:

- regression;
- manual override;
- exceptional reviewed import;
- complex/contested profile research.

Do not require one bundle per automatically enumerated person.

## Required L3 tests

Every new L3 feeder must prove:

- multi-page/full-scope enumeration;
- complete coverage calculation;
- stable provider record keys;
- unchanged rerun idempotency;
- changed-record immutable version;
- partial failure;
- resume;
- blocked policy before network;
- credentials not persisted;
- disallowed/private fields not persisted;
- migration-backed DB persistence;
- existing single-pull/staging behavior remains valid if still supported.

## Hard prohibitions

- raw search result -> Person;
- name-only merge;
- confidence score -> canonical merge;
- vector similarity -> canonical merge;
- full provider response storage when policy/minimization forbids it;
- checkpoint ahead of committed observation;
- generic crawler as a shortcut for missing API work;
- new shadow career/identity schema when a canonical contract exists;
- source count inflation from duplicate/reprinted origin;
- private-family/residence/contact discovery;
- Temporal/Airflow/Celery/Kafka/Kubernetes added for L3.

## Completion

A feeder is promoted to L3 only when its code, tests, persistence, docs and run/resume
semantics all satisfy the L3 contract.

Report evidence, not intention.
