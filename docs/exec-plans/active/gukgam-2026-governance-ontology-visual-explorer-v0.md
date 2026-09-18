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

## Slice 0 — source reconnaissance + ontology contract + graph skeleton

### Official Gukgam source reconnaissance

The National Assembly's official committee pages are the source family for committee plans,
audited organizations and witness/reference-person attachments.

The source contract is recorded in
`docs/architecture/GUKGAM_2026_SOURCE_CONTRACT.md`.

Current gate:

```text
RECONNAISSANCE / DISCOVERY_ONLY
```

The exact current 2026 post/attachment rights, stable attachment ID and correction semantics still
need one end-to-end source review before live acquisition is authorized.

### Ontology projection

Branch `work/gukgam-ontology-slice0` contains:

- `packages/rendering/governance_ontology.py`;
- public `GET /ontology/people/{person_id}`;
- regression coverage for evidence-backed projection and fail-closed missing Evidence;
- `docs/architecture/GOVERNANCE_ONTOLOGY.md`.

The first projection creates only Claim-scoped target nodes for already-supported Person relation
predicates. It does not invent canonical Organization/School/Company identities from text.

Independent review tightened the semantics:

- `NOMINATED_AS` / `DESIGNATED_AS` are not rewritten as `HELD_ROLE`;
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

- full Verify succeeds after independent-review fixes;
- final diff has no publication-gate bypass;
- no raw evidence excerpt appears in ontology output;
- no identity merge is introduced;
- no schema, migration, dependency or deployment change.

## Next concrete action

Close Slice 0 with Verify, then review one exact current 2026 committee audit-plan/witness
post+attachment end to end and activate only that source-specific collection path.
