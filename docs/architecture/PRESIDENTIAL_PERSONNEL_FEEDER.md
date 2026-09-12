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

## Current source-route gate — 2026-09-12

The official [Presidential Office briefing list](https://www.president.go.kr/briefings) is a
published HTML index. The browser-rendered list reported 923 briefings, ten entries per page,
and title/content search with `sSearchGbn`, `sSearchTxt` and `pageNo` parameters. A title search
for `인사` returned 41 results and `인선` returned 11 results. These keyword counts are search
results, not a complete personnel universe: personnel actions can be described under other
titles, and one briefing can contain several actions.

Each detail page has a stable-looking `/briefings/{id}` path, title, registration date and
written body. The path ID is a provider record key only. It identifies the briefing page, not an
individual action, appointment term or Person. An action-level observation therefore requires
the page ID plus a reviewed action locator/ordinal; the provider has not published an action ID,
correction link, replacement rule or updated-at/version field in this route.

The inspected `qGTHgnQ8` page makes this boundary concrete: one narrative contains ten action
subjects—six minister nominees, one committee vice-chair nominee, two adviser designations and
one special-adviser appointment—without row-level action keys. A human-reviewed locator/ordinal
is therefore snapshot-scoped provenance, not a provider-issued stable identity.

The current [organization page](https://www.president.go.kr/organization) publishes the office
structure and role names, but it is a current organizational snapshot rather than a dated
occupancy roster. It may support the existence and scope of an office; it cannot populate a
person or historical tenure without a separate official personnel record.

The [Presidential Office copyright policy](https://www.president.go.kr/copyright-policy) states
that marked works use KOGL type 4 (attribution, noncommercial use and no modification), while
unmarked material requires prior consultation. The existing metadata-only policy therefore
remains `can_fetch=False`, with no fulltext, excerpt, AI or commercial use. A page being publicly
reachable is not a reuse or automated-collection grant.

The inspected [qGTHgnQ8 detail page](https://www.president.go.kr/briefings/qGTHgnQ8) also renders
the KOGL type 4 notice on the page itself. That is evidence of the page-level condition presented
to readers, not a packet-specific authorization for fulltext retention, derivative normalization,
AI use, automated enumeration or commercial republication. The metadata-only policy and the
source-route gate therefore remain unchanged.

The route is suitable for an exact, rights-approved briefing packet reviewed by a human. Such a
packet can be normalized into the existing `PresidentialPersonnelRecord` fixture shape while
preserving the official page and the analyst-normalized representation as separate provenance
layers. It does not authorize keyword crawling, automatic FACT promotion, Person creation or
conversion of reported prior careers into independently verified CareerEpisodes.

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
