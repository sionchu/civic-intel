# Career Facets

## Purpose

Civic Intel models **routes into public office** without assigning a person one permanent
occupation or `person_type`.

A person may have several simultaneous or sequential career facets:

```text
Person
├── Education / Credentials
├── Legislative
├── Local Elected Office
├── Academic
├── Corporate
├── Civic / Association / Nonprofit
├── Public Service
├── Legal / Judicial / Prosecution
└── Military / Diplomatic
```

Facets are evidence-backed projections of the canonical chain:

`Person -> Claim -> ClaimEvidence -> Source -> SourcePolicy`

They are not parallel truth stores. A facet field that becomes publishable must ultimately
be traceable to canonical evidence.

## Cross-cutting fields

Prefer reusable, time-bounded facts over occupation-specific duplicates:

- education institution, degree, field, dates when documented
- organization, position, role and tenure
- external identifiers such as National Assembly `MONA_CD`, NEC `huboid`, ORCID,
  OpenAlex author ID, and DART corporation linkage
- valid time and recorded time
- source provenance and source policy

Do not guess missing dates, degrees, identifiers, or organization links.

## Legislative facet

### Raw/documented facts

- party membership
- constituency and election type
- terms served
- committee membership and committee roles
- representative-sponsored bills
- co-sponsored bills
- bill proposal date
- responsible committee
- bill processing result/status
- roll-call participation when an official dataset supports it
- hearings, seminars and other documented legislative events

### Derived views

Derived values must be labelled as derived and retain source coverage:

- representative-sponsored bill count
- co-sponsored bill count
- counts by committee or processing result
- bill-title/topic distribution
- voting similarity or co-sponsorship network metrics

Never turn a partial page or incomplete source into an exact lifetime/term count.

### Faction / political lineage

`계파`, `누구 계열`, `측근`, `친○○`, or similar political-lineage labels are **not raw
profile facts** merely because people co-sponsor bills, vote similarly, appear together,
or belong to the same party.

They may be represented only as dated `CLAIM`, `INFERENCE`, or `HYPOTHESIS` with explicit
evidence. Stronger evidence can include public self-identification, documented campaign
roles, repeated appointments/collaboration, or direct statements. Network similarity is a
signal, not a faction FACT.

## Local elected-office facet

Central Election Commission candidate/winner APIs provide a strong official feeder for
subnational political careers.

Supported election scopes include:

- `3` 시·도지사
- `4` 구·시·군의 장
- `5` 시·도의회의원
- `6` 구·시·군의회의원
- historical `10` 교육의원
- `11` 교육감

The candidate API exposes NEC candidate ID, name/Hanja, birth date, election jurisdiction,
party, candidate number, public occupation, education, two career strings and registration
status. The winner API supplies official winner identity and vote result fields.

### Provenance rule

Education, occupation and career fields in the NEC candidate feed are **candidate-submitted
election records**. Civic Intel may accurately state that the candidate reported those
fields to the election authority, but should not silently promote every string into an
independently verified biography FACT.

### Privacy rule

The NEC API also exposes a coarse public address. Civic Intel discards it before staging
because location is unnecessary for appointment-path analysis.

### Election outcome rule

A candidate is a valid CareerEpisode whether elected or not. Losing candidacy must not be
dropped from a political career timeline.

Winner joins use NEC candidate ID when available. If winner pagination/coverage is
incomplete, absence from the staged winner page remains `UNKNOWN`; only complete source
coverage may support `NOT_WINNER`.

The unfiltered candidate and winner endpoints are separate L3 feeders for one exact
`(sgId, sgTypecode)` scope. Each validates provider page/size, total count, row count and unique
`huboid`, then persists resumable metadata-only observations. Filtered candidate/winner review
staging remains a separate L2-compatible path.

Candidate observations retain exact registration status without inferring an election outcome;
winner observations retain exact result fields. Both retain name, birth date, jurisdiction and
party while discarding address, gender and age. Neither bypasses Person materialization or
publication review.

### Career-path value

Local-election history can support descriptive feeder paths such as:

```text
기초의원 -> 광역의원 -> 기초단체장
지방의원 -> 국회의원
기초단체장 -> 국회의원 / 장관 / 대통령실
광역단체장 -> 중앙정부 고위직
교육감 -> 교육정책 고위공직
```

Historical frequency is descriptive and never appointment probability.

