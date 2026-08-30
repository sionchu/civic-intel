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

## Legislative v0 source boundary

The first legislative activity source is the National Assembly `의원 발의법률안` Open API
(service code `nzmimeepazxkubdpn`). It provides bill identifiers/titles, proposal date,
committee, processing result, Assembly term, representative proposer (`RST_PROPOSER`) and
co-proposers (`PUBL_PROPOSER`).

The API's `PROPOSER` filter is treated as representative-proposer search. Therefore:

- a complete filtered result may support an exact representative-sponsored count;
- the same filtered result does **not** establish a person's complete co-sponsorship count;
- complete proposer-role coverage requires the proposer-detail source in a later scope;
- proposal reason / full major-content text is not scraped in this scope.
