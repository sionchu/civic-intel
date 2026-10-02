# 2026 National Assembly audit source contract — reconnaissance

## Status

`RECONNAISSANCE / MULTI-COMMITTEE PLAN ATTACHMENTS RIGHTS-REVIEWED / AUTOMATED_COMMITTEE_HTML_BLOCKED`

This document records the official-source shape observed during the first Gukgam 2026 release
slice and the dated witness research refresh below. It does **not** authorize a live committee-site
feeder, canonical attachment full-text storage, raw-file AI processing or public witness identity
materialization. The current human/source/public-access
decision packet is the [active Gukgam research plan](../exec-plans/active/gukgam-2026-ontology-research.md).

## Source family

The National Assembly states that committee-adopted 국정감사 plans and related materials are
available through the individual committee websites. Those committee pages remain authoritative
origin/provenance references for the plan documents.

Observed official committee pages use `*.na.go.kr` hosts, including the shared committee web
platform exposed through pages such as `science.na.go.kr`. Detailed records expose
stable-looking `nttId` query parameters and HWP/PDF preview locators.

The first current source has been pinned for the Science, ICT, Broadcasting and Communications
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

The official plan list independently shows this as the newest 2026 row for that committee.
The public page exposes preview locators using `atchFileId + fileSn + viewType=CONTBODY`.
The actual download control is JavaScript-driven and posts through the board form; there is no
reviewed standalone GET download URL. Preserve provider attachment identifiers and do not invent
a download URL.

No separate institution-witness, general-witness or reference-person attachment was observed on
this exact plan post. Such material must be treated as separate official records when published.

Correction/replacement semantics across later posts remain an open gate.

## Witness-source refresh, 2026-10-02

The owner's instruction to connect audited institutions and officially listed witnesses
supersedes the preceding institution-only work order for bounded source research. An Aside
operator lookup of the first Science Committee reference-materials list and its two 2026
detail pages confirmed these separate official records:

| Record | nttId | Publication | PDF attachment / fileSn |
| --- | --- | --- | --- |
| 2026년도 과학기술정보방송통신위원회 국정감사 기관증인 명단 | 3078724 | 2026-09-22 | 8023b8baac924e0aa23d2c9eaaf07a32 / 2 |
| 2026년도 과방위 국정감사 일반증인 및 참고인 명단 | 3078723 | 2026-09-22 | 2fdefa0fd9d24ab89e331c5d89a34bcd / 2 |

Both pages explicitly identify 과학기술정보방송통신위원회 and display the public-nuri
attribution/commercial-use/modification-permitted notice (KOGL Type 1). The PDF filenames
and attachment IDs were checked against each detail page's own download control. Exact
attachment GET locators were discovered through a secondary site's links and independently
matched to those controls; the secondary site's copied rows and counts are not evidence.

This source-specific research decision permits one bounded operator acquisition of each
exact PDF for local verification and deterministic extraction of public name, institution
group heading, printed affiliation/title, explicit audited-target column, witness category,
requested date/time, decision-date text and page/row provenance. Institution group headings are
list context, not a per-person employment field. It permits
Codex assistance on these minimized fields, not sending raw fulltext or unnecessary personal
fields to AI. Operator artifacts are local verification inputs, not a second canonical raw
truth store. No fulltext, birth dates, sex/age, addresses, contacts or raw republication enter
the research packet, snapshots, logs or public projections. Source attribution is required.

Repeated committee retrieval remains blocked. Field-by-field human review, canonical identity
binding, operational ingestion and Claim publication are not supplied by this source lookup.
Rows remain source-scoped research candidates. A listed general witness's employer does not
automatically become an audited institution. A request to attend is not actual attendance.
The attachment filename's “최종” is its printed label, not proof that later amendments cannot
exist; any later version needs a fresh exact capture and review.

## Critical committee-identity rule

The hostname is not sufficient committee identity.

The shared committee platform can render records whose displayed committee differs from the host
label. Bind each record to the explicit committee field plus exact post/attachment metadata. Do
not derive committee identity from `science.na.go.kr` or another host name alone.

## Robots / automated-access gate

On 2026-09-19 the exact committee host returned:

```text
User-agent: *
Disallow: /
Allow: /$
```

Therefore repeated automated collection from committee HTML/attachment routes is **blocked** for
this release, even though the reviewed post displays a public-reuse mark.

This distinction is mandatory:

```text
publicly viewable / reusable content
!=
permission for automated retrieval
```

Do not implement a repeated `httpx`, crawler, browser-bot or generic scraper against the
committee-site paths while this robots contract remains in force.

The committee page may remain an origin URL used for manual/operator verification and provenance.
A separately reviewed human-assisted packet path may be considered only under the existing source
acquisition playbook; it is not an automated feeder and does not bypass identity/publication gates.

## Automation-permitted schedule lane

The official public-data catalog now provides a bounded automation-permitted route for schedule
discovery:

```text
data.go.kr dataset: 15126132
name: 국회 국회사무처_국회일정 통합 API
provider: 국회 국회사무처
cost: free
reuse: 이용허락범위 제한 없음
approval: development auto-approval / operation review
```

