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

The National Assembly's official audit pages are the target source family for committee plans,
audited organizations and witness/reference-person attachments. The site exposes committee/year
search over the 국정감사/국정감사계획서 area; source-specific locator and attachment semantics are
being verified against a current 2026 committee plan before acquisition code is authorized.

Current public reporting confirms that committee plans are being adopted and published in
September; the canonical collector will rely on the Assembly source itself rather than reporting
for dates, target organizations or witness rows.

### Ontology projection

Branch `work/gukgam-ontology-slice0` now contains:

- `packages/rendering/governance_ontology.py`;
- public `GET /ontology/people/{person_id}`;
- regression coverage for evidence-backed projection and fail-closed missing Evidence;
- `docs/architecture/GOVERNANCE_ONTOLOGY.md`.

The first projection creates only Claim-scoped target nodes for already-supported Person relation
predicates. It does not invent canonical Organization/School/Company identities from text.

### Visual library gate

Cytoscape.js is the preferred v0 renderer. Dependency addition is deferred until the lockfile can
be updated through a normal npm execution boundary. Do not hand-edit the lockfile.

## Verification

PR #63 is the independent CI boundary for Slice 0. The implementation is not merge-ready until
Verify succeeds and the final diff is reviewed for publication-gate bypass, raw-data exposure and
ontology overreach.

## Next concrete action

Finish the exact official Assembly plan locator/attachment contract for one 2026 committee, then
use that evidence to implement the first source-specific Gukgam plan parser/enumerator while Slice
0 CI runs.
