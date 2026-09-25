# OpenDART listed-company executives — 2025 annual report

Base: `7a2a677ab8383a08002656db6cd60f9ad0f566cc`.

## Goal

Persist one bounded, complete OpenDART executive-status universe without attempting the 119,447
corporation master as one operational request batch.

Declared universe:

- official OpenDART corp-code master;
- retain exactly rows with a non-empty six-character `stock_code`;
- business year `2025`;
- report code `11011` (annual report);
- feeder `opendart_disclosed_executives`;
- scope `listed_corporations:2025:11011`;
- Person materialization remains REVIEW_REQUIRED.

## Live evidence — 2026-09-25

- corp master rows: 119,447;
- declared listed subset: 3,994 unique corp codes / stock codes;
- listed-universe fingerprint:
  `03d733a4318a9b62607ee3692f117c0020fa6e5616753178639116439ed76678`;
- provider policy in the reviewed SourcePolicy notes error `020` generally above 20,000 requests,
  so the 3,994-company lane remains below that documented request-count boundary;
- 100-company evenly spaced probe:
  - 2025 annual: status 000 = 72, status 013 = 28;
  - 2026 half-year: status 000 = 69, status 013 = 31;
- 2025 annual first-20 live parse after contract repair: 20 companies parsed, 174 executive rows;
- live `tenure_end_on` can use Korean `YYYY년 MM월 DD일`, normalized to an ISO date.

## Contract

The listed filter is applied before the universe fingerprint and before executive API iteration.
Checkpoint metadata stores `universe_mode=LISTED_ONLY`, the filtered total and fingerprint.
Resume is valid only for the same business year, report code, source contract, universe mode,
filtered total and fingerprint.

The existing `all_corporations` implementation remains available and backward-compatible. This
slice adds a distinct bounded scope rather than silently changing its semantics.

No employee-status API, compensation feed, ownership feed, Person creation, cross-source merge,
Claim publication or political inference is introduced.

## Acceptance

1. Ruff, mypy and focused OpenDART tests pass.
2. Existing all-corporation tests remain unchanged in behavior.
3. Listed-only fixture proves the unlisted corporation is never queried.
4. Listed-only partial run resumes from its filtered checkpoint.
5. Live proof confirms the current filtered total and parser.
6. Full repository Verify and GitHub CI pass before staging collection.
7. Staging collection runs only from merged master and may resume after a committed checkpoint.
8. Final checkpoint must equal the complete 3,994-company filtered universe.