The staged source-specific connector uses the Open Assembly operation code `ALLSCHEDULE` and
only the schedule fields required for discovery:

```text
SCH_KIND
SCH_DT
SCH_TM
CMIT_NM
SCH_CN
EV_PLC
CONF_SESS
CONF_DGR
```

The code/field contract is staged at L1 from the official dataset plus an independently maintained
Open Assembly client/catalog. A live provider sample is still required before L2 promotion because
the current execution boundary could not complete the external API probe.

The catalog's `free` value describes the provider endpoint's listed access cost. It does not
authorize a live request, credential provisioning, retention/redistribution or separately billable
infrastructure. Operation review and any deployment/resource-cost decision remain distinct human
gates; see the active research plan and [deployment preparation](../operations/EVIDENCE_PREVIEW_DEPLOYMENT.md).

This lane may classify a row as a **Gukgam schedule candidate** only when the provider's schedule
kind/content explicitly contains `국정감사`. That classification is discovery metadata, not a
published governance fact and not evidence for:

- audited-organization identity;
- institution/general witness identity;
- reference-person identity;
- a Person merge;
- committee-plan completeness.

The official Open API catalog exposes Gukgam meeting minutes and result/report families, but no
dedicated pre-audit plan, audited-organization, witness or reference-person operation was found in
the reviewed catalog. Those fields therefore remain under the committee-plan/reviewed-packet gate.

## Target bounded universe

The desired product universe remains:

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

The collection implementation must use an automation-permitted official route, such as a reviewed
National Assembly/open-data API or another officially documented interface. Search engines may
help discover official records but search-result text is not canonical evidence.

## Central official inspection portal discovery

The National Assembly Library's official local-parliament information page points users to the
current National Assembly inspection-data portal:

```text
https://www.assembly.go.kr/portal/cnts/cntsCont/dataA.do?cntsDivCd=INSPECT&menuNo=600236
```

and separately to the inspection information system:

```text
https://likms.assembly.go.kr/inspections/main.do
```

A bounded 2026-09-19 probe of `/robots.txt` on both `www.assembly.go.kr` and
`assembly.go.kr` returned `Bad Request` rather than a usable robots policy. That is **not**
interpreted as automation permission. Until a positive access contract is reviewed, use these
central pages for operator/discovery navigation only; do not build a repeated automated collector
against them.

The exact Science Committee PDF was subsequently supplied through the approved human-assisted
artifact boundary and verified against the reviewed packet. On 2026-09-20 the same bounded,
interactive-browser acquisition path captured exact plan PDFs for National Defense, Steering,
Public Administration and Security, Culture/Sports/Tourism, Agriculture/Food/Rural Affairs/Oceans,
Strategy and Finance, and Foreign Affairs and Unification. The first six of those additional plans
fit the existing reviewed-packet v1 schedule model and passed exact-artifact dry-run validation.
The Foreign Affairs and Unification plan is retained as an exact captured artifact only because its
overseas audit rows use multi-day date ranges that v1 cannot represent without information loss.
This does not change the automation decision for committee or central-portal HTML.

## Candidate stable locators

Source-level candidate:

```text
canonical detail URL + nttId
```

Attachment-level candidate:

```text
parent nttId + atchFileId + fileSn
```

The preview path is a locator, not permanent content identity. Correction/replacement semantics
remain open.

## Rights gate

Do not generalize a reuse notice visible on one National Assembly page to every attachment.

The reviewed Science Committee post visibly renders the KOGL Type-1 public-nuri mark. For content
reuse, the post supports attribution-based reuse under that displayed mark, subject to privacy,
third-party rights and other-law limits.

For automation, however, the host-level robots rule above controls the current collector decision.

Current v0 decision:

```text
official committee page as provenance/origin = permitted
manual/operator viewing for verification = permitted
repeated automated committee-site fetch = blocked
normalized schedule metadata via data.go.kr 15126132 = L1 contract staged; live sample pending
raw/full attachment storage = disabled
AI processing of raw attachment = disabled
public excerpt display = disabled
raw attachment republication = disabled
source attribution = required
```

## Privacy and identity

Witness/reference-person material may contain names and job titles. It does not authorize:

- name-only Person creation or linking;
- personal phone/email collection;
- precise residence collection;
- family discovery;
- raw attachment publication.

A witness row remains source-scoped until the existing identity gate resolves it.

## Next source task

Do **not** build a committee HTML scraper.

Continue the 17-standing-committee inventory through the same bounded interactive-browser acquisition
path. Exact official plan bytes are now captured for eight committees. Six newly reviewed packets
plus the existing Science packet pass v1 dry-run; Foreign Affairs and Unification remains
fail-closed at the packet boundary because of multi-day audit ranges.

For every remaining committee, use the central National Assembly inspection page only for
operator/discovery navigation, capture the exact official attachment before asserting schedule or
audited-target rows, and leave absence unresolved unless the official source affirmatively supports
another status. Search, press and broadcast records remain discovery-only.
