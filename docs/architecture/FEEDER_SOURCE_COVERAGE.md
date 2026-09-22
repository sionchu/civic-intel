# Feeder Source Coverage

## Purpose

Civic Intel maintains one canonical map of **where publicly consequential people can be
discovered before profiling** and which evidence lane is authoritative for each career
route.

This document is not a second SourcePolicy registry. `SourcePolicy` remains authoritative
for collection, storage, AI-use, excerpt and commercialization rights. This matrix only
tracks product coverage and source strategy.

Person-discovery lanes may proceed through this downstream flow after the relevant gates;
source-level observations can stop before identity. Profiling remains optional:

```text
authoritative public source
 -> safe staged person/career candidate
 -> Identity Resolution
 -> Person / CareerEpisode / institutional objects
 -> AppointmentPath / TalentPoolEntry
 -> Public Official Profiler
```

A person-discovery feeder discovers candidates. It does not assert appointment probability, ideology,
partisan desirability or hidden influence.

The matrix also records explicitly labeled enrichment-only lanes. Such lanes do not expand
the Person discovery universe; their observations still use the same policy/evidence gates.

## Maturity legend

- `L0 RESEARCHED`: source and policy strategy are documented.
- `L1 CONTRACT_STAGED`: canonical/staging contracts and deterministic fixtures exist.
- `L2 SINGLE_PULL`: a reviewed source-specific connector can fetch one page/entity, or a
  rights-approved human-assisted packet import proves the equivalent single-packet boundary.
- `L3 FULL_ENUMERATION`: the bounded source universe has validated coverage, persistent runs,
  committed checkpoints, resume and idempotent observation tests.
- `L4 PRODUCTION_SYNC`: scheduled or incremental refresh, freshness, reconciliation and
  operational monitoring exist.

`BLOCKED` qualifies the blocked path, not the usefulness of every possible acquisition route.
Keep actual maturity, automation ceiling and conditional human-assisted path separate. Code,
fixtures, manual row counts or a successful packet import alone do not promote a feeder to L3.

## Coverage matrix

