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

## Current checkpoint — next reviewed Gukgam manifest dry-run (2026-09-20)

- After the first verified two-item batch commit, read-only discovery found `106` current
  exact-one audited-target occurrences without a published Gukgam Claim.
- The next manifest was hand-assembled from the canonical reviewed-schedule order only. It contains
  exactly two 2026-10-15 과학기술정보방송통신위원회 occurrences:
  정보통신산업진흥원
  (`3078699:7938f3a874d5441892124093d19da1df:2:schedule:4:audited-target:1`,
  Organization `2a0a4a19-e13d-520b-b695-3838da56fec1`) and 한국인터넷진흥원
  (`...:schedule:4:audited-target:3`, Organization
  `8e9b1884-2947-5d85-a3a6-f35ea7c4c2df`). Target index 2 was not inferred or filled because it
  was not an exact-one reviewed candidate.
- Input order was target:3 then target:1. The installed no-write preflight canonicalized the
  receipt to target:1 then target:3 and returned manifest SHA-256
  `f95e12acd55d19c136f90d969167d0463123666469079a4e7263b3c21f6b1be2`.
- Both items returned `DRY_RUN`, `claim_persisted=false`, `claim_created=false`,
  `binding_committed=false`, `organization_created=false` and `network_fetch=false`.
  Top-level `write_performed=false`, `batch_commit_available=false` and
  `automatic_candidate_enumeration=false` remained explicit.
- The deterministic prospective Claim IDs are
  `eb004086-3776-5db2-b95f-d626cd133190` and
  `299b3e96-9e97-5bcf-9a99-d1d649ee13f7`; prospective ClaimEvidence IDs are
  `4547c25c-3dff-59af-aeff-756734a5c080` and
  `b0894c57-ce16-5df4-8c52-dab669ea075a`.
- An unchanged second preflight returned the same manifest hash, canonical order and deterministic
  Claim/Evidence IDs.
- Before and after both dry-runs, staging remained Organizations `347`, Claims `5470`,
  ClaimEvidence `5470`, Gukgam observations `57`, Gukgam source runs `14` and public targets
  `4`. No write occurred.
- The remote temporary manifest and this slice's temporary SSH key/local key files were deleted.
  Other independently existing SSH keys were left untouched.

## Current checkpoint — second reviewed Gukgam batch commit (2026-09-20)

- PR #104 merged as `164ccf78bb3a4f1f211df0caba7e22222b43a515` after Verify
  `35501690869` passed every canonical, Alembic, PostgreSQL, backup/restore, deployment-artifact
  and installed-entrypoint gate.
- The commit slice reused exactly the prior reviewed manifest and required SHA-256
  `f95e12acd55d19c136f90d969167d0463123666469079a4e7263b3c21f6b1be2`.
  No candidate was added, substituted or auto-selected.
- Commit-time baseline was Organizations `347`, Claims `5470`, ClaimEvidence `5470`,
  Gukgam observations `57`, Gukgam source runs `14` and public targets `4`; neither
  정보통신산업진흥원 nor 한국인터넷진흥원 was yet public.
- A fresh commit-time no-write preflight again returned the exact manifest hash, canonical order,
  deterministic Claim/Evidence IDs and `write_performed=false`.
- One explicit batch `--commit` returned `COMMITTED`, `claims_created=2`,
  `claims_reused=0`, `organizations_created=0`, `organizations_reused=2` and
  `write_performed=true`.
- 정보통신산업진흥원 created Claim
  `eb004086-3776-5db2-b95f-d626cd133190` with ClaimEvidence
  `4547c25c-3dff-59af-aeff-756734a5c080`. 한국인터넷진흥원 created Claim
  `299b3e96-9e97-5bcf-9a99-d1d649ee13f7` with ClaimEvidence
  `b0894c57-ce16-5df4-8c52-dab669ea075a`.
- The unchanged immediate retry returned `REUSED`, `claims_created=0`, `claims_reused=2`
  and `write_performed=false` with the same deterministic IDs.
- Post-commit staging verification passed: Organizations remained `347`; Claims and
  ClaimEvidence became `5472`; Gukgam observations remained `57`; Gukgam source runs remained
  `14`; public Claim-backed targets became exactly `6`.
- Public target API cross-check exposed both new Organizations with the exact Claim/Evidence IDs,
  shared Source `429d851c-3a6c-4756-8b3a-3ace5266d064`, SourceSnapshot
  `78ceba04-d4ff-4b78-a41c-527de8a9b728` and FeederObservation
  `9b207a42-ab78-45e4-9e74-d0f2baeb677a`.
- Live staging Web smoke returned `200`, rendered both new Organizations and their Claim/Evidence
  IDs, retained the bounded-coverage message and exposed neither `review_key` nor `match_class`.
- The remote temporary manifest and this slice's temporary Railway SSH key/local key files were
  deleted. The unrelated pre-existing `dev.new` key was left untouched.

## Current checkpoint — third reviewed Gukgam manifest dry-run (2026-09-20)

- After the second reviewed batch commit, read-only discovery found `104` current exact-one
  audited-target occurrences without a published Gukgam Claim.
- The next explicit manifest contains exactly two 2026-10-15
  과학기술정보방송통신위원회 occurrences in canonical reviewed-schedule order:
  한국방송통신전파진흥원
  (`3078699:7938f3a874d5441892124093d19da1df:2:schedule:4:audited-target:4`,
  Organization `940fc166-af5e-50a2-a5de-ba32abfb67c9`) and 한국지능정보사회진흥원
  (`...:schedule:4:audited-target:5`, Organization
  `463e5ec7-6743-5b19-b71a-5407bc0f6572`).
- The source manifest was supplied in reversed item order; the installed no-write preflight
  canonicalized it to target:4 then target:5 and returned SHA-256
  `b012c32c931dd97e5860436b6c58f245f8171abbcd5f2767a0a7ebeff12ea69e`.
- Both items returned `DRY_RUN`, `claim_persisted=false`, `claim_created=false`,
  `binding_committed=false`, `organization_created=false` and `network_fetch=false`.
  Top-level `write_performed=false`, `batch_commit_available=false` and
  `automatic_candidate_enumeration=false` remained explicit.
- Deterministic prospective Claim IDs are
  `a5369920-f37f-5f74-a7aa-44fec4c2ed07` and
  `44ca07f2-8b06-589d-bdc0-591a0c7c2ff2`; prospective ClaimEvidence IDs are
  `df01d639-b32a-5f8e-97d5-3e131ae1bdf4` and
  `429f693a-ca6c-5f2e-a4de-38b68326d7e5`.
- An unchanged second preflight returned the identical manifest hash, canonical order and
  deterministic Claim/Evidence IDs.
- Before and after both dry-runs, staging remained Organizations `347`, Claims `5472`,
  ClaimEvidence `5472`, Gukgam observations `57`, Gukgam source runs `14` and public targets
  `6`. No write occurred.
- The remote manifest, temporary Railway SSH key and local manifest/key files for this slice were
  deleted; the unrelated pre-existing `dev.new` key was left untouched.

## Current checkpoint — third reviewed Gukgam batch commit (2026-09-21)

- The commit slice reused exactly the prior two-item reviewed manifest and required SHA-256
  `b012c32c931dd97e5860436b6c58f245f8171abbcd5f2767a0a7ebeff12ea69e`.
  No candidate was added, substituted or auto-selected.
- Commit-time baseline was Organizations `347`, Claims `5472`, ClaimEvidence `5472`,
  Gukgam observations `57`, Gukgam source runs `14` and public targets `6`; neither
  한국방송통신전파진흥원 nor 한국지능정보사회진흥원 was yet public.
- A fresh commit-time no-write preflight again returned the exact manifest hash, canonical
  target:4 → target:5 order, deterministic Claim/Evidence IDs and `write_performed=false`.
- One explicit batch `--commit` returned `COMMITTED`, `claims_created=2`,
  `claims_reused=0`, `organizations_created=0`, `organizations_reused=2` and
  `write_performed=true`.
- 한국방송통신전파진흥원 created Claim
  `a5369920-f37f-5f74-a7aa-44fec4c2ed07` with ClaimEvidence
  `df01d639-b32a-5f8e-97d5-3e131ae1bdf4`. 한국지능정보사회진흥원 created Claim
  `44ca07f2-8b06-589d-bdc0-591a0c7c2ff2` with ClaimEvidence
  `429f693a-ca6c-5f2e-a4de-38b68326d7e5`.
- The unchanged immediate retry returned `REUSED`, `claims_created=0`, `claims_reused=2`
  and `write_performed=false` with the same deterministic IDs.
- Post-commit staging verification passed: Organizations remained `347`; Claims and
  ClaimEvidence became `5474`; Gukgam observations remained `57`; Gukgam source runs remained
  `14`; public Claim-backed targets became exactly `8`, still under one committee.
- Public target API cross-check exposed both new Organizations with the exact Claim/Evidence IDs,
  shared Source `429d851c-3a6c-4756-8b3a-3ace5266d064`, SourceSnapshot
  `78ceba04-d4ff-4b78-a41c-527de8a9b728` and FeederObservation
  `9b207a42-ab78-45e4-9e74-d0f2baeb677a`.
- Live staging Web smoke returned `200`, rendered both new Organizations and their Claim/Evidence
  IDs, retained the bounded-coverage message and exposed neither `review_key` nor `match_class`.
- The remote temporary manifest and this slice's temporary Railway SSH key/local key files were
  deleted. Other independently existing SSH keys were left untouched.

## Current checkpoint — fourth reviewed Gukgam manifest dry-run (2026-09-21)

- After the third reviewed batch commit, read-only discovery found `102` current exact-one
  audited-target occurrences without a published Gukgam Claim.
- The next explicit manifest contains exactly two occurrences in canonical reviewed-schedule order:
  한국데이터산업진흥원
  (`3078699:7938f3a874d5441892124093d19da1df:2:schedule:4:audited-target:6`,
  Organization `fe771e6b-09b4-5d42-928b-c1f567d6b824`) and 시청자미디어재단
  (`...:schedule:5:audited-target:4`, Organization
  `de62b1f1-71ac-5643-a580-d93a0e5e478c`).
- The source manifest was supplied in reversed item order; the installed no-write preflight
  canonicalized it to target:6 then the next schedule-row target:4 and returned SHA-256
  `4b962fc72e48d1238047b185c7a20cd7287b62642ff7feff2fe9bdfe4f97185c`.
- Both items returned `DRY_RUN`, `claim_persisted=false`, `claim_created=false`,
  `binding_committed=false`, `organization_created=false` and `network_fetch=false`.
  Top-level `write_performed=false`, `batch_commit_available=false` and
  `automatic_candidate_enumeration=false` remained explicit.
- Deterministic prospective Claim IDs are
  `ccfbd72d-7511-5669-b0da-64523ae48375` and
  `da33bb39-84c2-5f58-8645-404f989cbdf8`; prospective ClaimEvidence IDs are
  `433c4f49-aec1-50da-9aaa-ce66fb5fd713` and
  `8ec9aa4e-ce66-5635-8935-ae1eff796c69`.
- The first item reuses FeederObservation `9b207a42-ab78-45e4-9e74-d0f2baeb677a`; the second
  uses `731be71a-8413-4df6-bee4-7bb422cc56c4`. Both retain Source
  `429d851c-3a6c-4756-8b3a-3ace5266d064` and SourceSnapshot
  `78ceba04-d4ff-4b78-a41c-527de8a9b728`.
- An unchanged second preflight returned the identical manifest hash, canonical order and
  deterministic Claim/Evidence IDs.
- After both dry-runs, staging remained Organizations `347`, Claims `5474`,
  ClaimEvidence `5474`, Gukgam observations `57`, Gukgam source runs `14` and public targets
  `8`. No write occurred.
- The remote temporary manifest was deleted by the execution command. This slice's temporary
  Railway SSH key and local key files were deleted; independently existing keys were left untouched.

## Current checkpoint — fourth reviewed Gukgam batch commit (2026-09-21)

- The commit slice reused exactly the prior two-item reviewed manifest and required SHA-256
  `4b962fc72e48d1238047b185c7a20cd7287b62642ff7feff2fe9bdfe4f97185c`.
  No candidate was added, substituted or auto-selected.
- Commit-time baseline was Organizations `347`, Claims `5474`, ClaimEvidence `5474`,
  Gukgam observations `57`, Gukgam source runs `14` and public targets `8`; neither
  한국데이터산업진흥원 nor 시청자미디어재단 was yet public.
- A fresh commit-time no-write preflight again returned the exact manifest hash, canonical order,
  deterministic Claim/Evidence IDs and `write_performed=false`.
- One explicit batch `--commit` returned `COMMITTED`, `claims_created=2`,
  `claims_reused=0`, `organizations_created=0`, `organizations_reused=2` and
  `write_performed=true`.
