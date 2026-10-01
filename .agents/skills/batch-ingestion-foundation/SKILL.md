---
name: batch-ingestion-foundation
description: Build and verify source-bounded policy-first batch ingestion using existing canonical workers and persistence.
---

# Batch ingestion foundation

Use this skill for reviewed official/public source lanes that need bounded enumeration,
resumable ingestion, record observations, or safe identity materialization. It specializes but
does not override `AGENTS.md`, `ARCHITECTURE.md`, product/source policy, role documents, or
workflow gates.

Before planning or changing a feeder, read [the detailed invariants reference](references/invariants.md).
It retains the full SourcePolicy, source-rights, provenance, checkpoint atomicity, identity,
publication, ReviewedPersonBundle, testing, prohibition, and promotion rules. The reference is
normative alongside this entrypoint; this summary does not relax any gate.

Then identify the source, bounded public-interest scope, reviewed SourcePolicy, stable provider
key, pagination/checkpoint semantics, permitted normalized fields, semantic destination, identity
hints, and current maturity. Reuse the canonical connector, `IngestionPipeline`, Source,
SourceSnapshot, FeederObservation, contracts, repository, and tests before proposing additions.
Do not introduce a generic batch framework until two concrete source lanes demonstrate the same
need.

A worker may acquire and normalize approved input and request deterministic materialization. It
cannot authorize identity merges or publish Claims. Any L3 promotion requires full bounded
coverage, pagination/coverage validation, checkpoint/resume, idempotency, run receipts, and offline
multi-page regressions; report evidence rather than intention.
