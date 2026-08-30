# Feeder Source Coverage

## Purpose

Civic Intel maintains one canonical map of **where publicly consequential people can be
discovered before profiling** and which evidence lane is authoritative for each career
route.

This document is not a second SourcePolicy registry. `SourcePolicy` remains authoritative
for collection, storage, AI-use, excerpt and commercialization rights. This matrix only
tracks product coverage and source strategy.

Every feeder ends in the same flow:

```text
authoritative public source
 -> safe staged person/career candidate
 -> Identity Resolution
 -> Person / CareerEpisode / institutional objects
 -> AppointmentPath / TalentPoolEntry
 -> Public Official Profiler
```

A feeder discovers people. It does not assert appointment probability, ideology,
partisan desirability or hidden influence.

## Status legend

- `MERGED`: a review-only source-specific path exists in the repository.
- `ISSUE_OPEN`: implementation is scoped in an existing GitHub issue.
- `RESEARCHED`: source strategy is known but no implementation issue exists yet.
- `UNRESEARCHED`: source lane still needs source-policy and contract research.
- `BLOCKED`: collection is prohibited or currently too ambiguous to automate.

## Coverage matrix

| Feeder | Public person scope | Strongest source lane | Mode | Identity anchor | Career / ontology destination | Status |
|---|---|---|---|---|---|---|
| National Assembly members | elected National Assembly members | 열린국회정보 member API | API | `MONA_CD` | Legislative | MERGED |
| National Assembly legislation | representative/co-sponsorship and bill activity | 열린국회정보 bill APIs | API | `MONA_CD`, bill ID | Legislative | MERGED; completeness #13 |
| Local elected offices | governors, mayors/county/district heads, local councilors, education superintendents, candidates | NEC candidate + winner APIs | API | NEC `huboid` | Local Elected Office | MERGED |
| Presidential Office | chiefs, senior secretaries, secretaries and publicly named senior staff | official organization/appointment releases | OFFICIAL_WEB | name + office + dates | Public Service / Appointment | RESEARCHED |
| Presidential commissions / TFs | chair, vice-chair, member, adviser where publicly named | official body/appointment records | OFFICIAL_WEB / STRUCTURED_DISCLOSURE | person + body + role + dates | CommitteeMembershipEpisode | MERGED contract |
| Central/local civil service | Senior Civil Service, senior local executives, open/competitive appointees, path-relevant named officials | official personnel notices, gazette, 나라일터 route evidence | OFFICIAL_WEB / STRUCTURED_DISCLOSURE | name + agency + title + date + adjacent career anchors | Public Service | MERGED contracts/staging; live adapter pending |
| Retired-public-official employment review | covered former officials and destination organizations in published ethics review | MPM / Government Public Ethics Committee | STRUCTURED_DISCLOSURE | name + former agency/title + destination + review date | EmploymentReviewEvent | MERGED contracts/staging; live adapter pending |
| Public institutions | institution heads, standing executives, relevant directors/auditors | ALIO item 4 / general public-institution dataset | STRUCTURED_DISCLOSURE | ALIO institution code + name + role + term | Institutional Governance / Public Service | MERGED staging; live adapter pending |
| Public-institution executive compensation | role-category compensation/annual-pay disclosures | ALIO item 10 | STRUCTURED_DISCLOSURE | institution + executive role category + fiscal year | Institutional Governance | MERGED staging; person attribution prohibited by default |
| Public-institution reemployment | executive reemployment; employee rows retained only without Person candidate | ALIO item 7-1 | STRUCTURED_DISCLOSURE | institution + executive name when public + dates | Institutional Governance / Reemployment | MERGED staging; separate from #23 ethics review |
| Policy banks / state-linked companies | public-policy bank executives; state-linked listed-company boards/executives | statute + ALIO/OpenDART/KRX/institution governance | STRUCTURED_DISCLOSURE | org IDs / DART corp code + person | Institutional Governance / Corporate | MERGED contract; connectors pending |
| Private-sector senior leaders | registered directors, disclosed executives, CEO/CTO/CSO, officially named senior technical/business leaders | OpenDART -> company official -> KRX | API / STRUCTURED_DISCLOSURE / OFFICIAL_WEB | DART corp code + person anchors | Corporate | ISSUE_OPEN #18 |
| Government-funded policy research outputs | named responsible researchers on public policy outputs | NKIS `ReportList.do` | API | NKIS output ID + responsible-researcher text + year | Academic / Policy Research Output | MERGED staging; no employment inference |
| Government-funded research careers | institute presidents/directors/researchers with verified role/tenure | institute official profile / appointment release | OFFICIAL_WEB | person + institute + role + dates | Academic / Policy Research Career | verification lane pending |
| General academia | professors/researchers relevant to public appointments | KCI, OpenAlex, Crossref, ORCID + university official profile | API + OFFICIAL_WEB | DOI/ORCID/OpenAlex + identity anchors | Academic | RESEARCHED |
| Judges / prosecution / judicial administration | judges, court presidents, prosecutors, senior prosecution and judicial-administration roles | MOJ prosecutor personnel + Supreme Court personnel releases/Court Gazette | STRUCTURED_DISCLOSURE / OFFICIAL_WEB | name + office/title + effective date + prior office anchors | Legal/Judicial/Prosecution | MERGED contracts/staging; live adapters pending |
| Lawyers / law firms | public professional registration and publicly consequential law-firm roles | KBA public search + official law-firm biography | OFFICIAL_WEB | public professional identity + firm/role/date when verified | Legal / Professional | RESEARCHED; no broad crawling |
| Military | generals, chiefs, JCS/defense-policy leadership and path-relevant retired senior officers | MND/service personnel releases and official bios | OFFICIAL_WEB | name + rank/command + date | Military / Defense | RESEARCHED |
| Diplomacy | ambassadors, senior foreign-service officers, path-relevant diplomats | MOFA personnel/appointment records | OFFICIAL_WEB | name + post + appointment date | Diplomatic / Public Service | MERGED staging semantics; live adapter pending |
| Labor organizations / public leadership | explicitly public union representative/leadership only; no ordinary membership | 전국노동조합표준데이터 + official federation/commission records | STRUCTURED_DISCLOSURE / OFFICIAL_WEB | representative name + union + source/as-of anchors | Civic / Labor Leadership | MERGED staging; federation/commission verification pending |
| Civic / NGO / professional associations | public leaders of significant civic/professional bodies | official organization/governance/public disclosure | OFFICIAL_WEB / STRUCTURED_DISCLOSURE | person + organization + role + dates | Civic / Association / Nonprofit | RESEARCHED |
| Party permanent staff | publicly named senior party staff/policy committee leadership | party official appointments; NEC for party context | OFFICIAL_WEB | person + party role + date | Political / Party | RESEARCHED |
| Party think tanks | presidents/directors/researchers where public-interest relevance exists | official party-institute pages/publications | OFFICIAL_WEB | person + institute + role/output | Policy Research / Political | RESEARCHED |
| Campaign staff | officially announced senior campaign roles | candidate/party official campaign releases; NEC election context | OFFICIAL_WEB | election + candidate + role + date | Campaign CareerEpisode | RESEARCHED |
| Parliamentary staff / legislative researchers | publicly named aides/secretaries, committee professional staff, legislative researchers | official Assembly/public biographies and personnel notices | OFFICIAL_WEB | person + member/committee/office + dates | Legislative Staff / Public Service | RESEARCHED |
| Media / public broadcasting | publicly consequential media executives, directors, senior editorial/policy leaders | broadcaster/company governance, OpenDART where applicable, official bios | STRUCTURED_DISCLOSURE / OFFICIAL_WEB | person + media organization + public role | Media Career Facet | RESEARCHED |
| International organizations | Koreans with verified UN/OECD/World Bank/IMF/etc. roles | international-organization official bio/appointment; MOFA route/JPO context | OFFICIAL_WEB / API context | person + organization + post + dates | International / Diplomatic | RESEARCHED |
| Financial-market institutions | KRX/KSD/payment/clearing leaders; financial-holding/bank executives and outside directors | ALIO where applicable; OpenDART/company governance otherwise | STRUCTURED_DISCLOSURE / API | org/corp code + person + board role | Institutional Governance / Corporate | covered by #18 and ALIO staging |
| Science/technology/medical public experts | national-lab/hospital/technical-society leaders and publicly named advisers relevant to appointments | institution/committee official sources | OFFICIAL_WEB | person + institution/body + role | Academic/Technical/Public Advisory | UNRESEARCHED |