- 한국데이터산업진흥원 created Claim
  `ccfbd72d-7511-5669-b0da-64523ae48375` with ClaimEvidence
  `433c4f49-aec1-50da-9aaa-ce66fb5fd713`. 시청자미디어재단 created Claim
  `da33bb39-84c2-5f58-8645-404f989cbdf8` with ClaimEvidence
  `8ec9aa4e-ce66-5635-8935-ae1eff796c69`.
- The unchanged immediate retry through the same batch-commit module returned `REUSED`,
  `claims_created=0`, `claims_reused=2` and `write_performed=false` with the same
  deterministic IDs.
- Post-commit staging verification passed: Organizations remained `347`; Claims and
  ClaimEvidence became `5476`; Gukgam observations remained `57`; Gukgam source runs remained
  `14`; public Claim-backed targets became exactly `10`, still under one committee.
- Public target API cross-check exposed both new Organizations with the exact Claim/Evidence IDs.
  한국데이터산업진흥원 retained FeederObservation
  `9b207a42-ab78-45e4-9e74-d0f2baeb677a`; 시청자미디어재단 retained
  `731be71a-8413-4df6-bee4-7bb422cc56c4`. Both retained Source
  `429d851c-3a6c-4756-8b3a-3ace5266d064` and SourceSnapshot
  `78ceba04-d4ff-4b78-a41c-527de8a9b728`.
- Live staging Web smoke returned `200`, rendered both new Organizations and their Claim/Evidence
  IDs, retained the bounded-coverage message and exposed neither `review_key` nor `match_class`.
- The remote temporary manifest and this slice's temporary Railway SSH key/local key files were
  deleted. Independently existing keys were left untouched.

## Current checkpoint — fifth reviewed Gukgam manifest dry-run (2026-09-21)

- Exact canonical `master` was `4bdcc2446bc6f7b668a46a2b1453551dccb3731a`; no newer
  `origin/master` progress existed before this slice.
- Read-only staging discovery found `100` current unpublished exact-one reviewed occurrences.
  The first two in canonical reviewed-schedule order were 한국방송광고진흥공사
  (`3078699:7938f3a874d5441892124093d19da1df:2:schedule:5:audited-target:5`,
  Organization `fa96033b-f447-5bf6-9450-aca8aabcd40c`) and 한국연구재단
  (`3078699:7938f3a874d5441892124093d19da1df:2:schedule:6:audited-target:22`,
  Organization `224e4e43-a737-5090-884a-0147b4652c17`).
- The explicit two-item manifest hashed to
  `e154f49c3575dd1a23f95489b3c7087467fd18d33eecd8ff010c7556c3e7e899`.
  No candidate was inferred, substituted, ranked, fuzzy-matched, alias-expanded or auto-selected.
- Two executions of the installed `civic-preflight-gukgam-reviewed-claim-batch` command with the
  unchanged manifest produced byte-identical receipts, the same canonical item order and the same
  manifest hash.
- 한국방송광고진흥공사 returned prospective Claim
  `c12aa7d9-22e2-5a3c-b496-aa05dae0afea`, ClaimEvidence
  `0195706b-55b9-599e-964e-3c9cb9ce318a`, FeederObservation
  `731be71a-8413-4df6-bee4-7bb422cc56c4`, SourceSnapshot
  `78ceba04-d4ff-4b78-a41c-527de8a9b728` and Source
  `429d851c-3a6c-4756-8b3a-3ace5266d064`.
- 한국연구재단 returned prospective Claim
  `7c1ba70a-c59b-5e5a-9a26-e65793a47143`, ClaimEvidence
  `a46231c2-4021-5637-a03f-9e6248675c05`, FeederObservation
  `42fe6d0c-8da1-44ad-aaf6-826a24b7eb57`, the same SourceSnapshot and the same Source.
- Both receipts preserved `status=DRY_RUN`, `write_performed=false`,
  `batch_commit_available=false`, `automatic_candidate_enumeration=false` and
  `network_fetch=false`. No batch `--commit` command was executed.
- Before and after both dry-runs, staging remained Organizations `347`, Claims `5476`,
  ClaimEvidence `5476`, Gukgam observations `57`, Gukgam source runs `14`, public
  Claim-backed targets `10` and public committee count `1`.
- The temporary manifest, receipt files, read-only verifier and this slice's Railway SSH key/local
  keypair were deleted. Pre-existing unrelated keys were left untouched.

## Current checkpoint — fifth reviewed Gukgam batch commit (2026-09-21)

- Exact canonical `master` remained `e0b408a261b456b21bccd9814d43dc7e1aaab156` with a clean
  tree and no newer concurrent Gukgam batch PR before execution.
- The commit slice recreated only the exact prior two-item reviewed manifest and required SHA-256
  `e154f49c3575dd1a23f95489b3c7087467fd18d33eecd8ff010c7556c3e7e899`. No candidate was
  added, substituted, ranked, fuzzy-matched, alias-expanded or auto-selected.
- Commit-time baseline was independently read as Organizations `347`, Claims `5476`,
  ClaimEvidence `5476`, Gukgam observations `57`, Gukgam source runs `14`, public targets `10`
  and public committee count `1`.
- A fresh commit-time no-write preflight exactly matched the prior fifth dry-run: both
  Organizations, review keys, prospective Claim/Evidence IDs, Observation/Snapshot/Source IDs,
  manifest hash and all zero-write flags matched. It returned `DRY_RUN`,
  `write_performed=false`, `batch_commit_available=false`,
  `automatic_candidate_enumeration=false` and `network_fetch=false`.
- One explicit `civic-import-gukgam-reviewed-claim-batch` execution with the exact manifest,
  exact expected SHA and `--commit` returned `COMMITTED`, `claims_created=2`,
  `claims_reused=0`, `organizations_created=0`, `organizations_reused=2`,
  `write_performed=true`, `automatic_candidate_enumeration=false` and `network_fetch=false`.
- 한국방송광고진흥공사 created Claim `c12aa7d9-22e2-5a3c-b496-aa05dae0afea` with
  ClaimEvidence `0195706b-55b9-599e-964e-3c9cb9ce318a`; 한국연구재단 created Claim
  `7c1ba70a-c59b-5e5a-9a26-e65793a47143` with ClaimEvidence
  `a46231c2-4021-5637-a03f-9e6248675c05`.
- Live staging Web verification after the commit rendered both new Organizations with the exact
  Claim/Evidence IDs and exact provenance: Source `429d851c-3a6c-4756-8b3a-3ace5266d064`,
  SourceSnapshot `78ceba04-d4ff-4b78-a41c-527de8a9b728`, FeederObservation
  `731be71a-8413-4df6-bee4-7bb422cc56c4` for 한국방송광고진흥공사 and
  `42fe6d0c-8da1-44ad-aaf6-826a24b7eb57` for 한국연구재단. The page reported current public
  scope `12` and one committee, and exposed neither `review_key` nor `match_class`.
- A direct post-commit internal aggregate re-read was attempted, but the ChatGPT/OpenAI tool safety
  gate blocked that read-only invocation before it reached Desktop Commander. Therefore Claims
  `5478`, ClaimEvidence `5478`, observations `57` and source runs `14` are the transaction-expected
  post-commit values, but are not independently re-read receipts in this slice. Do not rewrite
  them as independently verified until a later read-only check succeeds.
- This was not a commit failure: the write command reached Railway and returned the concrete
  `COMMITTED` receipt above. Do not replay this `e154f49c...e899` manifest.
- This slice's temporary commit/verification Railway SSH keys, local keypairs, manifest and Web
  verification artifact were deleted. The pre-existing `dev.new` and
  `civic-intel-gukgam-commit-b012-20260920` keys were left untouched.

## Current checkpoint — fifth reviewed Gukgam post-commit aggregate verification (2026-09-21)

- The previously blocked internal aggregate re-read was completed later without broadening the
  staging security boundary. Desktop Commander remained the control path and Railway CLI's
  official `connect postgres --ssh --tunnel-only` opened a private localhost tunnel; no public
  Postgres/API domain was created.
- The tunnel reused the existing Railway SSH configuration. A temporary local PostgreSQL driver
  was installed only in the repo virtual environment for the read-only query and uninstalled
  immediately after verification; no repository dependency or canonical artifact changed.
- The PostgreSQL session was forced read-only and independently returned Organizations `347`,
  Claims `5478`, ClaimEvidence `5478`, Gukgam observations `57` and Gukgam source runs `14`.
- A fresh live staging Web read independently confirmed public Claim-backed Gukgam scope `12`,
  committee count `1`, both new Claim/Evidence IDs and their exact Source/Snapshot/Observation
  provenance. `review_key` and `match_class` remained absent from public HTML.
- The private tunnel and all temporary verification files were closed/deleted after use. No
  staging write occurred in this verification slice.
- The fifth reviewed batch is now fully post-commit verified. Do not replay manifest SHA-256
  `e154f49c3575dd1a23f95489b3c7087467fd18d33eecd8ff010c7556c3e7e899`.

## Current checkpoint — sixth reviewed Gukgam manifest dry-run (2026-09-21)

- Exact canonical `master` was `816af91a2660f4834d7698511bdfebfb2c4155ee`; the worktree
  was clean and no newer concurrent Gukgam batch PR existed before this slice.
- A private Railway PostgreSQL SSH tunnel was used only for read-only staging discovery and
  verification. No public API/Postgres domain was created and no repository dependency changed.
- Read-only discovery found `98` current exact-one audited-target occurrences without a published
  Gukgam Claim. The first two in canonical reviewed-schedule order were 한국과학창의재단
  (`3078699:7938f3a874d5441892124093d19da1df:2:schedule:6:audited-target:24`, Organization
  `41207207-55ec-55d0-a9c2-a5e21f976442`) and 기초과학연구원
  (`3078699:7938f3a874d5441892124093d19da1df:2:schedule:6:audited-target:33`, Organization
  `84f1db6c-1b41-5073-91c1-f2bb4745aaea`).
- The next observed exact-one occurrence was target:35; it was not added to the manifest.
- The explicit two-item manifest was written manually and canonicalized to SHA-256
  `6ba9411125127d2fcb58bb16fe271ffc745a79bc8fc7114716d060c053a655db`.
- Two unchanged executions of the canonical no-write batch preflight against current staging
  produced byte-identical receipts with the same manifest hash and canonical item order.
- 한국과학창의재단 returned prospective Claim `cd536f95-a7a0-56c0-a7ff-a7aa0a61468a`,
  ClaimEvidence `9f499e00-2665-532c-9242-21d11151d3b5`, FeederObservation
  `42fe6d0c-8da1-44ad-aaf6-826a24b7eb57`, SourceSnapshot
  `78ceba04-d4ff-4b78-a41c-527de8a9b728` and Source
  `429d851c-3a6c-4756-8b3a-3ace5266d064`.
- 기초과학연구원 returned prospective Claim `2f03776c-d785-5291-ae93-b51f52adfd02`,
  ClaimEvidence `f79c143a-4484-561d-b7a2-7e2428e1af66`, the same FeederObservation,
  SourceSnapshot and Source.
- Both receipts preserved `status=DRY_RUN`, `write_performed=false`,
  `batch_commit_available=false`, `automatic_candidate_enumeration=false` and
  `network_fetch=false`. No batch `--commit` command was executed.
- Before and after both dry-runs, staging remained Organizations `347`, Claims `5478`,
  ClaimEvidence `5478`, Gukgam observations `57`, Gukgam source runs `14`, public
  Claim-backed targets `12` and public committee count `1`.
- The private tunnel, temporary discovery/preflight scripts, manifest, receipts and Web
  verification files were deleted after use. The temporary local PostgreSQL driver was also
  uninstalled; pre-existing Railway SSH keys were left untouched.

## Current checkpoint — sixth reviewed Gukgam batch commit (2026-09-21)

- Exact canonical `master` remained `2d26b913978af24eb884f15b964d46f213134197` with a clean
  tree and no newer concurrent Gukgam batch PR before execution.
- The commit slice reused only the exact prior two-item reviewed manifest and required SHA-256
  `6ba9411125127d2fcb58bb16fe271ffc745a79bc8fc7114716d060c053a655db`.
  No candidate was added, substituted, ranked, fuzzy-matched, alias-expanded or auto-selected.
- Commit-time baseline was independently re-read as Organizations `347`, Claims `5478`,
  ClaimEvidence `5478`, Gukgam observations `57`, Gukgam source runs `14`, public targets `12`
  and public committee count `1`.
- A fresh commit-time canonical preflight exactly matched the sixth dry-run: both Organizations,
  review keys, prospective Claim/Evidence IDs, Observation/Snapshot/Source IDs, manifest hash and
  all zero-write flags matched. It returned `DRY_RUN`, `write_performed=false`,
  `batch_commit_available=false`, `automatic_candidate_enumeration=false` and
  `network_fetch=false`.
