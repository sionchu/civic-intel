# Gukgam 2026 Governance Ontology + Visual Explorer v0

Status: IN PROGRESS.

## Objective

Ship a public-beta Gukgam 2026 research surface on top of the existing Evidence Core without
turning Civic Intel into a season-only product. The release combines bounded official-source
collection with a read-only governance ontology projection and search-first graph exploration.

Target beta date: 2026-09-29.

## Baseline

- Repository baseline: `0d40df42a38b77ea0b296bbfb12e8f1c821122e3`.
- Verify `35370449189`: SUCCESS.
- Staging schema `0006`; People `299`; Organizations `347`; Claims/ClaimEvidence
  `5466/5466`.
- ALIO item-4 Claims/Evidence `3970/3970`; executive Claims/Evidence `3624/3624`.
- Cross-lane candidate v0: 56 review-only pairs, 0 resolved pairs.

## Release boundaries

- PostgreSQL remains SSOT.
- No graph database, vector database or second raw store.
- No name-only Person resolution.
- No precise-residence or private-family relation.
- Every public ontology edge must retain Claim/Evidence provenance.
- Missing committee plans are `NOT_YET_PUBLISHED`, not evidence of no audit.
- Public reuse rights never imply automated-access permission.

## Slice 0 — source reconnaissance + ontology contract + graph skeleton

### Official Gukgam source reconnaissance

The National Assembly committee pages are authoritative origin references for committee plans and
related attachments. The first current 2026 Science Committee plan was pinned:

```text
nttId: 3078699
title: 2026년도 국정감사계획서
published: 2026-09-15
attachment: atchFileId 7938f3a874d5441892124093d19da1df
```

The source contract is recorded in
`docs/architecture/GUKGAM_2026_SOURCE_CONTRACT.md`.

Current gate:

```text
ONE CURRENT POST RIGHTS-REVIEWED
+
AUTOMATED COMMITTEE HTML COLLECTION BLOCKED
```

The exact host's robots contract is `User-agent: * / Disallow: / / Allow: /$`.
Therefore the committee page remains a provenance/origin source but is not a repeated automated
collection route.

### Ontology projection

PR #63 contains:

- `packages/rendering/governance_ontology.py`;
- public `GET /ontology/people/{person_id}`;
- regression coverage for evidence-backed projection and fail-closed missing Evidence;
- `docs/architecture/GOVERNANCE_ONTOLOGY.md`.

The executable v0 is intentionally narrower than the future vocabulary. It maps only the
canonical `HELD_ROLE` predicate to a Claim-scoped `OFFICE` node.

Independent review tightened the semantics:

- appointment/election/nomination/designation events are not rewritten as `HELD_ROLE`;
- `UNKNOWN`, `ENTITY_UNRESOLVED`, `INFERENCE`, `HYPOTHESIS` do not become connection edges;
- SUPPORT+REFUTE ClaimEvidence is preserved as `source_conflict=true`;
- cross-Person path search is deferred until shared institution/event identity can be bound without
  label-based merging.

### Visual library gate

Cytoscape.js remains the preferred v0 renderer. Dependency addition is deferred until real eligible
graph data is ready for a public visual surface and the lockfile can be updated through a normal npm
execution boundary. Do not hand-edit the lockfile.

## Verification

PR #63 is the independent CI boundary for Slice 0.

Required closure:

- full Verify succeeds on the final head;
- final diff has no publication-gate bypass;
- no raw evidence excerpt appears in ontology output;
- no identity merge is introduced;
- no schema, migration, dependency or deployment change.

## Current checkpoint — Web surface + reviewed packet staging (2026-09-19)

- Governance Ontology Slice 0 merged as `f5189b61febbd5729c79b3ac349ace57fb6f8ac7`.
  The public Person ontology route remains a read-only Claim/Evidence projection; nomination,
  UNKNOWN/inference relations and label-based cross-Person path merging remain excluded.
- The first Web/Product surface merged as
  `e6d58c733093abe1a236ab09e6226aac5782ef0a`: top-level `국감 2026`, the editorial
  `/gukgam/2026` landing, Home launch treatment, and an accessible Person local ontology graph
  with a complete textual relation list. No frontend graph dependency or new backend/schema was
  added.
- The reviewed Gukgam plan-packet L1 parser merged as
  `d0b7c0efd2091cb418e585b5ade9fe5eb19253fc`. The pinned Science Committee fixture contains
  reviewed source metadata only; its schedule remains empty until exact official PDF rows are
  reviewed. The parser performs no fetch, persistence, identity materialization or publication.
- Final master Verify `35380740361` passed on
  `d0b7c0efd2091cb418e585b5ade9fe5eb19253fc`.
- Exact-commit staging deployments passed:
  API `0b8317d1-a6ee-44bd-89b2-8e5bf821b0f7` and Web
  `ba1acc7d-5b88-454a-8e62-5923918de41b`, both at the same master commit. PostgreSQL remained
  on `172ec443-e3cc-44bb-a5c1-195f54f86824`; no data import, schema write, resource, domain,
  variable, volume or replica change was made.
- Runtime evidence: API deploy logs show `GET /ready 200` and `GET /people 200`. The Web
  deployment healthcheck at `/` passed, and its production build explicitly contains
  `/gukgam/2026` and `/people/[id]`. The current tool execution boundary could not fetch the
  Railway public domain for rendered-content QA, so screenshot/content-level staging QA remains
  a separate browser check rather than an inferred PASS.
