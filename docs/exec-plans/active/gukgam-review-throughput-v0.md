# Gukgam review throughput receipt v0

Status: IN PROGRESS.

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
