# Labor Organization / Public Leadership Feeder

## Purpose

Civic Intel may use public labor-organization data to explain career paths through union
leadership, labor federations, social-dialogue bodies and later public office. It does not
compile or infer ordinary union membership.

```text
전국노동조합표준데이터 / official federation or commission source
 -> LaborOrganizationRecord
 -> explicit public representative only
 -> IdentityCandidate
 -> verified LaborLeadershipEpisode
 -> public commission / party / elected-office links
 -> AppointmentPath / TalentPoolEntry
 -> Public Official Profiler
```

## Official structured source

The nationwide labor-union standard dataset on the Public Data Portal aggregates union
records managed by local governments. The reviewed 2026-07 dataset exposes fields including:

- 노동조합명
- 노동조합형태
- 설립일자
- 소속연합단체명
- 대표자명
- 조합원수
- 소속사업장명

It also exposes address, telephone and coordinates. Those location/contact fields are not
needed for public appointment-path analysis and are discarded before staging.

The first implementation keeps live collection and commercial reuse fail-closed until the
exact standard-data adapter and item-level terms are reviewed.

## Organization facts vs person facts

The following are organization-level facts:

- union name/form;
- establishment date;
- affiliated federation;
- membership count;
- publicly listed workplace/enterprise context.

`membership_count` is never attached to an individual person.

The `대표자명` field can create a **leadership IdentityCandidate** because the source
explicitly publishes that person in a representative role. A masked, missing or generic name
does not create a Person candidate.

## Sensitive-affiliation rule

Union membership or affiliation can be sensitive personal information. Therefore:

- ordinary member rosters are prohibited;
- employment at a unionized workplace does not establish union membership;
- demonstration/strike participation does not establish membership;
- donations, social media, photographs or association with a leader do not establish
  membership;
- membership of relatives/colleagues is never inferred;
- a public union representative role must not be generalized into unrelated political
  loyalty, party or faction labels.

Only an explicitly public leadership role with a public-interest purpose may enter the Person
feeder.

## Identity rule

A representative name in the standard dataset is an identity/discovery anchor, not an
automatic merge with every same-name Person already in Civic Intel.

Useful anchors include:

- union name;
- source record identifier;
- public data as-of date;
- later official federation/committee/public-office records.

If the same-name identity cannot be resolved safely, keep it under review.

## Federation and public-policy links

An organization's `소속연합단체명` establishes the union organization's disclosed federation
context. It does **not** automatically create a personal relationship between the union
representative and every federation leader or political figure.

A future public-interest leadership path may be added only from explicit evidence such as:

- federation/confederation official leadership page;
- officially named bargaining representative;
- Economic, Social and Labor Council or government committee appointment;
- official party/campaign/public-office appointment record.

## Career-path value

Supported descriptive routes can include:

```text
union representative
 -> federation/confederation public leadership
 -> government/social-dialogue committee
 -> National Assembly / local elected office / public appointment
```

or:

```text
public-sector union leadership
 -> civic/labor-policy role
 -> local council / National Assembly
```

Historical frequency is descriptive and never appointment probability.

## First implementation

- reviewed metadata-only SourcePolicy for the nationwide standard-data lane;
- privacy-safe normalized fixture parser;
- union organization metadata staging;
- representative-name-only IdentityCandidate staging;
- membership count remains organization-level only;
- address/phone/coordinate and any member-list fields are discarded;
- no DB upsert/publication;
- no federation-site crawler;
- no inference of ordinary membership, ideology, party or faction.

The next best labor-specific step is to verify a small set of publicly consequential
federation/commission leadership roles from their own official sources without expanding
into a general membership directory.
