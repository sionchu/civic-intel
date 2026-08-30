# Civil Service Career Feeder

## Purpose

Civil servants are a first-class feeder into ministers, Presidential Office roles, public
institutions, commissions and regulated/private-sector leadership. Civic Intel models
**named public-interest career events**, not an employee directory.

```text
official personnel notice / gazette / appointment result
 -> CivilServicePersonnelRecord
 -> IdentityCandidate
 -> CivilServiceCareerEpisode
 -> AppointmentPath / TalentPoolEntry
 -> Public Official Profiler

retirement
 -> Government Public Ethics Committee employment review
 -> EmploymentReviewEvent
 -> destination organization
 -> later Corporate / PublicInstitution CareerEpisode
```

## Public-service categories

V0 distinguishes:

- central general civil service
- local general civil service
- foreign service
- police
- fire service
- tax
- customs
- audit
- corrections
- immigration
- other specific public services

Prosecution/judiciary remain in the legal feeder and military remains a separate specialized
career facet.

## Personnel events

Do not collapse a career into one current title. Preserve dated events:

- `APPOINTMENT`
- `PROMOTION`
- `TRANSFER`
- `SECONDMENT`
- `DISPATCH`
- `RETIREMENT`

The appointment/entry route is a separate dimension:

- regular route
- Senior Civil Service
- open competitive position
- internal competitive position
- fixed-term appointment
- external-career appointment

For example, `민간 연구원 -> 개방형직위 국장` is an appointment event with an
`OPEN_POSITION` route, while `과장 -> 고위공무원단 국장` may be a promotion event with a
`SENIOR_CIVIL_SERVICE` route.

## Source lanes

### Named personnel episodes

Prefer official ministry/agency/local-government personnel releases, official appointment
announcements, gazette records and official senior biographies.

A source-specific adapter should emit only the fields needed for the career graph:

- person name
- event date
- organization
- title / public grade when documented
- personnel event type
- appointment route when documented
- previous organization/title when explicitly published
- source reference

No contact or home-location data belongs in the feeder.

### 나라일터

나라일터 is primarily route evidence for:

- open competitive positions
- internal competitive positions
- central/local public-service recruitment
- appointment/result announcements when publicly posted

A recruitment notice proves that a route/position was open. It does **not** establish who
was appointed until an official result or appointment source names the person.

### Government organization data

Government organization systems can establish organizational context and historical
structure. They are not automatically person rosters.

## Seniority / public-interest boundary

Eligible named-person records are limited to roles that explain public decision-making or
appointment paths, such as:

- Senior Civil Service / 실·국장급 and above
- vice-minister/commissioner/administrator-level posts
- deputy governors, deputy mayors, vice superintendents and comparable local executive roles
- publicly appointed open/competitive position holders
- other publicly named bureau/specialized leaders only when they are needed to explain a
  documented public-service path

Ordinary staff rows must fail closed at staging rather than being stored and hidden later.

## Retired-public-official employment review

Ministry of Personnel Management / Government Public Ethics Committee publishes employment
review results for covered former public officials.

Civic Intel preserves the official decision as a discrete fact:

- `EMPLOYABLE` / 취업가능
- `APPROVED` / 취업승인
- `RESTRICTED` / 취업제한
- `DISAPPROVED` / 취업불승인
- `UNKNOWN` when a source uses another status that requires review

The original Korean decision text is always retained.

A post-government job is **not** automatically a revolving-door violation. In particular,
`취업가능` and `취업승인` must never be re-labelled as wrongdoing. A restriction or
disapproval is also reported only as the official committee decision unless separate facts
support another claim.

Published review tables may mask a person's name. A masked or partially masked name is not
an identity anchor and must never create a Person candidate. The review record may remain as
an organization-level/public decision record with `PERSON_NAME_NOT_PUBLIC` semantics.

## Identity rule

Personnel notices often omit birth dates. Name-only matching is therefore insufficient.
Use additional anchors such as:

- organization and title
- event date
- previous organization/title
- appointment route
- adjacent known CareerEpisodes

If the identity remains ambiguous, keep `REVIEW`/`ENTITY_UNRESOLVED` rather than merging.

## Current implementation boundary

The first implementation is deliberately offline and deterministic because there is no
single stable named-person API covering all Korean central and local civil-service moves:

- normalized fixture parser for official named personnel rows
- normalized fixture parser for retired-public-official employment-review rows
- mapping into the existing `IdentityCandidate` only when the public name is usable
- canonical contracts for `CivilServiceCareerEpisode` and `EmploymentReviewEvent`
- no automatic database upsert
- no broad government-site crawler

Every future live source must have its own SourcePolicy and source-specific parser. The next
source adapter should target one stable official named-person feed/notice family and reuse
these semantics instead of creating another career model.
