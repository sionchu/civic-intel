# National Assembly Roll-Call Votes L3 Sign-off v0

Status: COMPLETE — 22nd-Assembly roll-call lane promoted to L3 after final-contract convergence, full-universe unchanged rerun, resume proof and request-limit observation.

## Objective

Close the two evidence gaps that still keep the 22nd-Assembly plenary roll-call lane at L2:

1. live idempotent full-term rerun under the final normalized contract;
2. live request-limit behavior observation without exposing the API key.

No publication, Person materialization, ideology scoring, vote-alignment analysis, or schema change is
in scope.

## Baseline already proven

Existing keyed 2026-10-05 disposable run:

- universe: 1,911 / 1,911 voted bills;
- member-vote observations: 568,649;
- run status: SUCCESS;
- tally exception: one bill
  `PRC_G2Z5L1L1C2F1O1S6A0I6O4J4T5B8G3` = `SOURCE_CONFLICT`;
- no Person / Claim publication path.

A disposable SQLite DB outside the repository was reused for sign-off.

Baseline before the new rerun:

- feeder observations: 568,649;
- source runs: 4.

The API credential was supplied only through an existing private wrapper outside the repository.
The wrapper loads only `ASSEMBLY_API_KEY` from the owner's private env, puts it in the child
process environment, and scrubs the value from output. This plan does not read or record the key.

## Historical normalization convergence discovered during sign-off

The first fresh rerun on current master initially reported created observations instead of unchanged.

A version comparison proved this is not provider drift. Earlier observations created before the
tally-conflict hardening commit lacked:

`bill_tally_reconciliation: MATCHED`

The current final contract includes that field.

Example provider key:

`ARC_A2A4S1W1C2J2N1Z4I3X5E4M1V3I9W2:04T3751T`

Old content hash:
`b80ca3712348f774679903a2bd3cb8d1781afbb7f1990656ae6252735e3f56b1`

Current-contract hash:
`952b906d73b9ea89abf2122115bb1e4e78c1b6fd6d23b43e984f69370c9bee97`

The only semantic addition in the normalized record is `bill_tally_reconciliation: MATCHED`.

This is expected immutable-version convergence because the original full-term acquisition was
resumed after the conflict-handling contract changed around the earlier checkpoint. Do not delete or
rewrite the old observations.

## Live sign-off evidence

### Run A — final-contract convergence

A fresh `--enumerate` was run against the existing disposable DB.

Two transient generic `AssemblyApiError` request failures occurred at checkpoints 410 and 532.
Both left committed checkpoints intact. `--resume` revalidated the unchanged universe fingerprint
and continued.

Aggregated across the fresh run and its two resumes:

- universe: **1,911 / 1,911 bills**
- records seen: **568,649**
- immutable versions created: **175,612**
- unchanged: **393,037**
- final status: **SUCCESS**
- one tally exception retained:
  `PRC_G2Z5L1L1C2F1O1S6A0I6O4J4T5B8G3 = SOURCE_CONFLICT`

The created count is exactly the historical prefix acquired before
`bill_tally_reconciliation` entered the normalized contract. The remaining 393,037 observations
were already on the final contract and were unchanged.

A direct keyed request of the next bill after the second transient failure returned:

- HTTP 200
- `INFO-000`
- 300 member rows

so the interrupted run was not caused by a deterministic bad bill row.

### Run B — full-universe idempotency

Immediately after convergence, another fresh full enumeration was started under the same final
contract.

The outer proof process was interrupted after checkpoint 1008. The DB receipt was explicitly
closed as PARTIAL without moving the checkpoint:

- created: **0**
- unchanged: **299,948**

A normal `--resume` continued from 1008 and completed the remaining 903 bills:

- created: **0**
- unchanged: **268,701**
- final status: **SUCCESS**
- checkpoint: **1911 / 1911**

Aggregated full-universe idempotency proof:

- **observations_created = 0**
- **observations_unchanged = 568,649**
- same universe fingerprint
- same tally-exception semantics

### Request-limit observation

The official service metadata displays request-limit value `200000`.

A minimal keyed summary probe returned:

- HTTP 200
- no response headers whose names contained rate / limit / retry / remaining / quota

A keyed member-vote probe after a transient full-run failure likewise returned:

- HTTP 200
- `INFO-000`
- 300 rows
- no such rate-limit headers

The complete run therefore proves ordinary keyed use well below the displayed 200000 value, but
the provider does **not** expose a reset period in the observed response headers. This plan does
not relabel `200000` as a daily/hourly limit and does not attribute the transient request failures
to throttling.

## Acceptance

- the final-contract convergence run completes successfully;
- the following full-universe Run B is fully unchanged;
- request-limit behavior is described precisely and without inventing a reset period;
- coverage matrix + feeder doc promoted from L2 to L3 only after the evidence exists;
- focused tests and repository-wide verification pass;
- no new analysis/scoring/publication behavior is introduced.



## Verification closure

Focused latest-master verification:

- Ruff: PASS
- mypy: PASS
- `tests/test_assembly_roll_call_votes.py`: PASS

Repository-wide verification in the isolated sign-off worktree:

- Ruff: PASS
- mypy: PASS over 132 source files
- pytest: **985 passed / 3 skipped**
- Golden Set 001: PASS
- web lint: PASS
- web typecheck: PASS
- web tests: **42 / 42**
- Next.js production build: PASS
- standalone runtime asset preparation: PASS
- full verification exit code: **0**

The isolated worktree required `npm ci` before web verification because it had no local
`node_modules`. This changed no package or lockfile. npm reported pre-existing dependency audit
warnings; no dependency change is part of this milestone.

No runtime/source connector code, schema, Person, Claim, publication, ideology/alignment scoring or
scheduler behavior is introduced by this sign-off. The code already satisfied the L3 mechanics; this
milestone closes the missing live operational evidence and promotes the documented maturity.

## Stop condition

Stop at acquisition L3 sign-off. Do not schedule or publish roll-call-derived intelligence in this
slice.