- Committee-site repeated automation remains blocked by the reviewed robots contract. Official
  data.go.kr metadata confirms the National Assembly Secretariat publishes an Open API catalog
  with unrestricted reuse, but the catalog landing metadata does not itself identify a
  Gukgam-specific operation. The official OpenAPI guide/service list must be searched before
  scaling reviewed packets.

## Current checkpoint — Open Assembly schedule discovery L1 (2026-09-19)

- Official data.go.kr dataset `15126132` confirms the National Assembly Secretariat
  `국회일정 통합 API` is free and has `이용허락범위 제한 없음`.
- The reviewed Open API catalog does not expose a dedicated pre-audit plan / audited-organization /
  institution-witness / general-witness / reference-person operation. Gukgam-specific API families
  cover meeting minutes and post-audit/result reports instead.
- `packages/connectors/open_assembly_schedule.py` stages the smallest read contract for
  `ALLSCHEDULE`: date, kind, time, committee, schedule content, place, session and degree.
- `국정감사` text matching produces a discovery candidate only. It does not materialize a Hearing,
  Organization, Person, witness or Claim.
- The exact operation/field contract still needs one live provider sample before L2 promotion;
  the current external-probe execution boundary failed before a provider response was obtained.

## Current checkpoint — Scale collection + ontology product v0 (2026-09-19)

- National Assembly schedule discovery L1 merged as
  `7b69bd6b4efb3d94109631d1a6b700824fbf732f`; the read-only probe worker followed at
  `70c9ae3fc91bbf964c77cbf1d639c186a04234ae`. Verify runs `35415849302` and
  `35416280261` passed. The official endpoint is reachable from GitHub Actions: a bounded
  `ALLSCHEDULE` request returned HTTP 200. The repository has no `ASSEMBLY_API_KEY` secret,
  and the documented public `sample` key returned provider code `ERROR-290` (invalid key).
  Schedule L2 is therefore credential-blocked, not network-blocked. No API result was persisted.
- Search-first Gukgam discovery merged as
  `fe064a1335631f67694aa4e692295f7a7565b566`; Verify `35417435004` passed and staging Web
  deployment `8c168adf-69a5-4cc5-8cba-6f8ca78d29ef` succeeded. CJK desktop/mobile visual QA
  `35417606721` passed. Interaction QA `35417739316` independently proved
  `한국전력공사` Organization search, at least two distinct `박지원` Person results with the
  same-name separation warning, and mobile search behavior. Search filters existing canonical
  records only; it creates no score, rank or identity match.
- Organization ontology v0 merged as
  `5018e31a4202572940b32e6b66c367921958aa06`; Verify `35418442406` passed. Exact staging
  deployments succeeded: API `d0f1a76e-fc13-409a-89d5-1cd0890561d4` and Web
  `a200f0e9-fc72-4586-b44e-2c116cf5ac77`. PostgreSQL remained
  `172ec443-e3cc-44bb-a5c1-195f54f86824`. The projection is
  `canonical Organization → LISTS_EXECUTIVE → SOURCE_LISTED_ROLE_HOLDER`; the target node has
  `canonical_id=null`, is Claim-scoped, and never auto-links to a Person. 한국전력공사 staging
  smoke/visual QA `35418537339` passed with 김동철 and other published ALIO executive records,
  while raw normalized/contact fields remained absent.
- Dense same-relation graph labels were polished in
  `4554602bb2a7eac8b66e51e7061dfac48e3e2195`; Verify `35418826810` passed and Web staging
  deployment `1d2df428-3e2e-46b7-9352-1e69e8773eae` succeeded. Final CJK screenshot QA
  `35418874131` passed; repeated `공식 공시상 임원` edge labels are collapsed to one visual
  label while the complete textual Evidence list remains unchanged.
- Reviewed Gukgam plan L2 import boundary merged as
  `a37acfa1ea5a4320bd644db31ca6abfa3e0debd7`; final master Verify `35419420199` passed.
  It separates provenance into raw attachment SHA-256 (`SourceSnapshot.content_hash`), reviewed
  packet SHA-256 (`SourceRun/Checkpoint metadata`) and normalized schedule-row SHA-256
  (`FeederObservation.content_hash`). Dry-run is default. A commit can persist only
  SourcePolicy/Source/SourceSnapshot/Run/Checkpoint/Observation and explicitly creates zero
  Person, Organization, Claim, ClaimEvidence or identity link.
- The pinned Science Committee exact PDF has now been captured through the approved
  human-assisted artifact boundary and independently matched to the existing reviewed packet.
  Raw attachment SHA-256 is
  `82d37b337790e5869e74af3420b7dab74c86a7fb14b44a54932f8dbd2f31e533`; the reviewed packet
  contains 8 audit rows / 96 audited-target strings and retains packet hash
  `4f74bf8b7f0dfae52ad6fafff646d0c5f78a2c602a3d53d1bf55796284c8a74d`.
  The real artifact dry-run passed with zero Person/Organization/Claim materialization.
  No staging observation has been written yet. Committee-site repeated automation remains blocked.

## Current checkpoint — public-beta HTTP acceptance + directory latency (2026-09-19)

