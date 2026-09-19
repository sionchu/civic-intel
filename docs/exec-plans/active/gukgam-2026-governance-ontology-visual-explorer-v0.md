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

## Next concrete action

Run one live, bounded `ALLSCHEDULE` sample for the 2026 audit window and the Science Committee,
then compare the returned candidate date/content against the exact official committee plan.

- If the live response matches the staged fields/filters, add the source-specific L2 observation
  path for schedule discovery only.
- Regardless of that result, continue the Science Committee reviewed plan packet for audited
  organizations because schedule text is not authority for target/witness identity.
- Keep `apps/web` unchanged until canonical Gukgam schedule/target data exists.
