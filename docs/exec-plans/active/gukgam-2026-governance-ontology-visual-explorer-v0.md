# Gukgam 2026 Governance Ontology & Visual Explorer v0

## Goal

Ship a 2026 National Assembly audit event surface inside Civic Intel while preserving Civic Intel
as the long-lived evidence-backed public-governance intelligence product.

Target public-beta candidate:

```text
2026-09-29
```

This plan replaces serial person-by-person work with bounded scale collection plus a read-only
Governance Ontology projection.

## Baseline

```text
baseline HEAD:
0d40df42a38b77ea0b296bbfb12e8f1c821122e3

Verify:
35370449189 — SUCCESS

schema:
0006

People:
299

Organizations:
347

Claims / ClaimEvidence:
5466 / 5466

ALIO executive Claims:
3624

cross-lane discovery:
56 REVIEW / 0 RESOLVED
```

The closed cross-lane candidate pipeline remains the identity boundary. Name-only discovery never
becomes resolution.

## Release tracks

### Track A — Scale Collection

Priority universe:

1. official 2026 Gukgam committee plans;
2. witnesses/reference persons when officially published;
3. audited organizations;
4. current heads/executives of those organizations;
5. questioning Assembly members;
6. the existing 56 reduced ALIO↔Person candidates;
7. official biography/corporate/education sources connected to that universe.

Collection remains source-specific and bounded. No generic web crawler.

### Track B — Ontology Product

```text
Evidence Core
→ Governance Ontology projection
→ Search
→ 1-hop Ego Graph
→ bounded Person/Organization Path
→ Career Timeline
→ Evidence Drawer
→ /gukgam/2026
```

PostgreSQL remains the canonical SSOT.

## Non-negotiable gates

- rendered fact → Claim → ClaimEvidence → Source → SourcePolicy;
- no name-only Person link or merge;
- no graph database in v0;
- no precise-residence or family connection edge;
- no friendship, faction, motive or influence inference;
- no political ranking or persuasion layer;
- source rights before acquisition;
- unresolved witness rows do not become canonical People;
- public ontology edges are published FACT/attributable CLAIM with provenance.

## Agent verification

Implementation and verification are separate roles.

Required receipts:

- code/architecture verifier;
- data/provenance verifier;
- browser QA;
- independent official-source spot check;
- CI Verify.

The implementing agent does not close its own release gate.

## Slice 0 — Source reconnaissance + ontology contract

Status: IN PROGRESS

Deliverables:

- official Gukgam source-family reconnaissance;
- source rights remain discovery-only until exact current attachment review;
- Governance Ontology node/relation vocabulary;
- provenance-gated public edge contract;
- deterministic bounded BFS;
- regression tests;
- no schema/API/deployment change.

### Slice 0 evidence

Observed official National Assembly committee pages use a shared `*.na.go.kr` committee platform,
stable-looking `nttId` detail locators and HWP/PDF attachments. Hostname alone cannot identify the
committee because the shared platform may render records belonging to other committees.

Current source rights for the exact 2026 plan/witness attachments are not yet closed, so acquisition
remains fail-closed.

### Slice 0 acceptance

- ontology projection code is persistence-free;
- path max_hops ≤ 3 and max_paths ≤ 5;
- public edges require Claim/Evidence/Source;
- UNKNOWN cannot become a public connection edge;
- residence relation is absent;
- tests and full Verify pass;
- source rights remain discovery-only until reviewed.

## Slice 1 — First current 2026 committee source

After Slice 0 PASS:

- review one current 2026 committee plan/witness source end-to-end;
- pin exact rights and attachment/version semantics;
- implement one source-specific collector;
- prove expected universe/coverage;
- no identity bypass.

## Slice 2 — Ontology API + Gukgam page

After first source data is canonical:

- add bounded read-only ontology routes;
- add `/gukgam/2026`;
- integrate Cytoscape.js only when real eligible graph data can render;
- graph is supplemental to textual relation/evidence list.

## Current checkpoint

```text
Slice 0 implementation branch:
feat/gukgam-ontology-slice0

Current action:
land ontology contract/tests + source reconnaissance, then independent CI verification.
```

## Next concrete action

Close Slice 0 with CI, then review the first exact current 2026 committee audit-plan/witness
attachment and activate only that source-specific collection path.