- Read-only Public Beta preflight merged as
  `d4d3529f8e63dea1f7394d41fcde99997b97769e`; final master Verify
  `35422460313` passed. It checks Home, `/gukgam/2026`, robots/sitemap, optional Person and
  Organization detail routes, staging/public indexing semantics and selected raw/contact leak
  tokens without mutating application data or Railway configuration.
- Real staging preflight run `35426383959` passed against
  `https://web-staging-efe2.up.railway.app`: Home, Gukgam, robots, sitemap,
  Person `44745d09-398c-46ce-bc38-81f0f606c1d7` and Organization
  `3ef4de75-fa3f-5815-81f4-8bc5efdc33f1` all returned HTTP 200. Staging correctly remained
  noindex/disallow-all.
- The first timing run showed a real list-path bottleneck: `/people` ~1.0–1.17 s,
  `/organizations` ~2.5–2.97 s and `/gukgam/2026` ~3.10–3.81 s.
- API publication-context batching merged as
  `8c50218cdd8a8de31c0c1ec97192c044da7643e8`; final Verify `35422992753` passed and staging
  API deployment `57efc9cd-4f7b-49b5-b1e7-188e8f723f5f` succeeded.
- Web directory-list revalidation merged as
  `a58050b778b1f29bb7167b8c534acbb6ab9013d1`; final Verify `35426886029` passed and staging
  Web deployment `328a8649-8fba-4021-9ab5-258e8360abff` succeeded. Only public People and
  Organization list fetches use a 60-second revalidation window; detail, ontology, Evidence,
  source, money and review reads remain request-time.
- Post-change timing run `35427116217` showed `/gukgam/2026` at ~0.55–0.57 s after the
  directory cache is populated. `/organizations` had one cold ~2.86 s request then ~0.56–0.78 s;
  `/people` settled around ~0.59–0.61 s. Publication validation remains in the canonical API.
- Railway already has a `production` environment
  `7dd4f01b-25c6-47ce-b91e-f5e2c9b71b15`, but it currently contains zero services. No
  production service, database, public/custom domain or indexing activation was created.
  Production creation/domain/indexing remain explicit public-access/cost gates.
- The exact Science Committee PDF is available through the approved human-assisted local artifact
  boundary and is verified against the canonical reviewed packet. The attachment itself is not
  committed or retained in the repository. Repeated committee-site automation remains blocked,
  and no committee may gain canonical schedule/target rows from press or search snippets alone.

## Public-beta release gate

Before public indexing is enabled:

1. obtain explicit approval for the production/public-access boundary and any resulting Railway
   resource cost;
2. create or select the final public Web/API/Postgres topology and final domain;
3. set `CIVIC_PUBLIC_BASE_URL` to that final origin and `CIVIC_INDEXING_ENABLED=true` only on
   the approved public Web service;
4. deploy one exact verified master commit;
5. run `workers.public_beta_preflight --expect-indexing enabled`;
6. run independent rendered desktop/mobile QA and verify canonical/OG/robots/sitemap behavior.

Staging must stay noindex.

## Current checkpoint — standing-committee exact attachment batch 1 (2026-09-20)

- The owner-operated Aside Browser local daemon was recovered and used as the bounded,
  human-assisted acquisition boundary. No committee crawler or repeated HTTP collector was added.
- Exact official plan PDFs are now captured for eight standing committees: the existing Science
  Committee plus Steering, National Defense, Public Administration and Security,
  Culture/Sports/Tourism, Agriculture/Food/Rural Affairs/Oceans, Strategy and Finance, and
  Foreign Affairs and Unification.
- Six new v1 reviewed packets passed exact-artifact dry-run:
  Steering `3/10`, Public Administration and Security `12/45`,
  Culture/Sports/Tourism `7/69`, Agriculture/Food/Rural Affairs/Oceans `8/49`,
  Strategy and Finance `10/48`, and National Defense `9/73`
  (`schedule rows / audited-target mentions`).
- Every successful dry-run reported `fulltext_retained=false`,
  `person_materialization=false`, `organization_materialization=false`, and
  `claim_publication=false`. Raw PDFs remain outside the repository.
- Foreign Affairs and Unification is exact-attachment captured but packet-blocked: the official
  overseas schedule contains multi-day ranges (`10.11~10.22`, `10.11~10.20`,
  `10.11~10.21`) while v1 supports only one `audit_date`. No range was collapsed or guessed.
- Targeted reviewed-packet/importer verification passed `24 tests`. Local full verification then
  passed: Ruff, mypy, `444 passed / 1 skipped` pytest, Golden quality, Web lint/typecheck,
  22 Web tests, production build, and `git diff --check`.
- PR #85 Verify `35454900420` passed, and squash merge `f808433bae6a2b838430bef96fd0c4b13ba00f9b`
  reached `master`. Merge-head Verify `35455358644` also passed every canonical, migration,
  PostgreSQL, backup/restore, deployment-artifact and installed-entrypoint step.

## Current checkpoint — staging observation-only import batch 1 (2026-09-20)

- An owner-authenticated Railway CLI session opened a temporary SSH tunnel to the private staging
  PostgreSQL service. No public database domain was created. A staging-specific public SSH key was
  registered only for the tunnel, then removed after the import; the tunnel was terminated.
- Baseline staging remained schema `0006`: People `299`, Organizations `347`, Claims `5466`,
  ClaimEvidence `5466`, and `gukgam_reviewed_plan` observations `0`.
