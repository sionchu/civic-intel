# Source parsing and semantics

Status: governing architecture reference, source-boundary audit and bounded packet proof on
2026-09-14.
This document fixes the boundary between source acquisition, parsing, normalized observations,
canonical records and derived product output. It does not approve a source, add a live collection
mode, create an L3 feeder or promote a lane to L3. A bounded reviewed packet may
exercise the existing Claim/Evidence and derived projection path only when its source identity,
snapshot and policy references remain attached.

The [source acquisition playbook](FEEDER_SOURCE_COVERAGE.md#source-acquisition-playbook) remains
the authority for acquisition modes, maturity ceilings, rights gates and human-assisted packet
conditions. This document is the companion semantic contract: it describes what each stage means
after a route or packet has been selected.

## Why this boundary exists

Civic Intel receives heterogeneous public material: APIs, structured disclosures, HTML boards,
PDFs, spreadsheets, information-request responses and bounded manual collections. A source can
be useful without providing a complete machine-readable universe, and a normalized row can be
useful without being a canonical Person or a published fact.

The repository therefore keeps these questions separate:

1. Who issued or answered the material?
2. What exact source, dataset, release, document or disclosure was captured?
3. What record and field did the parser read?
4. What immutable observation was retained under the applicable `SourcePolicy`?
5. Which canonical entity or event, if any, can a later identity and publication gate support?
6. What claim or derived presentation may be rendered from that evidence?

An empty field, a withheld field, a masked person, a non-response and a source that does not
publish a value are distinct source states. A parser preserves those states; it does not fill
them from names, proximity, search results or a later fetch.

## Canonical source hierarchy

The logical hierarchy is:

```text
Publisher / Authority
  → Source / Dataset lane
  → Release / Document / Disclosure
  → Source Record
  → Normalized Observation
  → Canonical Entity / Event
  → Claim / ClaimEvidence
  → Derived Intelligence / Product presentation
```

The hierarchy is semantic, not a request to create a table for every noun. Current persistence
uses the smallest existing objects:

| Layer | Meaning | Current repository representation | Boundary |
|---|---|---|---|
| Publisher / Authority | Institution that issues the record or answers the request; a curated project may be a separate publisher of a transformation | `Source.publisher`, `SourcePolicy.domain`/`source_class`, and source metadata | Publisher attribution is not proof that every field in a derivative dataset came from that publisher |
| Source / Dataset lane | One policy-scoped origin or curated representation with its own route, rights and field authority | `Source` + `SourcePolicy`; lane/scope in `SourceRun` and `FeederObservation` | Official origin and curated transformation are separate Sources even when they describe the same subject |
| Release / Document / Disclosure | A publication, attachment, filing, issue, response or dated edition inside a lane | `Source.url`, `Source.published_at`, `SourceSnapshot.metadata`, and source-specific normalized fields such as `notice_id`, `disclosure_no`, `rcept_no` | No generic `Release`, `Document` or `Disclosure` row exists; do not invent one to make a source look complete |
| Source Record | The provider's row/object/entry, including its provider namespace and source scope | Source-specific typed dataclasses plus `FeederObservation.provider_record_key` when persisted | A provider key identifies a source record; it is never automatically a canonical Person ID |
| Normalized Observation | Immutable, policy-minimized representation of what the source record said at capture | `FeederObservation` with `snapshot_id`, `run_id`, `normalized`, `content_hash`, scope and identity hints | An observation is not a canonical fact and cannot bypass identity or publication gates |
| Canonical Entity / Event | Repository object that has passed the relevant semantic and identity boundary | `Person`, `Organization`, `Office`, appointments, career/committee episodes, `Event`, asset contracts and other existing domain contracts | Parsers do not construct a canonical Person or infer a domain event from an unresolved row |
| Claim / ClaimEvidence | Publishable proposition and its attributable support/refutation | `Claim`, `ClaimEvidence`, `Source`, `SourcePolicy`, optional `SourceSnapshot`/`FeederObservation` | `FACT` requires the existing assertion and evidence gate; `UNKNOWN` remains explicitly non-asserted |
| Derived Intelligence / Product | Reproducible computation or presentation over eligible Evidence Core inputs | North Star concept only; no generic derived table or ontology is present | Derived output never edits Evidence Core or becomes a Claim through a side path |

`SourceRun` and `SourceCheckpoint` describe collection operations and resume state. They are not
evidence, publication status or real-world time. `SourceSnapshot` is the canonical source-level
capture. The repository has no second raw-payload truth store.

## Actual current model coverage

The current contracts and rows are sufficient for the existing source-specific paths:

- `SourcePolicy` gates technical fetch, metadata/fulltext retention, AI processing, excerpts,
  commercialization and related use conditions.
- `Source` identifies the policy-bound source URL and publisher. `SourceSnapshot` records capture
  time, the current source-level captured-body content hash, permitted metadata and optional
  permitted fulltext.
- `FeederObservation` records a provider key, exact snapshot/run references, semantic scope,
  policy-permitted normalized fields, identity hints and a normalized content hash.
- `PersonObservationLink`, `IdentityReviewItem` and `MaterializationDecision` keep identity and
  review decisions downstream from collection.
- `Person`, organization/office contracts, temporal episodes, `Claim` and `ClaimEvidence` are
  the canonical downstream objects. The existing repository is shared by API and workers.
- `AssetDisclosure` and `AssetItem` exist as small domain/persistence contracts, but they are
  not a completed asset acquisition product or a generic financial framework.

There is intentionally no first-class `Authority`, `Dataset`, `Release`, `Document`,
`Disclosure`, `SourceRecord`, `FieldLocator`, `ParserRegistry`, `RawObservation` or universal
expense/event table. Source-specific identifiers and locators can remain in existing metadata
or normalized JSON while that is sufficient and policy-permitted. A future table is justified
only by a real source contract that cannot be represented without losing rights, lineage,
correction or identity semantics; it must then use the normal Pydantic, SQLAlchemy and Alembic
path.

## Worked boundary case: National Assembly historical member-career API

The official [historical member-career service contract](https://open.assembly.go.kr/portal/data/service/selectAPIServicePage.do/OD21030011944P19666)
is the concrete validation case for this document. It is a separate service from the current
National Assembly roster API; the catalog names its endpoint `nfzegpkvaclgtscxt`, requires a
term-scoped `PROFILE_UNIT_CD` query, labels the service version `1 (21-01-08)`, and reports no
request limit. The active [CHANGE plan's source gate](../exec-plans/active/change-discovery-experience-v1.md)
records the read-only 2026-09-13 contract probe: pages were complete for the observed code
range, but the provider does not publish a finite code manifest, stable row key, correction
semantics or service-specific reuse decision. Its separate term-inventory service publishes
`ERACO` and term boundary fields, but its 55 response rows do not map every historical
`PROFILE_UNIT_CD` to that inventory.

The same probe fetched `PROFILE_UNIT_CD=100001..100022` page by page. The responses label those
codes `제헌` through `제22대` and contain 5,467 rows in total; the current roster response
contained 299 rows, with zero `MONA_CD` overlap across the observed historical rows. This is
consistent with the service's “재직자 미포함” description, not evidence that the two services
form a complete current-plus-former universe. `100000` and `100023` returned the provider's
no-data response, but those probes do not establish an upper bound or a permanent manifest.

The source gate remains documentation-only for live acquisition. The repository now contains a
packet-only typed parser and deterministic reviewed fixture for this case; they do not authorize a
historical-career connector, worker, source-policy expansion, database change, L3 promotion or
live CHANGE coverage.

### Identity, scope, time and record key are different

| API field/concept | Semantic role | What it is not |
|---|---|---|
| `MONA_CD` (for example `XQ98168F`) | Official Assembly provider identity/crosswalk value in the Assembly namespace; it can be an input to a later accepted bridge | Not `Person.id`, not proof of a canonical merge by itself, and not a term/history record key by itself |
| `PROFILE_UNIT_CD` (for example `100019` or `100020`) | Provider term/history scope for the career row; `PROFILE_UNIT_NM` is its provider label | Not a person identifier, not an election-to-Person mapping, and not a real-world date interval |
| `FRTO_DATE` (for example a source-reported `2012-05-30–2016-05-29` interval) | Temporal field published by this service for the source row; retain its source spelling/parse result and scope | Not capture time, not automatic proof of continuity or termination, and not permission to infer a later CHANGE |
| `{MONA_CD}:{PROFILE_UNIT_CD}` | A provider-person/term grouping value that identifies the observed scope | Not a source-record key: the probe found 17 duplicate groups among 5,467 rows, including two different periods for `0P85685J:100015`; not a canonical Person key, permanent global record ID or implemented identifier |
| term/history scope | The declared query and coverage boundary: former-member service, selected term codes and pages | Not a complete current-plus-former universe until the provider manifest and composition are established |
| canonical `Person` | Existing accepted Assembly identity object reached only through the downstream identity/materialization rules | Not created by parsing a row, matching a name, or concatenating provider fields |

The historical service publishes fields such as `HG_NM`, `HJ_NM`, `PROFILE_SJ`, `MONA_CD`,
`PROFILE_UNIT_CD`, `PROFILE_UNIT_NM` and `FRTO_DATE`. `PROFILE_SJ` is a composite display string;
the service does not publish separate party, district or title columns. The probe nevertheless
shows source-level changes: `XQ98168F` moves from `제19대 새누리당 울산 울주군` to `제20대 무소속
울산 울주군`, and `0P85685J:100015` has two dated periods within one term. A future typed source
record may retain these fields only under a reviewed policy and declared source scope. A
normalized observation would remain attributable to the historical service and its snapshot.
The current Assembly roster API remains a separate field authority for current roster fields;
the official term inventory remains a separate source for the term boundaries it publishes.
These sources must not be merged into one Source or treated as independent corroboration merely
because their records contain the same provider code.

If a later gate closes, an exact `MONA_CD` bridge to an existing resolved Person may support a
downstream identity decision. That decision would still be separate from parsing, and any
publishable role proposition would need its own Claim, ClaimEvidence, source policy and temporal
review. A changed `FRTO_DATE` would first be a changed source observation; it would not itself
be a real-world CHANGE event. The present lane remains `L1 CONTRACT_STAGED; L3 promotion blocked`.

## Parsing and normalization boundary

Parsing is a deterministic translation from one bounded source representation to a typed source
record or normalized observation candidate. It is not a general-purpose truth, identity or
analysis engine.

### Allowed parser responsibilities

- Extract fields from the declared API response, HTML table, PDF page/table, XLSX sheet or
  information-request attachment.
- Parse dates, amounts, units and provider enum values without changing their source meaning.
- Preserve provider identifiers, scope, source-reported labels and explicit missingness.
- Apply privacy minimization before persistence; exclude contact fields, unnecessary addresses,
  private family details and provider secrets.
- Emit deterministic source locators and normalization/content hashes when the representation
  supports them.
- Retain the parser, normalization and source-contract revisions in existing run/snapshot
  metadata where policy permits.
- Reject incomplete, contradictory or out-of-scope rows rather than silently repairing them.

### Parser prohibitions

A parser or source-specific worker must not:

- merge or materialize a canonical Person, infer a family member, or use name-only linking;
- turn an asset row, disclosure row, election row or source-record key into a Person ID;
- infer wrongdoing, ideology, friendship, influence, motive, causation or responsibility;
- reconcile two sources by choosing the last fetched value or by hiding disagreement;
- convert a missing, masked, withheld, not-held or unreadable value into zero, none or a name;
- treat a curated representation as the official origin, or treat a request response as a blanket
  reuse license;
- publish a Claim, promote a normalized value to `FACT`, or emit a derived CHANGE result;
- use a generic crawler, unbounded search result, Firecrawl output or analysis dataset as runtime
  truth; or
- make `ReviewedPersonBundle` the normal batch path.

### Logical processing stages

The current code implements these stages in source-specific modules rather than a generic
orchestration framework:

| Stage | Current responsibility | Required output/boundary |
|---|---|---|
| Fetch / capture | Policy-aware connector transport and `IngestionPipeline`; source-specific request scope and credential separation | `Source` and policy-permitted `SourceSnapshot`; no credentials in URLs, metadata or error summaries |
| Parse | Connector parser such as `parse_members`, `parse_executives`, `parse_candidates` or a document/table parser | Typed provider record with source fields, source key and explicit missingness |
| Normalize | Worker-specific `normalized_*` mapping and deterministic hash | Policy-minimized normalized candidate; preserve source semantics and units |
| Validate contract | Source-specific page totals, complete scope, duplicate/key checks, rights preflight and allowed-field checks | Accept, reject or fail closed; no implicit coverage promotion |
| Persist immutable observation | Shared `SqlAlchemyRepository.commit_source_page` | `FeederObservation` attached to the exact `SourceSnapshot`/`SourceRun`; checkpoint advances only in the same committed transaction |
| Identity / materialization | Existing provider-specific materialization or review gate | Only accepted identity rules can create/link a Person; ambiguous lanes remain review-only |
| Claim / publication | Existing verification claim and publication gates | `ClaimEvidence` preserves source trace; workers cannot publish through a side path |
| Derived / product | Future read-time or separately approved projection | Inputs, method, coverage and corrections remain explicit; never mutate Evidence Core |

`ConnectorDocument.body` is an in-memory transport value. `IngestionPipeline` may retain a
source-level fulltext only when `SourcePolicy` permits it. That is not a license to add a raw
record archive or expose a provider payload in a product surface.

## Multi-source composition and field-level provenance

OpenWatch and information-disclosure projects demonstrate a useful methodology pattern: one
dataset can combine several official or request-acquired lanes, while individual fields retain
different authorities. Civic Intel adopts the pattern with stricter boundaries:

```text
official origin or response
  → attributable Source/Snapshot
  → optional curated transformation Source/Snapshot
  → source-specific normalized observation
  → field-scoped ClaimEvidence where publication is allowed
```

Examples include current Assembly fields from 열린국회정보, historical fields from a separate
Assembly service, a 헌정회 crosswalk value, Gazette disclosure values, NEC election fields,
information-request attachments and analyst-normalized values. A field authority map must name
the provider namespace, effective/as-of time, transformation and source reference. A row-level
label such as `official=true` is not enough.

When two sources are composed, prefer separate observations and atomic claims. If a future
representation needs a combined row, it must retain per-field source/snapshot/locator
references and the transformation revision. `SourceOriginCluster` can prevent copies from being
counted as independent corroboration; it is not a field-lineage graph. Preserve disagreement
instead of overwriting one value with another.

OpenWatch IDs, `hjId`, NEC IDs, MOIS area codes and local curator keys stay in their own provider
namespaces. An explicit source-backed crosswalk may support a later research or identity gate;
similar strings and names alone never do.

## Locator strategy

A locator answers “where in this captured representation was the value read?” It is distinct
from a stable source-record key, which answers “which provider record is this?”

| Representation | Minimum locator components | Key/version rule |
|---|---|---|
| API JSON/XML | endpoint/service, credential-free request scope, page/index, provider field path and provider record key | Use the provider key if stable; page number alone is not identity |
| XLSX/CSV | attachment or release reference, captured-byte hash when available, workbook/file name, sheet/table, row and column/header | Sheet row ordinal is snapshot-local unless the provider supplies a stable row key |
| PDF | document/attachment reference, captured-byte hash when available, page, table/section, row and field/cell | OCR is a candidate transcription; page/table locator remains tied to the captured representation |
| HTML | origin URL, post/detail/disclosure ID, captured snapshot, table/list and row locator | A table ordinal can locate a row within a snapshot but is not a permanent Person or case ID |
| Information request | safe request reference, responding institution, response/attachment reference, hash and page/row locator | Request ID identifies the request packet, never a person or fact across rounds |

The current contracts carry these details in `Source.url`, `SourceSnapshot.metadata`,
`SourceRun.metadata`, `SourceCheckpoint.metadata` and source-specific normalized fields when
needed. They do not validate locator JSON as foreign keys. Do not fabricate a public HTTP URL for
a private/local attachment merely to satisfy `Source.url`; a real rights-approved origin or a
narrow future packet design is required.

## Version, correction and republication semantics

Keep four revisions distinct in existing metadata when a source path needs them:

- `source_contract_revision`: the reviewed endpoint/document/rights/coverage contract;
- `parser_revision`: extraction rules and field mapping;
- `normalization_revision`: deterministic normalized representation and hash rules; and
- `app_revision` or repository revision: the code/configuration revision that ran the job.

`SourceRun.metadata`, `SourceCheckpoint.metadata`, `SourceSnapshot.metadata` and connector
metadata are the current storage locations. No parser-version registry or migration is implied.

Source-snapshot capture and normalized semantics have different identities:

1. `SourceSnapshot.content_hash` identifies the current source-level captured body after the
   ingestion path's whitespace normalization; it is not a record/item key.
2. `FeederObservation.content_hash` identifies the normalized observation content.
3. The current persistence uniqueness rule uses `(feeder, scope, provider_record_key,
   content_hash)`. A changed normalized value under the same provider key is a new immutable
   observation; an unchanged rerun is idempotent.
4. If a provider declares correction, withdrawal, replacement or republication semantics, retain
   the new snapshot/observation and the declared relation. Never overwrite the old observation.
5. If the provider gives no such semantics, a changed row cannot be called a correction from
   response content alone. Use a fail-closed review rule rather than inventing one.

The current deduplication key does not capture every possible lineage-only change when the
normalized key and hash remain identical. A future source that requires lineage-sensitive
identity may justify a narrow contract/storage revision, but no speculative table or hash
framework is added now. `recorded_at`, fetch time and source publication time must not be
substituted for a provider's real-world event time. In the Assembly case, a changed `FRTO_DATE`
is first a new source observation; the CHANGE product must not infer a role transition from it.

## Maturity and human-assisted paths

`L3 promotion blocked` describes the automation ceiling, not the absence of research value. A
finite, rights-approved official document or response packet can support an L1/L2
human-assisted lane when it has a fixed manifest, deterministic extraction, exact locators,
reviewer comparison, explicit missingness, permitted storage and reproducible correction notes.

Human curation is still source-bounded processing. It cannot:

- become an automatic `FACT` promotion path;
- erase the original document/response or merge it with the analyst representation;
- use manual work to bypass robots, terms, retention or redistribution restrictions;
- create a Person from a name or local join key; or
- claim L3 from a manual row count.

For example, a source row that lacks a public person identity can remain a source-level
observation. It must not be forced into `EmploymentReviewEvent`, whose canonical contract
requires a `person_id`, organization IDs and a review date. This preserves the research value of
the packet without fabricating a canonical event.

## Current parser and worker inventory

The following inventory is based on the current repository, not a proposed universal parser:

| Lane | Actual modules | Current boundary |
|---|---|---|
| Assembly current roster | `packages/connectors/open_assembly.py`, `workers/assembly_roster.py` | JSON typed records; `MONA_CD` provider key; source-specific L3 enumeration and the only automatic Assembly materialization path |
| Assembly bill participation | `packages/connectors/open_assembly_bills.py`, `workers/legislative_activity.py` | Code-first bill records keyed by `BILL_ID`; multi-person observation; no Person creation |
| Assembly historical member career | `packages/connectors/open_assembly_historical.py`; `packages/verification/assembly_historical_review.py`; bounded fixture in `tests/fixtures/assembly_historical_known_positive_001.json` | Packet-only typed parsing and reviewed Claim/Evidence proof for one resolved Assembly Person; immutable snapshots are required, provider row identity/correction semantics remain unavailable, and no live worker/migration/L3 run exists |
| Gwanbo personnel notices | `packages/connectors/gwanbo_personnel.py`, `workers/gwanbo_personnel.py` | Bounded HTML/POST notice parser keyed by notice ID; metadata-only observation; no Person |
| NEC candidates/winners | `packages/connectors/nec_local_elections.py`, `workers/local_elections.py` | Source-specific API parsers keyed by NEC `huboid` within election scope; candidate-submitted semantics preserved |
| ALIO public-institution executives | `packages/connectors/alio_disclosures.py`, `workers/public_institutions.py` | Directory/report/document/table parsing; `disclosure_no:ordinal` observation keys; vacancies, masks and corrections explicit |
| ALIO institution-head business expense | `packages/connectors/alio_disclosures.py`, `workers/alio_business_expense.py`, `packages/rendering/money_projection.py` | Bounded Item 12 directory/report parsing for three known-positive institutions; `disclosureNo:fiscal_year` after exact report/unique-year validation; aggregate only, no Person attribution; organization Claim builder/read path is canonical-row gated, with no automatic organization binding or public MONEY route |
| OpenDART executives and related disclosures | `packages/connectors/open_dart_corporate.py`, `workers/corporate_talent.py` | XML/JSON corp master and report parsers; company/report/row keys; Person materialization remains review-gated |
| Civil service and MPM staging | `packages/connectors/civil_service_records.py`, `workers/civil_service.py` | Typed personnel/employment-review records; anonymous MPM rows remain source-level; no canonical event fabrication |
| Legal personnel | `packages/connectors/legal_personnel_records.py`, `workers/legal_careers.py` | MOJ/Court source-specific staged records; no unified universe or automatic Person path |
| Presidential personnel | `packages/connectors/presidential_personnel_records.py`, `workers/presidential_personnel.py` | Typed action records and source-attributed prior-career text; no independent career inference |
| Labor, policy research and company profiles | `packages/connectors/labor_union_records.py`, `nkis_research.py`, `company_official_profiles.py` plus their workers | Bounded/staging parsers with explicit scope and missingness; no generic roster or identity registry |
| Shared transport/capture | `packages/connectors/http.py`, `workers/ingest.py` | Policy-aware transport and source snapshot capture only; no discovery/parser registry |

The historical Assembly service has no live connector or parser-driven enumeration in the current
tree. The parser-specific regression file exercises only a bounded known-positive packet and the
existing persistence/projection chain; its fixture is not a complete history universe or a live
source authorization.

The ALIO Item 12 lane is different: its source-specific connector performs a bounded live pull for
three explicitly selected institutions. The directory `apbaId` is an institution namespace, the
current `disclosureNo` is a report identity, `submissionNo` is a submission/attachment locator,
and `fiscal_year` identifies the annual table item. The provider does not publish an annual-row
correction chain. The worker therefore retains only policy-permitted normalized aggregate fields,
uses `disclosureNo:fiscal_year` only after duplicate-year validation, and stores a changed value
as a new immutable observation rather than labeling it a correction. `.xls`/`.xlsx` names are
locators only; attachment bytes and report staff contacts are not stored.

## Storage and PostgreSQL impact

| Classification | Current decision |
|---|---|
| KEEP | `SourcePolicy`, `Source`, `SourceSnapshot`, `SourceOriginCluster`, `SourceRun`, `SourceCheckpoint`, `FeederObservation`, identity review/materialization links, canonical domain contracts, `Claim`, `ClaimEvidence`, shared repository and Alembic discipline |
| REVISE LATER | Metadata vocabulary for locators/revisions; source-lane granularity where one host has materially different rights; field-level lineage only when a real composition cannot be expressed safely in existing metadata; lineage-sensitive observation identity only when a real source requires it |
| MISSING ONLY WHEN A REAL SOURCE REQUIRES IT | First-class release/document/disclosure or locator records, or a narrowly scoped source-level reviewed-packet importer, only if existing Source/Snapshot/Observation metadata cannot preserve the source contract, rights, correction relation and exact locator |
| REJECT | `RawRecord`, `GenericDocument`, universal financial/event schemas, parser registry, shadow raw store, graph/RDF/OWL model, generic crawler rewrite and a `ReviewedPersonBundle` batch replacement |

The original Item 12 source-boundary slice had no PostgreSQL impact and added no generic financial
model, table, dependency or runtime table. The follow-on organization Claim contract adds only
the in-place `claims.organization_id` subject field through Alembic `0005`; it does not add an
`OrganizationClaim` table or a financial abstraction. Existing JSON metadata is not a substitute
for a future relational model when a concrete source proves one is necessary, but a future model
must be small, source-driven and migration-backed rather than speculative. The Item 12 MONEY
projection remains an in-memory deterministic result over exact observations; it does not become
a public MONEY surface through this contract.

## Verification contract

The existing tests are the evidence for the current source-specific architecture:

- `test_open_assembly.py` and `test_open_assembly_bills.py` cover policy-first access, key
  separation/redaction, typed fields and metadata-only source boundaries.
- `test_assembly_historical_change.py` covers source-key separation, bounded historical packet
  parsing, immutable observation/version behavior, ClaimEvidence provenance and the source-scoped
  derived CHANGE proof; the historical test does not perform a live fetch.
- `test_batch_assembly.py`, `test_batch_assembly_bills.py`, `test_batch_gwanbo.py`,
  `test_batch_nec_candidates.py`, `test_batch_nec_winners.py`, `test_batch_alio_executives.py`
  and `test_batch_opendart_executives.py` cover source-specific scope, page totals, duplicate
  keys, idempotency, changed versions, resume/checkpoint transactions, privacy and policy gates.
- `test_alio_item12_money.py` covers the Item 12 directory/report contract, five annual rows,
  `천원` normalization, attachment metadata-only handling, malformed/duplicate/mismatched input,
  three-institution bounded persistence, immutable reruns, no-Person/privacy gates, exact
  provenance, deterministic MONEY deltas and zero-baseline handling. It also covers the exclusive
  Person/Organization Claim subject contract, the reviewed Organization binding gate, exact
  organization Claim/Evidence import, immutable-version rejection and read-only organization
  routes.
- Domain, repository, materialization, migration and identity tests cover canonical contracts,
  publication gates, Alembic head checks, fail-closed identity and the boundary between research
  identity and canonical Person materialization.
- Staging tests for civil service/MPM, legal, presidential, NEC, ALIO, policy and company lanes
  cover typed normalization, explicit missingness and identity-safe source attribution.

For the source-boundary portion, run the repository's existing verification commands and a
relative-link check. The Assembly packet proof may produce a derived CHANGE in the test fixture
only; do not run a live historical-career fetch, add a fixture that implies a complete history
universe, download a new packet, or treat the proof as L3/live coverage. The ALIO Item 12 live
proof is limited to its three selected institutions and does not promote the complete directory
or the public MONEY surface.

## Boundary checklist for a future source

Before implementation, a source-specific plan must answer all of these questions:

1. What exact authority supplies each field, and is a curated representation separated from its
   origin?
2. What finite universe, term, date, page, release or packet is in scope?
3. What is the provider record key, and is it different from any canonical Person ID?
4. What locator identifies the field in the captured representation?
5. Which values are missing, masked, withheld, not-held, unreadable or not-applicable?
6. What source terms permit fetch, metadata/fulltext storage, normalization, AI processing,
   excerpts, publication, commercial use and redistribution?
7. How are correction, replacement, withdrawal, republication and late amendments represented?
8. Which existing `SourceRun`, `SourceCheckpoint`, `SourceSnapshot` and `FeederObservation`
   fields can preserve the contract without a new table?
9. What deterministic QA proves completeness, duplicates, cardinality, unit handling and
   unchanged reruns at the proposed maturity?
10. What exact downstream identity and Claim/Evidence gate is allowed, and what remains review-
    only or derived-only?

Failure to answer one of these is a reason to retain the lane at its current maturity or use a
bounded human-assisted path. It is not a reason to relax source rights, identity or publication
rules.
