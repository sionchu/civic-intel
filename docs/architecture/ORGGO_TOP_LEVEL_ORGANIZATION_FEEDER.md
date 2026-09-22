# org.go Top-Level Organization Feeder

## Purpose

Stage the Ministry of the Interior and Safety Government Organization Management System
(`www.org.go.kr`) top-level institution-chart list as a credential-free official Organization
universe source. This source is independent from Gukgam text and therefore may support later
reviewed canonical Organization materialization without deriving identity from an audit schedule.

This lane does **not** create Organizations, Claims or Gukgam bindings by itself.

## Source contract

Reviewed 2026-09-22:

```text
host: www.org.go.kr
list route: /cop/bbs/getInstiChartList.do?pageIndex={n}
detail locator: openDetail(category, orgCode, chartId)
provider Organization key: seven-digit orgCode
current live total: 63 top-level institutions
robots.txt: Disallow: /search only
```

The current list spans these provider categories:

```text
중앙행정기관: 49
중앙행정기관에 준하는 기관: 8
헌법기관: 4
헌법상 자문기구: 1
기타: 1
```

## Rights and storage boundary

The public list is directly fetchable, but the site footer states `All rights reserved` and no
blanket reusable-data license was found during this review. V0 therefore uses the conservative
SourcePolicy:

- fetch allowed;
- normalized metadata storage allowed;
- raw/fulltext retention disabled;
- excerpt display disabled;
- AI transmission disabled;
- commercialization disabled.

Raw live HTML is not a canonical artifact. Verification retains only normalized row metadata,
provider counts and page content hashes.

## Record semantics

Each list row contributes only provider-authored metadata:

```text
organization_name
category
org_code
chart_id
```

`org_code` is a provider Organization key. It is not a Civic Intel Organization UUID and does not
authorize automatic Gukgam binding. `chart_id` is a provider detail locator only. Category labels
are stored verbatim; Civic Intel does not reinterpret them into a broader ontology at this stage.

The parser fails closed on malformed subject locators, duplicate provider codes/detail locators,
missing or ambiguous provider total count, missing required labels, and page row counts that exceed
the provider total.

## Live bounded proof

On 2026-09-22 the connector fetched the current list sequentially through seven pages:

```text
page rows: 10, 10, 10, 10, 10, 10, 3
total rows: 63
distinct org_code: 63
distinct organization_name: 63
```

Per-page HTML SHA-256 receipts were:

```text
1  60c841837a2aa2eac008592531357f2bca99060781b2506e74c35d493d503994
2  b992dbeefe6f15c58eb19efb9e9138a5c8b6ee2eb5638331f7d6f624322cfa11
3  609bd69bd7155dc74a68b6728cf7652f389a3ef60b2e6277250ad4297314ecfb
4  761a9963e6e65d455e2e467c779e1725113fbd7d9ad761e163006a6d5bcbebe5
5  eee631294c41b17153a69cb08688ab0893c18b99c10407c4d250892cc78a36e0
6  be7e4d51534ae65669942cccb8a75db097699808348edff5b5165e99b7402a40
7  b5d61ca2d317c54e2a7378865de8b39b580d5d95239bf6cbeb9e20e9fd3068dd
```

Comparing only exact provider names against the current Gukgam `NO_EXACT` planning set produced
`27` distinct label overlaps covering `41` occurrences. This comparison is planning evidence only;
it does not create Organizations or convert those occurrences into published targets.

## Maturity ceiling

Current maturity is **L2 SINGLE_PULL**. The connector and live bounded pull are proven, but there is
no persistent SourceRun/checkpoint/resume/idempotent enumeration contract for this lane. L3 requires
a separate implementation slice. Any canonical Organization materialization requires an explicit
reviewed proposal contract and must remain separate from Gukgam publication logic.
