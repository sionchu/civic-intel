# 2026 National Assembly audit source contract — reconnaissance

## Status

`RECONNAISSANCE / DISCOVERY_ONLY`

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

These are reconnaissance observations only. Exact 2026 attachment version/correction semantics
must be pinned against a current committee plan before acquisition reaches L3.

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

The exact attachment identifier and correction/replacement semantics remain an open gate.

## Rights gate

Do not generalize a reuse notice visible on one National Assembly page to every attachment.

The exact current 2026 audit-plan/witness post and attachment must be reviewed before automated
acquisition, storage, AI use, excerpt display or commercial reuse is enabled.

Until that source-specific review closes:

```text
collection_mode = DISCOVERY_ONLY
automated full acquisition = disabled
fulltext storage = disabled
AI processing = disabled
excerpt display = disabled
commercial reuse = disabled unless the exact source license permits it
```

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

Review one **current 2026** committee plan/witness source end to end and pin:

1. official post identifier;
2. attachment identifier and correction/version behavior;
3. exact rights/reuse notice for the post and attachment;
4. plan/witness row structure;
5. coverage denominator/pagination.

Only then may the first source-specific Gukgam collector be activated.
