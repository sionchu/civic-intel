# 2026 National Assembly audit source contract — reconnaissance

## Status

`RECONNAISSANCE / ONE CURRENT POST RIGHTS-REVIEWED`

This document records the official-source shape observed during the first Gukgam 2026 release
slice. It does **not** authorize a live feeder, attachment full-text storage, AI processing or
public witness identity materialization.

## Source family

The National Assembly itself states that committee-adopted 국정감사 plans and related materials
are available through the individual committee websites. The first collector therefore targets
the official National Assembly committee web platform rather than news or third-party summaries.

Observed official committee pages use `*.na.go.kr` hosts, including the shared committee web
platform exposed through pages such as `science.na.go.kr`. Detailed records expose stable-looking
`nttId` query parameters and may provide HWP/HWPX/PDF attachments.

The first current source has now been pinned for the Science, ICT, Broadcasting and Communications
Committee (과학기술정보방송통신위원회):

```text
post:
https://science.na.go.kr/cmmit/bbs/BCMT2002/view.do?nttId=3078699&menuNo=2000030&pageIndex=1

nttId:
3078699

title:
2026년도 국정감사계획서

published:
2026-09-15

attachment family:
atchFileId = 7938f3a874d5441892124093d19da1df
fileSn=1 = 2026년도 국정감사계획서.hwp
fileSn=2 = 2026년도 국정감사계획서.pdf
```

The public page exposes preview locators using `atchFileId + fileSn + viewType=CONTBODY`.
The actual download control is JavaScript-driven (`downloadFile(...)`) and posts through the
board form; there is no reviewed standalone GET download URL. A connector must preserve the
provider attachment identifiers and must not invent a download URL.

No separate institution-witness, general-witness or reference-person attachment is present on
this exact post. Such material must be discovered as separate official records when published.

Correction/replacement semantics across later posts remain an open gate before L3.

## Critical committee-identity rule

The hostname is not sufficient committee identity.

The shared committee platform can render records whose displayed committee differs from the host
label. A collector must bind each record to the explicit committee field plus exact
post/attachment metadata. Do not derive committee identity from `science.na.go.kr` or another
host name alone.

## Target bounded universe

The first live collector may enumerate only:

```text
2026 National Assembly standing committees
→ currently published official audit-plan / witness material
```

Desired official record classes are:

- audit plan / 감사계획;
- audit date and venue when explicitly published;
- audited organization / 피감기관 or 대상기관;
- institution witness / 기관증인;
- general witness / 일반증인;
- reference person / 참고인;
- post publication/update date;
- exact official attachment locator.

If a committee has no currently discoverable plan, operational coverage is
`NOT_YET_PUBLISHED`. It is not evidence of `NO_AUDIT`.

## Candidate stable locators

Source-level candidate:

```text
canonical detail URL + nttId
```

Attachment-level candidate:

```text
parent nttId + official attachment identifier/URL + filename
```

For the reviewed Science Committee plan, the exact attachment identity is:

```text
parent nttId + atchFileId + fileSn
```

The preview path is a locator, not a permanent content identity. Correction/replacement semantics
across later posts remain an open gate.

## Rights gate

Do not generalize a reuse notice visible on one National Assembly page to every attachment.

The National Assembly copyright policy states that Assembly-owned works carrying the KOGL
Type-1 mark may be reused with source attribution, including commercial use and modification.
The exact reviewed Science Committee post visibly renders the `KOGL_Type1.gif` public-nuri mark.

For this v0 source contract:

```text
official post/attachment metadata fetch = permitted
normalized public-governance metadata storage = permitted
raw/full attachment storage = disabled
public excerpt display = disabled
raw attachment republication = disabled
source attribution = required
```

This narrow decision applies to the reviewed post family and does not automatically license every
National Assembly attachment. Each additional committee source family must preserve the visible
license/rights state, and third-party rights/privacy restrictions still override the general mark.

Browser reconnaissance may identify official URLs, post structure and attachment metadata without
creating canonical facts.

## Privacy and identity

Witness/reference-person material may contain names and job titles. It does not authorize:

- name-only Person creation or linking;
- personal phone/email collection;
- precise residence collection;
- family discovery;
- raw attachment publication.

A witness row remains source-scoped until the existing identity gate resolves it.

## Next source task

Finish the reviewed Science Committee plan structure and pin:

1. audit-schedule table headings and row semantics;
2. audited-organization grouping/count semantics;
3. whether witness/reference rows are embedded in the plan or always separate records;
4. correction/replacement behavior across newer official posts;
5. committee-list coverage denominator/pagination.

Then implement only the first source-specific metadata collector. Do not generalize to a universal
committee scraper until a second committee proves the same contract.