## Source-mode rules

### API

Use when a reviewed official API has stable fields and a SourcePolicy. Credentials must be
injected only at request time and never persisted in discovered URLs, metadata, errors or
snapshots.

### STRUCTURED_DISCLOSURE

Use official filings, gazette tables, ALIO/OpenDART/KRX disclosures and published ethics
review results. Preserve disclosure date and reporting semantics.

### OFFICIAL_WEB

Use named personnel announcements, official biographies, organization/board pages and
appointment releases. Do not introduce a generic crawler simply because no API exists;
prefer source-specific parsers and deterministic fixtures first.

### DISCOVERY_ONLY

News and search may discover a candidate fact or person, but cannot silently become the
canonical evidence source when a stronger public record should exist.

## Public-interest roster boundary

Civic Intel intentionally does **not** build broad directories of ordinary people merely
because a source exposes them.

Eligible discovery is limited to roles with a plausible public-decision, governance,
appointment or accountability purpose. Examples include elected officials, senior public
servants, institution heads, public board members, disclosed corporate executives, public
research/policy leaders, public union leadership and public civic-organization leadership.

The following are prohibited feeder behavior:

- ordinary civil-servant staff directories
- ordinary public-institution employee rosters
- ordinary private-company employee rosters
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

ALIO major-career entry
 -> FACT that the public institution disclosed the entry
 -> verify important prior CareerEpisodes against their original sources

ALIO role-category compensation
 -> FACT about institution/role-category compensation disclosure
 -> not automatically a named person's compensation or wealth

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

Current recommended sequence after labor-leadership staging:

1. #18 private-sector senior talent;
2. #13 legislative completeness and official bill summaries;
3. small federation/social-dialogue public leadership verification lane using #20 semantics;
4. one reviewed live MOJ/Supreme Court personnel adapter using #21 semantics;
5. official institute-profile/appointment adapter for NKIS-discovered researchers;
6. one reviewed live ALIO adapter using the #25 staging contracts;
7. one reviewed live civil-service/ethics source adapter using the #23 contracts.

Reorder only when a stronger source dependency or a concrete product target justifies it.
