# 2026 National Assembly audit source contract — reconnaissance

## Status

`RECONNAISSANCE / DISCOVERY_ONLY`

This document records the official-source shape observed during the first Gukgam 2026 release
slice. It does **not** yet authorize a live feeder or full-text storage.

## Source family

Primary discovery surface:

```text
National Assembly committee web platform
*.na.go.kr / committee pages
```

Observed official examples use the committee platform hosted at:

```text
https://science.na.go.kr/
```

with detailed records using stable-looking `nttId` query parameters, including patterns such as:

```text
/cmmit/bbs/B0000051/view.do?...&nttId=<id>
/cmmit/cmtEstn/cmtEstn/detail.do?...&nttId=<id>
```

Official records may expose HWP and PDF attachments.

## Critical identity rule

The hostname is **not** sufficient committee identity.

The shared National Assembly committee platform can render records whose displayed committee is
different from the host label. A collector must bind the record to the explicit committee field
and exact post/attachment metadata, not infer committee identity from `science.na.go.kr`.

## Target bounded universe

The first live collector may enumerate only:

```text
2026 National Assembly standing committees
→ currently published official audit-plan / witness material
```

Desired official record classes:

- audit plan / 감사계획;
- audit date and venue when explicitly published;
- audited organization / 피감기관 or 대상기관;
- institution witness / 기관증인;
- general witness / 일반증인;
- reference person / 참고인;
- post publication/update date;
- exact attachment locator.

If a committee has no currently discoverable plan, record operational coverage as
`NOT_YET_PUBLISHED`. Do not infer `NO_AUDIT`.

## Stable keys

Candidate source-level locator:

```text
canonical detail URL + nttId
```

Candidate attachment locator:

```text
parent nttId + official attachment identifier/URL + filename
```

The exact attachment ID/version semantics must be verified before L3 acquisition.

## Rights gate

Do not generalize the reuse terms of one National Assembly page to every attachment.

Some official committee pages expose a public-reuse/Korea Open Government License notice, but the
exact audit-plan and witness attachments must be reviewed before enabling storage or AI processing.

Until that review:

```text
collection_mode = DISCOVERY_ONLY
can_fetch = false for automated full acquisition
can_store_metadata = only after SourcePolicy review
can_store_fulltext = false
can_send_to_ai = false
can_show_excerpt = false
can_commercialize = false unless exact license permits it
```

Browser reconnaissance may identify URLs and structure without creating canonical facts.

## Privacy / identity

Witness and reference-person lists may contain names and job titles. They do not authorize:

- name-only Person creation or linking;
- personal phone/email collection;
- precise residence collection;
- family discovery;
- raw attachment publication.

A witness row remains source-scoped until the existing identity gate resolves it.

## Next source task

Review one current 2026 committee plan/witness attachment end to end and pin:

1. official post identifier;
2. attachment identifier and correction/version behavior;
3. exact rights/reuse notice;
4. plan/witness row structure;
5. coverage denominator/pagination.

Only then may the first source-specific collector be activated.
