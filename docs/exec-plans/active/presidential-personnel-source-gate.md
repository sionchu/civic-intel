# Presidential personnel source-route gate

## Status

2026-09-12: source-route review complete; `L1 CONTRACT_STAGED` retained. Live collection and
L3 promotion are blocked pending a source-specific route and rights contract. This is a gate
record, not approval for a crawler or a new persistence model.

## Objective and scope

Evaluate the official Presidential Office briefing and organization pages for the existing
PresidentialPersonnelRecord contract. The lane covers publicly named senior Presidential
Secretariat/National Security Office personnel, special advisers, commissions and explicitly
public task-force roles. It does not cover ordinary staff, meeting attendance, political
influence or inferred relationships.

## Observed official route

- [Briefing list](https://www.president.go.kr/briefings) reported 923 publications, ten rows per
  page, title/content search and `pageNo` pagination. A title search for `인사` returned 41 rows;
  `인선` returned 11 rows. Search terms are not a declared personnel universe.
- A detail route such as
  [qGTHgnQ8](https://www.president.go.kr/briefings/qGTHgnQ8) exposes a page ID, title,
  registration date and written body. The page describes multiple actions in one narrative.
- The [organization page](https://www.president.go.kr/organization) describes current offices and
  role structure but is not a dated occupancy roster.
- The [copyright policy](https://www.president.go.kr/copyright-policy) describes marked works as
  KOGL type 4 (attribution, noncommercial use and no modification) and directs prior consultation
  for unmarked material.
- The inspected [qGTHgnQ8 detail page](https://www.president.go.kr/briefings/qGTHgnQ8) itself
  renders the same KOGL type 4 notice. This confirms the page-level condition shown to a reader,
  but it does not grant fulltext retention, excerpting, derivative normalization, AI use,
  automated enumeration or commercial republication for Civic Intel.

## Contract decision

The briefing path supplies a useful official record key candidate at page level, but it does not
publish an action ID, typed personnel dataset, updated-at/version field, correction link,
replacement rule or complete personnel inventory. A page ID is not a Person ID. An action-level
observation needs the page ID plus a reviewed locator/ordinal, and a later page or explicit source
correction must create a new observation rather than silently replace the old one.

The existing `presidential_personnel_policy()` remains metadata-only with `can_fetch=False`, no
fulltext/excerpt/AI/commercial use, and no automated list traversal. The page-level KOGL notice
narrowly describes the displayed reuse condition; it is not a packet-specific authorization for
Civic Intel's storage or publication path. Public reachability is not a reuse or collection grant.
No live connector, importer, scheduler, raw page capture or migration is authorized by this gate.

## Human-assisted usable path

After packet-specific rights approval, one finite manifest of exact official briefing URLs may be
reviewed manually. Each accepted action must retain the official page URL, page ID, registration
date, action locator/ordinal, review date and analyst-normalized fields. The official page and the
analyst representation remain separate Sources/snapshots. Existing parser semantics preserve
`임명`, `지명`, `내정`, `위촉`, `보직/겸임` and release wording without conversion.

The path can support source-level L1/L2 research observations and review-required identity
candidates. It cannot promote human-curated values to automatic FACT, create Persons from names
alone, or turn reported prior careers into independently verified CareerEpisodes.

## Reopen conditions

1. Obtain a bounded route or packet contract that states the exact source universe, page size,
   request limits and permitted acquisition/storage/republication uses.
2. Establish page/action identity and correction, amendment, replacement and republication
   semantics, with a deterministic action locator that remains snapshot-scoped.
3. Provide fixtures covering multi-action pages, masked/vacant names, action wording, missingness
   and later corrections; compare every accepted field against the official source.
4. Preserve official-code or independently verified career anchors where available; never use
   name-only linking or organization proximity to merge Persons.

Until these conditions close, keep the lane at `L1 CONTRACT_STAGED`, use exact reviewed packets
only when separately authorized, and do not write an automated implementation ExecPlan.
