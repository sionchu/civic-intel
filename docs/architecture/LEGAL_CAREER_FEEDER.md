# Legal / Judicial / Prosecution Career Feeder

## Purpose

Civic Intel treats legal careers as time-bounded professional and public-service episodes.
It does **not** flatten judges, prosecutors, lawyers, judicial administrators and legal-policy
roles into one generic `LAWYER` label.

```text
MOJ / Supreme Court / Court Gazette / public professional source
 -> LegalPersonnelRecord or verified professional record
 -> IdentityCandidate
 -> LegalCareerEpisode
 -> AppointmentPath / TalentPoolEntry
 -> Public Official Profiler
```

## Career types

The canonical contract distinguishes:

- `JUDGE`
- `COURT_PRESIDENT`
- `SUPREME_COURT_JUSTICE`
- `JUDICIAL_ADMINISTRATION`
- `PROSECUTOR`
- `CHIEF_PROSECUTOR`
- `PROSECUTOR_GENERAL`
- `MINISTRY_OF_JUSTICE_LEGAL_ROLE`
- `LAWYER`
- `LAW_FIRM_PARTNER`
- `PUBLIC_DEFENDER_OR_LEGAL_AID`
- `CONSTITUTIONAL_COURT_ROLE`
- `LEGAL_ACADEMIC`
- `GOVERNMENT_LEGAL_ADVISER`

Career event types remain separate from the career type:

- appointment / new assignment
- transfer
- promotion
- assignment
- concurrent appointment / concurrent release
- retirement
- professional registration

A person's timeline may contain several of these types over time.

## Official prosecution lane

Ministry of Justice prosecutor-personnel releases are strong evidence for dated appointment
and transfer events. Reviewed 2026 examples include the 2026-01-29 first-half prosecutor
personnel announcement and the 2026-08-24 second-half general-prosecutor transfer
announcement.

Normalize only public-interest personnel fields:

- name
- effective date
- destination prosecution office / Ministry of Justice role
- title
- previous office/title when explicitly published
- appointment/transfer type
- official assignment domain when explicitly published
- source reference

The personnel release establishes the role transition. It does **not** establish individual
responsibility for every investigation or prosecution conducted by the office.

## Official judiciary lane

Supreme Court personnel releases and Court Gazette personnel orders are strong evidence for
judicial appointments, transfers, judicial-administration posts and concurrent assignments.
The reviewed 2026-01-30 release and February Court Gazette use a structured pattern such as:

```text
previous affiliation/title
 -> person name
 -> appointment order
 -> effective date
```

Preserve the effective date and the exact public-office transition. Do not overwrite a
career timeline with only the latest court/title.

## Lawyer / law-firm lane

The first implementation does not crawl lawyers or law-firm staff.

Future verification may use:

- Korean Bar Association public lawyer/law-firm search for public professional identity;
- official law-firm biographies for publicly presented role and career history;
- official appointment or court record where public representation is directly relevant.

Professional registration or law-firm affiliation does **not** create:

- a private client roster;
- a political relationship edge;
- a faction/ideology label;
- an inference that the person personally handled every matter of the firm.

## Case and decision attribution

Case-level evidence is a separate future lane from career evidence.

Rules:

- judge participation in a published decision != political ideology;
- assignment to a court division != personal responsibility for every case in that division;
- prosecutor assignment to an office/unit != personal responsibility for every case there;
- law-firm affiliation != representation of every firm client;
- reported win/loss, sentencing or indictment rates are not supported as V0 person scores;
- sealed/non-public case material is out of scope.

If a future public-interest case record is added, its role must be explicitly attributed and
kept separate from the generic career episode.

## Disciplinary / controversy data

No disciplinary parser is included in this PR. If official bar/judicial/prosecution
disciplinary records are ever used, preserve the precise disposition, status, date,
reversal/appeal context and source. An allegation or pending process cannot be silently
presented as established wrongdoing.

## Privacy and neutrality

Do not collect or publish:

- private client lists;
- personal address/phone/email;
- family data unrelated to an official public record;
- sealed case information;
- ideology scores;
- guilt-by-association through a former court, prosecution office or law firm.

The feeder describes public roles and dated transitions, not political desirability.

## First implementation

The first implementation is deliberately staging-only:

- canonical `LegalCareerType`, `LegalCareerEventType`, and `LegalCareerEpisode` contract;
- normalized Ministry of Justice prosecutor-personnel fixture/parser;
- normalized Supreme Court personnel fixture/parser;
- mapping to the existing `IdentityCandidate`;
- privacy-safe review JSON;
- SourcePolicies keep live fetch/fulltext/AI/commercial reuse fail-closed until each adapter's
  rights and format are reviewed;
- no automatic DB upsert/publication;
- no broad legal-professional crawler.

The next best source-specific step is to add one reviewed live official personnel adapter
while retaining these same normalized semantics.