- Seven packet-ready committees were committed exactly once: Science `8`, Steering `3`, Public
  Administration and Security `12`, Culture/Sports/Tourism `7`, Agriculture/Food/Rural
  Affairs/Oceans `8`, Strategy and Finance `10`, and National Defense `9` schedule observations.
  Total new `gukgam_reviewed_plan` observations: `57`.
- Each packet was immediately rerun unchanged. All seven reruns reported
  `observations_created=0` and `observations_unchanged=<schedule_rows>`, proving idempotent reuse of
  the same observation versions. The 14 successful source runs are seven first commits plus seven
  unchanged reruns.
- Canonical entity counts were asserted before and after and remained exactly People `299`,
  Organizations `347`, Claims `5466`, ClaimEvidence `5466`. The import still materialized no Person,
  Organization, Claim or ClaimEvidence and retained no attachment fulltext.
- The central official inspection list was then rechecked committee-by-committee using both
  `2026년도 국정감사` and broader `2026` title filters. No 2026 plan row was visible for the
  eight `DISCOVERY_PENDING` committees or Health and Welfare, so their inventory states were not
  promoted or downgraded by inference.

- A table-level scan across all eight exact plan PDFs found date ranges elsewhere only on excluded
  non-audit rows: Public Administration and Security holidays, National Defense holidays, and the
  Science Committee field-inspection row. Foreign Affairs and Unification is the only current exact
  plan with multi-day ranges attached to actual audited targets.

## Current checkpoint — review-only schedule projection v0 (2026-09-20)

- Added a pure review projection for current `gukgam_reviewed_plan` observations and a gated
  `GET /admin/gukgam/2026/schedule` endpoint. The route exists only when
  `enable_review_surface=True`; the default public API and `/gukgam/2026` remain unchanged.
- Current-row selection follows the checkpoint's attachment SHA and chooses the latest immutable
  observation version per provider record key. A checkpoint/current-row count mismatch fails closed
  instead of guessing correction semantics.
- The projection allowlist includes only reviewed committee/date/time/venue/target/page metadata and
  exact source provenance. It excludes canonical Organization IDs, Claim IDs, run IDs, raw
  `normalized` payloads and fulltext.
- Targeted static/contract verification passed: Ruff, mypy, and 27 Gukgam projection/packet/import
  tests. Local full verification also passed: Ruff, mypy, `447 passed / 1 skipped` pytest, Golden
  quality, Web lint/typecheck, 22 Web tests, production build, and `git diff --check`.
- Owner-local review-surface execution against the real staging database passed with
  `7 committees / 57 schedule rows / 390 audited-target mentions`; the forbidden fields above
  were absent. This was a read-only projection check, not a staging API deployment or publication.
- The temporary Railway SSH tunnel and review-only registered public key used for that check were
  closed/removed afterward.

## Current checkpoint — review-only Organization binding candidates v0 (2026-09-20)

- Added a pure exact-name candidate projection and gated
  `GET /admin/gukgam/2026/organization-binding-candidates` endpoint. It reuses the current
  review-only schedule projection and `organizations(current_only=True)`; no persistence path,
  matcher service, alias table or public route was added.
- Match classes are explicit and non-authoritative:
  `EXACT_CANONICAL_NAME_OVERLAP_DISCOVERY_ONLY`,
  `NO_EXACT_CANONICAL_NAME_OVERLAP`, and
  `MULTIPLE_EXACT_CANONICAL_NAME_OVERLAPS_REVIEW_REQUIRED`.
- Exact overlap never means bound. The DTO contains only source occurrence context plus candidate
  Organization ID/name. It contains no score, rank, probability, confidence, Claim ID or write
  action.
- Targeted validation passed Ruff, mypy and 29 Gukgam review/packet/import tests. Local full
  verification then passed: Ruff, mypy, `449 passed / 1 skipped` pytest, Golden quality, Web
  lint/typecheck, 22 Web tests, production build, and `git diff --check`.
- Owner-local read-only execution against the real staging database measured 347 current canonical
  Organizations, 390 target mentions and 359 distinct target strings. Exact overlap produced
  110 mention candidates / 103 distinct target candidates; 280 mentions / 256 distinct targets had
  no exact candidate; multiple exact candidates were 0.
- The temporary Railway SSH tunnel and registered public key used for the staging measurement were
  closed/removed afterward.

## Current checkpoint — reviewed Organization binding preflight v0 (2026-09-20)

- Added gated `GET /admin/gukgam/2026/organization-binding-preflight`. It requires an exact
  source-occurrence `review_key` and an operator-supplied existing current Organization ID.
- The preflight re-runs the current exact-name candidate report, requires exactly one candidate,
  requires the supplied ID to match it, re-checks current Organization state and uniquely recovers
  the exact committee-plan provenance. It returns only a `DRY_RUN` receipt with
  `binding_committed=false` and `claim_publication=false`.
- Wrong Organization IDs, missing review keys and occurrences without exactly one exact-name
  candidate fail closed. The default public API still exposes none of these admin routes.
- Targeted verification passed Ruff, mypy and 34 Gukgam review/packet/import tests. Full local
  verification then passed: Ruff, mypy, `454 passed / 1 skipped` pytest, Golden quality, Web
  lint/typecheck, 22 Web tests, production build, and `git diff --check`.
