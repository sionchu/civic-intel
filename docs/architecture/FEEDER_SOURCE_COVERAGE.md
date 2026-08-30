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
| Retired-public-official employment review | covered former officials and destination organizations in published ethics review | MPM / Government Public Ethics Committee | STRUCTURED_DISCLOSURE | name + former agency/title + destination + review date | EmploymentReviewEvent | MERGED contracts/staging; source parser pending |
| Public institutions | institution heads, standing executives, relevant directors/auditors | ALIO | STRUCTURED_DISCLOSURE / API where reviewed | institution + name + role + term | Institutional Governance / Public Service | ISSUE_OPEN #25 |
| Policy banks / state-linked companies | public-policy bank executives; state-linked listed-company boards/executives | statute + ALIO/OpenDART/KRX/institution governance | STRUCTURED_DISCLOSURE | org IDs / DART corp code + person | Institutional Governance / Corporate | MERGED contract; connectors pending |
| Private-sector senior leaders | registered directors, disclosed executives, CEO/CTO/CSO, officially named senior technical/business leaders | OpenDART -> company official -> KRX | API / STRUCTURED_DISCLOSURE / OFFICIAL_WEB | DART corp code + person anchors | Corporate | ISSUE_OPEN #18 |
| Government-funded policy research | institute leaders/researchers and named policy-output authors | NKIS + institute official profiles | API + OFFICIAL_WEB | research output + person/institute anchors | Academic / Policy Research | ISSUE_OPEN #24 |
| General academia | professors/researchers relevant to public appointments | KCI, OpenAlex, Crossref, ORCID + university official profile | API + OFFICIAL_WEB | DOI/ORCID/OpenAlex + identity anchors | Academic | RESEARCHED |
| Legal / judiciary / prosecution | judges, prosecutors, lawyers, legal-policy leaders | MOJ, Supreme Court, court gazette, KBA, official law-firm bios | STRUCTURED_DISCLOSURE / OFFICIAL_WEB | name + office + appointment date; bar identity where public | Legal/Judicial/Prosecution | ISSUE_OPEN #21 |
| Military | generals, chiefs, JCS/defense-policy leadership and path-relevant retired senior officers | MND/service personnel releases and official bios | OFFICIAL_WEB | name + rank/command + date | Military / Defense | RESEARCHED |
| Diplomacy | ambassadors, senior foreign-service officers, path-relevant diplomats | MOFA personnel/appointment records | OFFICIAL_WEB | name + post + appointment date | Diplomatic / Public Service | MERGED staging semantics; live adapter pending |
| Labor movement | publicly named union/federation leadership only | 전국노동조합표준데이터 + official federation/commission records | STRUCTURED_DISCLOSURE / OFFICIAL_WEB | representative + union + date; requires identity review | Civic / Labor Leadership | ISSUE_OPEN #20 |
| Civic / NGO / professional associations | public leaders of significant civic/professional bodies | official organization/governance/public disclosure | OFFICIAL_WEB / STRUCTURED_DISCLOSURE | person + organization + role + dates | Civic / Association / Nonprofit | RESEARCHED |
| Party permanent staff | publicly named senior party staff/policy committee leadership | party official appointments; NEC for party context | OFFICIAL_WEB | person + party role + date | Political / Party | RESEARCHED |
| Party think tanks | presidents/directors/researchers where public-interest relevance exists | official party-institute pages/publications | OFFICIAL_WEB | person + institute + role/output | Policy Research / Political | RESEARCHED |
| Campaign staff | officially announced senior campaign roles | candidate/party official campaign releases; NEC election context | OFFICIAL_WEB | election + candidate + role + date | Campaign CareerEpisode | RESEARCHED |
| Parliamentary staff / legislative researchers | publicly named aides/secretaries, committee professional staff, legislative researchers | official Assembly/public biographies and personnel notices | OFFICIAL_WEB | person + member/committee/office + dates | Legislative Staff / Public Service | RESEARCHED |
| Media / public broadcasting | publicly consequential media executives, directors, senior editorial/policy leaders | broadcaster/company governance, OpenDART where applicable, official bios | STRUCTURED_DISCLOSURE / OFFICIAL_WEB | person + media organization + public role | Media Career Facet | RESEARCHED |
| International organizations | Koreans with verified UN/OECD/World Bank/IMF/etc. roles | international-organization official bio/appointment; MOFA route/JPO context | OFFICIAL_WEB / API context | person + organization + post + dates | International / Diplomatic | RESEARCHED |
| Financial-market institutions | KRX/KSD/payment/clearing leaders; financial-holding/bank executives and outside directors | ALIO where applicable; OpenDART/company governance otherwise | STRUCTURED_DISCLOSURE / API | org/corp code + person + board role | Institutional Governance / Corporate | covered by #18/#25 strategy |
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
- ordinary private-company employee rosters
- ordinary union-member rosters or inferred union affiliation
- ordinary NGO/professional-association member rosters
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

NKIS report author
 -> FACT of authorship on that public output
 -> not automatically institute-employment FACT

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

Current recommended sequence after civil-service staging:

1. #25 ALIO public-institution executives/governance;
2. #24 NKIS policy-research feeder;
3. #21 legal/judicial/prosecution;
4. #20 labor-union public leadership;
5. #18 private-sector senior talent;
6. #13 legislative completeness and official bill summaries;
7. one reviewed live civil-service/ethics source adapter using the #23 contracts.

Reorder only when a stronger source dependency or a concrete product target justifies it.