## Academic facet

Candidate source families, each requiring its own reviewed SourcePolicy:

- KCI Open API: article metadata, authorship, affiliation, journal, keywords and DOI
- OpenAlex: works/authors/institutions/topics and source-defined citation metadata
- Crossref REST: DOI/work/funder/ORCID/ROR metadata
- ORCID Public API: public works, employment and education where visibility permits

Expected projections:

- publications and authorship role when documented
- institution/affiliation history
- recurring research topics
- grants/funding when documented
- source-defined citation/impact metrics

Citation count is not an automatic research-quality score. Abstract/full-text rights are
reviewed separately from metadata rights.

## Corporate facet

Primary source family: OpenDART and company filings.

Expected projections:

- company and executive/director role
- tenure
- disclosed individual compensation
- officer/major-shareholder securities holdings
- company financial/business metrics during tenure
- material supply/sales contract disclosures when applicable

**Attribution rule:** company sales, orders, contracts, profit or valuation during an
executive's tenure are `company performance during tenure`. They are not automatically
attributed to that executive personally. Personal causal contribution requires separate
evidence and remains CLAIM/INFERENCE where appropriate.

## Civic / association / nonprofit facet

Expected projections:

- organization identity and public legal/registration status where available
- leadership role and tenure
- publicly documented activities, campaigns and projects
- compensation only when officially/publicly disclosed
- public-interest corporation settlement/financial disclosures
- donation collection/use disclosures where legally/publicly available
- sponsorship/donor relationships only when explicitly public and policy-approved

Do not discover private donors, infer donor relationships from social proximity, or expose
non-public financial/personnel information.

## Public-service / legal / military / diplomatic facets

Prefer official appointment/personnel announcements, gazette records, ministry/court/
prosecution/military/diplomatic biographies and other policy-reviewed public records.

Do not use private personnel databases as a shortcut.

## Facet lifecycle

```text
Reviewed source
    -> safe normalized record
    -> identity resolution / external-ID linkage
    -> staged facet candidate
    -> evidence/quality review
    -> canonical Claim/Evidence persistence
    -> facet projection / profile UI
```

Staging alone never creates a publishable factual assertion.

## Legislative source boundary

The National Assembly `의원 발의법률안` Open API (`nzmimeepazxkubdpn`) provides bill
identifiers/titles, proposal date, committee, processing result, Assembly term, display-name
proposers, and code fields used for exact participation:

- `RST_MONA_CD`: representative-proposer member codes; joint leads can be comma-separated;
- `PUBL_MONA_CD`: co-proposer member codes; reviewed public implementations document
  semicolon separation.

Exact term counts use an **unfiltered full-Assembly scan** and the reviewed Person's
`MONA_CD`. Name matching is not used for exact participation.

Exact representative/co-sponsored counts require all of the following:

- scan begins at page 1 and fetches every expected page;
- page totals remain consistent;
- unique `BILL_ID` count equals source `list_total_count`;
- no duplicate-page or conflicting duplicate-bill anomaly exists;
- both role-code fields are present and parseable on every source bill row.

If any condition fails, exact counts remain `UNKNOWN`/`None` rather than falling back to
`PROPOSER`, `RST_PROPOSER`, or `PUBL_PROPOSER` name strings.

The unfiltered term endpoint is L3. It persists one immutable multi-person event observation per
`BILL_ID`, with transactional page checkpoints and resume. Persistent observations retain exact
member-code sets but omit display-name proposer strings. They do not create Persons or publish
participation claims without an accepted exact `MONA_CD` identity and the canonical evidence gate.

A bill count is descriptive participation data, not a performance score. Raw
`PROC_RESULT` stays canonical; `대안반영폐기` is never silently treated as
`원안가결`/`수정가결`.

### Proposal reason / main-content text

As of the 2026-08-30 implementation review, no verified Open Assembly structured endpoint
was found that returns full `제안이유` / 주요내용 text. Current public datasets that contain
those texts obtain them from `likms.assembly.go.kr` bill-detail HTML.

Because Issue #13 prohibits bill-detail HTML scraping, Civic Intel records this source lane as
`BLOCKED_NO_VERIFIED_STRUCTURED_SOURCE`. It preserves official bill/detail identifiers and
links but does not fabricate a `BPMBILLSUMMARY` connector, infer content from titles, or use
third-party scraped text as canonical evidence.