- Owner-local execution against real staging selected one live exact-name candidate occurrence and
  passed the preflight. A random wrong Organization ID returned `422 INVALID_INPUT`.
- Staging counts before/after were identical: People `299`, Organizations `347`, Claims
  `5466`, ClaimEvidence `5466`, Gukgam observations `57`, Gukgam source runs `14`.
  The check therefore performed no Organization, Claim/Evidence or source-run write.
- The SSH tunnel used for this read-only proof was closed afterward. No public DB domain was
  created.

## Current checkpoint — reviewed Gukgam Organization Claim importer v0 (2026-09-20)

- Added source-specific predicate `LISTED_AS_GUKGAM_AUDIT_TARGET`. Its FACT semantics are
  limited to the exact official plan listing: the Organization is printed as an audited target for
  that schedule occurrence. It does not state that the audit happened/completed or imply
  wrongdoing, responsibility, performance or outcome.
- Added `civic-import-gukgam-reviewed-claim`. The command requires one existing current
  Organization UUID and one target-level reviewed `review_key`, re-runs the current binding
  preflight and exact schedule/source-policy validation, and builds deterministic Claim/Evidence
  with exact observation/snapshot/source provenance.
- `review_key` is the Claim source key so distinct target organizations in one schedule row do not
  collide. The row-level provider key is retained separately in qualifiers.
- The command is dry-run by default and performs no network fetch. `--commit` is the only Claim
  write path. Exact stored semantics return `REUSED`; conflicting stored semantics, wrong
  Organization bindings and multiple immutable observation versions fail closed.
- Follow-up review SSOT'd current-row selection: the admin review surface and Claim worker now use
  the same checkpoint-selected schedule loader, including packet/attachment metadata checks and
  the checkpoint `schedule_row_count` gate. A new regression proves an incomplete current-row
  universe fails closed before Claim preparation.
- Initial targeted/local verification passed Ruff, mypy, 38 Gukgam tests and
  `458 passed / 1 skipped` full pytest plus Golden/Web/build/diff gates. PR #90 strengthened-code Verify
  `35484811916` passed the strengthened head with `459 passed / 1 skipped` and all canonical,
  Alembic, PostgreSQL, backup/restore, deployment-artifact and installed-entrypoint gates.
- Owner-local execution against real staging selected one exact-name candidate and ran the new
  worker **without** `--commit`. Result: `DRY_RUN`, predicate
  `LISTED_AS_GUKGAM_AUDIT_TARGET`, `claim_persisted=false`,
  `claim_created=false`, `binding_committed=false`, and no network fetch.
- Staging before/after remained People `299`, Organizations `347`, Claims `5466`,
  ClaimEvidence `5466`, Gukgam observations `57`, Gukgam source runs `14`. No write occurred.
  The temporary private-DB tunnel was closed afterward.

## Current checkpoint — first staging Gukgam Claim commit receipt (2026-09-20)

- Execution used merged `master` `b02f306d474ec35d19f6a668140a41edb8c4818e` against the
  existing private staging PostgreSQL boundary; no public database domain was created.
- The reviewed occurrence was 과학기술정보방송통신위원회 / 2026-10-13 /
  한국원자력안전기술원, Organization
  `2b389008-a8c1-53d4-87d9-f4221aa8dfa5`, with review key
  `3078699:7938f3a874d5441892124093d19da1df:2:schedule:3:audited-target:3`.
- A pre-commit dry-run returned `DRY_RUN` with staging counts unchanged at People `299`,
  Organizations `347`, Claims `5466`, ClaimEvidence `5466`, Gukgam observations `57`,
  and Gukgam source runs `14`.
- Exactly one `--commit` then created Claim
  `7c4b2e8d-b9eb-5f4c-87ba-fb3c561ecb83` and ClaimEvidence
  `e5f2a33b-59da-5e1e-90d9-384f14fff689`. Counts became Claims `5467` and
  ClaimEvidence `5467`; People, Organizations, Gukgam observations and Gukgam source runs
  remained unchanged.
- Immediate unchanged rerun returned `REUSED` with counts still unchanged, proving the
  deterministic single-occurrence retry contract. Owner-local public Claim read smoke against the
  staging database passed through the ordinary Organization Claim/Evidence gate.
- The temporary SSH key used for this private-DB execution was removed, and its local private/public
  key files plus temporary execution scripts were deleted. No bulk publication was performed.

## Current checkpoint — public Claim-backed Gukgam target projection v0 (2026-09-20)

- Added read-only `GET /gukgam/2026/targets` backed exclusively by current published
  `LISTED_AS_GUKGAM_AUDIT_TARGET` Organization Claims.
- The projection semantics are `PUBLIC_CLAIM_BACKED_GUKGAM_AUDIT_TARGETS_V1` with coverage
  `BOUNDED_INCOMPLETE_PUBLISHED_CLAIMS_ONLY`. Absence is explicitly not evidence of no audit.
- Each item retains canonical Organization identity plus Claim, ClaimEvidence, Source,
  SourceSnapshot and FeederObservation IDs. Review keys, candidate match classes, scores, ranks,
  raw normalized payloads and review-only binding state are not exposed.
- There is no fallback from reviewed observations or exact-name binding candidates. Regression
  coverage proves that multiple reviewed audited-target strings with only one committed Claim
  produce exactly one public target item.
