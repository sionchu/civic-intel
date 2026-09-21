# C0908 Identity Acceptance Contract Fix v1

Status: COMPLETE — `ALIO_ORGANIZATION_CONTENT_DEPLOYED_STAGING — PASS` (2026-09-18).

## Objective

Correct the C0908 staging acceptance without changing live data, rerunning the ALIO importer or
weakening either source lane's identity rules. The acceptance must distinguish the deterministic
Item 4 Organization identity from the explicit reviewed Item 12 Organization binding.

## Contract

- Item 4 executive content uses `apbaId -> organization_id_for_alio_apba_id(apbaId)` for the
  deterministic Organization ID of that materialized Item 4 corpus.
- Item 12 reviewed MONEY content uses an explicit existing canonical Organization ID together
  with the source-scoped `institution_code`/`apbaId` binding.
- `organization_id_for_alio_apba_id()` is not a global ALIO Organization registry resolver and
  must not be used to reinterpret a reviewed Item 12 binding.
- A reviewed Item 12 binding is accepted only when the existing canonical Organization is current,
  the source institution name matches, the exact `institution_code` is preserved in Claim
  qualifiers, and ClaimEvidence proves the Source, SourceSnapshot and FeederObservation chain.
- Name-only identity linking and automatic Item 12 Organization materialization remain forbidden.

## Implementation

The existing `tests/test_alio_item12_money.py` regression creates a canonical Organization with a
reviewed UUID deliberately different from the Item 4 helper UUID, imports the bounded C0908
2024/2025 pair, checks both published Claims and exact provenance, and verifies the reviewed
detail/claims/MONEY routes. The helper-derived C0908 routes remain 404 in that Item 12-only
fixture. No production code, schema, migration, importer behavior or live staging data changed.

## Staging baseline and read-only closure

The approved live publication already completed before this contract fix. The preserved staging
baseline is schema `0006`, 299 People, 347 Organizations, 5,466 Claims and 5,466 ClaimEvidence;
the reviewed C0908 Organization is
`b6c4df5d-2d9b-4c26-aedb-2c5a0f079b11` with two published Item 12 Claims. The deterministic helper
returns `3059f7f9-94d5-5e32-83e2-4b7aa37fee9a`; its absence is not a failure because C0908 is not
present in the activated Item 4 corpus.

No importer, `--commit`, `--resume`, DB write, migration, deployment or Railway resource change is
allowed in this milestone. Read-only browser closure confirmed the reviewed detail/Claims/MONEY
views, two C0908 annual Claims, exact source/evidence trace, the 347-organization public directory,
and the 299-person public directory. The helper-derived C0908 route remained not found. The
public page did not render normalized observation/contact fields. The browser could not expose
private schema/deployment identifiers, so those remain supported by the preserved live receipt and
pre-existing deployment evidence rather than inferred from the page.

## Reopen condition

Reopen only if the explicit reviewed C0908 Organization, its published Claims/Evidence provenance,
or the preserved staging topology cannot be confirmed read-only. Do not create a second C0908
Organization or migrate existing Claims to the Item 4 helper identity as an acceptance workaround.

## Verification

- Targeted regression: `pytest -q tests/test_alio_item12_money.py tests/test_alio_organization_activation.py`
  — 46 passed.
- Full local Python verification: `pytest` — 372 passed, 1 skipped; Ruff passed; mypy passed
  for 63 source files; Golden quality passed.
- Web verification: lint, typecheck, UI tests (11/11), production build and standalone runtime
  contract all passed.
- Production code and schema are unchanged; the implementation diff is test plus documentation
  only.
- The prior live publication receipt records schema `0006`, unchanged Railway topology and the
  existing staging deployment IDs. This milestone performed no staging write or deployment.

## Next concrete action

Select one reviewed cross-lane Person-linking packet from the already published ALIO executive
corpus using exact non-name identity evidence; keep name-only linking prohibited and do not begin
another feeder.
