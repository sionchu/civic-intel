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

## Next concrete action

After Slice 0 merges, start Slice 1 by finding an **automation-permitted official** route for 2026
Gukgam metadata. Prioritize 열린국회정보 / National Assembly Open API and central official audit
schedule metadata.

Do not implement a committee-site scraper while the reviewed robots contract blocks those paths.
If no suitable official automated route exists, use the existing rights-reviewed human-assisted
packet gate for one committee rather than weakening source policy.