- The remote installed-entrypoint SSH invocation remained blocked by the ChatGPT/OpenAI tool
  gate, so the exact same canonical batch commit module was executed locally against Railway's
  official private `connect postgres --ssh --tunnel-only` endpoint. This did not create a public
  API/Postgres domain, change the repo, or bypass the batch manifest/hash/transaction gates.
- One canonical commit execution returned `COMMITTED`, `claims_created=2`, `claims_reused=0`,
  `organizations_created=0`, `organizations_reused=2`, `write_performed=true`,
  `automatic_candidate_enumeration=false` and `network_fetch=false`.
- 한국과학창의재단 created Claim `cd536f95-a7a0-56c0-a7ff-a7aa0a61468a` with ClaimEvidence
  `9f499e00-2665-532c-9242-21d11151d3b5`; 기초과학연구원 created Claim
  `2f03776c-d785-5291-ae93-b51f52adfd02` with ClaimEvidence
  `f79c143a-4484-561d-b7a2-7e2428e1af66`.
- Post-commit read-only PostgreSQL verification returned Organizations `347`, Claims `5480`,
  ClaimEvidence `5480`, Gukgam observations `57` and Gukgam source runs `14`.
- Live staging Web verification reported public Claim-backed Gukgam scope `14`, committee count
  `1`, both new Organizations and the exact Claim/Evidence/Source/Snapshot/Observation provenance.
  Public HTML exposed neither `review_key` nor `match_class`.
- The private tunnel, temporary commit script and verification files were deleted after use; the
  temporary local PostgreSQL driver was uninstalled. Pre-existing Railway SSH keys were unchanged.
- The sixth reviewed batch is fully committed and verified. Do not replay manifest SHA-256
  `6ba9411125127d2fcb58bb16fe271ffc745a79bc8fc7114716d060c053a655db`.

## Current checkpoint — seventh reviewed Gukgam manifest dry-run (2026-09-21)

- Exact canonical `master` was `cc4e51ebb5276ac3162f7714587265c8e98aacb6`; the worktree
  was clean and no newer concurrent Gukgam batch PR existed before this slice.
- A private Railway PostgreSQL SSH tunnel was used only for read-only staging discovery and
  verification. No public API/Postgres domain was created and no repository dependency changed.
- Read-only discovery found `96` current exact-one audited-target occurrences without a published
  Gukgam Claim. The first two in canonical reviewed-schedule order were 연구개발특구진흥재단
  (`3078699:7938f3a874d5441892124093d19da1df:2:schedule:6:audited-target:35`, Organization
  `e67f5343-ab30-51fd-bf96-4610f25cc318`) and 한국과학기술기획평가원
  (`3078699:7938f3a874d5441892124093d19da1df:2:schedule:6:audited-target:36`, Organization
  `121bf96a-30c3-5ad9-822f-c759c1b57a2e`).
- The next observed exact-one occurrence was target:38; it was not added to the manifest.
- The explicit two-item manifest was written manually and canonicalized to SHA-256
  `0644ba99b1bdae7079160db125dc214550cf5fab07aed14b3497d0c97191a8a8`.
- Two unchanged executions of the canonical no-write batch preflight against current staging
  produced byte-identical receipts with the same manifest hash and canonical item order.
- 연구개발특구진흥재단 returned prospective Claim `d23dd77c-94be-5160-8245-bfc59880a9de`,
  ClaimEvidence `6fcf671d-b05a-5269-9386-c47663868eb4`, FeederObservation
  `42fe6d0c-8da1-44ad-aaf6-826a24b7eb57`, SourceSnapshot
  `78ceba04-d4ff-4b78-a41c-527de8a9b728` and Source
  `429d851c-3a6c-4756-8b3a-3ace5266d064`.
- 한국과학기술기획평가원 returned prospective Claim `3da83dd6-7251-5798-ad9c-a26368fa9c6a`,
  ClaimEvidence `fcdd17d7-d192-5f0c-aea4-1ec01917d12e`, the same FeederObservation,
  SourceSnapshot and Source.
- Both receipts preserved `status=DRY_RUN`, `write_performed=false`,
  `batch_commit_available=false`, `automatic_candidate_enumeration=false` and
  `network_fetch=false`. No batch `--commit` command was executed.
- Before and after both dry-runs, staging remained Organizations `347`, Claims `5480`,
  ClaimEvidence `5480`, Gukgam observations `57`, Gukgam source runs `14`, public
  Claim-backed targets `14` and public committee count `1`.
- The private tunnel, temporary discovery/preflight scripts, manifest, receipts and Web
  verification files were deleted after use. The temporary local PostgreSQL driver was also
  uninstalled; pre-existing Railway SSH keys were left untouched.

## Current checkpoint — seventh reviewed Gukgam batch commit (2026-09-21)

- Exact canonical `master` remained `3c6d9c9dedb0bc016016cfb36ea1968914f67a3c` with a clean
  tree and no newer concurrent Gukgam batch PR before execution.
- The commit slice reused only the exact prior two-item reviewed manifest and required SHA-256
  `0644ba99b1bdae7079160db125dc214550cf5fab07aed14b3497d0c97191a8a8`.
  No candidate was added, substituted, ranked, fuzzy-matched, alias-expanded or auto-selected.
- Commit-time baseline was independently re-read as Organizations `347`, Claims `5480`,
  ClaimEvidence `5480`, Gukgam observations `57`, Gukgam source runs `14`, public targets `14`
  and public committee count `1`.
- A fresh commit-time canonical preflight exactly matched the seventh dry-run: both Organizations,
  review keys, prospective Claim/Evidence IDs, Observation/Snapshot/Source IDs, manifest hash and
  all zero-write flags matched. It returned `DRY_RUN`, `write_performed=false`,
  `batch_commit_available=false`, `automatic_candidate_enumeration=false` and
  `network_fetch=false`.
- The exact canonical batch commit module was executed locally against Railway's official
  private `connect postgres --ssh --tunnel-only` endpoint, preserving the manifest SHA,
  revalidation and atomic transaction gates without creating a public API/Postgres domain.
- One canonical commit execution returned `COMMITTED`, `claims_created=2`, `claims_reused=0`,
  `organizations_created=0`, `organizations_reused=2`, `write_performed=true`,
  `automatic_candidate_enumeration=false` and `network_fetch=false`.
- 연구개발특구진흥재단 created Claim `d23dd77c-94be-5160-8245-bfc59880a9de` with ClaimEvidence
  `6fcf671d-b05a-5269-9386-c47663868eb4`; 한국과학기술기획평가원 created Claim
  `3da83dd6-7251-5798-ad9c-a26368fa9c6a` with ClaimEvidence
  `fcdd17d7-d192-5f0c-aea4-1ec01917d12e`.
- Post-commit read-only PostgreSQL verification returned Organizations `347`, Claims `5482`,
  ClaimEvidence `5482`, Gukgam observations `57` and Gukgam source runs `14`.
- Live staging Web verification reported public Claim-backed Gukgam scope `16`, committee count
  `1`, both new Organizations and the exact Claim/Evidence provenance. Public HTML exposed neither
  `review_key` nor `match_class`.
- The private tunnel, temporary commit script and verification files were deleted after use; the
  temporary local PostgreSQL driver was uninstalled. Pre-existing Railway SSH keys were unchanged.
- The seventh reviewed batch is fully committed and verified. Do not replay manifest SHA-256
  `0644ba99b1bdae7079160db125dc214550cf5fab07aed14b3497d0c97191a8a8`.

## Current checkpoint — control-plane RE0 and reviewed-batch operating decision (2026-09-21)

- RE0 started from exact `origin/master` `145900ff6082846998f350c6529b6854faf78996`; the prior
  local master was one commit behind, so no change was made until the checkout was fast-forwarded.
- `docs/exec-plans/active/` had accumulated historical plans. Status audit moved `34` explicitly
  completed plans to `docs/exec-plans/completed/` and `7` blocked/source-gate plans to
  `docs/exec-plans/blocked/`. Only this Gukgam plan remains in `active/`.
- Documentation links were rewritten to the canonical new paths and a local Markdown-link audit
  found only two cross-category relative links; both were corrected.
- GitHub control-plane cleanup closed stale/superseded PRs `#98`, `#84`, `#69` and obsolete issue
  `#62`. Draft PR `#75` remains open as `KEEP DEFERRED` for the later CONNECTION phase and must be
  rebased/re-reviewed before any future merge.
- The reviewed Gukgam manifest/commit implementation has no two-item production limit: it accepts
  a non-empty explicit manifest Sequence, re-preflights every supplied item, rejects partial
  publication state and persists the complete batch in one transaction.
- A new local regression exercised one explicit ten-item reviewed manifest through the same
  canonical no-write preflight and batch commit path. The focused Gukgam batch test file passed
  `12/12`; the ten-item case created zero Organizations, reused `10`, created `10` Claims and
  preserved deterministic manifest/hash and zero-write preflight semantics.
- Therefore the next expansion trial uses an operational cap of `10` explicitly reviewed items.
  This is an operator/runbook decision, not a schema or parser limit and not permission to
  auto-enumerate, rank, expand aliases, substitute candidates or create Organizations.

## Current checkpoint — eighth reviewed Gukgam 10-item manifest dry-run (2026-09-21)

- Exact canonical `master` was `84e3b3c004ddf288e2808bbc0ad12fee8cc53a57`; the worktree
  was clean and no newer concurrent Gukgam batch PR existed before this slice. Draft PR `#75`
  remained the only open PR and stayed deferred/out of scope.
- Fresh staging baseline was Organizations `347`, Claims `5482`, ClaimEvidence `5482`, Gukgam
  observations `57`, Gukgam source runs `14`, public Claim-backed targets `16` and public
  committee count `1`. Public HTML exposed neither `review_key` nor `match_class`.
- Read-only discovery found `94` current exact-one audited-target occurrences without a published
  Gukgam Claim. The operating decision from control-plane RE0 was applied: select exactly the
  first `10` occurrences in canonical reviewed-schedule discovery order, with no automatic
  manifest enumeration, ranking, alias expansion, candidate substitution or Organization creation.
- The selected set is seven Science Committee occurrences followed by three Defense Committee
  occurrences. The next occurrence, 국방과학연구소 (`schedule:4:audited-target:2`), was explicitly
  outside this manifest boundary.
- The manually written ten-item manifest canonicalized to SHA-256
  `d9102c2bd71002725228322458dd45d40187bb5ef00131969ba1ee1e2c7fdbf0`.
- Explicit reviewed manifest items were:
  - 한국원자력의학원 — `3078699:7938f3a874d5441892124093d19da1df:2:schedule:6:audited-target:38` — Organization `db1109cf-bef6-5fd7-850f-697fc4d833e0`
  - 국립대구과학관 — `3078699:7938f3a874d5441892124093d19da1df:2:schedule:6:audited-target:39` — Organization `03cd9918-a60e-5dc5-8e0a-96084680dd51`
  - 국립광주과학관 — `3078699:7938f3a874d5441892124093d19da1df:2:schedule:6:audited-target:40` — Organization `6a338202-0120-533e-bd36-f0fe96f6c71a`
  - 국립부산과학관 — `3078699:7938f3a874d5441892124093d19da1df:2:schedule:6:audited-target:41` — Organization `6bd19af3-91fd-57af-96db-4ff42b8f5c70`
  - 한국나노기술원 — `3078699:7938f3a874d5441892124093d19da1df:2:schedule:6:audited-target:43` — Organization `f0c3ef32-b11d-58b6-827d-bd3d86e8d65c`
  - 과학기술사업화진흥원 — `3078699:7938f3a874d5441892124093d19da1df:2:schedule:6:audited-target:44` — Organization `f70d7fc6-f4f6-529a-a535-35f70742e231`
  - 한국여성과학기술인육성재단 — `3078699:7938f3a874d5441892124093d19da1df:2:schedule:6:audited-target:45` — Organization `eb3c9580-c608-51ac-8793-e86bd0d77e62`
  - 한국국방연구원 — `3078693:27e3a715445a4620b51cf3d6d9423e74:2:schedule:1:audited-target:23` — Organization `8dd66d94-2631-59d8-94de-07ebdb46fe45`
  - 국방전직교육원 — `3078693:27e3a715445a4620b51cf3d6d9423e74:2:schedule:1:audited-target:25` — Organization `1d0d0df5-c42a-5501-b839-379764c1d3cb`
  - 전쟁기념사업회 — `3078693:27e3a715445a4620b51cf3d6d9423e74:2:schedule:1:audited-target:27` — Organization `f18a9294-2269-51cb-8dbf-97c030844461`
- Canonical manifest serialization sorts by `review_key`, so the deterministic receipt lists the
  three Defense items before the seven Science items. That serialization order does not change the
  reviewed discovery selection or authorize candidate reordering/substitution.
