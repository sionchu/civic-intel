# Definition of done

P0 is done only when `make verify` passes and the executable Golden Set 001 report shows:

- the exact ten-person 2026-08-30 roster with no identity contamination;
- every published FACT traceable through supporting evidence, source, and policy;
- explicit non-asserted UNKNOWN output, conflicting evidence, and origin deduplication;
- episode, relationship, source-policy, privacy, and raw-search exclusion gates passing;
- SQLAlchemy-backed API reads and migration coverage;
- web lint, typecheck, tests, and production build passing.

Local results must be described as local unless a GitHub check run exists.
