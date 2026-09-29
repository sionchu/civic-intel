# Gukgam review throughput receipt v0

Status: COMPLETED 2026-09-30.

Base: `77e2767`.

## Goal

Instrument the existing 41-item Gukgam existing-Organization human-review lane without changing
canonical data, Claim publication or commit authority. The measurement answers how much human work
one review item requires before the project expands coverage.

The review decision remains human. This slice records an append-only private operator receipt only;
it does not convert an APPROVE click into a reviewed Claim manifest or commit authorization.

## Contract

Each receipt is bound to the exact current Gukgam manifest SHA and current DB-derived `review_key`.
The server revalidates the manifest and item before append.

Per item record:

- opened / decided timestamps;
- decision: APPROVE / REJECT / HOLD;
- bounded HOLD reason enum;
- active milliseconds using a five-minute idle cap;
- evidence-link opens for the two evidence paths actually present in this lane:
  canonical Organization and Gukgam schedule observation;
- server-derived Organization occurrence index/count;
- batch-decided flag (v0 single-item UI always false).

The receipt file lives outside the repository/canonical DB and contains IDs/timing/dispositions only;
no source bodies, excerpts, URLs, credentials or free-text notes.

## Acceptance

- no migration, canonical table or Claim/Organization mutation;
- no default decision and no automatic next/commit action;
- stale manifest/review key fails closed;
- append-only receipt retries are idempotent by request ID;
- summary reports median and p90 active time, HOLD reasons, evidence-open rate and first-vs-repeat
  occurrence metrics;
- 41-item metrics are not reused as MOIS-70 estimates;
- current review screen continues to state that item decisions do not authorize Claim commit;
- focused tests, real private browser QA and full `make verify` pass.

## Non-goals

- MOIS 70-item throughput instrumentation;
- reviewed manifest generation;
- Gukgam Claim commit;
- Organization materialization;
- L4 scheduling;
- public analytics or telemetry.

## Closure evidence

- The 41-item existing-Organization lane now records private append-only review receipts outside
  Git, the canonical database and AdminOperationRow. No migration or canonical write path was added.
- Every write revalidates the current DB-derived Gukgam lane, exact manifest SHA and review key;
  stale state fails closed. V0 accepts only one item per decision and retries are idempotent by
  request ID.
- Receipts contain IDs, timestamps, APPROVE/REJECT/HOLD disposition, bounded HOLD reason, active-time
  proxy, evidence-open counters and Organization occurrence position. They omit names, source
  bodies, excerpts, URLs, credentials and free-text notes.
- Read-only Mac PostgreSQL verification returned the exact manifest SHA
  `9bb202c3de7c219382f69c91b8b0014bba7442428b673b55ac7ebbf766e711a9`, 41 items / 27
  Organizations, decided 0 / remaining 41, and did not create a receipt file.
- Real private Mac browser QA started one review, opened the canonical Organization and Gukgam
  schedule observation in separate tabs, kept HOLD disabled until a reason was selected, disabled
  other starts while one review was active, then canceled. The temporary receipt file remained
  absent; no real decision was recorded.
- After the Mac remote tunnel went offline, the exact base `77e2767` branch was reconstructed in a
  clean Windows worktree. Focused Ruff/mypy, six receipt tests, Web typecheck/lint and UI 26/26
  passed there.
- GitHub Verify run `36599415626` passed canonical verification with `652 passed / 3 skipped`,
  mypy over 106 source files, Golden Set PASS, Web 26/26 and standalone production build PASS.
  Alembic round-trip, PostgreSQL migration/load/API, backup/restore, deployment artifacts and the
  installed sync entrypoint also passed.
- No Gukgam Claim commit, reviewed manifest generation, Organization materialization, publication,
  source fetch or operational canonical DB write occurred.