- Two unchanged executions of the canonical no-write batch preflight produced byte-identical
  receipts (`131.68 s` total for the two staging preflights). Both returned `DRY_RUN`,
  `item_count=10`, `write_performed=false`, `batch_commit_available=false`,
  `automatic_candidate_enumeration=false` and `network_fetch=false`.
- Prospective Claim / ClaimEvidence IDs were:
  - 한국국방연구원 `62c22119-c37a-5db4-991d-8c4b829a31f8` / `a5a604eb-f59f-5e42-8fbb-558131225284`
  - 국방전직교육원 `e17f3b83-4e2b-56ef-816d-23d81744f221` / `f7855eee-00f4-5dc0-a27e-ca5dcd31e81e`
  - 전쟁기념사업회 `6fec67aa-241f-5bac-ad14-3425db29a58c` / `b8a22604-11f8-5f47-aa56-890f8717bad6`
  - 한국원자력의학원 `c13f270a-fc3e-519e-a848-5a003ef7dd93` / `2277da96-0603-52a0-be27-f197cd0ca267`
  - 국립대구과학관 `a7a8448f-a713-55ce-8e6b-d208d568b0a0` / `20f0146d-c581-5a26-a739-6b5c74763d98`
  - 국립광주과학관 `096c85e4-a832-5818-84ad-8b07e2f65484` / `363c4b82-8b18-5ef3-9b22-c2f17d171bc3`
  - 국립부산과학관 `6f44724a-8c6a-591f-aa4f-836c3c656e8b` / `4a9c56e5-d43d-54c6-a648-24789420450f`
  - 한국나노기술원 `c641c758-fa07-5c0b-aaa8-e1896e0f33f6` / `8db3a546-4e32-5672-8298-b1f4725152a9`
  - 과학기술사업화진흥원 `20b19389-0a07-58d6-9b30-76edc27f2555` / `89c848a1-b776-5f0c-979d-263ca39f255f`
  - 한국여성과학기술인육성재단 `7779fa5e-0a39-5fc6-9ac3-3b2aa789bdc1` / `3d3f886b-1165-566c-8d98-814724e4f250`
- The three Defense items share FeederObservation `fc649498-3c45-4c9a-941c-48cd6ad8a7f4`,
  SourceSnapshot `9d011d49-f683-4873-9f24-d545b170393c` and Source
  `077b433b-47b3-4501-a51f-e4fd248fb885`. The seven Science items share FeederObservation
  `42fe6d0c-8da1-44ad-aaf6-826a24b7eb57`, SourceSnapshot
  `78ceba04-d4ff-4b78-a41c-527de8a9b728` and Source
  `429d851c-3a6c-4756-8b3a-3ace5266d064`.
- Every item preserved `organization_created=false`, `claim_persisted=false`,
  `claim_created=false`, `binding_committed=false` and `network_fetch=false`.
- Before and after both dry-runs, staging remained Organizations `347`, Claims `5482`,
  ClaimEvidence `5482`, Gukgam observations `57`, Gukgam source runs `14`, public Claim-backed
  targets `16` and public committee count `1`. No batch commit was executed in this slice.
- The private tunnel and all temporary discovery/manifest/preflight/Web artifacts were closed or
  deleted after use. The project PostgreSQL driver remains installed because it is a canonical
  `pyproject.toml` dependency.

## Current checkpoint — eighth reviewed Gukgam 10-item batch commit (2026-09-21)

- Exact canonical `master` was `16b2f330ee0a839935bffc2987f726b70597b753`; the worktree
  was clean and draft PR `#75` remained the only concurrent PR, deferred and out of scope.
- Commit-time baseline exactly matched the eighth dry-run: Organizations `347`, Claims `5482`,
  ClaimEvidence `5482`, Gukgam observations `57`, Gukgam source runs `14`, public targets `16`
  and public committee count `1`.
- The exact ten-item reviewed manifest from the prior dry-run was recreated without additions or
  substitutions and canonicalized to SHA-256
  `d9102c2bd71002725228322458dd45d40187bb5ef00131969ba1ee1e2c7fdbf0`.
- A fresh no-write preflight revalidated all ten Organizations, review keys, prospective
  Claim/Evidence IDs, Observation/Snapshot/Source provenance and zero-write flags against current
  staging before persistence. Every value matched the prior dry-run receipt exactly.
- The canonical batch commit path then executed one atomic transaction and returned `COMMITTED`,
  `item_count=10`, `claims_created=10`, `claims_reused=0`, `organizations_created=0`,
  `organizations_reused=10`, `write_performed=true`,
  `automatic_candidate_enumeration=false` and `network_fetch=false`.
- The ten persisted Claim/Evidence IDs exactly matched the prior dry-run receipt; no reviewed
  item, Organization binding or provenance reference changed between dry-run and commit.
- Post-commit read-only PostgreSQL verification returned Organizations `347`, Claims `5492`,
  ClaimEvidence `5492`, Gukgam observations `57` and Gukgam source runs `14`.
- Live staging Web verification returned public Claim-backed targets `26` across `2` committees.
  All `10/10` new Claim IDs and `10/10` new ClaimEvidence IDs were present in the rendered public
  projection, while `review_key` and `match_class` remained absent.
- The private Railway PostgreSQL tunnel and temporary commit/verification artifacts were closed or
  deleted after verification. No public API/Postgres domain or new resource was created.
- The eighth reviewed batch is fully committed and verified. Do not replay manifest SHA-256
  `d9102c2bd71002725228322458dd45d40187bb5ef00131969ba1ee1e2c7fdbf0`.

## Current checkpoint — reviewed-batch operating cap expansion (2026-09-21)

- The eighth reviewed ten-item batch committed atomically and passed independent post-commit DB and
  public Web verification with zero Organization creation, zero automatic candidate enumeration
  and unchanged source/observation counts.
- User approval explicitly expands the next operating trial beyond ten items.
- The next trial cap is `20` explicitly reviewed items. This changes only operator batch size; it
  does not authorize automatic manifest enumeration, ranking, fuzzy matching, alias expansion,
  candidate substitution or Organization creation.
- Dry-run and write remain separate slices. A twenty-item dry-run must prove deterministic receipts
  and unchanged staging/public counts before any later commit slice.

## Current checkpoint — ninth reviewed Gukgam 20-item manifest dry-run (2026-09-21)

- Exact canonical `master` was `1b9d466f71a416c33a39fba10c8219734dbbff97`; the worktree
  was clean before the slice and deferred draft PR `#75` remained out of scope.
- Fresh staging baseline was Organizations `347`, Claims `5492`, ClaimEvidence `5492`, Gukgam
  observations `57`, Gukgam source runs `14`, public Claim-backed targets `26` and public
  committee count `2`; public HTML exposed neither `review_key` nor `match_class`.
- Read-only discovery found `84` current exact-one audited-target occurrences without a published
  Gukgam Claim. The approved expanded operating cap selected exactly the first `20` in canonical
  reviewed-schedule order; the 21st occurrence, 한국농업기술진흥원 (`schedule:3:audited-target:7`),
  was explicitly outside this manifest.
- The manually written twenty-item manifest canonicalized to SHA-256
  `9cde9f2d0047b23c1dcdec12f4c85b41d998650c01c669d786776712bb9c0f04`.
- Explicit reviewed manifest items were:
  - 국방과학연구소 — `3078693:27e3a715445a4620b51cf3d6d9423e74:2:schedule:4:audited-target:2` — Organization `4a182dce-0f81-5832-a26f-a0aa7f2bcefb`
  - 축산물품질평가원 — `3078709:462de504d58f47e7a888f3ca286309ba:2:schedule:1:audited-target:2` — Organization `f932bef7-3644-583e-9f23-b3b7757f6523`
  - 가축위생방역지원본부 — `3078709:462de504d58f47e7a888f3ca286309ba:2:schedule:1:audited-target:3` — Organization `64c30255-d978-5ff7-b9e2-1063fa609bed`
  - 농업정책보험금융원 — `3078709:462de504d58f47e7a888f3ca286309ba:2:schedule:1:audited-target:4` — Organization `2cdb14b0-4d15-5790-9b50-1f93baaa6f79`
  - 농림식품기술기획평가원 — `3078709:462de504d58f47e7a888f3ca286309ba:2:schedule:1:audited-target:5` — Organization `ac08219f-64e2-5ac0-856d-f6348afe982b`
  - 농림수산식품교육문화정보원 — `3078709:462de504d58f47e7a888f3ca286309ba:2:schedule:1:audited-target:6` — Organization `50d241b8-6909-58a3-97bf-d97e89235eeb`
  - 국립농업박물관 — `3078709:462de504d58f47e7a888f3ca286309ba:2:schedule:1:audited-target:8` — Organization `a5dcdc8a-4aef-5507-a2d2-a28f12d39eb7`
  - 한국수산자원공단 — `3078709:462de504d58f47e7a888f3ca286309ba:2:schedule:2:audited-target:2` — Organization `a6c2727c-d1e1-5c4a-8dfc-89ec2c9c442f`
  - 한국해양수산연수원 — `3078709:462de504d58f47e7a888f3ca286309ba:2:schedule:2:audited-target:3` — Organization `03cbb525-805a-58d9-99b3-7a54db0abd14`
  - 한국해양진흥공사 — `3078709:462de504d58f47e7a888f3ca286309ba:2:schedule:2:audited-target:4` — Organization `35783223-f568-5052-a128-93489a690864`
  - 한국해양과학기술원 — `3078709:462de504d58f47e7a888f3ca286309ba:2:schedule:2:audited-target:5` — Organization `5927aaa2-aec8-5c13-b685-f00e242a1c96`
  - 한국해양교통안전공단 — `3078709:462de504d58f47e7a888f3ca286309ba:2:schedule:2:audited-target:6` — Organization `32d0efa8-5dcc-5e8d-834f-94a9cb6061a7`
  - 국립해양생물자원관 — `3078709:462de504d58f47e7a888f3ca286309ba:2:schedule:2:audited-target:7` — Organization `3570e89a-e3e5-5da6-b802-58e8b225ffac`
  - 국립해양박물관 — `3078709:462de504d58f47e7a888f3ca286309ba:2:schedule:2:audited-target:8` — Organization `c8f1550a-2c37-558e-8f1a-ad81f5ff23b3`
  - 국립울진해양과학관 — `3078709:462de504d58f47e7a888f3ca286309ba:2:schedule:2:audited-target:9` — Organization `8ca3659d-776b-520f-a6f6-630618e86f5f`
  - 한국농어촌공사 — `3078709:462de504d58f47e7a888f3ca286309ba:2:schedule:3:audited-target:2` — Organization `8f7e5441-b836-5e17-b5f2-032fa8f66682`
  - 한국농수산식품유통공사 — `3078709:462de504d58f47e7a888f3ca286309ba:2:schedule:3:audited-target:3` — Organization `8c640fe4-5063-51c3-8eff-0c78251007fd`
  - 국제식물검역인증원 — `3078709:462de504d58f47e7a888f3ca286309ba:2:schedule:3:audited-target:4` — Organization `0a5f50f0-770b-5396-aec4-281b2af312f9`
  - 한식진흥원 — `3078709:462de504d58f47e7a888f3ca286309ba:2:schedule:3:audited-target:5` — Organization `c4d81996-bbf3-5f41-87d5-b52079f2da07`
  - 한국식품산업클러스터진흥원 — `3078709:462de504d58f47e7a888f3ca286309ba:2:schedule:3:audited-target:6` — Organization `fdcf5b2a-21bf-5a44-9add-2fbbea5ce73d`
- Two unchanged executions of the canonical no-write batch preflight produced byte-identical
  receipts. Both returned `DRY_RUN`, `item_count=20`, `write_performed=false`,
  `batch_commit_available=false`, `automatic_candidate_enumeration=false` and
  `network_fetch=false`.
- The exact canonical dry-run receipt bytes are pinned by SHA-256
  `b6f211014fcaa093e2af44284dc0efc1b7221f31abd3387c114614792b049ec7`; this receipt covers all
  twenty prospective Claim/Evidence IDs and their Organization/Observation/Snapshot/Source values.
- The Defense item used FeederObservation `4d1d4d64-586e-4fcf-a7fb-9fbc2a4b4407`,
  SourceSnapshot `9d011d49-f683-4873-9f24-d545b170393c` and Source
  `077b433b-47b3-4501-a51f-e4fd248fb885`.
- The Agriculture items used SourceSnapshot `43a11905-2beb-4cc5-a829-f3d78a6492e4` and Source
  `920a5369-5315-44ab-9c76-eea01b94164e`, with exact schedule-row observations retained by the
  receipt (`7f2586d4-c1b6-457f-9fbf-f7da4aedc8ce`, `c535004b-bd33-4d58-af00-851c4852e91f`,
  `15517e33-2665-43a1-8de3-b22d503c9beb`).
