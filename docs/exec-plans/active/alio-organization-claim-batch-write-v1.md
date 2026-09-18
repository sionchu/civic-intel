# Civic Intel — ALIO Organization Claim Batch-Write v1

Status: ACTIVE — repository batch-write refactor and local verification PASS; disposable proof
pending. Live staging `--commit` is explicitly prohibited in this plan.

## Objective and boundary

Remove the per-Organization, per-Claim and per-Evidence database round trips from
`SqlAlchemyRepository.import_organization_claim_batch()` while preserving the existing atomic
`Organization → Claim → ClaimEvidence → Source → SourcePolicy` publication contract.

This milestone is a write-path proof only. It does not change ALIO acquisition, the schema,
Claim/Evidence contracts, API/Web behavior, Railway serving resources or Person materialization.
The first ALIO Organization Claim publication to live staging remains a separate, explicitly
approved operation.

## Baseline

- Repository and `origin/master`: `a9b50ea980e1987d7a7e51ef9c31ee9695625d7f`.
- Prior Verify run: `35309878272` — SUCCESS.
- Schema: `0006`; live staging People `299`, Organizations `1`, Claims `1496`,
  ClaimEvidence `1496`.
- Complete ALIO item-4 state: `3799` observations, one checkpoint and successful run
  `e57f88d4-953b-4de5-bf1c-13fa4b3e43db`.
- Prior bounded dry-run: `346` Organizations, `3970` Claims, `3624` named rows and `174`
  masked/vacant rows. It produced no Organization Claim write in staging.

## Existing bottleneck

The batch path currently reads each Organization separately, invokes the full database-loading
validator for every Claim/Evidence packet, checks each requested Claim/Evidence ID separately,
loads Evidence separately for each matching Claim, queries immutable observation versions per
Evidence, flushes each new Claim and then re-reads the newly created Claim. That shape is safe
for the old one- or two-Claim reviewed paths but is not bounded for the real ALIO batch.

## Implementation contract

1. Keep the current semantic validator as the single source of truth for subject, publication,
   policy, provenance, snapshot/observation consistency and immutable-version checks. Split its
   database loading from semantic validation so single, pair and batch paths share the checks.
2. Preload requested Organization IDs and names in bounded queries. Reuse an exact current ID
   only when name and current state match. Reject a current same-name row for a new ID and reject
   duplicate names among incoming new Organizations without adding a uniqueness constraint.
3. Keep the existing source key
   `(organization_id, predicate, source_contract, provider_record_key)` and cross-Organization
   ownership checks. Load current Organization Claims once, all matching Claim Evidence in
   bounded reads, and all requested Claim/Evidence IDs before validation.
4. Load unique Source, SourcePolicy, SourceSnapshot and FeederObservation records in bounded
   sets. Group immutable-version reads by `(feeder, scope_key)` and bounded provider-key chunks;
   any referenced key with multiple content hashes fails closed.
5. Stage all approved new Organization, Claim and ClaimEvidence rows in one transaction. Permit
   at most one Organization-stage flush and one final flush/commit; never flush per Claim or
   re-read a newly staged Claim. Integrity/operational failures roll back the complete batch and
   retain the current redacted error category.
6. Keep deterministic IDs, exact semantic idempotency, all collision errors, the publication
   gate, Person isolation and the existing single/pair import behavior.

The bounded `IN` chunk size remains private to persistence. No raw SQL, database-specific JSON
query, cache, generic orchestration framework or second raw truth store is introduced.

## Verification contract

- Add query-shape regression using the existing ALIO activation fixture and a materially scaled
  equivalent batch. Assert a bounded SELECT shape rather than timing; verify there is no
  per-Claim flush/read-back pattern.
- Preserve or extend regressions for first commit, idempotent rerun, exact Organization reuse,
  same-name and duplicate-input rejection, source-key ownership, Claim/Evidence collisions,
  missing Source/Policy, policy denial, snapshot/source and observation/snapshot mismatch,
  immutable multi-version conflict, late atomic rollback and unchanged Person count.
- Run targeted ALIO tests, full Python tests, Ruff, mypy, Golden quality, Web checks/build,
  markdown link validation and `git diff --check`. No Alembic round trip is required because
  schema `0006` is unchanged.
- After code and CI pass, use exactly one private disposable restore boundary. Do not reacquire
  ALIO and do not write live staging. On the restored copy, run the real `3970`-Claim commit and
  the exact same command again within the bounded operational budget; verify canonical counts,
  evidence/provenance, subject XOR, C0908 Item-12 stability, no Person/raw payload leakage and
  the disposable API read path. Destroy the boundary and confirm no live staging delta.

## Acceptance and closure

Use `ALIO_ORGANIZATION_BATCH_WRITE_PROOF — PASS` only when code, CI, first disposable commit,
second idempotent disposable commit, disposable API acceptance and cleanup all pass. If the
disposable proof fails or exceeds its budget, remain fail-closed and record the exact blocker;
never compensate with a live staging commit.

## Implementation evidence

- Added one shared `_validate_organization_claim_semantics()` seam. The single-Claim and pair
  paths still load their small contexts through the same semantic checks; the batch path loads
  all provenance and immutable-version state before validation.
- Batch Organization IDs/names, Claim IDs, Evidence IDs, matching Claim Evidence, Source,
  SourcePolicy, Snapshot and Observation rows now use private 500-ID chunks. Immutable versions
  are loaded by feeder/scope group and provider-key chunks. New Claims/Evidence are staged
  without per-Claim flush or read-back; only the optional Organization-stage flush and one final
  flush/commit remain.
- Added query-shape coverage with a 600-Claim/120-Organization scaled fixture, plus duplicate
  input, exact collision and cross-Organization ownership regressions. The scaled SELECT count
  stayed within the fixed chunk/group allowance rather than growing with Claim count.
- Local verification passed: targeted ALIO activation and Item-12 tests; full pytest `368 passed,
  1 skipped`; Ruff; mypy (`63` source files); Golden quality; Web lint/typecheck/UI (`11 passed`);
  standalone production build; Markdown check (`80` files, `95` relative links, `0` broken); and
  `git diff --check`. No schema, dependency, acquisition, API/Web or Railway change was made.

The code/fixture proof is not the real-scale acceptance. The remaining gate is a fresh private
disposable restore with the real ALIO observations, first commit, exact idempotent rerun,
disposable API reads and cleanup. No staging write is allowed before that gate passes.

## Next concrete action

Implement the shared semantic-validation seam and bounded repository preload helpers, then add
the query-shape and collision regressions before running the full verification matrix.
