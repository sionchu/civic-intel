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
- The pinned Science Committee real fixture still has zero reviewed schedule rows and no exact
  local artifact proof, so no real Gukgam schedule/target observation has been written to staging.
  Committee-site repeated automation remains blocked by the reviewed robots contract. Temporary
  GitHub QA/probe workflow files were removed after use.

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
- The official Science Committee PDF preview remains inaccessible through the current approved web
  execution paths, and repeated committee-site automation remains blocked by the reviewed robots
  contract. The exact reviewed packet therefore still requires an approved manual/Codex-local
  artifact boundary; no PDF content was guessed from news or search snippets.

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

## Next concrete action

Complete exactly one reviewed Science Committee 2026 plan packet from the pinned official PDF:

1. obtain one exact local copy of the pinned attachment through the approved manual/Codex-local
   boundary and record the exact official locator;
2. record the raw PDF SHA-256 and confirm the exact attachment metadata rights review;
3. fill the schedule rows and audited-target strings field-by-field from that attachment;
4. run `workers.gukgam_reviewed_plan_import` in dry-run mode;
5. independently verify the source locator, raw hash, packet hash, row count, target count and
   zero Person/Organization/Claim publication;
6. only if the dry-run receipt passes, perform one staging `--commit` single-pull and prove the
   unchanged rerun.

Do not bind audited-target names to canonical Organizations in the same slice. Do not weaken the
committee-site robots boundary while the official API credential remains unavailable.