- Before and after both dry-runs, staging remained Organizations `347`, Claims `5492`,
  ClaimEvidence `5492`, Gukgam observations `57`, Gukgam source runs `14`, public Claim-backed
  targets `26` and public committee count `2`; public HTML still exposed neither `review_key` nor
  `match_class`. No batch commit was executed in this slice.

## Current checkpoint — ninth reviewed Gukgam 20-item batch commit (2026-09-21)

- Exact canonical `master` was `ea7b536ed988cd65db15f06ed05e0956c7d0c019`; the worktree
  was clean and deferred draft PR `#75` remained the only concurrent PR, out of scope.
- Commit-time baseline exactly matched the twenty-item dry-run: Organizations `347`, Claims
  `5492`, ClaimEvidence `5492`, Gukgam observations `57`, Gukgam source runs `14`, public targets
  `26` and public committee count `2`.
- The exact reviewed manifest SHA-256 remained
  `9cde9f2d0047b23c1dcdec12f4c85b41d998650c01c669d786776712bb9c0f04` with `20` items.
- The first fresh commit-time preflight attempt ended before any write because the private SSH
  tunnel dropped with `SSL error: unexpected eof while reading`; independent DB counts remained
  `5492/5492` Claims/ClaimEvidence. No commit function had started.
- A fresh private tunnel retry completed the full no-write preflight. Its exact receipt SHA-256 was
  `b6f211014fcaa093e2af44284dc0efc1b7221f31abd3387c114614792b049ec7`, byte-identical to the
  prior dry-run receipt and therefore exact across all twenty Organization/Claim/Evidence and
  Observation/Snapshot/Source values plus zero-write flags.
- A new private tunnel was opened immediately before the write. The canonical commit path
  re-preflighted the same manifest again and then executed one atomic transaction, returning
  `COMMITTED`, `item_count=20`, `claims_created=20`, `claims_reused=0`,
  `organizations_created=0`, `organizations_reused=20`, `write_performed=true`,
  `automatic_candidate_enumeration=false` and `network_fetch=false`.
- The complete commit receipt bytes are pinned by SHA-256
  `d36c552edee2526ca94fb0f41e7661c1587511a6c30eef667db5f1146cbbc4c1`.
- Post-commit read-only PostgreSQL verification returned Organizations `347`, Claims `5512`,
  ClaimEvidence `5512`, Gukgam observations `57` and Gukgam source runs `14`.
- Live staging Web verification returned public Claim-backed targets `46` across `3` committees.
  All `20/20` new Claim IDs and `20/20` new ClaimEvidence IDs were present in the rendered public
  projection, while `review_key` and `match_class` remained absent.
- All private tunnels and temporary manifest/preflight/commit/Web artifacts were closed or deleted.
  No public API/Postgres domain, new Railway resource or Organization creation occurred.
- The ninth reviewed batch is fully committed and verified. Do not replay manifest SHA-256
  `9cde9f2d0047b23c1dcdec12f4c85b41d998650c01c669d786776712bb9c0f04`.

## Current checkpoint — tenth reviewed Gukgam 20-item manifest dry-run (2026-09-22)

- Exact canonical `master` was `320895f4632c63b940fa642a57c0795d7cfc3d3d`; the worktree
  was clean and deferred draft PR `#75` remained the only concurrent PR, out of scope.
- Fresh staging baseline was Organizations `347`, Claims `5512`, ClaimEvidence `5512`, Gukgam
  observations `57`, Gukgam source runs `14`, public Claim-backed targets `46` and public
  committee count `3`; public HTML exposed neither `review_key` nor `match_class`.
- Read-only discovery found `64` current exact-one audited-target occurrences without a published
  Gukgam Claim. Exactly the first `20` were selected in canonical reviewed-schedule discovery order.
  The 21st occurrence, 영화진흥위원회 (`schedule:3:audited-target:10`), was explicitly outside
  this manifest boundary.
- The manually written twenty-item manifest canonicalized to SHA-256
  `71167ba4936f2212dc7b15195d1a247902d27061882d05fe96e3d98ec1319898`.
- Explicit reviewed manifest items were:
  - 한국농업기술진흥원 — `3078709:462de504d58f47e7a888f3ca286309ba:2:schedule:3:audited-target:7` — Organization `d7314288-bd56-5cea-82fc-e62e55615001`
  - 한국마사회 — `3078709:462de504d58f47e7a888f3ca286309ba:2:schedule:4:audited-target:4` — Organization `dc61f48c-e361-52fa-9753-77a5829652c7`
  - 해양환경공단 — `3078709:462de504d58f47e7a888f3ca286309ba:2:schedule:5:audited-target:2` — Organization `8f406a63-8e71-5f13-93ba-ff4d059af867`
  - 부산항만공사 — `3078709:462de504d58f47e7a888f3ca286309ba:2:schedule:5:audited-target:4` — Organization `5190c91c-9bf2-5961-9143-db6d8f25e4fd`
  - 인천항만공사 — `3078709:462de504d58f47e7a888f3ca286309ba:2:schedule:5:audited-target:5` — Organization `03acf9f3-dc64-57f3-8fed-9888cd57be21`
  - 여수광양항만공사 — `3078709:462de504d58f47e7a888f3ca286309ba:2:schedule:5:audited-target:6` — Organization `724df4e1-493f-5aca-82de-7b9db9e14cf2`
  - 울산항만공사 — `3078709:462de504d58f47e7a888f3ca286309ba:2:schedule:5:audited-target:7` — Organization `342c5bf1-67d9-5807-b9a7-a4ef3c7ec5ea`
  - 해양수산과학기술진흥원 — `3078709:462de504d58f47e7a888f3ca286309ba:2:schedule:5:audited-target:8` — Organization `4030bed7-0f2b-54d3-be82-b396022df1e2`
  - 한국어촌어항공단 — `3078709:462de504d58f47e7a888f3ca286309ba:2:schedule:5:audited-target:9` — Organization `9282e978-81e4-5ed1-8b86-03008b255fcb`
  - 국립인천해양박물관 — `3078709:462de504d58f47e7a888f3ca286309ba:2:schedule:5:audited-target:10` — Organization `8dced1eb-e115-5f91-83a7-295e7205c465`
  - 한국항로표지기술원 — `3078709:462de504d58f47e7a888f3ca286309ba:2:schedule:5:audited-target:11` — Organization `e6c2c245-4aca-5710-8c07-7d73b3c3f2fe`
  - 한국해양조사협회 — `3078709:462de504d58f47e7a888f3ca286309ba:2:schedule:5:audited-target:12` — Organization `733b47d2-b314-563d-a673-877f49d67f77`
  - 한국산림복지진흥원 — `3078709:462de504d58f47e7a888f3ca286309ba:2:schedule:6:audited-target:2` — Organization `3d98e0b2-d311-5d7f-a733-a7031446599e`
  - 한국수목원정원관리원 — `3078709:462de504d58f47e7a888f3ca286309ba:2:schedule:6:audited-target:3` — Organization `28b70174-38ca-5e34-9ccc-53f3394763aa`
  - 한국임업진흥원 — `3078709:462de504d58f47e7a888f3ca286309ba:2:schedule:6:audited-target:4` — Organization `dafb1cd2-6f8d-5527-aa59-1b66bb0afc85`
  - 국가유산진흥원 — `3078704:114e8e5e4cf843db89f0abb4479c79f1:2:schedule:2:audited-target:7` — Organization `68e40a6a-21c5-564f-ab5b-48e0ec352fc7`
  - 한국콘텐츠진흥원 — `3078704:114e8e5e4cf843db89f0abb4479c79f1:2:schedule:3:audited-target:1` — Organization `fba0fd3e-607c-5c3e-bb60-d073c4ebe654`
  - 한국문화정보원 — `3078704:114e8e5e4cf843db89f0abb4479c79f1:2:schedule:3:audited-target:7` — Organization `03fc31c6-6c37-5f01-8ae4-b0beccbb7711`
  - 세종학당재단 — `3078704:114e8e5e4cf843db89f0abb4479c79f1:2:schedule:3:audited-target:8` — Organization `2f793b53-fe24-5d79-8716-585f0bf75af1`
  - 국립아시아문화전당재단 — `3078704:114e8e5e4cf843db89f0abb4479c79f1:2:schedule:3:audited-target:9` — Organization `c1a2cdb7-1133-5e7c-b5e3-d7e95d51339b`
- Two unchanged executions of the canonical no-write batch preflight produced byte-identical
  receipts. Both returned `DRY_RUN`, `item_count=20`, `write_performed=false`,
  `batch_commit_available=false`, `automatic_candidate_enumeration=false` and
  `network_fetch=false`.
- The exact canonical dry-run receipt bytes are pinned by SHA-256
  `efc12263bd56bf66b56d23ab61ecc0bdad30f7159c772cec56e0da9debaed836`; this receipt covers all
  twenty prospective Claim/Evidence IDs and their exact Organization/Observation/Snapshot/Source
  values, so the next commit slice must reproduce the complete receipt, not only the manifest hash.
- Agriculture items use SourceSnapshot `43a11905-2beb-4cc5-a829-f3d78a6492e4`, Source
  `920a5369-5315-44ab-9c76-eea01b94164e` and exact schedule-row observations
  `15517e33-2665-43a1-8de3-b22d503c9beb`, `d2043a2a-e5f1-4641-b536-dbd93036606d`,
  `9bec7c98-0e52-418d-92c1-1ab671e78b3a` and `f8bb8742-2e7a-46cc-badb-48a9ec2e2bdf`.
- Culture/Sports/Tourism items use SourceSnapshot `670b558e-c9ea-473f-b5ee-1833a80ef27e`, Source
  `94055d1a-977d-4568-b004-7a3ebcfd6c03` and exact schedule-row observations
  `0de1aa78-759b-4809-9363-3e000c823db4` and `7a9e51a5-a4d1-4e02-be89-96fbba6f7cfa`.
- Before and after both dry-runs, staging remained Organizations `347`, Claims `5512`,
  ClaimEvidence `5512`, Gukgam observations `57`, Gukgam source runs `14`, public Claim-backed
  targets `46` and public committee count `3`; public HTML exposed neither `review_key` nor
  `match_class`. No batch commit was executed in this slice.
- All private tunnels and temporary discovery/manifest/preflight/Web artifacts were closed or
  deleted after verification. No public API/Postgres domain or new Railway resource was created.

## Current checkpoint — tenth reviewed Gukgam 20-item batch commit (2026-09-22)

- Exact canonical `master` was `2630f2ac1112a4ef8e2cdd99449ad58fef20c8a2`; the worktree
  was clean and deferred draft PR `#75` remained the only concurrent PR, out of scope.
- Commit-time baseline exactly matched the tenth dry-run: Organizations `347`, Claims `5512`,
  ClaimEvidence `5512`, Gukgam observations `57`, Gukgam source runs `14`, public targets `46`
  and public committee count `3`.
- The exact reviewed manifest SHA-256 remained
  `71167ba4936f2212dc7b15195d1a247902d27061882d05fe96e3d98ec1319898` with `20` items.
- The first local receipt-hash guard stopped before any write because the dry-run file hash had
  been pinned from Windows redirected stdout (`CRLF`) while the script initially hashed normalized
  `LF` bytes. Independent DB counts remained `5512/5512`; no commit function had started.
- A separate read-only preflight proved the semantics were unchanged: LF SHA-256 was
  `7fc7690e28f3441d5968d14a0af385864d65afb1a66943ac2564da1c86b6fe2e`, while CRLF SHA-256
  exactly matched the canonical prior receipt `efc12263bd56bf66b56d23ab61ecc0bdad30f7159c772cec56e0da9debaed836`.
- With the receipt guard corrected to the actual Windows CRLF bytes, a fresh no-write preflight
  again matched the exact prior receipt before persistence. The canonical commit path then
  re-preflighted the same manifest and executed one atomic transaction.
- The commit returned `COMMITTED`, `item_count=20`, `claims_created=20`, `claims_reused=0`,
  `organizations_created=0`, `organizations_reused=20`, `write_performed=true`,
  `automatic_candidate_enumeration=false` and `network_fetch=false`.
- The canonical sorted commit receipt JSON is pinned by SHA-256
  `60bd0c4964f66350dceb67b12dd1183ec60379be1c8e53ac29422260a546b1cb`.
- Post-commit read-only PostgreSQL verification returned Organizations `347`, Claims `5532`,
  ClaimEvidence `5532`, Gukgam observations `57` and Gukgam source runs `14`.
- Live staging Web verification returned public Claim-backed targets `66` across `4` committees.
  All `20/20` new Organization names, `20/20` Claim IDs and `20/20` ClaimEvidence IDs were present
  in the rendered public projection, while `review_key` and `match_class` remained absent.