- Targeted verification passed Ruff, mypy across 76 Python source files and 40 Gukgam
  review/Claim/import tests. Full local verification passed Ruff, mypy,
  `460 passed / 1 skipped` pytest, Golden quality, Web lint/typecheck, 22 Web tests,
  production build and `git diff --check`.
- This slice changes the API contract only. The existing Web `/gukgam/2026` page is unchanged,
  and no additional Organization binding or Claim publication was performed.

## Current checkpoint — staging Claim-backed Gukgam target API (2026-09-20)

- PR #92 merged as `c7038763ed8093bb8e39564e60e1b4eaa88fe892` after Verify
  `35486439758` passed every canonical, Alembic, PostgreSQL, backup/restore, deployment-artifact
  and installed-entrypoint gate.
- A generic Railway `redeploy` was rejected as deployment evidence because it reused the stale
  source snapshot for commit `8c50218...`; that deployment was superseded and removed.
- Owner-local deployment then reset a clean working tree to exact merged `master` `c703876...`
  and uploaded that tree to the existing staging API service with `railway up`. Deployment
  `151f9078-0088-428f-a384-eab7fd8bde47` reached `SUCCESS`.
- The staging API remains private-only: zero Railway service domains and zero custom domains. No
  database, Web service, environment variable, schema or indexing setting changed.
- Private-container smoke called `/ready` and `GET /gukgam/2026/targets` over localhost and
  passed exact assertions. The response contained exactly one target and one committee with
  semantics `PUBLIC_CLAIM_BACKED_GUKGAM_AUDIT_TARGETS_V1` and coverage
  `BOUNDED_INCOMPLETE_PUBLISHED_CLAIMS_ONLY`.
- The sole target was 한국원자력안전기술원
  (`2b389008-a8c1-53d4-87d9-f4221aa8dfa5`) under 과학기술정보방송통신위원회 on
  `2026-10-13`, backed by Claim
  `7c4b2e8d-b9eb-5f4c-87ba-fb3c561ecb83` and ClaimEvidence
  `e5f2a33b-59da-5e1e-90d9-384f14fff689`. Exact Source, SourceSnapshot and
  FeederObservation IDs were present; no observation/name-match fallback appeared.
- The temporary SSH key `civic-intel-gukgam-projection-20260920` was removed from Railway after
  the smoke, and both local private/public key files were deleted. The pre-existing unrelated
  `dev.new` key was left untouched.

## Current checkpoint — staging Gukgam published-target Web slice (2026-09-20)

- PR #94 merged as `3f868fea873a3e4ef5d126478e9b6bf1fb27e4ba` after GitHub Verify
  `35486918538` passed, matching local full verification: Ruff, mypy, `460 passed / 1 skipped`
  pytest, Golden quality, Web lint/typecheck, `23 / 23` Web tests, production standalone build
  and `git diff --check`.
- The existing `/gukgam/2026` page now reads only `GET /gukgam/2026/targets` for its
  "공개된 피감대상" section. It reuses existing Claim-card and audit-detail grammar; no new CSS,
  ranking, review candidate, name-overlap fallback, client-side publication state or identity logic
  was added.
- Each rendered target links to its canonical Organization `#claims` section and exposes
  Claim/Evidence/Source/SourceSnapshot/FeederObservation identifiers behind an audit-details
  disclosure. The UI always states that the current set is not the complete audit-target list and
  does not infer absent targets.
- A clean owner-local working tree was reset to exact merged `master` `3f868fe...` and uploaded
  to the existing staging Web service. Deployment
  `28a7b423-7240-4a7e-8c2f-af7fa6d1629c` reached `SUCCESS`; the existing staging domain
  remained `web-staging-efe2.up.railway.app`.
- Live staging HTTP smoke against `/gukgam/2026` returned `200` and confirmed the published
  target heading, 한국원자력안전기술원, 과학기술정보방송통신위원회, `2026-10-13`, the canonical
  Organization `#claims` link, Claim
  `7c4b2e8d-b9eb-5f4c-87ba-fb3c561ecb83`, and ClaimEvidence
  `e5f2a33b-59da-5e1e-90d9-384f14fff689`. The response did not expose `review_key` or
  `match_class`.
- The API service remained on deployment `151f9078-0088-428f-a384-eab7fd8bde47`; no database
  write, Claim publication, Organization binding, API domain, environment variable or schema change
  occurred in this Web deployment slice.

## Current checkpoint — second reviewed Gukgam Claim commit (2026-09-20)

- With the cross-view public Claim contract merged on `master`, staging review selected exactly one
  additional exact-name candidate: 한국원자력통제기술원, Organization
  `f3d71e88-c6d1-5eba-9ae7-5df04ff4e0c9`, review key
  `3078699:7938f3a874d5441892124093d19da1df:2:schedule:3:audited-target:4`.
- Read-only discovery showed 109 current exact-one occurrences without a published Gukgam Claim;
  no automatic selection, scoring, ranking, fuzzy match or bulk approval was introduced.
- Dry-run returned `DRY_RUN` with `claim_persisted=false`, `claim_created=false`,
  `binding_committed=false`, `organization_created=false` and `network_fetch=false`.
  Public target count remained `1`.
- Pre-commit staging counts were Organizations `347`, Claims `5467`, Gukgam observations
  `57`, Gukgam source runs `14`, public target count `1`.
