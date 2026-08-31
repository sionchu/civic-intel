# CleanEye Local Public Institution Feeder

## Purpose

CleanEye is the intended official source lane for local-public-institution governance that
corresponds to ALIO's central-public-institution lane. The target public-interest roles are
institution heads and the executive/director/auditor roles the provider itself discloses for:

- local public enterprises;
- local-government invested institutions; and
- local-government contributed institutions.

The lane is currently `L0 RESEARCHED; BLOCKED`. It must not be implemented from the public HTML
surfaces while their automated-access policy remains closed, and the available official REST
catalog does not expose named executive status.

## Official institution surfaces

Reviewed on 2026-08-31:

```text
local public enterprise establishment status:
https://www.cleaneye.go.kr/siteGuide/pubCompStatus.do

local invested/contributed institution establishment status:
https://www.cleaneye.go.kr/siteGuide/iptCompStatus.do
```

The first page states 423 local public enterprises at 2026-01-01. The second states 890
invested/contributed institutions at 2026-06-30.

The current institution selectors expose two different source-specific identity contracts:

```text
local public enterprise:
entId / entName / entKind

local invested/contributed institution:
insttCode / insttNm / entKind
```

The category fields must remain source-specific. Current local-public-enterprise category codes
distinguish direct enterprises, corporations and authorities. Current invested/contributed
category codes distinguish invested from contributed institutions. Do not force these into the
ALIO `apbaId` or classification contract.

The dated establishment totals and live selector results are different source surfaces. A
future L3 contract must name which one is the authoritative enumeration universe and prove its
complete current coverage; it must not silently compare or merge rows by institution name.

## Named executive disclosure

The official item selectors return these exact routes:

```text
local public enterprise item 2_2_1 / ownerStatus:
POST https://www.cleaneye.go.kr/user/empOwnerStatus.do

local invested/contributed item 20_20 / iptSuOwnerStatus:
POST https://www.cleaneye.go.kr/user/iptSuOwnerStatus.do
```

The current pages expose:

- position;
- name;
- term text;
- major career as reported by the institution; and
- selection procedure.

They also expose gender, origin and disclosure-staff contact data. Those fields are not needed
for the Civic Intel governance lane and are prohibited from snapshots, observations, source
metadata and errors.

The inspected pages expose no stable executive-person identifier, no disclosure number and no
explicit page-level as-of/version field. A source row or ordinal therefore cannot authorize
automatic Person creation, linking or merge. Name + position + institution is not identity.

The local-public-enterprise writing standard covers the provider's disclosed heads,
directors/auditors and standing/non-standing roles. The invested/contributed writing standard
states that the institution head and standing executives are included while non-standing,
unpaid general executives are excluded. This difference must remain explicit in any future
connector and coverage calculation.

## Official REST catalog

The official catalog is:

```text
https://www.cleaneye.go.kr/user/openDataSet.do
```

On 2026-08-31 it listed 34 REST datasets. No named-executive-status dataset was present. The
`openApiOwnerSal` executive-compensation API is not a substitute: it exposes annual institution
and role-category counts/compensation, not executive names or provider Person identifiers.

Do not derive an executive endpoint from the salary service name, HTML route or an adjacent
dataset. A future connector requires an official published named-executive operation and exact
field documentation.

## Rights and automated-access boundary

The official policy page is:

```text
https://www.cleaneye.go.kr/user/copyrightPolicy.do
```

It permits free use of site-owned works and public data, including commercial use, subject to
protected third-party rights exclusions. That reuse statement does not publish a named-
executive API or grant an automated HTML collection contract.

The current official robots policy is:

```text
https://www.cleaneye.go.kr/robots.txt

User-agent: *
Disallow: /
```

No request limit is published for the named-executive HTML routes. Limits stated for REST
datasets apply only to those operations and must not be borrowed for HTML enumeration.

Therefore current allowed activity stops at finite contract review. Full or repeated automated
HTML enumeration is blocked. A live L3 worker must wait for one of:

1. an official machine-readable named-executive dataset with complete contract documentation;
2. a changed official automated-access policy that permits the exact source-bounded routes; or
3. written provider permission defining the routes, fields, request limits and storage terms.

## Future minimized observation boundary

If the source gate later passes, normalized metadata may include only:

```text
institution lane / source identifier / name / official category
executive position / disclosed name / term text
reported major-career text
selection procedure
provider disclosure as-of/version when explicitly supplied
```

`SourceSnapshot` remains the raw-level provenance capture under SourcePolicy. Raw HTML,
attachments, gender, origin, addresses, employee rows and disclosure-staff identities or
contacts remain excluded.

Every future observation must use the canonical `SourceRun`, `SourceCheckpoint` and
`FeederObservation` persistence transaction. Because the current source exposes no stable
executive-person identifier, deterministic materialization must return `REVIEW_REQUIRED` and
create zero Persons automatically.

## Maturity decision

```text
L0 RESEARCHED; BLOCKED
```

Public pages and aggregate APIs establish the source strategy, but no permitted machine-readable
named-executive universe currently satisfies L1/L2/L3. No connector, guessed field, generic
crawler or ALIO/CleanEye abstraction is authorized by this review.