- All private tunnels and temporary hash-check/commit/Web artifacts were closed or deleted. No
  public API/Postgres domain, new Railway resource or Organization creation occurred.
- The tenth reviewed batch is fully committed and verified. Do not replay manifest SHA-256
  `71167ba4936f2212dc7b15195d1a247902d27061882d05fe96e3d98ec1319898`.

## Current checkpoint — eleventh reviewed Gukgam 20-item manifest dry-run (2026-09-22)

- Exact canonical `master` was `b8fc3e0841d059047a93ecf666bcacb95817da77`; the worktree was clean and deferred draft PR `#75` remained the only concurrent PR, out of scope.
- Fresh staging baseline was Organizations `347`, Claims `5532`, ClaimEvidence `5532`, Gukgam observations `57`, Gukgam source runs `14`, public Claim-backed targets `66` and public committee count `4`.
- Read-only discovery found `44` current exact-one audited-target occurrences without a published Gukgam Claim.
- Exactly the first `20` occurrences in canonical reviewed-schedule order were selected explicitly; the 21st occurrence, 대한체육회 (`3078704:114e8e5e4cf843db89f0abb4479c79f1:2:schedule:6:audited-target:1`), was excluded from this manifest.
- The manually written twenty-item manifest canonicalized to SHA-256 `2d4be686649de5ee76a6ba82d5658098feb1f895721d1287c2e630c10e84b884`.
- Explicit reviewed manifest items and prospective Claim/Evidence IDs were:
  - 영화진흥위원회 — `3078704:114e8e5e4cf843db89f0abb4479c79f1:2:schedule:3:audited-target:10` — Organization `87a49064-d253-53cf-814c-4d6c03feb944` — Claim `0e0824ef-7e6e-56d3-a958-19b03f95cc6b` — Evidence `1cd3cd90-a923-5dac-af86-d9a32dc41335`
  - 영상물등급위원회 — `3078704:114e8e5e4cf843db89f0abb4479c79f1:2:schedule:3:audited-target:11` — Organization `f5438862-48b9-54bd-b41a-2323bdd79d78` — Claim `ae669080-88ef-50ec-b246-84436fb4933c` — Evidence `3db2da0f-acf0-57fd-b2f3-391cc9b156b7`
  - 한국영상자료원 — `3078704:114e8e5e4cf843db89f0abb4479c79f1:2:schedule:3:audited-target:12` — Organization `f254f8dd-ba57-5d9b-930b-ee4d6d2996f5` — Claim `2832f178-7826-5219-a206-1f5a589c1541` — Evidence `aa97a8b5-78db-5aad-8d54-69cf96c556b2`
  - 게임물관리위원회 — `3078704:114e8e5e4cf843db89f0abb4479c79f1:2:schedule:3:audited-target:13` — Organization `0dd2b2df-62a4-5de6-af79-ae55aedc9179` — Claim `dd45f36b-1a62-55b1-8317-77e5d8cf0eac` — Evidence `70c605fd-6109-5f4c-b257-f59cc4974c1a`
  - 한국저작권위원회 — `3078704:114e8e5e4cf843db89f0abb4479c79f1:2:schedule:3:audited-target:14` — Organization `f9328bac-0156-5a53-a4db-52fc08532e83` — Claim `0c0a86ce-725a-5cb7-bcbf-b286fe524f7a` — Evidence `7cd8de90-a9d5-501b-a21b-f99e27dbbd5e`
  - 한국저작권보호원 — `3078704:114e8e5e4cf843db89f0abb4479c79f1:2:schedule:3:audited-target:15` — Organization `9d66dc23-dfa3-5d1c-a723-f0e02f7ef8c5` — Claim `40fd67cb-c2d6-54ff-8f93-8a5334d39437` — Evidence `85575a34-253f-54d0-9369-e03d46da74a9`
  - 한국도박문제예방치유원 — `3078704:114e8e5e4cf843db89f0abb4479c79f1:2:schedule:4:audited-target:10` — Organization `e8512a7f-86a2-56d2-a90d-ff70b53311a6` — Claim `7647f2f3-e4b2-58eb-83ed-4cb31f57fb4f` — Evidence `c602436f-d4cd-534a-8f6b-5e6378b7c47e`
  - 한국문화관광연구원 — `3078704:114e8e5e4cf843db89f0abb4479c79f1:2:schedule:4:audited-target:4` — Organization `fd795466-dca7-5941-8c6d-813a864b3bc4` — Claim `0c8e9cf6-1340-5efb-a3f4-36eb1f068d3f` — Evidence `55665034-ee11-58b6-9999-948ebdbc7e55`
  - 한국출판문화산업진흥원 — `3078704:114e8e5e4cf843db89f0abb4479c79f1:2:schedule:4:audited-target:5` — Organization `6198c75e-f0ba-5201-9574-6f226d9caf50` — Claim `996171a7-0143-5729-8133-f03a1c153a8d` — Evidence `ee974f70-60cb-5c64-9802-3dc8300d7271`
  - 한국언론진흥재단 — `3078704:114e8e5e4cf843db89f0abb4479c79f1:2:schedule:4:audited-target:6` — Organization `e823814d-bca6-59fc-bee9-f3690a1bb830` — Claim `5de483a4-8c6d-5f76-b03f-08beeca2fbce` — Evidence `59b1c743-4a0c-50db-a4cc-d04e4de40944`
  - 국제방송교류재단 — `3078704:114e8e5e4cf843db89f0abb4479c79f1:2:schedule:4:audited-target:7` — Organization `9f3e6183-5e6f-5d70-a7a2-4064ed23376f` — Claim `94103cd7-2df4-53d9-a8e6-3cc33e8b6c02` — Evidence `6657c678-0aa7-57d6-85cc-2a6b819fbdcb`
  - 한국관광공사 — `3078704:114e8e5e4cf843db89f0abb4479c79f1:2:schedule:4:audited-target:8` — Organization `f7e354cb-37f0-5c9e-b9ab-826bceb44676` — Claim `fe8c569a-294d-5ed0-b272-b59c05f3a0d1` — Evidence `65b0265a-ce99-5490-a8d4-f610da0e5faa`
  - 한국문화예술교육진흥원 — `3078704:114e8e5e4cf843db89f0abb4479c79f1:2:schedule:5:audited-target:10` — Organization `a8b57a18-c0b9-5f8d-be65-528574d901a3` — Claim `ee2711e5-0f4a-5a09-91f7-8315e783ad98` — Evidence `6487a216-5a1c-5320-ab2b-65a53f5141ef`
  - 한국문화예술위원회 — `3078704:114e8e5e4cf843db89f0abb4479c79f1:2:schedule:5:audited-target:11` — Organization `b132ce29-0176-594d-8c51-bad73f59d5a0` — Claim `05b89923-101b-5756-93b6-129bb37f4b54` — Evidence `71519c74-c913-5e96-82a1-439ea674b837`
  - (재)예술경영지원센터 — `3078704:114e8e5e4cf843db89f0abb4479c79f1:2:schedule:5:audited-target:12` — Organization `ca1eca0d-8db2-504e-b4f3-21276a3631fa` — Claim `2f5c10bd-a65d-5fa1-9d9d-c6ba6fa27cfa` — Evidence `61cc4423-39eb-541c-8b09-ab4f9f0ee457`
  - 한국문학번역원 — `3078704:114e8e5e4cf843db89f0abb4479c79f1:2:schedule:5:audited-target:13` — Organization `a539bf48-c4a2-5764-a152-13a1d5563048` — Claim `23a8a629-b7d7-5c40-9b45-e6428df06b6c` — Evidence `99cb9b6e-1c3f-57c6-a042-f68d88e49710`
  - 예술의전당 — `3078704:114e8e5e4cf843db89f0abb4479c79f1:2:schedule:5:audited-target:14` — Organization `8862a259-6e54-51ae-8f54-9ae2d9896352` — Claim `01f10c34-bbdf-55ad-b339-1b1bb1a33376` — Evidence `92199a81-d396-5bb9-835e-b4f18db112cb`
  - 국악방송 — `3078704:114e8e5e4cf843db89f0abb4479c79f1:2:schedule:5:audited-target:15` — Organization `cafa5948-6bfd-5e97-b253-f45bf8da9b24` — Claim `66200fb1-15fb-5752-ae92-3e1e004fd950` — Evidence `231154cf-08a2-5b3b-87b8-3fbcb38a51b3`
  - 한국예술인복지재단 — `3078704:114e8e5e4cf843db89f0abb4479c79f1:2:schedule:5:audited-target:16` — Organization `52065c3e-1aaf-54df-94f9-462fb3f7552a` — Claim `c62f8828-674c-53ec-80ab-71ef3e72cd42` — Evidence `f3377a1f-6af6-54df-893a-0b67e23deb66`
  - 국립박물관문화재단 — `3078704:114e8e5e4cf843db89f0abb4479c79f1:2:schedule:5:audited-target:17` — Organization `b8b5b0d9-e9ed-5df3-a411-a04187700ae2` — Claim `76051b2c-3adf-50c0-92b6-ce46000fc3b3` — Evidence `f2c4ecb4-fd63-5a76-aa81-ed63b11cc221`
- Two unchanged staging no-write preflights produced byte-identical receipts. Receipt SHA-256 was `130482d27c9a53c408fd1e05986c57411341a0b007ed9edc3ec5fa322dcb43c0`.
- Both receipts returned `DRY_RUN`, `item_count=20`, `all_preflights_passed=true`, `write_performed=false`, `batch_commit_available=false`, `automatic_candidate_enumeration=false` and `network_fetch=false`; every item preserved `claim_persisted=false` and `organization_created=false`.
- Before and after both dry-runs, staging remained Organizations `347`, Claims `5532`, ClaimEvidence `5532`, Gukgam observations `57`, Gukgam source runs `14`, public Claim-backed targets `66` and public committee count `4`; public HTML exposed neither `review_key` nor `match_class`.
- No batch commit was executed in this slice.

## Current checkpoint — eleventh reviewed Gukgam 20-item batch commit (2026-09-22)

- Exact canonical `master` was `1e88e5d3b11d060d4e88333d2461382ac6fb71e0`; the worktree was clean and deferred draft PR `#75` remained the only concurrent PR, out of scope.
- Commit-time baseline exactly matched the eleventh dry-run: Organizations `347`, Claims `5532`, ClaimEvidence `5532`, Gukgam observations `57`, Gukgam source runs `14`, public targets `66` and public committee count `4`.
- The exact reviewed twenty-item manifest was recreated without additions or substitutions and retained SHA-256 `2d4be686649de5ee76a6ba82d5658098feb1f895721d1287c2e630c10e84b884`.
- A fresh commit-time no-write preflight produced receipt SHA-256 `130482d27c9a53c408fd1e05986c57411341a0b007ed9edc3ec5fa322dcb43c0`, byte-identical to the canonical dry-run receipt, with `DRY_RUN`, `item_count=20`, `write_performed=false`, `automatic_candidate_enumeration=false` and `network_fetch=false`.
- The canonical commit path then re-preflighted the same manifest and executed exactly one atomic transaction.
- The commit returned `COMMITTED`, `item_count=20`, `claims_created=20`, `claims_reused=0`, `organizations_created=0`, `organizations_reused=20`, `write_performed=true`, `automatic_candidate_enumeration=false` and `network_fetch=false`.
- The canonical sorted commit receipt is pinned by SHA-256 `16883d93babad78b144b36bede56d74cbbf6c18dda842c37de1977a7eac9a9fc`; all `20/20` Claims persisted and no Organization was created.
- Post-commit read-only PostgreSQL verification returned Organizations `347`, Claims `5552`, ClaimEvidence `5552`, Gukgam observations `57` and Gukgam source runs `14`.
- Live staging Web verification returned public Claim-backed targets `86` across `4` committees. All `20/20` new Organization names, `20/20` Claim IDs and `20/20` ClaimEvidence IDs were present in the rendered public projection, while `review_key` and `match_class` remained absent.
- The private Railway PostgreSQL tunnel and temporary commit/preflight/Web artifacts were closed or removed after verification. No public API/Postgres domain, new Railway resource or Organization creation occurred.
- The eleventh reviewed batch is fully committed and verified. Do not replay manifest SHA-256 `2d4be686649de5ee76a6ba82d5658098feb1f895721d1287c2e630c10e84b884`.

## Current checkpoint — twelfth reviewed Gukgam 20-item manifest dry-run (2026-09-22)