- One explicit `--commit` created Claim
  `52fb5057-37f0-5b30-8645-415ac8131752` and ClaimEvidence
  `a13ebec6-ef4f-5570-b549-e9f6c3fefede`. Immediate unchanged rerun returned `REUSED`.
- Post-commit cross-view smoke passed: Organizations remained `347`, Claims became `5468`,
  Gukgam observations remained `57`, Gukgam runs remained `14`, and public target count became
  exactly `2`. The target API and Organization detail exposed the same Claim/Evidence IDs plus
  Source `429d851c-3a6c-4756-8b3a-3ace5266d064`, SourceSnapshot
  `78ceba04-d4ff-4b78-a41c-527de8a9b728` and FeederObservation
  `d79afce8-2e4d-4d87-b6c6-2340b1136078`.
- Live staging Web smoke returned `200` and rendered both 한국원자력안전기술원 and
  한국원자력통제기술원, including the second Claim/Evidence IDs and the bounded-coverage message.
  `review_key` and `match_class` remained absent from the public HTML.
- The temporary SSH key used for this execution was removed from Railway and both local key files
  were deleted. No other candidate was committed.

## Current checkpoint — reviewed Gukgam batch manifest dry-run v0 (2026-09-20)

- Added `civic-preflight-gukgam-reviewed-claim-batch` as a no-write operator preflight. The
  command accepts one explicit JSON manifest and intentionally exposes no `--commit` option.
- Manifest schema is `civic.gukgam.reviewed_claim_batch_manifest.v1`. Each item contains only
  `review_key` and an operator-supplied existing `organization_id`; unknown fields, empty
  manifests, invalid UUIDs and duplicate `review_key` values fail closed.
- Manifest items are canonical-sorted before execution and receipt hashing, so the same explicit
  item set produces the same SHA-256 and deterministic receipt regardless of input list order.
- Every item reuses `prepare_reviewed_gukgam_claim_import()`, preserving the existing
  current-schedule, exact-name Organization, source-policy, immutable observation and publication
  validation seams. No candidate enumeration or name-based approval is added.
- If any item is stale/wrong or already has the exact published Gukgam Claim, the whole manifest
  dry-run fails. A successful receipt always reports `write_performed=false`,
  `batch_commit_available=false`, `automatic_candidate_enumeration=false` and
  `network_fetch=false`.
- Targeted verification passed Ruff, mypy and `4 / 4` manifest tests, including deterministic
  reversed-order receipts, zero-write behavior, duplicate rejection, wrong-binding rejection and
  already-published rejection. Full local verification passed Ruff, mypy across 77 source files,
  `465 passed / 1 skipped` pytest, Golden quality, Web lint/typecheck, `23 / 23` Web tests,
  production standalone build and `git diff --check`.

## Current checkpoint — staging reviewed Gukgam batch manifest dry-run (2026-09-20)

- PR #99 merged as `a165d3e5de3c6d6341ca9425700eaa8506d01e5e` after GitHub Verify
  `35489803777` passed canonical verification, Alembic, PostgreSQL migration/load/API,
  backup/restore, deployment artifacts and installed entrypoint checks.
- A clean owner-local tree was reset to exact merged `master` and uploaded to the existing staging
  API service. Deployment `f178e1b0-b752-4e0e-bf29-2e581d1d8c71` reached `SUCCESS`.
- The explicit staging manifest contained exactly two still-unpublished reviewed occurrences:
  한국원자력안전재단
  (`3078699:7938f3a874d5441892124093d19da1df:2:schedule:3:audited-target:5`,
  Organization `7b9fc4f2-bda7-5fab-a455-fc7a08199938`) and 한국수력원자력(주)
  (`...:audited-target:6`, Organization `135a5433-8fbd-55ae-b5e4-e6a615e92d08`).
- Input order was target:6 then target:5. The installed
  `civic-preflight-gukgam-reviewed-claim-batch` command canonicalized the receipt to target:5 then
  target:6 and returned manifest SHA-256
  `a88c85ad097c8c249cf315cf927580f006982e6939d1733954c2e4ef57758342`.
- Both items returned `DRY_RUN`, `claim_persisted=false`, `binding_committed=false`,
  `organization_created=false` and `network_fetch=false`. The top-level receipt reported
  `write_performed=false`, `batch_commit_available=false` and
  `automatic_candidate_enumeration=false`.
- An unchanged second execution produced the same manifest hash, item order, deterministic Claim
  IDs (`90144deb-cb1f-59c9-ba56-9020ed91bd8e`,
  `1ef7bdad-a01b-5388-954d-da24ea562689`) and Evidence IDs
  (`691fa768-230e-59a6-ab83-43cabe24ad3a`,
  `efbc2609-9839-53aa-94af-e664368116ad`).
- Before and after both dry-runs, staging remained Organizations `347`, Claims `5468`,
  ClaimEvidence `5468`, Gukgam observations `57`, Gukgam source runs `14` and public targets
  `2`. No write occurred.
- The temporary remote manifest was deleted. The temporary Railway SSH key was removed and both
  local key files were deleted; the unrelated pre-existing `dev.new` key was untouched.

## Current checkpoint — reviewed Gukgam batch persistence adapter v0 (2026-09-20)

