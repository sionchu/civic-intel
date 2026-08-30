# Civil Service Feeder

## Purpose

Civic Intel treats civil service as a set of time-bounded public career episodes, not one permanent person type. The first implementation stages named, publicly consequential personnel events and retired-public-official employment-review decisions from authoritative public records.

## Scope

Eligible named career episodes include:

- central general civil service
- Senior Civil Service (`고위공무원단`)
- publicly named local-government executive posts
- open competitive / internal competitive appointments
- fixed-term or specialist public-service roles when relevant to a public appointment path
- diplomacy, police, fire, tax, customs, audit, corrections and immigration where an official named personnel record supports the episode

Judiciary/prosecution is handled separately. Military remains a specialized facet.

## Public-interest boundary

Do not build an ordinary civil-servant directory. The feeder is limited to officials whose public role is relevant to policy responsibility, institutional governance, appointment pathways, or a documented later move.

Examples include Senior Civil Service / 실·국장급 and above, agency heads, deputy governors/mayors, publicly appointed open-position officials, and lower offices only where needed to explain a documented path.

Private phone, email, home address and internal HR identifiers are prohibited.

## Personnel event semantics

Personnel records preserve the event instead of overwriting a single current title.

Supported event kinds:

- `APPOINTMENT`
- `PROMOTION`
- `TRANSFER`
- `SECONDMENT`
- `DISPATCH`
- `OPEN_POSITION_APPOINTMENT`
- `RETIREMENT`

A record should preserve source date, effective date, organization, title/grade when public, and event kind. If an official notice is ambiguous, staging leaves the event detail unresolved rather than guessing.

## Open / competitive positions

나라일터 is a route-evidence source for central/local open and competitive positions. A recruitment notice establishes that a route was open; it does not establish who was eventually appointed. A person CareerEpisode requires an official result or appointment record.

## Retired-public-official employment review

Government Public Ethics Committee / Ministry of Personnel Management publishes employment-review results. The canonical decision vocabulary preserves the official decision:

- `EMPLOYMENT_ALLOWED` (`취업가능`)
- `EMPLOYMENT_APPROVED` (`취업승인`)
- `EMPLOYMENT_RESTRICTED` (`취업제한`)
- `EMPLOYMENT_NOT_APPROVED` (`취업불승인`)
- `UNKNOWN`

An approved or allowed move is not labelled a revolving-door violation. A review event records only the published decision and the public former-role / destination-organization information.

The public framework distinguishes no close work relationship (`취업가능`), close relationship (`취업제한`), a special statutory approval ground (`취업승인`), and no qualifying approval ground (`취업불승인`).

## Canonical flow

```text
official personnel notice
 -> CivilServiceCareerRecord
 -> IdentityCandidate
 -> CivilService CareerEpisode
 -> AppointmentPath / TalentPoolEntry
 -> Profiler

retirement
 -> EmploymentReviewEvent
 -> destination organization
 -> later Corporate/PublicInstitution CareerEpisode
```

## First implementation boundary

The first PR is offline/staging-only because there is no single stable named-person API covering all Korean central and local civil-service personnel movements.

- parse deterministic fixtures modeled on official personnel notices
- parse deterministic fixtures modeled on published employment-review tables
- do not implement a generic government-site crawler
- do not auto-upsert Person or publish a Claim
- every future live source needs its own SourcePolicy and source-specific parser
