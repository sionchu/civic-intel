# Operator current review SSOT v0

Status: COMPLETED 2026-09-28.

Base: `2463ab3`.

## Goal

Replace the private operator console's stale 2026-09-22 org.go materialization artifact view with a
read-only current-review surface that is recomputed/revalidated against the connected canonical DB.

The manifest tab must show the two actual pending human boundaries:

1. current unpublished exact-one Gukgam Organization Claim candidates;
2. the current 70-item MOIS Organization proposal, only while its checked-in review artifact still
   matches the connected DB, current Gukgam schedule and current Organization universe.

## Boundaries

- no approval, Claim publication, Organization creation or source collection;
- no external /Users path as runtime input;
- no old completed org.go27 manifest as current state;
- Gukgam pending candidates are derived from the current schedule/checkpoints, current Organizations
  and current Gukgam Claims;
- MOIS review artifact is fail-closed against checkpoint/provider manifest, the 70 exact observation
  references, current Organization names and current NO_EXACT Gukgam occurrences;
- drift returns an explicit blocked/stale review state rather than silently reusing the artifact.

## Acceptance

- current Mac DB reports Gukgam 41 occurrences / 27 Organizations and the same manifest SHA
  `9bb202c3de7c219382f69c91b8b0014bba7442428b673b55ac7ebbf766e711a9`;
- current Mac DB validates MOIS 70 proposals / 74 occurrences / 159 unmatched labels;
- operator UI labels both lanes HUMAN REVIEW / NO WRITE and exposes exact record references;
- fixture DB without current Gukgam/MOIS data fails closed without mutation;
- full repository verification and production Web build pass;
- real operator screen is inspected after the local private console is launched, if the configured
  runtime can be started without changing canonical data.

## Closure evidence

- Current Mac PostgreSQL read-only projection returns `CURRENT_HUMAN_REVIEW_READY`.
- Gukgam lane: 41 pending exact-one occurrences / 27 Organizations, existing published Gukgam
  Claims 110, manifest SHA
  `9bb202c3de7c219382f69c91b8b0014bba7442428b673b55ac7ebbf766e711a9`,
  `claim_commit_authorized=false`.
- MOIS lane: the current complete SUCCESS checkpoint and provider manifest revalidate 70 proposals /
  74 occurrences / 159 unmatched labels / 0 ambiguous exact provider names,
  `materialization_authorized=false`.
- The private dev console was launched against the operational Mac PostgreSQL in database-enforced
  read-only mode. Real browser rendering showed the exact counts, hierarchy/lifecycle fields and
  record links. Organization, MOIS observation and Gukgam schedule-observation navigation were
  exercised without mutation.
- Full verification passed: `646 passed / 3 skipped`, Golden Set PASS, Web `26/26`, production
  standalone build PASS.
- No source fetch, canonical DB write, approval, Claim publication, Organization creation, migration
  or deployment occurred.