- PR #101 merged as `1af6a994461e8982817c998d1d1d5a3253792c30`; merge-head Verify
  `35500227982` passed canonical verification, Alembic, PostgreSQL migration/load/API,
  backup/restore, deployment artifacts and the installed-entrypoint gate.
- The internal adapter consumes only an already-prepared canonical reviewed manifest batch,
  rechecks prepared `(review_key, organization_id)` order and reuses the existing atomic
  `import_organization_claim_batch()` seam.
- Adapter regression proves existing Organizations are reused, two Claims commit atomically, an
  exact same prepared retry reuses both Claims, reordered prepared items fail closed and a late
  invalid Evidence source rolls back the whole Claim batch.
- PR #101 intentionally exposed no CLI commit path and performed no staging write.

## Current checkpoint — explicit reviewed Gukgam batch commit gate v0 (2026-09-20)

- Added separate operator entrypoint `civic-import-gukgam-reviewed-claim-batch`; the existing
  `civic-preflight-gukgam-reviewed-claim-batch` remains no-write.
- The write command requires the same explicit manifest plus both `--expected-manifest-sha256`
  and `--commit`. The canonical manifest hash must match before any item preflight is evaluated.
- Every item is re-preflighted against current schedule/provenance and the caller-supplied existing
  Organization ID. No candidate enumeration, fuzzy/alias matching, ranking or Organization
  creation path was added.
- A fully unpublished manifest may enter the atomic adapter. A fresh exact retry with every Claim
  already present returns `REUSED` without writing. A partially published manifest fails closed
  before persistence.
- Targeted verification passed Ruff, mypy across 78 source files and `11 / 11` batch
  manifest/adapter/commit tests. Full local verification then passed Ruff, mypy, `472 passed / 1
  skipped` pytest, Golden quality, Web lint/typecheck, `23 / 23` Web tests, production standalone
  build and `git diff --check`.

## Current checkpoint — staging reviewed Gukgam batch commit (2026-09-20)

- PR #102 merged as `ec78ff69d4b9b8891961587fd40e0f292b29afe9`; head Verify
  `35500819201` passed. Local full verification had already passed Ruff, mypy across 78 source
  files, `472 passed / 1 skipped` pytest, Golden quality, Web lint/typecheck,
  `23 / 23` Web tests, production standalone build and `git diff --check`.
- A clean owner-local tree was reset to exact merged `master` `ec78ff6...`. The already-reviewed
  two-item manifest from the prior staging dry-run was reused unchanged, with required SHA-256
  `a88c85ad097c8c249cf315cf927580f006982e6939d1733954c2e4ef57758342`.
- The manifest contained only 한국원자력안전재단
  (`...:schedule:3:audited-target:5`, Organization
  `7b9fc4f2-bda7-5fab-a455-fc7a08199938`) and 한국수력원자력(주)
  (`...:schedule:3:audited-target:6`, Organization
  `135a5433-8fbd-55ae-b5e4-e6a615e92d08`). No other candidate was added or auto-selected.
- The first explicit batch `--commit` receipt validated `COMMITTED`, `claims_created=2`,
  `claims_reused=0`, `organizations_created=0`, `organizations_reused=2` and
  `write_performed=true`. It created Claims
  `90144deb-cb1f-59c9-ba56-9020ed91bd8e` and
  `1ef7bdad-a01b-5388-954d-da24ea562689` with ClaimEvidence
  `691fa768-230e-59a6-ab83-43cabe24ad3a` and
  `efbc2609-9839-53aa-94af-e664368116ad`.
- The unchanged immediate retry validated `REUSED`, `claims_created=0`, `claims_reused=2`
  and `write_performed=false`. A later exact-manifest retry through the deployed staging commit
  gate returned the same `REUSED` result and deterministic Claim/Evidence IDs.
- Staging changed only as intended: Organizations remained `347`; Claims and ClaimEvidence moved
  from `5468` to `5470`; Gukgam observations remained `57`; Gukgam source runs remained
  `14`; public Claim-backed targets moved from `2` to `4`.
- The initial owner-local harness completed commit, retry and count assertions, then exited on an
  outdated projection response-key lookup in its final name check. A separate read-only verifier
  subsequently passed the corrected current API contract with the exact counts above, target count
  `4`, committee count `1`, expected Claim/Evidence IDs,
  `automatic_candidate_enumeration=false` and `network_fetch=false`.
- Exact merged `master` was uploaded to the existing staging API service; deployment
  `252eaca6-e11f-4717-a5ec-01295548d422` reached `SUCCESS` and `/ready` returned `200`.
- Live staging Web smoke returned `200` and rendered 한국원자력안전재단 and
  한국수력원자력(주), both new Claim/Evidence IDs and the bounded-coverage message. Public HTML
  still exposed neither `review_key` nor `match_class`.
- The remote temporary manifest was deleted. Temporary Railway SSH keys and all local key,
  manifest, execution-script and verification-log artifacts for this slice were deleted; only the
  unrelated pre-existing `dev.new` key remains.

## Next concrete action

Prepare the **next reviewed Gukgam manifest as a no-write dry-run only**, starting from the next
unpublished exact-one occurrences in the reviewed schedule and manually confirming each
`(review_key, organization_id)` pair. Require deterministic manifest hashing, unchanged staging
counts and no public-target change. Do not run another batch `--commit` in that same slice and do
not introduce automatic candidate selection.
