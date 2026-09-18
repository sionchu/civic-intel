# Civic Intel — First Live Staging ALIO Organization Publication v1

Status: COMPLETE — `ALIO_ORGANIZATION_CONTENT_DEPLOYED_STAGING — PASS` (2026-09-18).
The original post-publication acceptance was blocked by an incorrect C0908 helper-ID contract.
That historical state was preserved and resolved through a source-lane-specific acceptance
regression and read-only staging verification; no rollback, reset, compensating write, second
commit or deployment was run.

## Objective and boundary

Publish the already-acquired, already-proven ALIO item-4 Organization content to the existing
staging PostgreSQL through exactly one live `--commit`, then verify the existing private API and
cleanup boundary. This was an operations/data-publication task. No ALIO reacquisition,
`--resume`, schema/migration change, API/Web deployment, new Railway resource, credential change,
or Person materialization was in scope.

## Preflight and source

- Repository revision and `origin/master`: `908bf74d3485dac5765f0f67d64e90971c12a7e7`.
- GitHub Verify `35315858815`: SUCCESS.
- Railway staging service set remained `api`, `web`, `postgres`.
- Preflight deployment IDs were unchanged throughout: PostgreSQL
  `172ec443-e3cc-44bb-a5c1-195f54f86824`, API
  `76ec8f69-8874-4fbb-a67c-eeda55d0fd19`, Web
  `8fad7294-d590-4aee-9381-71c5f3bfca6f`.
- Existing successful item-4 run: `e57f88d4-953b-4de5-bf1c-13fa4b3e43db`.

## Backup and disposable restore

- Exactly one private Railway Sandbox was created: `6347251a-b116-4d60-b832-d818f497fbcc`,
  region `us-west2`, with no domain.
- Fresh custom/no-owner logical dump: `1,290,509` bytes; SHA-256
  `8050a2d9ece0a3ee2efd0dcc6cef1bd4c840b0f62b766bec69f1b897481dd84f`; command wall time
  approximately `28.2s`.
- PostgreSQL 18 loopback restore passed in `675ms`.
- Restored baseline matched live before publication: schema `0006`, People `299`,
  Organizations `1`, Claims/ClaimEvidence `1496/1496`, item-4 observations/checkpoint
  `3799/1`, C0908 Item-12 `15/2`, subject-XOR `0`, and item-4 Organization Claims `0`.

## Live receipts

The importer was executed from the exact pinned checkout. The live dry-run and the single
live commit used the existing `alio_public_institution_executives` source and
`item_4_current_all_institutions` scope.

- Dry-run: `14.470s`, `DRY_RUN`, run `e57f88d4-953b-4de5-bf1c-13fa4b3e43db`, observed `3798`,
  named `3624`, masked/vacant `174`, organizations `346`, claims `3970`,
  organizations created/reused `346/0`, claims created/reused `0/0`.
- Dry-run made no live count change.
- The exact one live commit: `25.387s`, `COMMITTED`, same run, organizations `346`, claims
  `3970`, organizations created/reused `346/0`, claims created/reused `3970/0`.
- Post-commit no-write projection: `17.948s`, `DRY_RUN`, organizations `346`,
  organizations created/reused `0/346`, claims created/reused `0/0`.

## Live publication result

- Schema remained `0006`.
- People remained `299`; Organizations became `347`.
- Claims/ClaimEvidence became `5466/5466`.
- ALIO item-4 observations/checkpoint remained `3799/1`.
- ALIO item-4 Claims/ClaimEvidence are `3970/3970`; every item-4 Claim has Evidence.
- Canonical ALIO import-key duplicate groups: `0`.
- Subject-XOR violations: `0`.
- Item-4 Claims with Person links: `0`; no Person was created from ALIO names.
- C0908 Item-12 remained `15` observations and `2` Claims.

## Private API and privacy evidence

- Existing private API read smoke: `/ready=200`, `/people=200` with `299`, and
  `/organizations=200` with `347`.
- Three ALIO Organizations with executive Claims were inspected. Each detail and claims route
  returned `200`; each had one classification Claim, executive Claims, one Evidence per Claim,
  source references, and zero Person links.
- Public DTO key scan found no forbidden normalized, raw, fulltext, contact, phone, email,
  secret or password fields.
- The existing reviewed C0908 binding
  `b6c4df5d-2d9b-4c26-aedb-2c5a0f079b11` returned detail/claims/MONEY `200` with two Claims.

## Historical blocking acceptance and diagnosis

The required helper calculation
`organization_id_for_alio_apba_id("C0908")` returned
`3059f7f9-94d5-5e32-83e2-4b7aa37fee9a`. That ID has no live Organization row and the
existing API returned `404` for its detail, claims and MONEY routes. The activated item-4
corpus contains `346` distinct `alio_apba_id` values and no C0908 item-4 Claim. C0908's
existing Item-12 Claims are attached to the explicit reviewed binding above, not to the
helper-derived ID.

This was a contract mismatch between the requested acceptance and the current canonical
reviewed-Organization identity path. It was not repaired ad hoc after publication. The live
staging state remained intact for the separate identity-contract decision.

## Resolved acceptance

The corrected acceptance uses the existing reviewed canonical binding, not the Item 4 helper
identity:

- reviewed Organization: `b6c4df5d-2d9b-4c26-aedb-2c5a0f079b11`;
- public staging organization detail, Claims and MONEY views returned successfully;
- two published C0908 annual Claims were visible for 2024 and 2025, with the exact `C0908`
  institution qualifier and ALIO Item 12 Source/Evidence trace;
- the public source card showed the ALIO source policy and permitted metadata/fulltext boundary;
- the helper-derived C0908 route `3059f7f9-94d5-5e32-83e2-4b7aa37fee9a` remained `Profile not found`;
- the public organization directory showed 347 records and the home directory showed 299 People;
- raw normalized observation/contact fields were not rendered in the reviewed organization page;
- no second Organization, Claim migration, importer run, database write, schema change or
  deployment was performed for this fix.

The acceptance contract is now closed as
`ALIO_ORGANIZATION_CONTENT_DEPLOYED_STAGING — PASS`. The exact regression is in
`tests/test_alio_item12_money.py` and proves that an explicit reviewed Organization UUID can
publish the bounded Item 12 pair even when it differs from the Item 4 deterministic helper UUID.

## Cleanup and closure

- Disposable PostgreSQL was stopped and task-owned dump, receipts, API response files and logs
  were removed inside the Sandbox.
- Sandbox `6347251a-b116-4d60-b832-d818f497fbcc` was destroyed; final sandbox list was empty.
- Railway deployment IDs, service topology, domain, volume/resource identity and plan remained
  unchanged. No API/Web deployment, migration, credential or permanent resource change occurred.
- At the original checkpoint the post-commit C0908 acceptance failed, so the PASS marker was not
  emitted then; the resolved acceptance above now supplies the marker without changing live data.

## Reopen condition

Resolve the C0908 identity contract in a separate approved code/data milestone: either make the
acceptance use the existing reviewed binding or prove a source-bounded item-4 C0908 record and
its exact canonical binding. Do not rerun a live commit or alter the current staging data until
that contract is reviewed.

## Next concrete action

Select one reviewed cross-lane Person-linking packet from the already published ALIO executive
corpus using exact non-name identity evidence; keep name-only linking prohibited and do not begin
another feeder.
