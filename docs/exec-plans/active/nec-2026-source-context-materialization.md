# NEC 2026 source-context Person materialization

Approved 2026-09-25 as the next step after full official NEC candidate enumeration.

Base: `e109bd06a664e2ff4f876db397b2a2ea545ea3c3`.

## Goal

Turn the safest subset of persisted 2026 NEC local-election candidate observations into private
source-context Person REVIEW nodes through the canonical evidence path:

```
NEC candidate API
-> SourcePolicy / Source / Snapshot / FeederObservation / SUCCESS checkpoint
-> deterministic source-context Person(REVIEW)
-> PersonObservationLink(DETERMINISTIC_SOURCE_CONTEXT)
-> DRAFT NEC_LOCAL_ELECTION_CANDIDACY Claim + exact Evidence
-> later human identity review
-> separate publication approval
```

This slice must not auto-link to an existing Person, auto-resolve identity, publish a Claim,
infer political affiliation, infer election outcome, or use the unavailable winner API.

## Covered source scopes

Election: `20260603`

Current supported candidate scopes:
- type 3: 시·도지사
- type 4: 구·시·군의 장
- type 5: 시·도의회의원
- type 6: 구·시·군의회의원
- type 11: 교육감

Type 10 is excluded because the current 2026 provider request fails. Winner collection remains
blocked because the currently issued service key is not registered for that API.

## Automatic CREATE eligibility

A current candidate observation is CREATE only when all are true:

1. feeder = `nec_local_election_candidates`;
2. semantic scope = `local_election_candidacy`;
3. exact scope is one approved 2026 election/type pair;
4. its exact content hash is present in the latest SUCCESS checkpoint manifest;
5. the checkpoint has complete page coverage and stable total;
6. the same provider record in that scope has no historical content-hash drift;
7. `candidate_id`, canonical name, birth date, election id/type and jurisdiction are present;
8. the `huboid` appears in exactly one current covered scope for this election;
9. no active Person canonical name or alias equals the candidate canonical name;
10. no active PersonObservationLink already manages that observation;
11. exact Source/Snapshot/SourcePolicy provenance is valid and metadata storage is permitted.

A failed condition becomes REVIEW or CONFLICT with an explicit reason. Existing names are never
AUTO_LINKed from name or name+birth-date. Cross-source equality remains review-only.

## Deterministic artifacts

Person ID:
UUIDv5 over `election_id | huboid` in a NEC-specific namespace.

Person:
- canonical name from the NEC candidate record;
- exact public birth date when present;
- identity status = `REVIEW`.

Claim:
- predicate = `NEC_LOCAL_ELECTION_CANDIDACY`;
- publication = `DRAFT`;
- epistemic = `CLAIM`;
- asserted_as_true = false;
- qualifiers preserve election id/type, jurisdiction, party/candidate number when present,
  source observation id, immutable observation hash and
  `identity_scope=DETERMINISTIC_NEC_CANDIDACY_SOURCE_CONTEXT`.

Candidate-submitted education/career remains only in the observation and is not promoted to a
canonical career FACT by this worker.

## Dry-run / commit gate

Dry-run is default. Receipt includes every current covered candidate row classified into
CREATE/REVIEW/CONFLICT/NOOP, explicit reason counts, selected artifact IDs/hashes and expected
post-counts.

Commit requires:
- explicit `--commit`;
- exact 64-hex receipt SHA;
- full preflight recomputation inside one transaction;
- advisory/table locks on PostgreSQL;
- atomic write of the complete selected batch;
- no source fetch and no Claim publication.

A rerun after commit must produce CREATE=0 and the prior rows as NOOP.

## Verification before staging commit

- focused Ruff/mypy/pytest;
- disposable SQLite atomicity/idempotency/drift tests;
- full GitHub Verify;
- staging dry-run twice with byte-identical receipt;
- fresh staging backup;
- observation/source/snapshot fingerprints unchanged by materialization;
- published Claim count unchanged;
- public Person roster unchanged.

## Next concrete action

Finish the live candidate enumeration, implement this worker and run staging dry-run. Commit only
after the merged implementation and exact dry-run receipt are verified.

## Verified staging dry-run — 2026-09-25

The five current 2026 candidate scopes completed L3 enumeration:
- type 3: 54;
- type 4: 585;
- type 5: 1,657;
- type 6: 4,402;
- type 11: 58;
- total current candidate observations: 6,756.

Type 5 required one resume after a Railway tunnel disconnect. The final SUCCESS checkpoint covers
all 1,657 rows; the materializer therefore validates resume coverage as prior committed pages plus
the final SUCCESS run records_seen, rather than requiring the resumed run alone to see the full scope.

Two read-only staging materialization dry-runs were byte-identical:
- CREATE: 6,133;
- REVIEW: 623;
- CONFLICT: 0;
- NOOP: 0;
- all 623 review rows are CURRENT_PERSON_OR_ALIAS_COLLISION;
- expected Person count: 2,987 -> 9,120;
- expected Claim/Evidence count: 8,264 -> 14,397;
- expected active PersonObservationLink count: 2,987 -> 9,120;
- published Claim count remains 5,576;
- receipt SHA-256:
  d302b1c5b628d1f14a65d252743266921c23785d2514913f06185a9a0310a220.

The human RESOLVE_PERSON action is extended only for validated NEC source-context links. It
revalidates the current candidate observation/checkpoint and exact DRAFT candidacy Claim/Evidence,
then changes only identity status to RESOLVED. The candidacy Claim remains DRAFT. Public Person
projection requires that exact NEC source-context candidacy Claim to be separately PUBLISHED.
An unrelated published Claim is insufficient.

## Next concrete action

Run the full repository verification and CI for this implementation. After merge, repeat the
read-only staging dry-run on merged master. If the receipt is unchanged, create a fresh backup and
commit exactly the 6,133 CREATE rows atomically. Then verify CREATE=0 / NOOP=6,133 on rerun,
published Claim count unchanged, public Person count unchanged, and source/snapshot/observation
fingerprints unchanged by materialization.