| Feeder | Public person scope | Strongest source lane | Mode | Identity anchor | Career / ontology destination | Maturity |
|---|---|---|---|---|---|---|
| National Assembly members | elected National Assembly members | 열린국회정보 member API | API | `MONA_CD` | Legislative | L3 FULL_ENUMERATION |
| National Assembly historical member careers (enrichment only) | former-member career rows returned for a selected `PROFILE_UNIT_CD`; current roster is a separate lane and is not included by this service | 열린국회정보 `nfzegpkvaclgtscxt` historical member-career API | API | `MONA_CD` is a provider namespace; no stable row-level Person key is published | packet-only parser plus existing temporal Claim/Evidence semantics; one reviewed Person proof can produce a derived CHANGE, but no automatic Person path or live CHANGE coverage | L1 CONTRACT_STAGED; L3 promotion blocked — 22 term labels were observed, but the provider publishes no complete code manifest, row key, correction/version contract or service-specific reuse decision |
| National Assembly asset disclosure (enrichment only) | existing officially anchored Assembly members; no family or staff discovery | National Assembly Gazette origin → opengirok/OpenWatch separate curated transformation sources | STRUCTURED_DISCLOSURE; source gate only | official `MONA_CD` preferred; curator IDs/row ordinals are not Person authority | existing AssetDisclosure/AssetItem and Claim/Evidence semantics; no new schema | L0 RESEARCHED; BLOCKED — release coverage, revision/key semantics and permitted route contract unresolved |
| Gwanbo personnel notices | official personnel-notice metadata in an explicit publication-date window | 대한민국 전자관보 인사 API | OFFICIAL_WEB | notice `cntntSeqNo`; no Person anchor at list stage | Public Service notice discovery | L3 FULL_ENUMERATION; metadata only, no Person creation |
| National Assembly bill participation | exact representative/co-sponsorship when complete source/code coverage exists | `nzmimeepazxkubdpn` full-term scan | API | `MONA_CD` + `RST_MONA_CD` / `PUBL_MONA_CD` + `BILL_ID` | Legislative | L3 FULL_ENUMERATION; multi-person event observations, no Person creation |
| National Assembly Gukgam schedule discovery (enrichment only) | official committee/date schedule candidates whose provider text explicitly identifies 국정감사 | National Assembly Secretariat 국회일정 통합 API, data.go.kr 15126132; staged Open Assembly code `ALLSCHEDULE` | API | no Person/Organization identity anchor and no stable row identity proven at L1 | Hearing / Committee schedule discovery only | L1 CONTRACT_STAGED; live sample, stable row key and correction semantics pending; schedule text cannot publish audited organizations or witnesses |
| National Assembly proposal-reason / major-content text | official full `제안이유` / 주요내용 | no verified structured Open Assembly source found in 2026-08-30 review | BLOCKED | bill ID/detail link only | Legislative text evidence | L0 RESEARCHED; BLOCKED, no HTML scraping |
| Local elected-office winners | governors, mayors/county/district heads, local councilors and education superintendents elected in one exact election/type scope | NEC winner API | API | NEC `huboid` within `(sgId, sgTypecode)` | Local Elected Office | L3 FULL_ENUMERATION |
| Local election candidates | all candidate-registration rows in one exact unfiltered election/type scope | NEC candidate API | API | NEC `huboid` within `(sgId, sgTypecode)` | Local Elected Office candidacy | L3 FULL_ENUMERATION |
| Presidential Office / National Security Office | chiefs, senior secretaries, secretaries and other publicly named senior staff | official organization + personnel briefings | OFFICIAL_WEB | name + role + exact personnel action + event date + source record | Public Service / Appointment | L1 CONTRACT_STAGED; live adapter blocked pending route/rights gate (2026-09-12) |
| Presidential advisers / commissions / TFs | publicly named special advisers, commission chair/vice-chair/member and explicit presidential TF leadership | official personnel/body appointment records | OFFICIAL_WEB / STRUCTURED_DISCLOSURE | person + body + role + exact personnel action + date | CommitteeMembershipEpisode / Appointment | L1 CONTRACT_STAGED; live roster blocked pending route/rights gate (2026-09-12) |
| Central/local civil service | Senior Civil Service, senior local executives, open/competitive appointees, path-relevant named officials | official personnel notices, gazette, 나라일터 route evidence | OFFICIAL_WEB / STRUCTURED_DISCLOSURE | name + agency + title + date + adjacent career anchors | Public Service | L1 CONTRACT_STAGED; live adapter pending |
| MOIS standard Organization codes | current administrative institutions exposed by `행정안전부_행정표준코드_기관코드` | data.go.kr dataset `15077870`, `StanOrgCd2/getStanOrgCdList2` | API | seven-digit `org_cd` plus provider hierarchy/lifecycle fields; never a Civic Intel UUID | Organization universe candidate only; no Gukgam auto-binding or Organization materialization | L1 CONTRACT_STAGED; fixture-tested connector only, live fetch `NOT_RUN` because `MOIS_ORG_CODE_API_KEY` is absent |
| Retired-public-official employment review | published Government Public Ethics Committee review rows with former agency/title and destination organization | MPM / Government Public Ethics Committee result board and PETI result index | STRUCTURED_DISCLOSURE | MPM post/attachment reference; row ordinal is snapshot-local and no Person anchor is published | EmploymentReviewEvent | L1 CONTRACT_STAGED; L3 promotion blocked pending source contract |
| Public institutions | institution heads, standing executives, relevant directors/auditors | ALIO item 4 current disclosure for every unfiltered directory institution | STRUCTURED_DISCLOSURE | ALIO `apbaId` + `disclosureNo:row ordinal` observation key + name/role/term; no provider Person ID; no-current, masked/vacant and correction-only outcomes remain explicit | Institutional Governance / Public Service | L3 FULL_ENUMERATION for current-disclosure observation coverage; source-specific operator-run Organization Claim publication is available; automatic Person materialization remains REVIEW_REQUIRED |
| Public-institution head business expense | no Person discovery; institution + `INSTITUTION_HEAD` role scope + fiscal-year aggregate | ALIO item 12 `기관장 업무추진비`, `reportFormRootNo=20701` | STRUCTURED_DISCLOSURE | `apbaId` identifies institution; exact `disclosureNo:fiscal_year` identifies a normalized annual row only after report identity and unique fiscal-year validation; never a Person ID | MONEY derived input; organization Claim publication requires an existing reviewed canonical Organization binding | L2 SINGLE_PULL for the bounded C0019/C0129/C0908 proof; L3 not attempted; live public MONEY surface blocked |
| Local public institutions | local-public-enterprise and local invested/contributed institution heads and disclosed executives | CleanEye named executive structured disclosures; official REST catalog has no named-executive dataset, and the exact HTML routes remain blocked by the current all-path robots/route contract | OFFICIAL_WEB / STRUCTURED_DISCLOSURE | institution-level `entId` or `insttCode`; no provider Person ID, so all materialization must remain REVIEW_REQUIRED | Institutional Governance / Public Service | L0 RESEARCHED; BLOCKED |
| Public-institution executive compensation | role-category compensation/annual-pay disclosures | ALIO item 10 | STRUCTURED_DISCLOSURE | institution + executive role category + fiscal year | Institutional Governance | L1 CONTRACT_STAGED; person attribution prohibited |
| Public-institution reemployment | executive reemployment; employee rows retained only without Person candidate | ALIO item 7-1 | STRUCTURED_DISCLOSURE | institution + executive name when public + dates | Institutional Governance / Reemployment | L1 CONTRACT_STAGED; separate from ethics review |
| Policy banks / state-linked companies | public-policy bank executives; state-linked listed-company boards/executives | statute + ALIO/OpenDART/KRX/institution governance | STRUCTURED_DISCLOSURE | org IDs / DART corp code + person | Institutional Governance / Corporate | L1 CONTRACT_STAGED; connectors pending |
| Private-sector disclosed executives | registered/non-registered executives publicly disclosed in periodic reports | OpenDART corp-code master + `exctvSttus` for one exact business-year/report-code scope | API | `{corp_code}:{rcept_no}:{row ordinal}` disclosure-row key; no provider Person ID | Corporate | L3 FULL_ENUMERATION; all Person materialization remains REVIEW_REQUIRED |
| Private-sector disclosed compensation | named statutory compensation disclosures | OpenDART compensation V2 APIs | API | DART corp code + receipt no + disclosed name | Corporate enrichment | L2 SINGLE_PULL; no Person creation alone |
| Private-sector officer/major-holder ownership | disclosed officers/major holders with specific-security ownership reports | OpenDART `elestock` | API | DART corp code + receipt no + reporter + public relation | Corporate / Ownership | L2 SINGLE_PULL; no automatic conflict inference |
| Private-sector senior technical/business leaders | CEO/CTO/CSO, research/technology-center and major business-unit heads not necessarily in DART executive status | company official governance/profile/press material | OFFICIAL_WEB | reviewed source + company + person + senior role + dates | Corporate | L1 CONTRACT_STAGED; per-company adapters pending |
| Government-funded policy research outputs | named responsible researchers on public policy outputs | NKIS `ReportList.do` | API | NKIS output ID + responsible-researcher text + year | Academic / Policy Research Output | L2 SINGLE_PULL; no employment inference |
| Government-funded research careers | institute presidents/directors/researchers with verified role/tenure | institute official profile / appointment release | OFFICIAL_WEB | person + institute + role + dates | Academic / Policy Research Career | L0 RESEARCHED; KDI automated profile path BLOCKED — no published complete universe, stable profile key, correction/version or profile-specific reuse contract |
| General academia | professors/researchers relevant to public appointments | KCI, OpenAlex, Crossref, ORCID + university official profile | API + OFFICIAL_WEB | DOI/ORCID/OpenAlex + identity anchors | Academic | L0 RESEARCHED |
| Judges / prosecution / judicial administration | judges, court presidents, prosecutors, senior prosecution and judicial-administration roles | MOJ prosecutor personnel + Supreme Court personnel releases/Court Gazette, independently gated by release/issue | STRUCTURED_DISCLOSURE / OFFICIAL_WEB | name + office/title + effective date + prior office anchors; post/issue keys are packet identity only | Legal/Judicial/Prosecution | L1 CONTRACT_STAGED; human-assisted L2 packet path conditional, live/L3 adapters pending |
| Lawyers / law firms | public professional registration and publicly consequential law-firm roles | KBA public search + official law-firm biography | OFFICIAL_WEB | public professional identity + firm/role/date when verified | Legal / Professional | L0 RESEARCHED; no broad crawling |
| Military | generals, chiefs, JCS/defense-policy leadership and path-relevant retired senior officers | MND/service personnel releases and official bios | OFFICIAL_WEB | name + rank/command + date | Military / Defense | L0 RESEARCHED |
| Diplomacy | ambassadors, senior foreign-service officers, path-relevant diplomats | MOFA personnel/appointment records | OFFICIAL_WEB | name + post + appointment date | Diplomatic / Public Service | L1 CONTRACT_STAGED; live adapter pending |
| Labor organizations / public leadership | explicitly public union representative/leadership only; no ordinary membership | 전국노동조합표준데이터 plus independently gated 민주노총, 한국노총 and 경사노위 official lanes | STRUCTURED_DISCLOSURE / OFFICIAL_WEB / DISCOVERY_ONLY | representative name + union/body + source/as-of/event anchors; provider/page keys are not Person authority | Civic / Labor Leadership | L1 CONTRACT_STAGED for standard data; federation/commission lanes L0 RESEARCHED, human-assisted only and L3 blocked |
| Civic / NGO / professional associations | public leaders of significant civic/professional bodies | official organization/governance/public disclosure | OFFICIAL_WEB / STRUCTURED_DISCLOSURE | person + organization + role + dates | Civic / Association / Nonprofit | L0 RESEARCHED |
| Party permanent staff | publicly named senior party staff/policy committee leadership | party official appointments; NEC for party context | OFFICIAL_WEB | person + party role + date | Political / Party | L0 RESEARCHED |
| Party think tanks | presidents/directors/researchers where public-interest relevance exists | official party-institute pages/publications | OFFICIAL_WEB | person + institute + role/output | Policy Research / Political | L0 RESEARCHED |
| Campaign staff | officially announced senior campaign roles | candidate/party official campaign releases; NEC election context | OFFICIAL_WEB | election + candidate + role + date | Campaign CareerEpisode | L0 RESEARCHED |
| Parliamentary staff / legislative researchers | publicly named aides/secretaries, committee professional staff, legislative researchers | official Assembly/public biographies and personnel notices | OFFICIAL_WEB | person + member/committee/office + dates | Legislative Staff / Public Service | L0 RESEARCHED |
| Media / public broadcasting | publicly consequential media executives, directors, senior editorial/policy leaders | broadcaster/company governance, OpenDART where applicable, official bios | STRUCTURED_DISCLOSURE / OFFICIAL_WEB | person + media organization + public role | Media Career Facet | L0 RESEARCHED |
| International organizations | Koreans with verified UN/OECD/World Bank/IMF/etc. roles | international-organization official bio/appointment; MOFA route/JPO context | OFFICIAL_WEB / API context | person + organization + post + dates | International / Diplomatic | L0 RESEARCHED |
| Financial-market institutions | KRX/KSD/payment/clearing leaders; financial-holding/bank executives and outside directors | ALIO where applicable; OpenDART/company governance otherwise | STRUCTURED_DISCLOSURE / API | org/corp code + person + board role | Institutional Governance / Corporate | L1 CONTRACT_STAGED through ALIO/OpenDART |
| Science/technology/medical public experts | national-lab/hospital/technical-society leaders and publicly named advisers relevant to appointments | institution/committee official sources | OFFICIAL_WEB | person + institution/body + role | Academic/Technical/Public Advisory | L0 RESEARCHED |

