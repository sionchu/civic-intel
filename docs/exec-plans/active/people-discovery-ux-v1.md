# People Discovery UX v1

Status: complete

## Objective

Make `/people` the canonical public people-discovery route over the existing published
Evidence Directory read model. Keep `/people/[id]` as the evidence dossier and make `/` a
discovery entry point rather than a second directory.

This plan does not add a feeder, a raw-observation UI, a search service, or a new truth model.

## Baseline audit

- `/` currently fetches resolved `Person` rows and renders the complete `RosterGrid` below the
  hero.
- `/people` has no index route; only `/people/[id]` exists for the person dossier.
- `RosterGrid` currently supports only client-side canonical-name filtering and renders a neutral
  initials marker plus a profile link.
- `GET /people` currently exposes only current, non-superseded `RESOLVED` `Person` rows. The
  existing detail route already loads published Claims, ClaimEvidence, Source/SourcePolicy and
  the approved `ProfileProjection`.
- The Assembly Base Profile contract has four exact published Claim fields: party, district,
  committees and reelection. One current field Claim is required for a deterministic facet;
  missing or multiple current values remain unavailable.

## Target information architecture

- Home `/`: product orientation and a link into discovery; a resolved-count signal is allowed,
  but the full directory is not rendered here.
- People `/people`: the single public people discovery route and one shared `RosterGrid`.
- Person `/people/[id]`: one canonical Person evidence dossier with the existing provenance and
  Evidence presentation.

## Public data contract

The list route will continue to start with `public_people()`, which returns only current,
non-superseded `RESOLVED` People. A narrow `discovery` read-model payload is derived only from
current published Person Claims whose ClaimEvidence passes the existing Source/SourcePolicy
publication gate. The payload may contain exact facet values, Claim/Evidence/Source identifiers,
and dates from those Claims. It must never read or return `FeederObservation.normalized`.

The approved Assembly Base Profile Claim qualifiers are the only source for party, district,
committees and reelection facets. A current Assembly `HELD_ROLE` Claim supplies the evidenced
role when its current-roster scope is explicit. No name-only identity linking or row-to-Person
substitution is introduced; each card and profile link remains keyed by canonical `Person.id`.

## Supported filters

- Name: exact canonical-name text search, client-side over the bounded current list.
- Party, district, committees and reelection: rendered only when the current published
  discovery payload contains deterministic non-null values for that facet. Filtering is exact;
  missing or ambiguous values never match and do not become inferred options.
- No pagination service, Elasticsearch, vector search or other premature search infrastructure.

## UX and failure states

- Same canonical names remain separate cards and separate `/people/{Person.id}` links. Cards show
  available role, party, district and reelection differentiators; an explicit same-name marker
  makes the separation visible.
- Cards use neutral initials only, with canonical name, evidenced role, available Assembly Base
  Profile fields, and source/date provenance summary. No portrait source is introduced.
- `/people` distinguishes loading, successful empty/no matches, incomplete facet data and API
  failure. A failed API request is never rendered as zero people.
- An unknown Person URL remains a dedicated public-record-not-found state linked back to
  `/people`.
- Existing dossier Evidence trace, Source and policy presentation is reused.

## Verification gates

1. Add deterministic API and projection regressions for published facet values, missingness,
   publication-gate failure, same-name separation, and API-unavailable behavior.
2. Add UI source regressions for the canonical route, IA split, supported filters, no raw
   observation access, loading state, keyboard semantics and unsupported-surface safeguards.
3. Run the local production artifact and inspect `/`, `/people`, Person, no-match, incomplete
   facets, unavailable API, keyboard focus and a 390px viewport with long Korean names.
4. Run project verification and inspect the final diff. No schema, migration or dependency
   change is expected.
5. Commit one coherent slice, push `origin HEAD:master`, wait for CI Verify, and record the
   actual result here and in `HANDOFF.md`.

## Completion record

Completed 2026-09-16 at commit `6d0b0893f5dd488c2c1d7ecb46f4ed7aa587b9a2`.

- `/people` is now the single public people-discovery route. Home `/` is an orientation and
  discovery entry point, `/people` is the bounded directory, and `/people/[id]` remains the
  evidence dossier. The existing `RosterGrid` is shared by the directory only; no parallel
  directory or raw-observation UI was added.
- The API list projection starts from current, non-superseded `RESOLVED` People and derives
  facets only from current published Person Claims whose ClaimEvidence passes the existing
  Source/SourcePolicy publication gate. It does not expose or read `FeederObservation.normalized`.
  No schema, migration, dependency or persistent model change was made.
- Name, party, district, committees and reelection filters are supported only from exact
  Assembly Base Profile Claim values. Missing or ambiguous values stay unavailable; the local
  incomplete-facet browser check rendered the explicit warning and omitted the unavailable
  party facet rather than inferring it.
- Cards use canonical Person IDs and neutral initials, display available role/profile values,
  ClaimEvidence count and as-of date, and mark same-name People separately. A reviewed
  same-name regression kept two canonical IDs and distinct party facets.
- Local verification passed: full Python `350 passed, 1 skipped`, Ruff, mypy for 59 source files,
  Clean-v0 quality, web UI tests `9 passed`, web lint, typecheck, production build and
  standalone contract. GNU Make is unavailable on this Windows host; the Makefile's
  constituent verification commands were run directly.
- Browser verification used a disposable SQLite dataset and standalone production artifact:
  Home IA, `/people`, party filter, no-match/reset, keyboard focus through skip/search/filter/
  card, resolved dossier navigation, incomplete facets, API-unavailable `SERVICE_UNAVAILABLE`,
  unknown-Person `Profile not found`, and a 390px viewport with a long Korean name. The mobile
  DOM reported `scrollWidth=375` for `innerWidth=390`; no console warning/error was captured.
- GitHub Actions Verify run `35090241928` for this commit completed successfully in `2m23s`.
  No staging/production deployment or database write was made for this milestone.