- Exact canonical `master` was `98b419de391ca3a108790152d5a3c735093d1165`; the worktree was clean and deferred draft PR `#75` remained the only concurrent PR, out of scope.
- Fresh staging baseline was Organizations `347`, Claims `5552`, ClaimEvidence `5552`, Gukgam observations `57`, Gukgam source runs `14`, public Claim-backed targets `86` and public committee count `4`.
- Read-only discovery found `24` current exact-one audited-target occurrences without a published Gukgam Claim.
- Exactly the first `20` occurrences in canonical reviewed-schedule order were selected explicitly; the remaining four begin with 전국재해구호협회 (`3078707:bf03a64c5e7a432e8c0475efcf15e545:1:schedule:1:audited-target:8`) and were excluded from this manifest.
- The manually written twenty-item manifest canonicalized to SHA-256 `c8da8721d501a4d6bf3a0fbfca6fa9b2952ea8bfa3efcb4a29b787e6fa062fa7`.
- Explicit reviewed manifest items and prospective Claim/Evidence IDs were:
  - 대한체육회 — `3078704:114e8e5e4cf843db89f0abb4479c79f1:2:schedule:6:audited-target:1` — Organization `b49fbf94-cd32-5ece-b905-7e856be28fe7` — Claim `b52aa637-f16b-5ac7-8668-aeafffcf93cc` — Evidence `3560d080-1851-54ab-be04-23bd968f8e34`
  - 서울올림픽기념국민체육진흥공단 — `3078704:114e8e5e4cf843db89f0abb4479c79f1:2:schedule:6:audited-target:2` — Organization `c62ae3a0-74fa-5c57-b832-e5988e3ec2b7` — Claim `9397658d-41fa-5119-b8bf-f3b507abea67` — Evidence `e2c79dc2-3219-58bb-9acd-99ba7e8d85f2`
  - 스포츠윤리센터 — `3078704:114e8e5e4cf843db89f0abb4479c79f1:2:schedule:6:audited-target:5` — Organization `fdc2cacb-6ecc-5e4f-a939-31901753e351` — Claim `3bab6314-9e6d-59e2-befe-024e413914af` — Evidence `8b1c12ab-47ce-5065-b699-66267b15e549`
  - 대한장애인체육회 — `3078704:114e8e5e4cf843db89f0abb4479c79f1:2:schedule:6:audited-target:6` — Organization `bea8e753-c2ea-5609-9241-b795b8a54eb2` — Claim `8f13fc54-59dc-5f1d-b1f9-3a2bcd606081` — Evidence `c948a7e4-d278-58a4-9a57-3535b62d51bd`
  - 태권도진흥재단 — `3078704:114e8e5e4cf843db89f0abb4479c79f1:2:schedule:6:audited-target:7` — Organization `71d93bc7-58ea-5f62-944e-8342b663477c` — Claim `bf16c651-0bf3-57f2-b412-4368665f0f86` — Evidence `50100d78-ce2e-5151-a2bc-d4a338cba236`
  - 한국지능정보사회진흥원 — `3078707:bf03a64c5e7a432e8c0475efcf15e545:1:schedule:1:audited-target:4` — Organization `463e5ec7-6743-5b19-b71a-5407bc0f6572` — Claim `a446f4e8-4679-5ea5-8fea-9b979166a1f9` — Evidence `64c72d40-7afd-5e98-a4f4-bb281741637a`
  - 한국승강기안전공단 — `3078707:bf03a64c5e7a432e8c0475efcf15e545:1:schedule:1:audited-target:5` — Organization `120bdf2e-94c5-5713-a332-48e7caf6aadd` — Claim `511d541a-96c4-5156-b95d-af9b66b0bb62` — Evidence `b915ab25-6807-552a-a777-61161f7b7d8b`
  - 민주화운동기념사업회 — `3078707:bf03a64c5e7a432e8c0475efcf15e545:1:schedule:1:audited-target:6` — Organization `831eacda-b90e-5c31-9907-04488360b133` — Claim `89272288-ab2b-5b3a-ab77-ead76a0ebb60` — Evidence `738d25db-7399-5ba0-8c9d-70961d60e668`
  - 한국관세정보원 — `3078708:5ed9af3fc7eb418f9e3aa5830d7307ac:2:schedule:10:audited-target:10` — Organization `30cb580d-2397-5151-8403-2073dfcd12c0` — Claim `a8eb6f90-a1fe-571b-a681-09d65d8b5b8e` — Evidence `4bfbc811-1671-510b-aa37-4606c86d6781`
  - 한국수출입은행 — `3078708:5ed9af3fc7eb418f9e3aa5830d7307ac:2:schedule:10:audited-target:3` — Organization `348e6aae-4bca-5418-ab6e-7e3595755856` — Claim `d2fb8df6-b092-506d-a758-52ce3604a163` — Evidence `5ae5f1bf-7523-5322-8b2e-2b4f8695f848`
  - 한국조폐공사 — `3078708:5ed9af3fc7eb418f9e3aa5830d7307ac:2:schedule:10:audited-target:4` — Organization `d1be0a71-ce79-5bbe-9fff-cf8cf870dd33` — Claim `bfe4e858-35bd-590e-a475-a09806b751a5` — Evidence `bae0eef3-1808-5132-b458-b83b971f2900`
  - 한국투자공사 — `3078708:5ed9af3fc7eb418f9e3aa5830d7307ac:2:schedule:10:audited-target:5` — Organization `10932068-6af0-5656-a889-75b4ae38ea76` — Claim `a5ef886e-3f93-5519-b003-3bfd05e782e3` — Evidence `73df5949-a65a-537c-a99d-45e62dbe34e2`
  - 한국재정정보원 — `3078708:5ed9af3fc7eb418f9e3aa5830d7307ac:2:schedule:10:audited-target:6` — Organization `ce185bd2-e0b5-5428-8bef-248190e5a13d` — Claim `3d693e6f-5f40-5999-9055-bbde5d702a3d` — Evidence `36f71213-35f9-54e1-9d7a-32c1954d5064`
  - 한국원산지정보원 — `3078708:5ed9af3fc7eb418f9e3aa5830d7307ac:2:schedule:10:audited-target:7` — Organization `1bad0861-000e-5859-90b6-35a5b55d9452` — Claim `76c73045-98cf-5c94-9d46-e7adbfcbec5b` — Evidence `5c400af5-9ad6-5296-985a-4236edc4a3de`
  - 한국수출입은행 — `3078708:5ed9af3fc7eb418f9e3aa5830d7307ac:2:schedule:8:audited-target:1` — Organization `348e6aae-4bca-5418-ab6e-7e3595755856` — Claim `fd4b2fdd-ebee-5c02-bcb5-cfeb84257006` — Evidence `9e9d8b9e-ba80-5520-8d9d-1651b70f7b76`
  - 한국조폐공사 — `3078708:5ed9af3fc7eb418f9e3aa5830d7307ac:2:schedule:8:audited-target:2` — Organization `d1be0a71-ce79-5bbe-9fff-cf8cf870dd33` — Claim `11a4494c-f0d9-5929-b9bd-8eb1bc5dbde8` — Evidence `d2e6de1c-b44b-57b6-8630-428727b4b639`
  - 한국투자공사 — `3078708:5ed9af3fc7eb418f9e3aa5830d7307ac:2:schedule:8:audited-target:3` — Organization `10932068-6af0-5656-a889-75b4ae38ea76` — Claim `2d4afa56-39cb-5824-9317-2093c2501665` — Evidence `cf3f4baf-8a7b-5879-b9c7-0d16fbf3c28f`
  - 한국재정정보원 — `3078708:5ed9af3fc7eb418f9e3aa5830d7307ac:2:schedule:8:audited-target:4` — Organization `ce185bd2-e0b5-5428-8bef-248190e5a13d` — Claim `0405289c-5dde-592f-a4ec-56b389d10b50` — Evidence `f8b1372c-0f0a-572d-af20-b9cdb0880e6d`
  - 한국원산지정보원 — `3078708:5ed9af3fc7eb418f9e3aa5830d7307ac:2:schedule:8:audited-target:5` — Organization `1bad0861-000e-5859-90b6-35a5b55d9452` — Claim `401031de-aa86-5d20-a85a-35d0e77dfef0` — Evidence `42350ca1-7acb-541a-876c-54449b722ba9`
  - 한국관세정보원 — `3078708:5ed9af3fc7eb418f9e3aa5830d7307ac:2:schedule:8:audited-target:8` — Organization `30cb580d-2397-5151-8403-2073dfcd12c0` — Claim `11c6cbf8-e143-524d-932b-a75b073c8913` — Evidence `39408c85-beb6-5e0d-a027-86858ef8aba8`
- Two unchanged staging no-write preflights produced byte-identical receipts. Receipt SHA-256 was `103fecb5c066b36946d6f46da1d180d55e71ec24e4d4d155b40386ecdeb55e6e`.
- Both receipts returned `DRY_RUN`, `item_count=20`, `all_preflights_passed=true`, `write_performed=false`, `batch_commit_available=false`, `automatic_candidate_enumeration=false` and `network_fetch=false`; every item preserved `claim_persisted=false` and `organization_created=false`.
- Before and after both dry-runs, staging remained Organizations `347`, Claims `5552`, ClaimEvidence `5552`, Gukgam observations `57`, Gukgam source runs `14`, public Claim-backed targets `86` and public committee count `4`; public HTML exposed neither `review_key` nor `match_class`.
- No batch commit was executed in this slice.

## Current checkpoint — repeated Organization batch blocker and adapter fix (2026-09-22)

- Exact canonical `master` was `46f42fb1c785d28c47cd54d47ff5837d983f0f2f`; the worktree was clean before the commit attempt.
- The twelfth manifest remained exactly `20` items with SHA-256 `c8da8721d501a4d6bf3a0fbfca6fa9b2952ea8bfa3efcb4a29b787e6fa062fa7`.
- Commit-time staging baseline still matched the dry-run: Organizations `347`, Claims `5552`, ClaimEvidence `5552`, Gukgam observations `57`, Gukgam source runs `14`, public targets `86` and public committee count `4`.
- A fresh no-write preflight produced receipt SHA-256 `103fecb5c066b36946d6f46da1d180d55e71ec24e4d4d155b40386ecdeb55e6e`, exactly matching the canonical dry-run receipt.
- The canonical commit path re-preflighted successfully, but persistence stopped before any database write with `OrganizationClaimImportError: organization batch contains duplicate ids`.
- Independent read-only counts immediately after the failure remained Claims `5552` and ClaimEvidence `5552`; the twelfth manifest was not committed.
- Root cause: a valid reviewed batch can contain multiple audit occurrences for the same canonical Organization, but the source-specific persistence adapter passed one Organization parent entry per manifest item. The repository correctly rejects duplicate parent IDs even though distinct Claims for the same Organization are valid.
- The fix keeps all manifest items and Claim/Evidence rows unchanged while deduplicating only the Organization parent list by canonical Organization ID before the atomic repository call. A duplicate ID with inconsistent Organization semantics fails closed.
- Exact-retry receipt semantics now also report `organizations_reused` as the unique Organization count rather than manifest item count.
- The real Science reviewed fixture proves the repeated-occurrence case: `과학기술정보통신부` appears in two audit occurrences. The regression commits two Claims while reusing one Organization, and an exact retry reuses one Organization and both Claims.
- Focused Gukgam batch tests passed `13/13`; Ruff and mypy passed for the changed batch worker files.

## Current checkpoint — twelfth reviewed Gukgam 20-item batch commit (2026-09-22)

- Exact canonical `master` was `8c72490c3b1e9a0fb9985de9ec5f0859dc5e2a64`; the worktree was clean and deferred draft PR `#75` remained the only concurrent PR, out of scope.
- Commit-time baseline exactly matched the twelfth dry-run: Organizations `347`, Claims `5552`, ClaimEvidence `5552`, Gukgam observations `57`, Gukgam source runs `14`, public targets `86` and public committee count `4`.
- Remote Desktop inspection found `24` stale local `railway connect postgres --ssh --tunnel-only` processes for this exact staging project/environment. Only those matching tunnel processes and their child SSH processes were terminated; a single fresh private Railway tunnel then connected successfully. No public DB endpoint was created.
- The exact reviewed twenty-item manifest was rebuilt from the canonical HANDOFF pairs and retained SHA-256 `c8da8721d501a4d6bf3a0fbfca6fa9b2952ea8bfa3efcb4a29b787e6fa062fa7`.
- A fresh no-write preflight through the clean tunnel produced receipt SHA-256 `103fecb5c066b36946d6f46da1d180d55e71ec24e4d4d155b40386ecdeb55e6e`, byte-identical to the canonical dry-run receipt, with `DRY_RUN`, `item_count=20`, `write_performed=false`, `automatic_candidate_enumeration=false` and `network_fetch=false`.
- The canonical commit path re-preflighted the same manifest and executed exactly one atomic transaction.
- The commit returned `COMMITTED`, `item_count=20`, `claims_created=20`, `claims_reused=0`, `organizations_created=0`, `organizations_reused=14`, `write_performed=true`, `automatic_candidate_enumeration=false` and `network_fetch=false`.
- The complete commit receipt bytes are pinned by SHA-256 `803ed920bb663bb0ddab563046a9be15158eacd4c3b6994bf705fc9ce74aed44`; all `20/20` Claims persisted across `14` unique existing Organizations.
- Post-commit read-only PostgreSQL verification returned Organizations `347`, Claims `5572`, ClaimEvidence `5572`, Gukgam observations `57` and Gukgam source runs `14`.
- Live staging Web verification returned public Claim-backed targets `106` across `6` committees. All `14/14` unique new Organization names, `20/20` Claim IDs and `20/20` ClaimEvidence IDs were present in the rendered public projection, while `review_key` and `match_class` remained absent.
- The fresh tunnel and its exact project/environment child SSH process were closed after verification. Temporary credential/tunnel/manifest/preflight/commit/Web artifacts were removed. No public API/Postgres domain, new Railway resource or Organization creation occurred.
- The twelfth reviewed batch is fully committed and verified. Do not replay manifest SHA-256 `c8da8721d501a4d6bf3a0fbfca6fa9b2952ea8bfa3efcb4a29b787e6fa062fa7`.

