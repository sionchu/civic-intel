# National Assembly roster to Evidence Directory

Status: completed — stop condition met locally on 2026-09-13.

## Objective

Close the existing National Assembly L3 roster and Evidence Directory gap without adding a
generic materialization framework, schema, dependency or new UI:

```text
official Assembly roster
 -> successful L3 run/checkpoint/observations
 -> existing Assembly materialization gate
 -> Person / PersonObservationLink
 -> published HELD_ROLE Claim/Evidence
 -> existing public API/profile projection
```

The seven-feeder maturity baseline and all other source gates remain unchanged.

## Non-goals

- no new feeder or materialization rule;
- no migration, table, projection cache or repository implementation;
- no changes to Gwanbo, NEC, ALIO, OpenDART, MPM, asset, CleanEye or other lanes;
- no feeder health dashboard or new Assembly-specific UI;
- no change to `ReviewedPersonBundle` semantics;
- no live credentialed fetch in tests or CI.

## Selection rule

Only a completed `national_assembly_members` / `current_member_roster` enumeration may trigger
materialization. The enumerator carries the exact observation IDs returned by each committed
page. On resume, IDs matching the prior checkpoint's committed provider-key/hash manifest are
included before newly committed pages. This avoids using `run_id` alone (unchanged observations
are reused across runs) and avoids selecting immutable history by fetched timestamp. A failed or
partial enumeration has no materialization path.

## Acceptance cases

- [x] first successful multi-page enumeration materializes one Person and published `HELD_ROLE`
      evidence per unique provider identity;
- [x] unchanged successful rerun creates no Person, claim or link duplicates;
- [x] changed metadata for the same `MONA_CD` creates one immutable observation and `AUTO_LINK`s
      to the existing Person without a duplicate role claim;
- [x] same-name/different-provider rows remain `REVIEW_REQUIRED`;
- [x] exact birth-date contradiction remains `HARD_CONFLICT` and is not public;
- [x] publication-gate failure leaves that materialization transaction without Person/Claim/
      Evidence/Link partial state;
- [x] public `/people` and `/people/{id}` expose only resolved materialized people and the
      profile's existing `HELD_ROLE` timeline entry with exact evidence provenance;
- [x] resume reconstructs already committed page observations from the checkpoint manifest before
      materializing the newly committed page;
- [x] existing Assembly enumeration/materialization/API/profile regressions remain green.

## Verification and delivery

Run targeted Assembly/materialization/API/profile tests, then the repository DoD commands,
including Python/web checks, quality, migration round-trip and `git diff --check`. Record local
runner limitations separately from any GitHub Actions result. Commit and push one coherent slice;
do not claim CI success without an actual green check run.

## Evidence

- Source-specific `enumerate_and_materialize()` now consumes only the exact observation IDs
  returned by committed pages; resume reconstructs prior IDs from the checkpoint's
  `seen_provider_hashes` manifest. No fetched-timestamp or historical-observation sweep is used.
- Existing `SqlAlchemyRepository.materialize_feeder_observation()` remains the only Assembly
  materialization transaction and publication gate. No schema, migration, dependency, generic
  runner, parallel repository or UI was added.
- `.venv\Scripts\python.exe -m pytest -o addopts='' tests/test_assembly_evidence_directory.py -q`:
  6 passed, 2 warnings.
- `.venv\Scripts\python.exe -m pytest -o addopts='' -q`: 282 passed, 4 warnings.
- `.venv\Scripts\python.exe -m ruff check apps packages workers tests/test_assembly_evidence_directory.py`:
  passed.
- `.venv\Scripts\python.exe -m mypy packages workers apps/api`: success; 51 source files.
- `.venv\Scripts\python.exe -m packages.verification.quality`: `passed: true`; all Golden Set
  checks passed.
- `npm --prefix apps/web run lint`, `typecheck`, `test` and `build`: all passed; web tests 4/4.
- Alembic upgrade/downgrade/upgrade round-trip: passed on a temporary SQLite database.
- `git diff --check`: passed.
- `make verify`: runner unavailable because GNU Make is not installed; all constituent checks were
  executed directly. No GitHub Actions green result is claimed locally.