## Source acquisition playbook

This section governs acquisition strategy; it does not add runtime collection modes or approve
a particular source. It extends the existing coverage artifact instead of creating a parallel
playbook. Audit date: 2026-09-14. OpenWatch/opengirok are **methodology references**, not a
requested feeder or a source of automatic truth.

The companion [Source parsing and semantics](SOURCE_PARSING_AND_SEMANTICS.md) document fixes the
post-acquisition hierarchy, typed source-record boundary, locator vocabulary and revision
semantics without adding runtime abstractions.

### Observed methodology and Civic Intel adaptation

| Observed pattern / primary documentation | Adopt | Do not inherit |
|---|---|---|
| [Assembly composition](https://docs.openwatch.kr/data/national-assembly): current/historical Assembly APIs plus 헌정회-provided historical API; rows repeat across terms | A field authority map with source namespace, term and as-of time: Assembly supplies monaCode/name/party/district; current-member API supplies committee/role; 헌정회 supplies hjId; OpenWatch research supplies special notes | An Assembly-hosted 헌정회 field is still attributed to that provider. Do not treat all fields as independently government-verified, convert lunar dates implicitly, or retain contacts/staff |
| [Document normalization](https://docs.openwatch.kr/data/national-assembly/asset-disclosure): Gazette PDFs become Google Sheets through 정보공개센터 | Reproducible document-to-row extraction with exact page/table/row locator, units and separate original/analyst provenance | A cleaned amount is not the official file, true market wealth or an independently verified claim |
| [Extra jobs](https://docs.openwatch.kr/data/local-council/extra-job): request-acquired disclosures and separately attributed SBS material; latest filing selection | Identify request batch, responding institution, filing date and selected attachment | Latest selection must not erase previous filings; availability is not blanket reuse permission |
| [Former activity](https://docs.openwatch.kr/data/local-council/former-career): regional groups request submitted records in two rounds; non-disclosure and nonexistence responses differ | Request/response/attachment provenance, separate rounds and explicit response status | Nonresponse, withheld or record-not-held cannot become “no activity” |
| [Contribution documentation](https://docs.openwatch.kr/data/political-contributions/national-assembly): NEC information-request route; totals and donor detail are separate | Use the acquisition pattern for bounded annual aggregate questions | No donor dataset download, donor identity discovery or implied permission to redistribute response files |
| [Bounded citizen work](https://cfoi.or.kr/19321): named council universe, fixed collection period, website review and further requests | Assign institutions/packets to reviewers, retain scope and unresolved fields; escalate gaps to evidence acquisition | Curator commentary or media context must not silently alter official values or create wrongdoing claims |
| [Field dictionary](https://docs.openwatch.kr/data/local-council): own member code, MOIS area code, NEC election fields, website-researched current party and explicit 정보없음 | Trace each field independently; election-time party and later website party are different dated statements | One row-level “official” label is insufficient; MOIS area code is not a Person identifier |
| [Public project catalog](https://github.com/opengirok/localcouncil): current/prior Sheets, collection notes and comment-based corrections | Publish permitted methodology, release manifest, QA and correction rationale | A Git commit pins catalog text, not mutable linked Sheets. Public collaboration does not prove exhaustive peer review or immutable row history |

These are documented practices, not a claim that OpenWatch already has Civic Intel's immutable
observation, field-lineage validator or automated QA architecture. The localcouncil catalog also
mentions phone verification and Wikipedia/search-derived context: those cannot independently
authorize canonical identity or facts here. Preserve provenance and seek an attributable official
record rather than infer a missing value. No new dataset was downloaded for this methodology
audit; earlier asset QA remains dated evidence, not a fresh measurement.

OpenWatch's own member/contribution codes serve its dataset joins, not canonical Person
authority. MONA_CD, hjId, NEC candidate IDs and MOIS area codes retain different namespaces
and meanings. Adopt only source-backed crosswalks; matching names or similar ID strings is not
a bridge. Field precedence must be explicit for the relevant date; preserve disagreements
rather than choose whichever source was fetched last.

### Shared gates for every acquisition mode

Before collection, define the public-interest question, finite source/packet inventory,
field authority and allowed fields; evaluate SourcePolicy access, metadata/fulltext retention,
AI processing, excerpts, commercial use, attribution and redistribution separately.
Manual collection and information requests are not rights bypasses. A disclosed file is not
automatically licensed for every downstream use. In particular, the localcouncil catalog and
[2026 project notice](https://cfoi.or.kr/19321) prohibit commercial reuse, unlike OpenWatch's
general CC BY-SA statement: evaluate the exact dataset/edition and original rights, not the
brand. Do not relabel third-party data as the repository's code license.

The modes below are architecture vocabulary. Actual SourceCollectionMode currently contains
API, RSS, HTTP, BROWSER, DISCOVERY_ONLY and BLOCKED; it does **not** contain the other labels.
Use the actual permitted transport and reviewed policy notes/source class where supported.
Do not invent enum values, fake domains, URLs or a new registry to make the design executable.
The matrix's existing OFFICIAL_WEB label is an umbrella for official-document or bounded
manual-page acquisition; it is not a new transport or permission to crawl.

**Maturity and usefulness are separate.** L1 requires a source-specific staged contract and
deterministic fixtures. L2 may be one reviewed live pull **or one reproducible, rights-approved
human-assisted source-packet import**, as defined in BATCH_INGESTION.md. Neither proves L3.
An unread or merely downloaded packet is not L2. L3 still requires full declared source-universe
coverage, transactional runs/checkpoints, resume, immutable changes and idempotent regressions.
Do not rename a convenient sample as the full universe to claim L3. L4 remains deferred.

### API

- **Authority / boundary:** issuing provider for its documented fields; exact endpoint,
  filters, period and page inventory, including declared no-data responses.
- **Normalization / provenance:** deterministic typed mapping; provider record ID plus
  Source/SourceSnapshot, request scope (without credentials), field origin and parser revision.
- **Identity / version:** official namespace anchors only under existing materialization rules;
  stable key plus semantic hash; preserve corrections, changed snapshots and declared tombstones.
- **Ceiling:** L2 single pull; L3 only after full-coverage tests; no L4 scheduling in this scope.
- **Rights / QA:** API terms, limits and field retention permissions; page totals, unique keys,
  drift, partial failures, retry/resume, missingness and secret exclusion.

### STRUCTURED_DISCLOSURE

- **Authority / boundary:** filing issuer and exact report/release inventory, not the download host;
  distinguish reporting entities, disclosure types and periods.
- **Normalization / provenance:** table/CSV/XLSX mapping with units and source locators;
  official filing and any curator representation remain distinct Sources/snapshots.
- **Identity / version:** filing/item keys are not Person IDs; snapshot-scoped ordinals require
  a justified rule; preserve release replacements rather than infer cross-release item continuity.
- **Ceiling:** L1 fixtures; L2 reviewed packet or pull; L3 only with a complete contracted universe.
- **Rights / QA:** origin and transformation licenses, fulltext/excerpt/redistribution separately;
  duplicates excluding ordinals, row/subtotal cardinality, field gaps, totals and amendment tests.

### OFFICIAL_DOCUMENT

- **Authority / boundary:** issuing institution's named notice/response packet, exact attachments,
  edition and page range; no archive-wide crawling.
- **Normalization / provenance:** deterministic PDF/table extraction plus human comparison;
  OCR is a candidate transcription, never authority. Pin byte hash, page/row/field locator,
  parser revision and reviewer decisions; separate official file from analyst-normalized Source.
- **Identity / version:** retain absent names/dates; no Person/event invention. Document+snapshot+
  locator may identify a packet observation, not a permanent case; new bytes/review corrections
  create new versions with explicit replacement reason, never overwrite.
- **Ceiling:** human-assisted L1/L2. Automated L3 needs a separately validated complete document
  manifest and all normal enumeration gates; PDF format alone neither enables nor forbids L3.
- **Rights / QA:** document-specific storage, parsing, redaction and reuse basis; page/row coverage,
  multi-line cells, dates/units, unknown tokens and visual review of every accepted pilot row.

### INFORMATION_REQUEST

- **Authority / boundary:** responding institution for the actual response, not the requester or
  portal tool; approved question, institution list, date window and request round.
- **Normalization / provenance:** request → response/decision → attachment → reviewed extraction.
  Keep safe request reference, institution, request/response dates, response status, attachment
  identifier/hash/page locator and amendment relations; exclude requester credentials/contacts.
- **Identity / version:** request IDs identify requests, never Persons. Separate rounds,
  supplemental responses, appeals and replacement attachments; no identity inferred from a name.
- **Ceiling:** L1/L2 human-assisted packets. A completed request batch does not prove a national
  source universe or authorize L3; reconsider only with a separately proven official contract.
- **Rights / QA:** sending requests, costs and account access need task-specific authority;
  receiving is not redistribution permission. Reconcile expected institutions, unanswered,
  transferred, partially disclosed, refused and not-held cases; check attachment completeness.

### BOUNDED_MANUAL_CURATION

- **Authority / boundary:** exact official institution page/packet for each field; analyst only
  attests transcription. Assign a finite institution/URL list, time window and reviewer.
- **Normalization / provenance:** fixed field dictionary and deterministic normalization;
  keep origin snapshot/locator, analyst representation, review date and correction rationale.
- **Identity / version:** no name-only linkage; curator join IDs remain local namespaces.
  Freeze each capture/review edition and retain prior values; never silently fill from another date.
- **Ceiling:** L1 staged fixture; L2 reviewed reproducible packet import, never L3 by manual row count.
- **Rights / QA:** respect source terms and data minimization, not robots evasion by outsourcing
  automation to people. Check all accepted pilot fields against origin; record explicit 정보없음,
  unreadable, withheld, not-collected and not-applicable separately from zero/none.

### DISCOVERY_ONLY

- **Authority / boundary:** no truth/identity authority; finite search or route reconnaissance
  for a stated question, including Firecrawl when available.
- **Normalization / provenance:** candidate URL, publisher and discovery reason only where
  policy permits; resolve to the actual origin before extracting supporting observations.
- **Identity / version:** no automatic links; discovery timestamp/version describes the lead,
  not the person's attributes or a source record.
- **Ceiling:** L0 source strategy; discovery results do not earn L1/L2 ingestion maturity.
- **Rights / QA:** check tool and target terms, no bypass/private payload; verify primary route,
  remove duplicate origins and distinguish stale/error/challenge pages from source no-data.

### Source-level reviewed observation import — design only

This is an acquisition boundary, **not** a new bundle, table, framework or implemented command.
It does not restore ReviewedPersonBundle as the main ingestion path.

1. Review an exact packet manifest and policies before any processing. Record permitted
   metadata/locators, publication/filing dates separately from capture time, and excluded fields.
2. Normalize with a pinned deterministic rule; have a reviewer compare accepted fields with
   the original. Preserve unresolved values explicitly; reviewer agreement is not FACT status.
3. Keep original response/document and analyst representation as different Sources/snapshots.
   Existing SourceOriginCluster prevents counting copies as independent corroboration; it is
   not a field-lineage graph. Split observations by source and atomic claims by field authority.
   If a composed representation is needed, require exact per-field source/snapshot/locator
   references and transformation provenance; no generic metadata “official” stamp.
4. Future implementation must validate all references, rights, duplicate keys and provenance
   before using the shared repository; record only policy-permitted normalized observations.
   Packet SUCCESS means that manifest was processed, not that all public records were acquired.
   Commit observations before/with the packet checkpoint and prove unchanged-rerun idempotency.
5. Separate byte identity from semantic changes and corrections. An unchanged semantic value
   with changed origin lineage must not silently reuse old provenance. Pin packet/edition scope
   and test lineage-sensitive identity or hashing; the current observation dedup key does not
   automatically preserve every later sighting. Never mutate an old normalized observation.
6. No automatic Person or FACT promotion. Unresolved identities remain observations; reviewed
   identity and Claim/Evidence publication checks remain independent downstream gates.

Actual-code constraints checked at master 2332755: Source.url is HttpUrl; a private local file
is not a valid new Source URL. SourcePolicy is currently bound uniquely by domain, so
per-attachment decisions cannot be implemented as conflicting same-domain policies. Do not
weaken a domain policy to accommodate one packet. SourceSnapshot has one source_id and
FeederObservation one snapshot_id; commit_source_page enforces one supplied snapshot per chunk.
Metadata references are not validated lineage FKs or a ready-made reviewed import API.
A packet lacking representable provenance/rights stays offline pending a narrowly scoped design;
no fake public URL, shadow archive or schema expansion is authorized by this audit.

EmploymentReviewEvent requires person/organization IDs and review_date; anonymous packet rows
must not be forced into it. Existing AssetDisclosure/AssetItem are skeletal contracts/tables,
not a working asset importer. Neither current materialization nor Claim.person_id permits
inventing a Person to store an anonymous official result.

### ogk tooling reference

[ogk README](https://github.com/opengirok/ogk) describes account-scoped request listing,
date/page selection, response-file download and status synchronization. Its “bills” are
information requests, not legislative bills. Inspected source revision:
[7d2295323a8970b2d7a9a60c10fb9665638bf1a1](https://github.com/opengirok/ogk/tree/7d2295323a8970b2d7a9a60c10fb9665638bf1a1).

The separate fetch/download/sync commands suggest useful acquisition stages. Source inspection
of [download.rs](https://github.com/opengirok/ogk/blob/7d2295323a8970b2d7a9a60c10fb9665638bf1a1/src/commands/download.rs)
also shows remote-repository synchronization/upload; it is not necessarily a local-only download.
[sync.rs](https://github.com/opengirok/ogk/blob/7d2295323a8970b2d7a9a60c10fb9665638bf1a1/src/commands/sync.rs)
uses a configured external database and refreshes pending requests when dates are omitted.
Adopt the separation of request inventory, status and attachments, not its storage, logging,
bulk request sizing, concurrency or remote upload behavior as a Civic Intel contract.

The [MIT license](https://github.com/opengirok/ogk/blob/7d2295323a8970b2d7a9a60c10fb9665638bf1a1/LICENSE)
covers the tool's code, not portal response data. No installation, login, request submission,
file download/sync, remote upload or integration was run. ogk is not an official API guarantee
or a runtime dependency. Firecrawl is route reconnaissance only; analysis tools are downloaded
dataset QA only. Neither supplies production truth.

### Bounded ALIO Item 12 reassessment

The Item 12 directory is a useful source-bounded structured-disclosure route even though the
complete institution directory has not been promoted to an annual-row L3 universe. The first
implementation proves one current report packet per explicitly selected known-positive institution:
the directory pointer, exact report page, embedded official document, normalized aggregate rows,
source-level snapshots and observation versions are all linked. The four current no-disclosure
directory rows remain explicit and are not converted into zero expense.

Its automation ceiling is bounded L2. The report exposes a current disclosure pointer and annual
rows, but no provider-declared correction/replacement chain for an annual row; the item-12
connector therefore fails closed on changed/duplicate identity conditions and never infers a
replacement or latest value. The canonical Claim contract now has an organization branch, but
publication still requires an existing reviewed Organization binding and an exact immutable
observation version. A narrow read-only organization MONEY route now consumes only published
annual organization Claims and exact ClaimEvidence/observation provenance. One operator-approved
C0908 local runtime slice exercises that route; this is not shipped/public coverage, and
organizations without the reviewed binding and annual Claim import still have no MONEY result.
The bounded observation worker remains L2 and is not promoted to L3 by this route.

### Blocked-lane reassessment

These are architecture classifications from the existing dated source gates, not new live
probes, permissions or maturity promotions. Human-assisted paths are conditional, not available
import commands. They need only a justified **packet** contract, not every L3 automation gate.

| Lane / unchanged maturity | Current automation ceiling | Human-assisted usable path | Reopen condition |
|---|---|---|---|
| Government Public Ethics / MPM — L1 CONTRACT_STAGED; L3 blocked | Existing offline stager only; no reviewed live L2 connector | One rights-approved named publication packet, deterministic extraction and full row review; source-level anonymous observations, no EmploymentReviewEvent requiring fabricated Person/review_date | Human L1/L2: packet permission, locators, typed dates/missingness and reviewed reproducibility. L3: separate complete result universe, correction/coverage and permitted route contract |
| National Assembly assets — L0 RESEARCHED; BLOCKED | No asset connector/import; earlier QA is not L2 | One official Gazette packet, minimized declared-value extraction and reviewer comparison, original/analyst Sources distinct; no OpenWatch ingestion or family Persons | Human L1/L2: rights-approved packet, units/type/period, safe keys/provenance and fixtures/import proof. L3: original-to-release completeness, revision reconciliation and permitted bulk contract |
| CleanEye — L0 RESEARCHED; BLOCKED | No repeated HTML collector under the revalidated all-path robots/route gate; no named-executive REST dataset | One institution's permitted official executive packet or supplied response; minimized named-role observations, REVIEW_REQUIRED, no name-only merge | Human L1/L2: approved finite acquisition/retention, exact institution/edition and reviewed fixture/import. L3: permitted named-executive route, institution universe, coverage and version contract |
| National Assembly roll-call votes — L0 RESEARCHED; BLOCKED | No vote connector; official catalog/service metadata gives only a partial scope and license/attribution surface, not a complete operation contract | One finite official file/packet under its published terms, with bill/session/member anchors and source-level review; no OpenWatch ingestion, ideology inference or automatic FACT promotion | Reopen: published operation/schema, 20th+ coverage proof, pagination/total, stable vote/member/bill keys, correction/version behavior, route limits and QA evidence |
| Labor federation / social-dialogue leadership — L0 source gates; aggregate labor standard-data lane remains L1 | No central stable roster or complete machine-readable universe across the independently reviewed 민주노총, 한국노총 and 경사노위 lanes; no live adapter | A finite rights-approved 민주노총 page packet, 경사노위 post/attachment packet or bounded 한국노총 official event may support human-reviewed source observations; no ordinary membership or name-only identity | Reopen L3 only with a complete declared universe, deterministic page/document coverage, stable record semantics, correction/version behavior, route limits and reuse rights; human L1/L2 requires packet manifest, locator, minimized fields and reproducible review |
| MOJ / Supreme Court legal personnel — L1 CONTRACT_STAGED | Release/issue packets expose named personnel tables, but no unified complete universe, row-level Person key or single correction/version contract; Court Gazette contains multiple order types; first MOJ packet candidate is not rights-cleared for acquisition | One rights-approved MOJ personnel-round packet or Court Gazette issue with deterministic extraction, exact locators and review; reuse `LegalPersonnelRecord` and shared observations, no case-responsibility or name-only inference | Reopen L3 only with an exact personnel/order universe, issue/page coverage, stable record semantics, correction/withdrawal behavior, route limits and rights; human L2 requires packet-specific storage/redistribution decision |
| Government-funded research careers / KDI — L0 RESEARCHED; automated path blocked | Current official researcher/profile views have no declared complete staff universe, stable profile key or profile-specific reuse contract; KDI Open API is publication metadata only | A finite rights-approved KDI profile/appointment packet may support human-reviewed source observations with original and analyst representations kept separate; no name-only identity or automatic Person materialization | Reopen automated L3 only with a complete institute universe, deterministic coverage, stable identity/version semantics, route limits and reuse rights; human L1/L2 requires exact packet scope, rights, deterministic mapping and reviewer comparison |

### National Assembly roll-call votes — documentation-only source gate (2026-09-12)

This candidate is not a feeder implementation and is not promoted above `L0 RESEARCHED; BLOCKED`.
The [official Open Assembly service](https://open.assembly.go.kr/portal/data/service/selectServicePage.do/OPR1MQ000998LC12535)
describes member plenary results as 찬성, 반대 and 기권, states that its table view provides 22nd
Assembly information and that file/API access provides 20th Assembly and later information, and
identifies the origin system as the bill-information-system voting records. The page displays a
Public Use source-attribution notice. The [data.go.kr catalog](https://www.data.go.kr/data/15125948/openapi.do)
lists the same provider/service family as XML and marks its use range `이용허락범위 제한 없음`.
These are official distribution/origin metadata, not a complete row contract.

The inspected public pages do not publish an unfiltered vote universe or counts, endpoint
parameters, page/cursor contract, request limits, a stable vote-record key, the exact member/bill/
session/date field mapping (including a published `MONA_CD` field), or correction, withdrawal,
replacement and republication semantics. The Open API portal requires an authentication-key
application workflow, and its public Q&A list includes a title reporting a request to check missing
member records across multiple bills. That title is a QA lead, not a measured completeness defect.
The official [API-service shutdown notice](https://www.data.go.kr/bbs/ntc/selectNotice.do?atchFileId=&nttApiYn=Y&originId=NOTICE_0000000004011&pageIndex=1&searchCondition2=2&searchKeyword1=)
also shows that adjacent Assembly APIs can be retired or replaced during system changes, so a
service label alone cannot establish version continuity.

Identity remains anchored to the official Assembly roster when an official member identifier is
published. Any OpenWatch identifier is a provider/crosswalk key only; it cannot authorize a
Person merge, and name-only linking is prohibited. A future finite official packet could be
reviewed as a human-assisted source-level lane under the playbook, with original and analyst
representations kept as separate Sources and no automatic FACT or Person materialization. No
canonical vote model, migration, connector, downloaded packet or runtime OpenWatch dependency is
introduced by this gate.

An absent permanent Person/case ID does not destroy packet-level research value. Conversely,
human review cannot cure forbidden storage, missing original provenance or an unidentified
person. The detailed source gates remain authoritative for L3 and their historical evidence.

## Public-interest roster boundary

Civic Intel intentionally does **not** build broad directories of ordinary people merely
because a source exposes them.

Eligible discovery is limited to roles with a plausible public-decision, governance,
appointment or accountability purpose. Examples include elected officials, senior public
servants, institution heads, public board members, disclosed corporate executives, public
research/policy leaders, public union leadership and public civic-organization leadership.

The following are prohibited feeder behavior:

- ordinary civil-servant staff directories
- ordinary Presidential Office / commission / TF staff directories beyond publicly consequential named roles
- ordinary public-institution employee rosters
- ordinary private-company employee rosters, including using OpenDART employee-status data for person discovery
- ordinary union-member rosters or inferred union affiliation
- ordinary NGO/professional-association member rosters
- broad institute staff scraping merely to populate a researcher directory
- broad lawyer/law-firm staff or client roster scraping
- private donor/client/contact networks
- private addresses, phone numbers, emails or precise locations
- inferring political faction, ideology or loyalty from organizational proximity alone

## Provenance semantics by lane

A source may establish a narrower fact than the text visually suggests.

Examples:

```text
National Assembly RST/PUBL MONA code fields
 -> FACT of code-linked representative/co-sponsorship when the full Assembly scan and role-code coverage are complete
 -> joint representative proposers remain joint leads
 -> co-sponsorship is participation, not faction/alliance proof

National Assembly proposal-reason text
 -> currently BLOCKED in V0 because no verified structured source was found and bill-detail HTML scraping is prohibited
 -> do not fabricate a BPMBILLSUMMARY endpoint or infer content from the title

Presidential personnel briefing
 -> FACT of the dated official personnel action with the exact wording: 임명/지명/내정/위촉/etc.
 -> 지명/내정 is not silently promoted to completed appointment
 -> prior-career text is FACT that the Presidential Office reported it, not automatically an independently verified CareerEpisode
 -> meeting/event attendance is not Presidential Office employment, adviser, commission or TF membership

Cross-lane profile research target
 -> an official source may supply two role observations when its wording explicitly pairs the same person across lanes
 -> explicit continuity evidence can resolve a research identity link without creating a Person merge
 -> preserve the exact source reference on each observation and do not invent an organization or completed appointment status
 -> the target remains research-only and does not publish a FACT by itself

NEC candidate career string
 -> FACT that the candidate submitted that career to NEC
 -> not automatically independently verified career FACT

NKIS responsible-researcher field
 -> FACT that NKIS identifies a person/text as responsible researcher for that output
 -> publishing institution is an output property, not automatically the person's employer
 -> institute employment/leadership needs an institute official source

NKIS repeated topic
 -> DERIVED only from at least two separate research outputs
 -> not a research-quality score or permanent expertise label

MOJ / Supreme Court personnel order
 -> FACT of the dated role/transfer/appointment stated in the official order
 -> not automatic personal responsibility for every case handled by that office
 -> not an ideology, sentencing-tendency or prosecution-tendency score

law-firm affiliation
 -> FACT of a verified professional affiliation when supported
 -> not a client relationship or political relationship edge

labor-union representative field
 -> FACT that the official standard dataset publicly names that representative for the union
 -> membership count remains organization-level
 -> does not establish ordinary membership, party, faction or ideology of other people

OpenDART executive-status row
 -> FACT that the reporting company disclosed the named person/role in that report
 -> preserve `rcept_no` because extracted OpenDART data is not a substitute for the original filing
 -> `corp_code` identifies the company and `rcept_no` identifies the filing; neither identifies a Person
 -> name + company + role does not authorize automatic Person creation, linking or merge

Retired-public-official employment-review row
 -> FACT of the Government Public Ethics Committee result fields published for the review packet
 -> `취업가능` / `취업승인` / `취업제한` / `취업불승인` are decision outcomes, not wrongdoing findings
 -> the result packet does not establish that the person actually took the job
 -> the published PDF sample has no person name or provider case identifier; no Person materialization or merge is authorized

OpenDART compensation row
 -> FACT of a disclosed compensation amount for the reporting period
 -> not total wealth and does not create a Person candidate without a separate senior-role identity match

OpenDART officer/major-holder ownership row
 -> FACT of a dated specific-security ownership disclosure and disclosed company relation
 -> not automatically effective control, conflict of interest or political influence

company official senior profile
 -> FACT that the company publicly identifies the person in the stated senior role/responsibility
 -> not automatic DART registered-director status or causal ownership of company performance

ALIO major-career entry
 -> FACT that the public institution disclosed the entry
 -> verify important prior CareerEpisodes against their original sources

ALIO role-category compensation
 -> FACT about institution/role-category compensation disclosure
 -> not automatically a named person's compensation or wealth

ALIO Item 12 institution-head business expense
 -> source observation of the institution's officially reported aggregate amount for a fiscal year
 -> preserve `apbaId` as the institution namespace, `disclosureNo` as report identity and
    `submissionNo`/attachment filename as locator metadata
 -> `amount_thousand_krw` is the source unit; `amount_krw` is deterministic integer normalization
 -> a descriptive year-over-year MONEY result is not personal spending, waste, corruption,
    performance, peer ranking or a named institution-head claim
 -> the bounded read-only organization MONEY route is Claim-gated; organizations without a
    reviewed Organization binding and annual organization Claim import have no live result

ALIO reemployment disclosure
 -> FACT of disclosed retirement/reemployment event
 -> not the same event as a Public Ethics Committee employment-review decision

public entity owns 26.41% of a listed company
 -> FACT of dated ownership
 -> not automatically FACT that government personally selected the CEO

retired-official employment review = 취업승인
 -> FACT of the committee decision
 -> not a revolving-door violation
```

## Implementation priority

Prefer new feeders in this order:

1. stable official API or structured disclosure with strong identity anchors;
2. official named personnel/appointment records;
3. official organization biographies/governance pages;
4. attributable media only for discovery/context.

Current recommended sequence after presidential-personnel staging:

1. completed (fixture-only): civil-service -> Presidential personnel -> profiler research target
   (`profile_target_lee_wonjoo_001`); no live adapter or Person materialization;
2. one small reviewed live Presidential personnel or commission-roster adapter using #36 semantics;
3. completed (2026-09-12): independent federation/social-dialogue source-contract gate using
   #20 semantics; no live adapter or maturity promotion;
4. completed (2026-09-12): MOJ/Supreme Court personnel source-contract gate using #21
   semantics; no live adapter or maturity promotion;
5. completed (2026-09-13): KDI institute-profile source-contract gate for NKIS-discovered
   researchers; automated profile path remains blocked, with no live adapter or maturity promotion;
6. completed: reviewed ALIO item 4 current-roster L3 adapter using the existing staging contracts;
7. completed (2026-09-13): CleanEye local-public-institution executive source-specific
   revalidation; the all-path `robots.txt` instruction and named-route contract remain open, so
   the lane stays L0 blocked. A stable Person ID is not a collection prerequisite, but it cannot
   authorize automatic materialization;
8. completed: source-bounded OpenDART executive-status L3 over the official corp-code master;
9. completed (2026-09-14): bounded ALIO item 12 institution-head business-expense source slice,
   organization-scoped Claim/Evidence path and Claim-gated read-only MONEY projection; L2 only,
   with no automatic organization binding or live claim run;
10. completed (2026-09-18): ALIO item 4 current executive observations can be activated through a
   dry-run-by-default, source-specific Organization Claim/Evidence importer and read-only
   organization directory without creating Persons or changing Item 12 binding semantics;
11. one reviewed live civil-service/ethics source adapter using the #23 contracts, only after a
   permitted source contract closes;
12. revisit bill proposal-reason text only if a verified official structured source becomes available.

Reorder only when a stronger source dependency or a concrete product target justifies it.