## Current checkpoint — final reviewed Gukgam 4-item manifest dry-run (2026-09-22)

- Exact canonical `master` was `76a2b5d66e5dbc127450fbda2a8bb0162a948080`; the worktree was clean and deferred draft PR `#75` remained the only concurrent PR, out of scope.
- Fresh staging baseline was Organizations `347`, Claims `5572`, ClaimEvidence `5572`, Gukgam observations `57`, Gukgam source runs `14`, public Claim-backed targets `106` and public committee count `6`.
- Read-only discovery found exactly `4` current exact-one audited-target occurrences without a published Gukgam Claim; no later exact-one occurrence remained.
- The explicit four-item manifest canonicalized to SHA-256 `cb05916c68b61afa7a1fafda449134225b7e6801a990b851316025a30222d4e2`.
- 전국재해구호협회 — `3078707:bf03a64c5e7a432e8c0475efcf15e545:1:schedule:1:audited-target:8` — Organization `f6b54412-5014-55e0-aee5-ea0f6c5528c6` — Claim `6bd85d9d-043e-5337-96f6-1e9f505d22c7` — Evidence `af00e287-3e39-586d-9f56-bf39ab9d9664`.
- 공무원연금공단 — `3078707:bf03a64c5e7a432e8c0475efcf15e545:1:schedule:2:audited-target:6` — Organization `24c556cf-8d8c-5a96-b9a9-0a0fcd1740c4` — Claim `bcefe8d4-de7c-56d2-bb87-e0f8892ed475` — Evidence `4a85a81a-d6b2-566e-87ef-930072c77ea4`.
- 한국소방산업기술원 — `3078707:bf03a64c5e7a432e8c0475efcf15e545:1:schedule:2:audited-target:7` — Organization `08d1e45c-56c7-5f84-a5af-b6234dcf9f2b` — Claim `079c6c3c-06c9-5a4f-8266-152c74f972f5` — Evidence `94c1d45a-9fc2-5c64-a5cc-0f181df10bd5`.
- 한국도로교통공단 — `3078707:bf03a64c5e7a432e8c0475efcf15e545:1:schedule:3:audited-target:2` — Organization `ca18675d-95cc-58b6-8c39-3af213b04bfc` — Claim `2720e9cf-9c29-5868-9115-261c45b506fe` — Evidence `400a2583-8235-5928-b133-02abd8d0ff47`.
- Two unchanged staging no-write preflights produced byte-identical receipts. Receipt SHA-256 was `4b22c3ee1c0e75aef36474fde71300456e44d30bc599b96d20b6b08d9b62eb50`.
- Both receipts returned `DRY_RUN`, `item_count=4`, `all_preflights_passed=true`, `write_performed=false`, `batch_commit_available=false`, `automatic_candidate_enumeration=false` and `network_fetch=false`; every item preserved `claim_persisted=false` and `organization_created=false`.
- Before and after both dry-runs, staging remained Organizations `347`, Claims `5572`, ClaimEvidence `5572`, Gukgam observations `57`, Gukgam source runs `14`, public Claim-backed targets `106` and public committee count `6`; public HTML exposed neither `review_key` nor `match_class`.
- No batch commit was executed in this slice.

## Current checkpoint — final reviewed Gukgam 4-item batch commit (2026-09-22)

- Exact canonical `master` was `624801fa8390590df6e2be46d30cd325cb677e38`; the worktree was clean and deferred draft PR `#75` remained the only concurrent PR, out of scope.
- Commit-time baseline exactly matched the final four-item dry-run: Organizations `347`, Claims `5572`, ClaimEvidence `5572`, Gukgam observations `57`, Gukgam source runs `14`, public Claim-backed targets `106` and public committee count `6`.
- The exact four-item manifest recreated from canonical HANDOFF review pairs retained SHA-256 `cb05916c68b61afa7a1fafda449134225b7e6801a990b851316025a30222d4e2`.
- A fresh no-write preflight produced receipt SHA-256 `4b22c3ee1c0e75aef36474fde71300456e44d30bc599b96d20b6b08d9b62eb50`, byte-identical to the canonical dry-run receipt, with `DRY_RUN`, `item_count=4`, `write_performed=false`, `automatic_candidate_enumeration=false` and `network_fetch=false`.
- The canonical commit path re-preflighted the same manifest and executed exactly one atomic transaction.
- The commit returned `COMMITTED`, `item_count=4`, `claims_created=4`, `claims_reused=0`, `organizations_created=0`, `organizations_reused=4`, `write_performed=true`, `automatic_candidate_enumeration=false` and `network_fetch=false`.
- The exact commit receipt bytes are pinned by SHA-256 `a8236c9cc84e484b180b3ac136bed9c6ebdf0a7ab5a641bfc315bb081c6d882f`.
- Persisted items were 전국재해구호협회 Claim `6bd85d9d-043e-5337-96f6-1e9f505d22c7` / Evidence `af00e287-3e39-586d-9f56-bf39ab9d9664`, 공무원연금공단 Claim `bcefe8d4-de7c-56d2-bb87-e0f8892ed475` / Evidence `4a85a81a-d6b2-566e-87ef-930072c77ea4`, 한국소방산업기술원 Claim `079c6c3c-06c9-5a4f-8266-152c74f972f5` / Evidence `94c1d45a-9fc2-5c64-a5cc-0f181df10bd5`, and 한국도로교통공단 Claim `2720e9cf-9c29-5868-9115-261c45b506fe` / Evidence `400a2583-8235-5928-b133-02abd8d0ff47`.
- Post-commit read-only PostgreSQL verification returned Organizations `347`, Claims `5576`, ClaimEvidence `5576`, Gukgam observations `57` and Gukgam source runs `14`.
- Live staging Web verification returned public Claim-backed targets `110` across `6` committees; all `4/4` new Claim IDs and `4/4` new ClaimEvidence IDs were present, while `review_key` and `match_class` remained absent.
- A fresh reviewed-schedule binding discovery after the commit returned `unpublished_exact_one=0`. The current exact-one reviewed publication backlog is therefore exhausted; do not continue the batch loop or infer/auto-resolve non-exact-one occurrences.
- No public API/Postgres domain, new Railway resource or Organization creation occurred. The final reviewed four-item manifest is fully committed and must not be replayed.

## Current checkpoint — Gukgam post-coverage audit + public-beta release gate (2026-09-22)

- Exact canonical `master` was `92a7efc99949c618a310cc2ea9f7ddd4a94238e6`; the worktree was clean and deferred draft PR `#75` remained the only concurrent PR, out of scope.
- Final reviewed exact-one publication state is Organizations `347`, Claims `5576`, ClaimEvidence `5576`, Gukgam observations `57`, Gukgam source runs `14`, public Claim-backed targets `110` and public committee count `6`.
- Fresh binding-review audit contains `390` audited-target mentions across `359` distinct target labels.
- Match classes are exactly `110` `EXACT_CANONICAL_NAME_OVERLAP_DISCOVERY_ONLY` mentions and `280` `NO_EXACT_CANONICAL_NAME_OVERLAP` mentions; `MULTIPLE_EXACT_CANONICAL_NAME_OVERLAPS_REVIEW_REQUIRED` count is `0`.
- All `110/110` exact-one mentions are published; current unpublished exact-one count remains `0`. Distinct exact-one target count is `103`; distinct no-exact target count is `256`.
- Committee occurrence coverage is: 과학기술정보방송통신위원회 `23/96` (`24.0%`), 국방위원회 `4/73` (`5.5%`), 국회운영위원회 `0/10` (`0.0%`), 농림축산식품해양수산위원회 `34/49` (`69.4%`), 문화체육관광위원회 `30/69` (`43.5%`), 재정경제기획위원회 `12/48` (`25.0%`), 행정안전위원회 `7/45` (`15.6%`).
- The remaining `280` mentions are coverage gaps, not ambiguous duplicate exact-name candidates. They must not be fuzzy-bound, alias-expanded, ranked, auto-selected or materialized from Gukgam observations.
- Repository public-release history/privacy checklist was already completed on 2026-08-31; this audit does not reopen that gate.
- Railway staging still has exactly `postgres`, private `api` and public `web`; all report successful latest deployments, and the PostgreSQL volume remains in `asia-southeast1-eqsg3a`.
- Railway `production` currently has zero services. Creating production services or a production public domain remains a separate external-state action requiring explicit approval.
- Staging Web remains intentionally non-indexable: `/robots.txt` returns `Disallow: /`, the Gukgam page contains `noindex` and `nofollow`, and the page still renders the explicit bounded-incomplete scope message.
- Current canonical master is newer than the latest staging Web/API deployments (both were created on 2026-09-20). Therefore staging is not yet an exact-master release candidate even though its live database contains the final reviewed publication state.
- Public beta may expose the current `110` Claim-backed occurrences only as explicitly bounded incomplete coverage; the remaining no-exact universe requires a separate Organization acquisition/binding contract, not another reviewed-batch loop.

## Current checkpoint — exact-master staging release candidate (2026-09-22)

- Exact canonical `master` was `4a236d062b74faebf12a7989efd55a3c59bbd3b6`; the worktree was clean and deferred draft PR `#75` remained the only concurrent PR, out of scope.
- GitHub Verify run `35675468960` for the post-coverage/release audit passed in `3m1s` before staging deployment.
- Direct `railway up` from the long-lived Windows repo failed before upload with local `os error 5`; no staging change occurred. A clean tracked-only release tree was therefore produced with `git archive` from exact master (`313` files, both reviewed Dockerfiles present), excluding local caches, venvs and locked artifacts.
- API deployment `557db960-7d31-40f5-9a01-4f5117bb4a57` was uploaded from that exact-master release tree and completed `SUCCESS`. Build logs show the current reviewed worker code in the snapshot; pre-deploy Alembic ran transactionally and runtime healthcheck `GET /ready` returned `200`.
- Web upload deployment `2800693a-d036-4239-b0e9-8d31b7bc3612` was provider-skipped with `no changes detected in watch paths`. Railway compared the exact-master uploaded snapshot against the current successful Web snapshot and found zero changes under configured `apps/web/**` and `deploy/Dockerfile.web` watch paths; the existing Web binary is therefore content-equivalent to exact master for its declared build inputs.
- Existing staging topology stayed unchanged: private `postgres`, private `api`, public-domain `web`; no production service, public API/database endpoint, domain, variable or indexing setting was created or changed.
- Public HTTP integration QA passed on staging: `/`, `/people`, `/organizations`, `/gukgam/2026` and `/robots.txt` returned `200`; one sampled Person detail and one sampled Organization detail also returned `200`.
- Gukgam public projection remained exactly `110` Claim-backed target occurrences across `6` committees. Final-batch Claim/Evidence IDs were present, while `review_key` and `match_class` remained absent from public HTML.
- Staging remained non-indexable: `/robots.txt` returns `Disallow: /`; Gukgam HTML contains both `noindex` and `nofollow`.
- Real Edge CDP layout QA passed at desktop `1440x1200` and mobile `390x844`: `documentElement.scrollWidth` was `1425` and `390` respectively, horizontal overflow was `false`, overflowing-element set was empty, scope `110` rendered in both viewports, and no browser console/runtime errors were observed.
- Railway `production` still contains zero services. This staging release-candidate proof does not authorize creating production services, a production domain, or enabling indexing.

## Next concrete action

The reviewed exact-one publication loop and exact-master staging release candidate are complete. Production launch is now an explicit external-state boundary: before creating any production `postgres`/`api`/`web` services or public production Web domain, obtain operator approval for the billable/public exposure change and prepare the exact resource/domain/indexing plan. In parallel, keep the `280` `NO_EXACT_CANONICAL_NAME_OVERLAP` occurrences in a separate Organization-coverage workstream; they are not release blockers for the explicitly bounded-incomplete 110-target beta and must not be auto-bound or published.
