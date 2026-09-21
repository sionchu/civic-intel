# ALIO Organization Importer Batch-Read Fix v1

Status: COMPLETE — ALIO_ORGANIZATION_IMPORTER_DRY_RUN — PASS (2026-09-18).

## Objective and boundary

Make the existing no-commit ALIO Organization importer resolve the current item-4 checkpoint
with one scope-wide observation read instead of thousands of provider-key reads. This is a
performance and query-shape fix only.

Do not reacquire ALIO data, run `--commit`, publish Organization Claims, change the schema,
change the public API/Web surface, change Railway configuration, or modify historical SourceRun
rows. Preserve the existing:

```text
SourcePolicy → Source → SourceSnapshot → FeederObservation → Organization → Claim → ClaimEvidence
```

The staging operational acceptance budget for the later no-commit gate is `180s`; that is not a
CI wall-clock assertion.

## Baseline

- Repository baseline: `c20133bb0cc90daf6307b19ba4294f027940039c`.
- GitHub Verify `35305638333` passed for that baseline.
- Existing staging evidence: schema `0006`, People `299`, Organizations `1`, Claims `1496`,
  ClaimEvidence `1496`, C0908 Item-12 `5` observations / `2` Claims.
- ALIO item-4 has successful run `e57f88d4-953b-4de5-bf1c-13fa4b3e43db`, checkpoint `355/355`,
  `3799` persisted observations and `3798` successful-run unique records. One earlier incomplete
  operational run remains in history and is not deleted, rewritten or used as importer input.
- The previous Sandbox dry-run was stopped after about `2408s` without a JSON receipt or any
  `--commit`; the post-timeout canonical Organization/Person/Claim counts were unchanged.

## Verified N+1 path

Before this fix, `prepare_import()` called `_current_observations()`, which called
`repository.feeder_observations(..., provider_record_key)` once per checkpoint provider key.
It then repeated the same provider-key read for every selected observation to check immutable
versions before the one batched provenance read. The 3,798-row staging manifest therefore
created approximately 7,596 sequential observation reads.

## Implementation contract

- Load the complete bounded ALIO feeder/scope observation set once through the existing
  `feeder_observations(feeder, scope_key)` seam.
- Index persisted versions in memory by `provider_record_key`.
- Resolve only keys present in the successful checkpoint manifest and require exactly one match
  for each expected content hash. Extra persisted keys remain outside the publishable set.
- Reject duplicate matching rows with the existing manifest-resolution error.
- Reject more than one distinct content hash for a provider key with the existing immutable
  observation-version error. Never silently select a latest row or delete an old version.
- Keep the existing batched `feeder_observation_contexts()` provenance read and all source-policy,
  identity, missingness, correction-only and organization binding checks unchanged.

## Verification gates

1. Add a direct regression proving one scope-wide observation read and zero provider-key reads.
2. Keep dry-run no-write, explicit local commit, idempotency, exact binding/same-name rejection,
   masked/vacant, no-current, correction-only, immutable-version, rollback and policy-denial
   regressions green.
3. Run targeted ALIO tests, then the repository Python/Ruff/mypy/Golden/Web checks and
   `git diff --check`. No Alembic round trip is needed because no schema changes.
4. Commit/push and require GitHub Verify success with `HEAD == origin/master` and a clean
   worktree.
5. Only after code/CI pass, take a fresh disposable logical backup/restore and run the updated
   staging importer without `--commit` for at most `180s`. Require a redacted `DRY_RUN` receipt;
   otherwise terminate and remain fail-closed. Verify all staging counts and the item-4
   observation/checkpoint are unchanged, then destroy the execution boundary.

The staging publication path and known per-Organization/per-Claim batch-write scaling issue are
out of scope. Even after a successful dry-run, stop before `--commit`.

## Implementation and local verification

- `_current_observations()` now performs one scope-wide
  `feeder_observations(ALIO_EXECUTIVE_FEEDER, ALIO_EXECUTIVE_SCOPE)` read, indexes all persisted
  immutable versions by provider record key, and selects only the exact successful checkpoint
  manifest entries.
- The repeated provider-key loop was removed. Missing/duplicate manifest matches still use the
  existing manifest-resolution failure, and multiple distinct content hashes still fail with the
  existing immutable-version failure.
- The direct query-shape regression proves one scope-wide read and zero provider-key reads.
- Targeted ALIO tests passed: `15 passed`.
- Full local verification passed: `368 passed, 1 skipped, 4 warnings`; Ruff passed, mypy passed
  for `63` source files, Golden quality passed, Web lint/typecheck passed, all `11` Web UI tests
  passed, and the standalone production build passed.
- No schema, dependency, API, Web, Railway or acquisition change was made. The staging gate was
  executed only after CI passed and no `--commit` was executed.

## Staging no-commit gate

Passed once after the code commit and GitHub Verify success.

- Fresh logical backup/restore passed in one new private Sandbox before the importer gate. Dump
  size was `1290509` bytes, SHA-256 was
  `6b4c86132ae627354c82b527b56f5fa790fbc4987f585ed69f3837eee3643a9b`, dump duration was `20s`,
  and loopback restore duration was `0s`. Restore checks matched schema `0006`, People `299`,
  Organizations `1`, Claims `1496`, ClaimEvidence `1496`, subject-XOR violations `0`, item-4
  observations `3799`, and C0908 item-12 `5` observations / `2` Claims.
- The updated importer ran exactly once without `--commit` under the `180s` operational budget.
  It exited `0` in `17s` and returned a redacted `DRY_RUN` receipt:
  - source `alio_public_institution_executives`
  - scope `item_4_current_all_institutions`
  - run `e57f88d4-953b-4de5-bf1c-13fa4b3e43db`
  - `observed_count=3798`
  - `named_rows=3624`
  - `masked_or_vacant_rows=174`
  - `organizations=346`
  - `claims=3970`
  - `organizations_created=346`
  - `organizations_reused=0`
  - `claims_created=0`
  - `claims_reused=0`
- Post-run read-only checks remained schema `0006`, People `299`, Organizations `1`, Claims
  `1496`, ClaimEvidence `1496`, item-4 observations `3799`, checkpoint count `1`, successful
  item-4 run count `1`, and C0908 item-12 `5` observations / `2` Claims. No Organization Claim,
  Person, Claim or ClaimEvidence write occurred.
- Sandbox `bf3adb1f-eac7-4841-a3ca-401b613cdba2` in `us-west2` was destroyed by exact ID;
  final Sandbox list was `[]`. No acquisition rerun, API/Web deployment, Railway topology
  change or public acceptance was performed.

## Closure marker

Use `ALIO_ORGANIZATION_IMPORTER_DRY_RUN — PASS` only after the code, CI, bounded staging
dry-run receipt, zero-write count checks and Sandbox cleanup all pass.

This plan satisfies that marker. The separate batch-write path remains unapproved and unrun.

## Next concrete action

Profile and remove the known per-Organization/per-Claim database round trips in
`SqlAlchemyRepository.import_organization_claim_batch()` before any staging `--commit`.
