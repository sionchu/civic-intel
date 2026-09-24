# ALIO safe source-context Person materialization

Approved 2026-09-24 by user request to increase actual Person coverage through the canonical parsing route.

Base: `8f11c6095f3bb1505327a59730c716151eef2e73`.

## Goal

Convert the safest subset of already persisted ALIO item-4 current executive observations into
canonical source-context Persons without weakening cross-source identity rules.

Pipeline:

```
official ALIO item-4
-> existing L3 observation/checkpoint
-> deterministic eligibility preflight
-> canonical REVIEW Person + PersonObservationLink + DRAFT ALIO_REVIEWED_PERSON_ROLE Claim/Evidence
-> dashboard source-context identity review
-> explicit human RESOLVE_PERSON
-> separate role-Claim publication approval
```

This slice may create Persons and DRAFT Claims only after dry-run proof and explicit commit command.
It must not auto-publish role Claims, merge Persons, modify immutable observations, recollect ALIO,
or touch the independent org.go27 Organization commit.

## Narrow automatic eligibility

An observation is AUTO_CREATE_SOURCE_CONTEXT only when all are true:

1. exact feeder/scope/semantic scope = current ALIO item-4 contract;
2. `name_status == PUBLIC`;
3. exact latest SUCCESS checkpoint contains the observation provider key and current content hash;
4. provider key has exactly one historical content hash in this canonical DB (no version drift);
5. canonical name appears exactly once in the current successful ALIO universe;
6. no current Person canonical name or alias equals that name;
7. no active PersonObservationLink exists for the provider record identity;
8. exact current ALIO Organization Claim binding resolves to one active canonical Organization whose
   name matches the source institution;
9. Source/Snapshot/SourcePolicy provenance is valid and metadata storage is permitted.

Any failed condition is REVIEW_REQUIRED or HARD_CONFLICT with an explicit reason. Do not silently
exclude ambiguous rows from accounting.

The new Person is created with identity_status=REVIEW, not RESOLVED. Its deterministic ID is
UUIDv5 over a source-specific namespace plus provider record key + immutable content hash.
An operator may later use RESOLVE_PERSON only after the current ALIO row, exact Organization
binding, DRAFT role Claim and Evidence are revalidated. That action resolves this source-context
node; it does not assert equality to a future NEC/OpenDART/other-source record. A changed ALIO row
never AUTO_LINKs to the earlier Person.

## Claim semantics

For each created Person:
- create exactly one active PersonObservationLink with a new source-specific decision class;
- create one `ALIO_REVIEWED_PERSON_ROLE` Claim using the existing ALIO role qualifier/evidence
  semantics;
- keep the Claim `DRAFT`, epistemic `CLAIM`, asserted_as_true=false;
- reuse the exact Source/Snapshot/FeederObservation Evidence;
- no public Person/profile while identity_status remains REVIEW;
- no public `DISCLOSED_ROLE_AT` edge until human RESOLVE_PERSON and the existing publication
  approval later succeed.

## Dry-run / commit contract

Add one dedicated CLI/worker, dry-run by default, operating only on the current successful ALIO
checkpoint. It must emit a deterministic receipt containing:
- current People count;
- eligible create count;
- review/conflict counts grouped by reason;
- exact selected observation IDs/provider keys/content hashes;
- expected post-create Person/Claim/Evidence/link counts;
- write_performed=false;
- source fetch=false;
- claim publication=false.

Commit requires an exact operator-confirmed receipt SHA and explicit `--commit`. Recompute the
whole preflight inside the transaction and fail on drift. One atomic transaction for the entire
selected batch. Idempotent rerun after success must report REUSE/NOOP, not duplicate rows.

## Verification

Before staging write:
- targeted unit/regression tests;
- full repository Verify / GitHub CI;
- SQLite and PostgreSQL disposable atomicity/idempotency/drift tests;
- dry-run twice against staging must be byte-identical;
- backup + post-read counts before commit;
- exact review/conflict accounting must reconcile to 3624 named ALIO rows.

After staging commit:
- post-read Person/Claim/Evidence/link deltas exactly equal committed create count;
- ALIO observation/source/snapshot counts and hashes unchanged;
- published Claim count unchanged;
- admin history remains unrelated (this worker is a deterministic materialization receipt, not a
  human admin action);
- dashboard shows increased canonical People, with new rows counted under
  source-context 신원 확인 필요 rather than 인물 연결 완료;
- public People count remains unchanged through automatic creation and human RESOLVE_PERSON;
- a source-context Person appears publicly only after a separately eligible PUBLISHED Claim;
- remaining repeated/collision rows stay in review rather than disappearing.

## Identity boundary

This rule is source-scoped AUTO_CREATE-to-REVIEW only. It does not authorize:
- name-only AUTO_LINK to existing Persons;
- cross-lane merge;
- assuming repeated ALIO rows are one Person;
- treating distinct name strings as unique human counts;
- auto-publication.

NEC/OpenDART remain credential-blocked on the current host and are separate future routes.
See docs/operations/API_CREDENTIALS.md for the five current acquisition credentials.

## Current baseline evidence

Read-only staging audit before implementation:
- People 299;
- ALIO item-4 observations 3799;
- PUBLIC named ALIO rows 3624;
- distinct name strings 3076;
- singleton current names 2716;
- repeated names 360 covering 908 rows;
- 40 distinct ALIO names collide with an existing current Person name;
- active ALIO PersonObservationLinks 0.

## Current checkpoint — implementation + staging dry-run

The source-specific verifier, atomic repository path, dry-run CLI, source-context REVIEW state,
explicit RESOLVE_PERSON admin action and dashboard accounting are implemented in the isolated
branch. Focused Python/web/mypy checks are passing.

Read-only staging dry-run was executed twice from the exact branch code; both runs were
byte-equivalent:
- current PUBLIC named rows: 3624;
- CREATE-to-REVIEW: 2688;
- REVIEW: 936;
- CONFLICT: 0;
- repeated-current-name review rows: 908;
- existing Person/alias collision review rows: 28;
- expected People 299 -> 2987;
- expected Claims/Evidence +2688, all role Claims DRAFT;
- PUBLISHED Claims stay 5576;
- receipt SHA-256: `96fd337f810592223011d2df02e7a73d4f61b2f919bc219751060b2cdd96a318`.

The earlier aggregate count of 40 colliding distinct names is compatible with the 28 receipt rows:
12 of those names are already classified under the higher-priority repeated-current-name branch.
All 3624 rows reconcile exactly: 2688 + 908 + 28.

## Next concrete action

Finish full regression/PostgreSQL CI and independent diff review, merge the implementation, take a
fresh staging backup and recompute the receipt from merged master. Only if the fresh receipt and
baseline remain exact should the 2688-row atomic commit run. Do not human-resolve or publish any
real Person as a test action.
