# Presidential Office / Presidential-Body Personnel Feeder

## Purpose

Civic Intel uses official Presidential Office organization and personnel materials to explain
public career paths through the Presidential Secretariat, National Security Office,
presidential advisers, presidential commissions and explicitly public presidential task
forces.

This feeder is about **public personnel actions and governance roles**, not proximity to the
President or inferred political influence.

```text
president.go.kr organization / official personnel briefing
 -> PresidentialPersonnelRecord
 -> IdentityCandidate
 -> Office / InstitutionalBody context
 -> reviewed Appointment or CommitteeMembershipEpisode projection
 -> CareerEpisode / AppointmentPath / TalentPoolEntry
 -> Public Official Profiler
```

## Source lanes

### Organization chart

The official organization page is strong evidence that a named office/body exists in the
published organizational structure.

It does **not** prove that a particular person occupies the office unless the page or another
official source explicitly identifies the person.

### Personnel briefing / written briefing

An official personnel announcement can establish a dated public personnel action such as:

- appointment;
- nomination;
- designation before formal appointment;
- commission/appointment to an advisory or committee role;
- explicit assignment/concurrent role;
- release/dismissal/resignation acceptance when officially stated.

The action wording is part of the fact and must not be normalized away.

## Action semantics

V0 preserves:

| Official wording | Canonical action | Meaning |
|---|---|---|
| 임명 | `APPOINTED` | official source states appointment |
| 지명 | `NOMINATED` | named as nominee/candidate; not completed appointment |
| 내정 | `DESIGNATED` | announced as intended appointee; not silently converted to appointment |
| 위촉 | `COMMISSIONED` | commissioned/appointed to advisory or committee-type public role |
| 보직 / explicit 겸임 | `ASSIGNED` | specific public assignment stated by source |
| 해촉 / 면직 / 사임수리 | `RELEASED` | official end/release event as stated |

`NOMINATED` and `DESIGNATED` never become `APPOINTED` merely because time passes. A later
appointment requires a later source/event.

## Role scopes

The first normalized scopes are:

- `PRESIDENTIAL_SECRETARIAT` — 대통령비서실 senior public staff;
- `NATIONAL_SECURITY_OFFICE` — 국가안보실 senior public staff;
- `SPECIAL_ADVISER` — publicly appointed presidential special advisers;
- `PRESIDENTIAL_COMMISSION` — presidential commission chair/vice-chair/member roles;
- `PRESIDENTIAL_TASK_FORCE` — explicitly public presidential TF/special-task leadership.

Presidential commissions and TFs map naturally to existing `InstitutionalBodyType` values.
Secretariat/security-office roles remain office/career context and should reuse canonical
Person identity rather than create a second personnel registry.

## Provenance semantics

### Personnel action

```text
official briefing: A was nominated/designated/appointed/commissioned as B
 -> FACT about that dated official personnel action
```

The precise action remains visible in the profile/timeline.

### Reported prior career

Official personnel briefings commonly explain why a person was selected by citing prior
experience.

```text
briefing says: A previously served as X
 -> FACT that the Presidential Office reported X as A's prior career
 -> not automatically independent verification of the X CareerEpisode
```

Important prior roles should be verified against their original source family: Assembly,
company/DART, ministry personnel record, public institution, university/research source,
union/civic organization, etc.

### Meeting attendance

Attendance at a presidential meeting, briefing, ceremony or event does not by itself prove:

- Presidential Office employment;
- commission membership;
- adviser status;
- TF membership;
- personal relationship or influence.

A meeting-attendance-shaped record fails closed in the personnel feeder.

## Identity rule

Public personnel sources frequently contain name + office + date but no birth date. Identity
resolution should use the complete set of available anchors:

- official source record;
- event date;
- role scope;
- organization/body;
- role/title;
- verified adjacent CareerEpisodes.

A masked, vacant or non-person label never creates a Person candidate. Same-name people remain
under normal Identity Resolution.

## Political-neutrality rule

A Presidential Office, commission or adviser role is a public career FACT when officially
supported. It does not automatically establish:

- political faction;
- personal loyalty;
- friendship/intimacy with the President;
- hidden influence;
- responsibility for every decision of the office/body;
- future appointment probability.

Those claims require their own predicates and evidence, with `CLAIM/INFERENCE/UNKNOWN`
semantics where appropriate.

## Privacy and scope boundary

Eligible people are publicly named senior roles with a clear governance/appointment purpose.
Do not build ordinary staff directories.

Do not collect or emit private addresses, phone numbers, personal email, private social-media
accounts, family/private-network data or non-public personnel records.

## First implementation

- metadata-only fail-closed `president.go.kr` SourcePolicy;
- normalized immutable official-personnel-announcement fixtures;
- distinct `APPOINTED/NOMINATED/DESIGNATED/COMMISSIONED/ASSIGNED/RELEASED` semantics;
- review-only IdentityCandidate staging;
- InstitutionalBody projection hints for presidential commission/TF roles;
- no generic Presidential Office crawler;
- no automatic DB upsert/publication;
- no political faction/loyalty/influence score.

The next source step should be one small, reviewed adapter for a stable official personnel
announcement family or explicitly named commission roster, without broad crawling.
