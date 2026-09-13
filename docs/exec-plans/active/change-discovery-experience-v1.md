# CHANGE discovery experience v1

Status: active plan — input gate complete; public CHANGE surface blocked pending an eligible
canonical input. Implementation has not started.

Date: 2026-09-13

## Objective

Prove one small, profile-scoped `ROLE_SEQUENCE_CHANGE` experience from existing dated,
published role Claims. The first implementation, if the input gate is satisfied, will be a
read-only projection that compares two eligible Claims deterministically and presents a
`DERIVED / CHANGE` result with an exact Claim → ClaimEvidence → Source trace.

This is a product projection, not a new truth layer. It does not create a global change feed,
fetch a new source, add a feeder, introduce a persistent model, or promote a derived result to
`FACT`.

## Baseline and boundaries

- Baseline is `origin/master` at `5ca7be86a0d938631f83250e5e68b12ba7d474b2`.
- The root checkout's local Assembly proposer candidate is outside this plan and is not shipped
  or evidence for the public product baseline.
- The existing `Claim`, `ClaimEvidence`, `Source`, `SourcePolicy`, `SourceSnapshot`,
  `FeederObservation`, repository, profile projection, API, and profile UI are the only
  foundation permitted for v1.
- `ReviewedPersonBundle` remains a fixture/manual/regression path, not the batch main path.
- No new source is approved by this plan. SourcePolicy remains the first gate for every source
  access and publication path.

## Input gate

Before implementation, inventory the actual public profile payload and deterministic reviewed
fixtures. Do not manufacture a pair merely to make the card appear.

An eligible input Claim must be all of the following:

1. It belongs to one resolved canonical Person and is not superseded.
2. It is published, asserted true, and has `FACT` epistemic status.
3. It has explicit supporting ClaimEvidence whose Source is covered by a permitted
   SourcePolicy. Where present, the exact SourceSnapshot and FeederObservation references stay
   attached.
4. Its predicate is `HELD_ROLE` or `APPOINTED_AS`, its `object_text` is non-empty, and its
   `qualifiers.date` is an explicit ISO calendar date.

The reviewed Kim Hyun-ji fixture is a deterministic proof candidate because it contains dated
role Claims from 2022, 2025, and 2026. It does not establish that Kim is part of the default
ten-person public seed. The input-gate result must state whether the real public corpus has an
eligible pair; if it does not, v1 may prove the pure rule with the fixture and must expose an
explicit unavailable/unknown state rather than a synthetic change or a global “no changes”
assertion.

Claims with missing or conflicting dates, non-FACT status, missing support, a different Person,
masked identity, policy exclusion, or supersession are excluded. Exclusion is not evidence that
no real-world change occurred.

## Input-gate result — 2026-09-13

- The Golden public seed contains 10 resolved people and one eligible `HELD_ROLE`/
  `APPOINTED_AS` Claim. It therefore has zero eligible cross-date pairs. This is a coverage
  limitation of the current public seed, not evidence that no person changed roles.
- The Kim Hyun-ji reviewed fixture contains four eligible role Claims: one dated 2022-06-22,
  two dated 2025-09-29, and one dated 2026-08-31. Four cross-date pairs satisfy the comparison
  rule; the same-date pair is correctly excluded. Each eligible Claim has SUPPORT Evidence and
  a non-blocked metadata SourcePolicy, with Snapshot references retained in the fixture.
- The fixture policies are `DISCOVERY_ONLY` and metadata-only. They validate deterministic
  comparison and evidence-trace shape, but do not authorize live fetching or establish a new
  public acquisition route.
- Decision: Milestone A may retain fixture rule/regression proof. Milestones B and C remain
  paused; no public CHANGE card or “no change” statement is exposed until an approved,
  source-bounded public input supplies at least two eligible dated Claims for one resolved
  Person.

## Source-contract gate — National Assembly historical member-history API

The official Open API catalog exposes a separate `역대 국회의원 의원이력` service, distinct from
the current-member API already used by the Assembly roster feeder:

- The [service contract](https://open.assembly.go.kr/portal/data/service/selectAPIServicePage.do/OD21030011944P19666)
  names the endpoint `nfzegpkvaclgtscxt`, describes the data as historical member careers, and
  explicitly excludes current members. It labels the service version `1 (21-01-08)`, declares
  `pIndex`/`pSize` pagination and “제한없음” request limits, and accepts `HG_NM`, `PROFILE_SJ`,
  `MONA_CD`, and required `PROFILE_UNIT_CD` filters. A request without that filter returned the
  documented `ERROR-300` missing-parameter response; `100000` and `100023` returned `INFO-200`
  no-data responses.
- Its output includes `HG_NM`, `HJ_NM`, `FRTO_DATE`, `PROFILE_SJ`, `MONA_CD`,
  `PROFILE_UNIT_CD`, and `PROFILE_UNIT_NM`. A read-only page-by-page probe on 2026-09-13
  fetched each observed code from `100001` through `100022` at `pSize=100`: every page reported
  a stable `list_total_count`, and the responses contained 5,467 rows in total. The observed
  response map was:

  | `PROFILE_UNIT_CD` | provider label | rows | pages | relation declared by service |
  |---|---|---:|---:|---|
  | `100001` | 제헌 | 209 | 3 | historical service; current excluded |
  | `100002` | 제2대 | 218 | 3 | historical service; current excluded |
  | `100003` | 제3대 | 208 | 3 | historical service; current excluded |
  | `100004` | 제4대 | 245 | 3 | historical service; current excluded |
  | `100005` | 제5대 | 305 | 4 | historical service; current excluded |
  | `100006` | 제6대 | 190 | 2 | historical service; current excluded |
  | `100007` | 제7대 | 186 | 2 | historical service; current excluded |
  | `100008` | 제8대 | 207 | 3 | historical service; current excluded |
  | `100009` | 제9대 | 251 | 3 | historical service; current excluded |
  | `100010` | 제10대 | 235 | 3 | historical service; current excluded |
  | `100011` | 제11대 | 285 | 3 | historical service; current excluded |
  | `100012` | 제12대 | 288 | 3 | historical service; current excluded |
  | `100013` | 제13대 | 308 | 4 | historical service; current excluded |
  | `100014` | 제14대 | 341 | 4 | historical service; current excluded |
  | `100015` | 제15대 | 333 | 4 | historical service; current excluded |
  | `100016` | 제16대 | 310 | 4 | historical service; current excluded |
  | `100017` | 제17대 | 304 | 4 | historical service; current excluded |
  | `100018` | 제18대 | 311 | 4 | historical service; current excluded |
  | `100019` | 제19대 | 287 | 3 | historical service; current excluded |
  | `100020` | 제20대 | 248 | 3 | historical service; current excluded |
  | `100021` | 제21대 | 176 | 2 | historical service; current excluded |
  | `100022` | 제22대 | 22 | 1 | historical service; current excluded |

  This is an observed response map, not a provider-declared finite manifest. The service page
  publishes no code list, lower/upper bound or code-to-term registry. The `100022` response
  contains 22 rows, while the separate current roster response contained 299 rows; the observed
  `MONA_CD` intersection was zero. That supports the service's current-member exclusion, but
  does not prove a complete current-plus-former composition.
- The separate [official term-inventory service](https://open.assembly.go.kr/portal/data/service/selectAPIServicePage.do/OLFZV7001148O518934)
  exposes `ERACO`, election date, `TERM_BG`, `TERM_ED`, and related term metadata. Its response
  reports `list_total_count=55` and 22 distinct `ERACO` labels, but has repeated exact rows and
  formatting variants (2 exact-duplicate groups, 4 rows in those groups) and no stable row ID or
  revision field. The inspected contract does not publish a mapping from those term labels to
  every historical `PROFILE_UNIT_CD` used by the member-history service.

The historical service can therefore produce bounded, dated source observations, but it is not
yet a closed Civic Intel input lane. The probe found 17 duplicate `{MONA_CD}:{PROFILE_UNIT_CD}`
groups among the 5,467 rows. For example, `0P85685J:100015` has two rows for `이회창` with
different `FRTO_DATE` periods and different composite `PROFILE_SJ` values within the same
term. The combination is a person/term grouping value, not a sufficient source-record key; a
row ordinal is not permanent without a provider ordering/identity contract.

Positive controls from the same bounded probe are source-level only:

- `XQ98168F` returns consecutive `제19대` and `제20대` rows. Its composite `PROFILE_SJ` changes
  from `새누리당 울산 울주군` to `무소속 울산 울주군`.
- `0135473I` returns consecutive `제17대` through `제20대` rows.
- `0767470D` returns a nonconsecutive sequence (`제16대`–`제19대`, then `제21대`).
- The service has no separate party, district or role-title columns; those changes are only
  visible, when present, inside the display string `PROFILE_SJ`.
- No current-plus-history positive control exists in the observed union: the current roster and
  all observed history rows have zero `MONA_CD` overlap, consistent with the published exclusion.

This gate is also the worked source-hierarchy and parser-boundary case in
[Source parsing and semantics](../../architecture/SOURCE_PARSING_AND_SEMANTICS.md). It remains a
documentation reference only: no implementation, L3 promotion or CHANGE publication follows
from the example.

- **Field authority:** the historical service is authoritative only for the historical term
  fields it publishes; the current-member API remains a separate authority for current roster
  fields; the term-inventory service is authoritative for Assembly term boundaries. Do not merge
  these into one Source or treat a copied field as independently corroborated.
- **Identity:** `MONA_CD` is an official Assembly provider/crosswalk namespace and
  `PROFILE_UNIT_CD` is a source term key. Neither is a canonical Person ID. Existing accepted
  Assembly `MONA_CD` anchors take priority; a historical row still requires an exact source-backed
  bridge to a resolved Person and never a name-only link.
- **Coverage:** pagination and `list_total_count` are present and the observed 22-code probe had
  stable totals, but the history service's current-member exclusion, missing provider code
  manifest, unproved complete current/former composition and 17 duplicate term-group keys prevent
  an L3 coverage claim. The current term inventory is a 55-row metadata response, not the missing
  row manifest.
- **Version:** the response exposes no updated-at, correction, replacement, withdrawal, or
  tombstone field, and the service version label is not a data-version history. A later changed
  row cannot be classified as a correction from the response alone; a future capture must use new
  SourceSnapshots and immutable observations with an explicit review decision. There is no
  provider-declared old/new representation, deletion marker or replacement chain.
- **Rights:** the [Open API terms](https://open.assembly.go.kr/portal/policy/openUserAgreementPage.do)
  require an issued key and source attribution and prohibit unauthorized access and copyright
  violations. The [copyright policy](https://open.assembly.go.kr/portal/policy/copyRightPage.do)
  grants free use without separate permission only for material fully owned by the Assembly and
  marked KOGL type 1; unmarked or other KOGL types require prior consultation. The historical
  service page did not expose a dataset-specific KOGL marker or explicit storage/normalization/
  republication permission. The data.go.kr no-restriction label for the current integrated API is
  not automatically extended to this separate historical service; the page's “제한없음” is a
  request-limit display, not a rights grant.

**Decision: KEEP L1.** The automation ceiling remains below L3. A finite, rights-approved source
packet may support a human-assisted source observation path, but human review cannot turn a
provider group key into a stable row key or make an unlicensed representation reusable. The
existing public CHANGE surface remains blocked until two dated role Claims are separately
imported as canonical, published Claim/Evidence for a resolved Person. No connector, importer,
API route, migration, or new source policy was added by this gate.

### Reopen conditions

1. Record a service-specific SourcePolicy decision covering API access, normalized metadata,
   storage, attribution, and any downstream republication; do not inherit the current-roster
   policy by hostname alone.
2. Obtain a provider-published finite `PROFILE_UNIT_CD` manifest and current/former composition;
   then prove page totals, a stable row-level key or explicitly packet-local row boundary,
   boundary cases and unchanged reruns. The observed 17 duplicate term-group keys must be handled
   by the source-specific contract, not discarded as duplicates.
3. Obtain correction/version behavior or retain a documented fail-closed rule with fixtures for
   changed, withdrawn, deleted and late-corrected term rows.
4. Resolve one provider code to an existing canonical Person through an accepted official bridge,
   publish two dated role Claims through existing ClaimEvidence/Source gates, and rerun the
   CHANGE input gate.

## Deterministic comparison rule

For one Person, order eligible Claims by `(qualifiers.date, claim_id)`. A candidate pair requires:

- two different explicit dates;
- later date strictly greater than the earlier date; and
- normalized role text that differs.

Same-date Claims do not establish order. Repeated identical role text is not a change. The
recorded timestamp, fetch time, source publication time, and free-text ordering do not resolve
an event-date tie. `APPOINTED_AS` retains its appointment meaning; the result must not silently
relabel it as a held role.

The output describes a dated sequence difference only. It must not assert role termination,
motive, causation, influence, faction, friendship, wrongdoing, or any other fact not present in
the input Claims.

Source correction and historical supersession semantics are outside v1. A superseded old input
is not used; `superseded_at` is not treated as the real-world end date. A later correction must
produce a new projection or no projection according to the same rule, without rewriting the old
Claim or turning the projection into a new fact.

## Projection contract

The result is computed at read time by extending the existing profile projection or by adding a
narrow pure helper. Do not create `DerivedIntelligence`, `ChangeEvent`, a new epistemic enum,
score, graph, generic analytics framework, or parallel repository.

The smallest presentation contract contains:

- stable `presentation_key` derived from the method version and ordered input Claim IDs;
- `kind: CHANGE` and a visible `DERIVED / CHANGE` label;
- canonical Person ID;
- earlier/later Claim IDs, dates, predicates, and role text;
- ClaimEvidence, Source, and available Snapshot/FeederObservation IDs for both inputs;
- `method_version: change.role-sequence.v1`;
- input scope, coverage, and limitations; and
- a concise derived reason that names the compared dates and role values without adding a
  causal explanation.

The key is not a Person ID, provider ID, asset/row key, or replacement for a Claim. Corrections
change the projection inputs; they do not mutate a canonical Person or source record.

## Product surface

Add a profile-level “최근 변화 / Recent changes” section next to the existing career timeline.
There is no global feed, rank, alert, recommendation, comparison page, party aggregate, or
community feature in v1.

An eligible card must show:

- `DERIVED · CHANGE` as distinct from a factual Claim;
- earlier → later role sequence and the dates used;
- the publication/epistemic status of each input Claim;
- “근거 보기” links into the existing source/evidence trace;
- the method version and coverage explanation behind an expandable methodology detail; and
- a clear statement that the card is a derived sequence, not a new fact about termination or
  motive.

When no eligible pair exists, show an explicit `UNKNOWN`/`PARTIAL` state with the actual input
coverage. Never render “no change” merely because the available data produced no pair. Policy
exclusion, conflict, missing dates, and unavailable source material must not become a headline
claim. Allowed source metadata may remain visible even when full text cannot be stored or
redistributed.

## Milestones

### A. Input gate and proof

- Record the public-payload/fixture inventory and eligible-pair outcome.
- Implement or test the pure comparison rule with positive, same-date, repeated-role, missing
  date, conflict, non-FACT, superseded, and unsupported-input cases.
- Preserve Golden Set and reviewed-person regressions.
- Stop the surface implementation if the real public corpus has no eligible pair; retain the
  deterministic fixture proof and explicit unavailable state.

### B. Read-only projection/API

- Extend the smallest existing profile response needed for the section.
- Reuse repository reads and existing Claim/Evidence publication gates.
- Return exact references for both input Claims; do not fetch or reinterpret a source.
- Keep the projection absent from the Claim/FACT persistence model and from batch checkpoints.

### C. Profile UI

- Render the section/card with Korean-first labels and the FACT-versus-DERIVED distinction.
- Reuse existing evidence/source cards and policy/audit details.
- Verify desktop, mobile, keyboard focus, overflow, empty/partial, and unavailable states.
- Do not add ranking, scoring, alerts, ideology/influence inference, or an all-people feed.

### D. Verification and delivery

- Run focused projection, API, profile, and UI checks, then the repository DoD checks.
- Run `ruff`, `mypy`, quality verification, web lint/typecheck/test/build, and `make verify` as
  applicable to the changed surface.
- Do not add a migration; if implementation unexpectedly requires persistence, stop and reject
  the change unless a separately justified canonical model is approved by the governing docs.
- Re-read the final diff, check links and drift, commit one coherent slice, and verify local
  HEAD, `origin/master`, and worktree state.

## Acceptance criteria

1. The input gate reports a reproducible eligible pair or an explicit no-input state using only
   existing canonical records and deterministic fixtures.
2. The result is reproducible from `method_version`, ordered Claim IDs, and a pinned input scope.
3. Both inputs trace through ClaimEvidence and permitted Source/SourcePolicy, retaining exact
   Snapshot/FeederObservation references when available.
4. The UI visibly labels the result `DERIVED · CHANGE` and exposes the input statuses.
5. Dates, ties, repeated roles, conflicts, superseded inputs, unresolved identities, and policy-
   excluded inputs cannot create a candidate.
6. The surface makes no termination, motive, causation, ideology, friendship, influence,
   faction, or wrongdoing claim.
7. Source corrections and timestamps follow the stated v1 rules without mutating canonical
   claims or using `superseded_at` as an event end date.
8. No new feeder, raw store, persistent model, migration, dependency, global feed, rank, alert,
   recommendation, or community feature is introduced.
9. Existing Clean-v0 publication, identity, privacy, source-policy, and regression boundaries
   remain intact.
10. Verification distinguishes local results, CI results, visual checks, and not-executed work;
    the final diff is clean and limited to the slice.

## Non-goals

Asset disclosures, roll-call votes, expenses, contributions, OpenWatch ingestion, source-
acquisition work, automatic Assembly proposer materialization, issue pages, global feeds,
cross-person comparisons, party averages, vote similarity, policy/influence inference, alerts,
recommendations, community/moderation, and MCP extensions are not part of this plan.

## Delivery note

This document defines the gate and contract; it does not claim that the CHANGE surface already
exists. On implementation, append the actual files, commands, test results, visual evidence,
commit, and any blocker to the active plan and `HANDOFF.md`.
